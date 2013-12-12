import json
from time import gmtime, strftime

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.utils.functional import lazy
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt

from commonware.response.decorators import xframe_allow

import django_filters

from snippets.base.decorators import access_control
from snippets.base.encoders import SnippetEncoder
from snippets.base.models import Client, JSONSnippet, Snippet, SnippetTemplate
from snippets.base.util import get_object_or_none


_http_max_age = lambda: getattr(settings, 'SNIPPET_HTTP_MAX_AGE', 90)
HTTP_MAX_AGE = lazy(_http_max_age, str)()
SNIPPETS_PER_PAGE = 50


class SnippetFilter(django_filters.FilterSet):

    class Meta:
        model = Snippet
        fields = ['on_release', 'on_beta', 'on_aurora', 'on_nightly',
                  'template']


def index(request):
    snippets = Snippet.objects.filter(disabled=False)
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
    pagination_range = range(max(1, snippets.number-2),
                             min(snippets.number+3, paginator.num_pages+1))
    data = {'snippets': snippets,
            'pagination_range': pagination_range,
            'snippetsfilter': snippetsfilter}
    return render(request, 'base/index.html', data)


@cache_control(public=True, max_age=HTTP_MAX_AGE)
@access_control(max_age=HTTP_MAX_AGE)
def fetch_snippets(request, **kwargs):
    client = Client(**kwargs)
    matching_snippets = (Snippet.cached_objects
                         .filter(disabled=False)
                         .match_client(client)
                         .order_by('priority')
                         .select_related('template')
                         .filter_by_available())

    return render(request, 'base/fetch_snippets.html', {
        'snippets': matching_snippets,
        'client': client,
        'current_time': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        'locale': client.locale,
    })


@cache_control(public=True, max_age=HTTP_MAX_AGE)
@access_control(max_age=HTTP_MAX_AGE)
def fetch_json_snippets(request, **kwargs):
    client = Client(**kwargs)
    matching_snippets = (JSONSnippet.cached_objects
                         .filter(disabled=False)
                         .match_client(client)
                         .order_by('priority')
                         .filter_by_available())
    return HttpResponse(json.dumps(matching_snippets, cls=SnippetEncoder),
                        mimetype='application/json')


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
    return render(request, 'base/preview.html', {
        'snippet': snippet,
        'client': PREVIEW_CLIENT,
        'preview': True
    })


def show_snippet(request, snippet_id):
    snippet = get_object_or_404(Snippet, pk=snippet_id, disabled=False)
    return render(request, 'base/preview.html', {
        'snippet': snippet,
        'client': PREVIEW_CLIENT,
        'preview': True
    })
