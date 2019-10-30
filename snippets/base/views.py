import json
from urllib.parse import urljoin, urlparse

from distutils.util import strtobool
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.functional import lazy
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

import sentry_sdk
from django_filters.views import FilterView
from django_statsd.clients import statsd

from snippets.base import util
from snippets.base.bundles import ASRSnippetBundle, SnippetBundle
from snippets.base.decorators import access_control
from snippets.base.filters import JobFilter
from snippets.base.models import CHANNELS, ASRSnippet, Client, Snippet, SnippetTemplate
from snippets.base.util import get_object_or_none


def _bundle_timeout():
    return getattr(settings, 'SNIPPET_BUNDLE_TIMEOUT')
SNIPPET_BUNDLE_TIMEOUT = lazy(_bundle_timeout, int)()  # noqa


class HomeView(TemplateView):
    template_name = 'base/home.jinja'


class JobListView(FilterView):
    filterset_class = JobFilter

    @property
    def template_name(self):
        if self.request.GET.get('calendar', 'false') == 'true':
            return 'base/jobs_list_calendar.jinja'

        return 'base/jobs_list_table.jinja'


def fetch_snippets(request, **kwargs):
    if settings.USE_PREGEN_BUNDLES and kwargs['startpage_version'] == 6:
        return fetch_snippet_pregen_bundle(request, **kwargs)
    return fetch_snippet_bundle(request, **kwargs)


@cache_control(public=True, max_age=settings.SNIPPET_BUNDLE_PREGEN_REDIRECT_TIMEOUT)
def fetch_snippet_pregen_bundle(request, **kwargs):
    statsd.incr('serve.bundle_pregen')
    client = Client(**kwargs)
    product = 'Firefox'
    channel = client.channel.lower()
    channel = next((item for item in CHANNELS if channel.startswith(item)), None) or 'release'
    locale = client.locale.lower()

    # Distribution populated by client's distribution if it starts with
    # `experiment-`. Otherwise default to `default`.
    #
    # This is because non-Mozilla distributors of Firefox (e.g. Linux
    # Distributions) override the distribution field with their identification.
    # We want all Firefox clients to get the default bundle for the locale /
    # channel combination, unless they are part of an experiment.
    distribution = client.distribution.lower()
    if distribution.startswith('experiment-'):
        distribution = distribution[11:]
    else:
        distribution = 'default'

    filename = (
        f'{settings.MEDIA_BUNDLES_PREGEN_ROOT}/{product}/{channel}/'
        f'{locale}/{distribution}.json'
    )

    full_url = urljoin(settings.CDN_URL or settings.SITE_URL,
                       urlparse(default_storage.url(filename)).path)
    # Remove AWS S3 parameters
    full_url = full_url.split('?')[0]

    return HttpResponseRedirect(full_url)


@cache_control(public=True, max_age=SNIPPET_BUNDLE_TIMEOUT)
@access_control(max_age=SNIPPET_BUNDLE_TIMEOUT)
def fetch_snippet_bundle(request, **kwargs):
    """
    Return one of the following responses:
    - 200 with empty body when the bundle is empty
    - 302 to a bundle URL after generating it if not cached.
    """
    statsd.incr('serve.snippets')

    client = Client(**kwargs)
    if client.startpage_version == 6:
        bundle = ASRSnippetBundle(client)
    else:
        bundle = SnippetBundle(client)
    if bundle.empty:
        statsd.incr('bundle.empty')

        if client.startpage_version == 6:
            # Return valid JSON for Activity Stream Router
            return HttpResponse(status=200, content='{}', content_type='application/json')

        # This is not a 204 because Activity Stream expects content, even if
        # it's empty.
        return HttpResponse(status=200, content='')
    elif bundle.cached:
        statsd.incr('bundle.cached')
    else:
        statsd.incr('bundle.generate')
        bundle.generate()

    return HttpResponseRedirect(bundle.url)


def preview_asr_snippet(request, uuid):
    try:
        snippet = get_object_or_404(ASRSnippet, uuid=uuid)
    except ValidationError:
        # Raised when UUID is a badly formed hexadecimal UUID string
        raise Http404()

    bundle_content = json.dumps({
        'messages': [snippet.render(preview=True)],
    })
    return HttpResponse(bundle_content, content_type='application/json')


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
        preview_client = Client(5, 'Firefox', '57.0', 'default', 'default', 'en-US',
                                'release', 'default', 'default', 'default')
    else:
        template_name = 'base/preview.jinja'
        preview_client = Client(4, 'Firefox', '24.0', 'default', 'default', 'en-US',
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
    preview_client = Client(4, 'Firefox', '24.0', 'default', 'default', 'en-US',
                            'release', 'default', 'default', 'default')

    if uuid:
        snippet = get_object_or_404(Snippet, uuid=snippet_id)
    else:
        snippet = get_object_or_404(Snippet, pk=snippet_id)
        if not snippet.published and not request.user.is_authenticated:
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

    with sentry_sdk.configure_scope() as scope:
        scope.level = 'info'
        scope.set_tag('logger', 'csp')

        sentry_sdk.capture_message(
            message='CSP Violation: {}'.format(blocked_uri))

    return HttpResponse('Captured CSP violation, thanks for reporting.')
