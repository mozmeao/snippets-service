import json

import sentry_sdk
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import (Http404, HttpResponse, HttpResponseBadRequest,
                         HttpResponseRedirect)
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from django_filters.views import FilterView
from ratelimit.decorators import ratelimit

from redirector.redirect import calculate_redirect
from snippets.base.bundles import generate_bundles
from snippets.base.filters import JobFilter
from snippets.base.models import ASRSnippet


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

    return fetch_snippet_pregen_bundle(request, **kwargs)


@cache_control(public=True, max_age=settings.SNIPPET_BUNDLE_PREGEN_REDIRECT_TIMEOUT)
def fetch_snippet_pregen_bundle(request, **kwargs):
    locale, distribution, full_url = calculate_redirect(locale=kwargs['locale'],
                                                        distribution=kwargs['distribution'])

    if settings.INSTANT_BUNDLE_GENERATION:
        content = generate_bundles(
            limit_to_locale=locale,
            limit_to_distribution_bundle=distribution,
            save_to_disk=False
        )
        return HttpResponse(status=200, content=content, content_type='application/json')

    return HttpResponseRedirect(full_url)


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
