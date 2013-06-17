import json
from datetime import datetime
from time import gmtime, strftime

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt

from commonware.response.decorators import xframe_allow

import django_filters

from snippets.base.decorators import access_control
from snippets.base.models import (Client, ClientMatchRule, Snippet,
                                  SnippetTemplate)
from snippets.base.util import get_object_or_none


HTTP_MAX_AGE = getattr(settings, 'SNIPPET_HTTP_MAX_AGE', 1)
SNIPPETS_PER_PAGE = 25


class SnippetFilter(django_filters.FilterSet):

    class Meta:
        model = Snippet
        fields = ['on_release', 'on_beta', 'on_aurora', 'on_nightly',
                  'on_firefox', 'on_fennec', 'template']


def index(request):
    snippets = Snippet.objects.all()
    snippetsfilter = SnippetFilter(request.GET, snippets)
    paginator = Paginator(snippetsfilter.qs, SNIPPETS_PER_PAGE)

    page = request.GET.get('page', 1)
    try:
        snippets = paginator.page(page)
    except PageNotAnInteger:
        snippets = paginator.page(1)
    except EmptyPage:
        snippets = paginator.page(paginator.num_pages)

    # Display links to the page before and after the current page when
    # applicable.
    pagination_range = range(max(1, snippets.number-1),
                             min(snippets.number+2, paginator.num_pages+1))
    data = {'snippets': snippets,
            'pagination_range': pagination_range,
            'snippetsfilter': snippetsfilter}
    return render(request, 'base/index.html', data)


@cache_control(public=True, max_age=HTTP_MAX_AGE)
@access_control(max_age=HTTP_MAX_AGE)
def fetch_snippets(request, **kwargs):
    client = Client(**kwargs)

    matching_snippets = (Snippet.objects.match_client(client)
                         .order_by('priority'))

    passed_rules, failed_rules = (ClientMatchRule.objects
                                  .filter(snippet__in=matching_snippets)
                                  .evaluate(client))
    matching_snippets = (matching_snippets
                         .exclude(client_match_rules__in=failed_rules))

    # Filter by date in python to avoid caching based on the passing of time.
    now = datetime.utcnow()
    matching_snippets = [
        snippet for snippet in matching_snippets if
        (not snippet.publish_start or snippet.publish_start <= now) and
        (not snippet.publish_end or snippet.publish_end >= now)
    ]

    return render(request, 'base/fetch_snippets.html', {
        'snippets': matching_snippets,
        'client': client,
        'current_time': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())
    })


PREVIEW_CLIENT = Client('4', 'Firefox', '24.0', 'default', 'default', 'en-US',
                        'release', 'default', 'default', 'default')


@xframe_allow
@csrf_exempt
@permission_required('base.change_snippet')
def preview_snippet(request):
    """
    Build a snippet using info from the POST parameters, and preview that
    snippet on a mock about:home page.
    """
    template_id = request.POST.get('template_id', None)
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
    return render(request, 'base/preview.html', {
        'snippet': snippet,
        'client': PREVIEW_CLIENT
    })
