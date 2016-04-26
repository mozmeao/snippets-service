import hashlib
import json

from distutils.util import strtobool

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.cache import patch_vary_headers
from django.utils.functional import lazy
from django.views.generic import TemplateView, View
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt

import django_filters
from product_details import product_details
from product_details.version_compare import version_list

from snippets.base.decorators import access_control
from snippets.base.encoders import ActiveSnippetsEncoder, JSONSnippetEncoder
from snippets.base.models import Client, JSONSnippet, Snippet, SnippetBundle, SnippetTemplate
from snippets.base.util import get_object_or_none


def _http_max_age():
    return getattr(settings, 'SNIPPET_HTTP_MAX_AGE', 90)
HTTP_MAX_AGE = lazy(_http_max_age, str)()


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
        self.snippets = (Snippet.cached_objects
                         .filter(disabled=False)
                         .prefetch_related('locales', 'countries',
                                           'exclude_from_search_providers'))
        self.snippetsfilter = SnippetFilter(request.GET, self.snippets)
        return self.render(request, *args, **kwargs)


class JSONSnippetIndexView(IndexView):
    template_name = 'base/index-json.jinja'

    def get(self, request, *args, **kwargs):
        self.snippets = (JSONSnippet.cached_objects
                         .filter(disabled=False)
                         .prefetch_related('locales', 'countries'))
        self.snippetsfilter = JSONSnippetFilter(request.GET, self.snippets)
        return self.render(request, *args, **kwargs)


@cache_control(public=True, max_age=settings.SNIPPET_BUNDLE_TIMEOUT)
@access_control(max_age=settings.SNIPPET_BUNDLE_TIMEOUT)
def fetch_pregenerated_snippets(request, **kwargs):
    """
    Return a redirect to a pre-generated bundle of snippets for the
    client. If the bundle in question is expired, re-generate it.
    """
    client = Client(**kwargs)
    bundle = SnippetBundle(client)
    if bundle.expired:
        bundle.generate()

    return HttpResponseRedirect(bundle.url)


@cache_control(public=True, max_age=HTTP_MAX_AGE)
@access_control(max_age=HTTP_MAX_AGE)
def fetch_render_snippets(request, **kwargs):
    """Fetch snippets for the client and render them immediately."""
    client = Client(**kwargs)
    matching_snippets = (Snippet.cached_objects
                         .filter(disabled=False)
                         .match_client(client)
                         .order_by('priority')
                         .select_related('template')
                         .filter_by_available())

    current_firefox_version = (
        version_list(product_details.firefox_history_major_releases)[0].split('.', 1)[0])
    response = render(request, 'base/fetch_snippets.jinja', {
        'snippet_ids': [snippet.id for snippet in matching_snippets],
        'snippets_json': json.dumps([s.to_dict() for s in matching_snippets]),
        'client': client,
        'locale': client.locale,
        'current_firefox_version': current_firefox_version
    })

    # ETag will be a hash of the response content.
    response['ETag'] = hashlib.sha256(response.content).hexdigest()
    patch_vary_headers(response, ['If-None-Match'])

    return response


def fetch_snippets(request, **kwargs):
    """Determine which snippet-fetching method to use."""
    if settings.SERVE_SNIPPET_BUNDLES:
        return fetch_pregenerated_snippets(request, **kwargs)
    else:
        return fetch_render_snippets(request, **kwargs)


@cache_control(public=True, max_age=HTTP_MAX_AGE)
@access_control(max_age=HTTP_MAX_AGE)
def fetch_json_snippets(request, **kwargs):
    client = Client(**kwargs)
    matching_snippets = (JSONSnippet.cached_objects
                         .filter(disabled=False)
                         .match_client(client)
                         .order_by('priority')
                         .filter_by_available())
    return HttpResponse(json.dumps(matching_snippets, cls=JSONSnippetEncoder),
                        content_type='application/json')


PREVIEW_CLIENT = Client('4', 'Firefox', '24.0', 'default', 'default', 'en-US',
                        'release', 'default', 'default', 'default')


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

    skip_boilerplate = request.POST.get('skip_boilerplate', 'false')
    skip_boilerplate = strtobool(skip_boilerplate)

    template_name = 'base/preview_without_shell.jinja' if skip_boilerplate else 'base/preview.jinja'
    current_firefox_version = (
        version_list(product_details.firefox_history_major_releases)[0].split('.', 1)[0])

    return render(request, template_name, {
        'snippets_json': json.dumps([snippet.to_dict()]),
        'client': PREVIEW_CLIENT,
        'preview': True,
        'current_firefox_version': current_firefox_version,
    })


def show_snippet(request, snippet_id):
    snippet = get_object_or_404(Snippet, pk=snippet_id)
    if snippet.disabled and not request.user.is_authenticated():
        raise Http404()

    current_firefox_version = (
        version_list(product_details.firefox_history_major_releases)[0].split('.', 1)[0])
    return render(request, 'base/preview.jinja', {
        'snippets_json': json.dumps([snippet.to_dict()]),
        'client': PREVIEW_CLIENT,
        'preview': True,
        'current_firefox_version': current_firefox_version,
    })


class ActiveSnippetsView(View):
    def get(self, request):
        snippets = (list(Snippet.cached_objects.filter(disabled=False)) +
                    list(JSONSnippet.cached_objects.filter(disabled=False)))
        return HttpResponse(json.dumps(snippets, cls=ActiveSnippetsEncoder),
                            content_type='application/json')
