from django.conf.urls import url

from watchman import views as watchman_views

from snippets.base import views
from snippets.base.feed import EnabledSnippetsFeed


urlpatterns = [
    url(r'^$', views.SnippetIndexView.as_view(), name='base.index'),
    url(r'^(?P<startpage_version>[^/]+)/(?P<name>[^/]+)/(?P<version>[^/]+)/'
        '(?P<appbuildid>[^/]+)/(?P<build_target>[^/]+)/(?P<locale>[^/]+)/'
        '(?P<channel>[^/]+)/(?P<os_version>[^/]+)/(?P<distribution>[^/]+)/'
        '(?P<distribution_version>[^/]+)/$', views.fetch_snippets,
        name='base.fetch_snippets'),
    url(r'^json/(?P<startpage_version>[^/]+)/(?P<name>[^/]+)/'
        '(?P<version>[^/]+)/(?P<appbuildid>[^/]+)/(?P<build_target>[^/]+)/'
        '(?P<locale>[^/]+)/(?P<channel>[^/]+)/(?P<os_version>[^/]+)/'
        '(?P<distribution>[^/]+)/(?P<distribution_version>[^/]+)/$',
        views.fetch_json_snippets, name='base.fetch_json_snippets'),
    url(r'^preview/$', views.preview_snippet, name='base.preview'),
    url(r'^show/(?P<snippet_id>\d+)/$', views.show_snippet, name='base.show'),
    url(r'^show/uuid/(?P<snippet_id>[\w-]+)/$', views.show_snippet,
        {'uuid': True}, name='base.show_uuid'),
    url(r'^json-snippets/', views.JSONSnippetIndexView.as_view(), name='base.index_json'),
    url(r'^csp-violation-capture$', views.csp_violation_capture,
        name='csp-violation-capture'),
    url(r'^healthz/$', watchman_views.ping, name="watchman.ping"),
    url(r'^readiness/$', watchman_views.status, name="watchman.status"),
    url(r'^feeds/snippets-enabled.ics$', EnabledSnippetsFeed()),
]
