from time import gmtime, strftime

from django.conf import settings
from django.shortcuts import render
from django.views.decorators.cache import cache_control

from snippets.base.decorators import access_control
from snippets.base.models import Client, ClientMatchRule, Snippet


HTTP_MAX_AGE = getattr(settings, 'SNIPPET_HTTP_MAX_AGE', 1)


def index(request):
    return render(request, 'base/index.html')


@cache_control(public=True, max_age=HTTP_MAX_AGE)
@access_control(max_age=HTTP_MAX_AGE)
def fetch_snippets(request, **kwargs):
    client = Client(**kwargs)

    matching_snippets = Snippet.objects.match_client(client)
    passed_rules, failed_rules = (ClientMatchRule.objects
                                  .filter(snippet__in=matching_snippets)
                                  .evaluate(client))

    matching_snippets = (matching_snippets
                         .exclude(client_match_rules__in=failed_rules))

    return render(request, 'base/fetch_snippets.html', {
        'snippets': matching_snippets,
        'current_time': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())
    })
