from django.conf.urls.defaults import patterns, url


def test_view(request):
    return 'test'


def test_view_skip_middleware(request):
    return 'skipped'


urlpatterns = patterns('',
    url(r'^test$', test_view),
    url(r'^test_skip$', test_view_skip_middleware, {'skip_middleware': True}),
)

