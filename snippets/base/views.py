import json
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.functional import lazy
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

import sentry_sdk
from django_filters.views import FilterView
from django_statsd.clients import statsd
from ratelimit.decorators import ratelimit

from snippets.base.bundles import ASRSnippetBundle
from snippets.base.decorators import access_control
from snippets.base.filters import JobFilter
from snippets.base.models import CHANNELS, ASRSnippet, Client


def _bundle_timeout():
    return getattr(settings, 'SNIPPET_BUNDLE_TIMEOUT')
SNIPPET_BUNDLE_TIMEOUT = lazy(_bundle_timeout, int)()  # noqa


class HomeView(TemplateView):
    template_name = 'base/home.jinja'


class JobListView(FilterView):
    filterset_class = JobFilter

    @ratelimit(rate=settings.RATELIMIT_RATE, block=True,
               key=lambda g, r: r.META.get('HTTP_X_FORWARDED_FOR', r.META['REMOTE_ADDR']))
    def get(self, request, **kwargs):
        return super().get(request, **kwargs)

    @property
    def template_name(self):
        if self.request.GET.get('calendar', 'false') == 'true':
            return 'base/jobs_list_calendar.jinja'

        return 'base/jobs_list_table.jinja'


def fetch_snippets(request, **kwargs):
    if kwargs['startpage_version'] != 6:
        raise Http404()

    if settings.USE_PREGEN_BUNDLES:
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
    bundle = ASRSnippetBundle(client)
    if bundle.empty:
        statsd.incr('bundle.empty')
        # Return valid JSON for Activity Stream Router
        return HttpResponse(status=200, content='{}', content_type='application/json')
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
