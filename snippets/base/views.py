import json
import logging

from distutils.util import strtobool

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.functional import lazy
from django.views.generic import TemplateView
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import django_filters
from django_statsd.clients import statsd
from raven.contrib.django.models import client as sentry_client

from snippets.base import util
from snippets.base.decorators import access_control
from snippets.base.encoders import JSONSnippetEncoder
from snippets.base.models import Client, JSONSnippet, Snippet, SnippetBundle, SnippetTemplate
from snippets.base.util import get_object_or_none


def _bundle_timeout():
    return getattr(settings, 'SNIPPET_BUNDLE_TIMEOUT')
SNIPPET_BUNDLE_TIMEOUT = lazy(_bundle_timeout, int)()  # noqa


class SnippetFilter(django_filters.FilterSet):

    class Meta:
        model = Snippet
        fields = ['on_release', 'on_beta', 'on_aurora', 'on_nightly',
                  'template']


class JSONSnippetFilter(django_filters.FilterSet):

    class Meta:
        model = JSONSnippet
        fields = ['on_release', 'on_beta', 'on_aurora', 'on_nightly']


class IndexView(TemplateView):
    def render(self, request, *args, **kwargs):
        paginator = Paginator(self.snippetsfilter.qs, settings.SNIPPETS_PER_PAGE)

        page = request.GET.get('page', 1)
        try:
            snippets = paginator.page(page)
        except PageNotAnInteger:
            snippets = paginator.page(1)
        except EmptyPage:
            snippets = paginator.page(paginator.num_pages)

        # Display links to the page before and after the current page when
        # applicable.
        pagination_range = range(max(1, snippets.number-2),
                                 min(snippets.number+3, paginator.num_pages+1))
        data = {'snippets': snippets,
                'pagination_range': pagination_range,
                'snippetsfilter': self.snippetsfilter}
        return render(request, self.template_name, data)


class SnippetIndexView(IndexView):
    template_name = 'base/index.jinja'

    def get(self, request, *args, **kwargs):
        self.snippets = (Snippet.objects
                         .filter(disabled=False)
                         .prefetch_related('locales', 'countries',
                                           'exclude_from_search_providers'))
        self.snippetsfilter = SnippetFilter(request.GET, self.snippets)
        return self.render(request, *args, **kwargs)


class JSONSnippetIndexView(IndexView):
    template_name = 'base/index-json.jinja'

    def get(self, request, *args, **kwargs):
        self.snippets = (JSONSnippet.objects
                         .filter(disabled=False)
                         .prefetch_related('locales', 'countries'))
        self.snippetsfilter = JSONSnippetFilter(request.GET, self.snippets)
        return self.render(request, *args, **kwargs)


@cache_control(public=True, max_age=SNIPPET_BUNDLE_TIMEOUT)
@access_control(max_age=SNIPPET_BUNDLE_TIMEOUT)
def fetch_snippets(request, **kwargs):
    """
    Return a redirect to a pre-generated bundle of snippets for the
    client. If the bundle in question is expired, re-generate it.
    """
    statsd.incr('serve.snippets')

    client = Client(**kwargs)
    bundle = SnippetBundle(client)
    if not bundle.cached:
        bundle.generate()
        statsd.incr('bundle.generate')
    else:
        statsd.incr('bundle.cached')

    return HttpResponseRedirect(bundle.url)


@cache_control(public=True, max_age=SNIPPET_BUNDLE_TIMEOUT)
@access_control(max_age=SNIPPET_BUNDLE_TIMEOUT)
def fetch_json_snippets(request, **kwargs):
    statsd.incr('serve.json_snippets')
    client = Client(**kwargs)
    matching_snippets = (JSONSnippet.objects
                         .filter(disabled=False)
                         .match_client(client)
                         .filter_by_available())
    return HttpResponse(json.dumps(matching_snippets, cls=JSONSnippetEncoder),
                        content_type='application/json')


@csrf_exempt
@permission_required('base.change_snippet')
def preview_snippet(request):
    """
    Build a snippet using info from the POST parameters, and preview that
    snippet on a mock about:home page.
    """
    try:
        template_id = int(request.POST.get('template_id', None))
    except (TypeError, ValueError):
        return HttpResponseBadRequest()

    template = get_object_or_none(SnippetTemplate, id=template_id)
    data = request.POST.get('data', None)

    # Validate that data is JSON.
    try:
        json.loads(data)
    except (TypeError, ValueError):
        data = None

    # If your parameters are wrong, I have no sympathy for you.
    if data is None or template is None:
        return HttpResponseBadRequest()

    # Build a snippet that isn't saved so we can render it.
    snippet = Snippet(template=template, data=data)

    if strtobool(request.POST.get('activity_stream', 'false')):
        template_name = 'base/preview_as.jinja'
        preview_client = Client('5', 'Firefox', '57.0', 'default', 'default', 'en-US',
                                'release', 'default', 'default', 'default')
    else:
        template_name = 'base/preview.jinja'
        preview_client = Client('4', 'Firefox', '24.0', 'default', 'default', 'en-US',
                                'release', 'default', 'default', 'default')

    skip_boilerplate = request.POST.get('skip_boilerplate', 'false')
    skip_boilerplate = strtobool(skip_boilerplate)
    if skip_boilerplate:
        template_name = 'base/preview_without_shell.jinja'

    return render(request, template_name, {
        'snippets_json': json.dumps([snippet.to_dict()]),
        'client': preview_client,
        'preview': True,
        'current_firefox_major_version': util.current_firefox_major_version(),
    })


def show_snippet(request, snippet_id, uuid=False):
    preview_client = Client('4', 'Firefox', '24.0', 'default', 'default', 'en-US',
                            'release', 'default', 'default', 'default')

    if uuid:
        snippet = get_object_or_404(Snippet, uuid=snippet_id)
    else:
        snippet = get_object_or_404(Snippet, pk=snippet_id)
        if snippet.disabled and not request.user.is_authenticated():
            raise Http404()

    template = 'base/preview.jinja'
    if snippet.on_startpage_5:
        template = 'base/preview_as.jinja'
    return render(request, template, {
        'snippets_json': json.dumps([snippet.to_dict()]),
        'client': preview_client,
        'preview': True,
        'current_firefox_major_version': util.current_firefox_major_version(),
    })


@csrf_exempt
@require_POST
def csp_violation_capture(request):
    data = sentry_client.get_data_from_request(request)
    data.update({
        'level': logging.INFO,
        'logger': 'CSP',
    })
    try:
        csp_data = json.loads(request.body)
    except ValueError:
        # Cannot decode CSP violation data, ignore
        return HttpResponseBadRequest('Invalid CSP Report')

    try:
        blocked_uri = csp_data['csp-report']['blocked-uri']
    except KeyError:
        # Incomplete CSP report
        return HttpResponseBadRequest('Incomplete CSP Report')

    sentry_client.captureMessage(
        message='CSP Violation: {}'.format(blocked_uri),
        data=data)

    return HttpResponse('Captured CSP violation, thanks for reporting.')


@cache_page(5)
def healthz(request):
    """For use with Healthchecks. Wrapped with cache_page to test cache."""
    assert Snippet.objects.exists(), 'No snippets exist'
    return HttpResponse('OK')
