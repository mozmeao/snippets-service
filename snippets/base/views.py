import json
from time import gmtime, strftime

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.cache import cache_control

from commonware.response.decorators import xframe_allow

from snippets.base.decorators import access_control
from snippets.base.models import (Client, ClientMatchRule, Snippet,
                                  SnippetTemplate)
from snippets.base.util import get_object_or_none


HTTP_MAX_AGE = getattr(settings, 'SNIPPET_HTTP_MAX_AGE', 1)


def index(request):
    return render(request, 'base/index.html')


@cache_control(public=True, max_age=HTTP_MAX_AGE)
@access_control(max_age=HTTP_MAX_AGE)
def fetch_snippets(request, **kwargs):
    client = Client(**kwargs)

    passed_rules, failed_rules = ClientMatchRule.objects.all().evaluate(client)
    matching_snippets = Snippet.objects.exclude(
        client_match_rules__in=failed_rules
    )

    return render(request, 'base/fetch_snippets.html', {
        'snippets': matching_snippets,
        'client': client,
        'current_time': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())
    })


PREVIEW_CLIENT = Client('4', 'Firefox', '24.0', 'default', 'default', 'en-US',
                        'release', 'default', 'default', 'default')


@xframe_allow
@permission_required('base.change_snippet')
def preview_snippet(request):
    """
    Build a snippet using info from the GET parameters, and preview that
    snippet on a mock about:home page.
    """
    template_id = request.GET.get('template_id', None)
    template = get_object_or_none(SnippetTemplate, id=template_id)
    data = request.GET.get('data', None)

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
    return render(request, 'base/preview.html', {
        'snippet': snippet,
        'client': PREVIEW_CLIENT
    })
