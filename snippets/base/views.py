import json
import logging

from distutils.util import strtobool

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.functional import lazy
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from django_statsd.clients import statsd
from raven.contrib.django.models import client as sentry_client

from snippets.base import util
from snippets.base.bundles import ASRSnippetBundle, SnippetBundle
from snippets.base.decorators import access_control
from snippets.base.encoders import JSONSnippetEncoder
from snippets.base.models import ASRSnippet, Client, JSONSnippet, Snippet, SnippetTemplate
from snippets.base.util import get_object_or_none


def _bundle_timeout():
    return getattr(settings, 'SNIPPET_BUNDLE_TIMEOUT')
SNIPPET_BUNDLE_TIMEOUT = lazy(_bundle_timeout, int)()  # noqa


class HomeView(TemplateView):
    template_name = 'base/home.jinja'


@cache_control(public=True, max_age=SNIPPET_BUNDLE_TIMEOUT)
@access_control(max_age=SNIPPET_BUNDLE_TIMEOUT)
def fetch_snippets(request, **kwargs):
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
        # This is not a 204 because Activity Stream expects content, even if
        # it's empty.
        return HttpResponse(status=200, content='')
    elif bundle.cached:
        statsd.incr('bundle.cached')
    else:
        statsd.incr('bundle.generate')
        bundle.generate()

    return HttpResponseRedirect(bundle.url)


@cache_control(public=True, max_age=SNIPPET_BUNDLE_TIMEOUT)
@access_control(max_age=SNIPPET_BUNDLE_TIMEOUT)
def fetch_json_snippets(request, **kwargs):
    statsd.incr('serve.json_snippets')
    client = Client(**kwargs)
    matching_snippets = (JSONSnippet.objects
                         .filter(published=True)
                         .match_client(client)
                         .filter_by_available())
    return HttpResponse(json.dumps(matching_snippets, cls=JSONSnippetEncoder),
                        content_type='application/json')


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
