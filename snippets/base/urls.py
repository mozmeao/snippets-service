from django.urls import path

from watchman import views as watchman_views

from snippets.base import views
from snippets.base import feed


urlpatterns = [
    path('', views.HomeView.as_view()),
    path('<int:startpage_version>/<name>/<version>/<appbuildid>/<build_target>/'
         '<locale>/<channel>/<os_version>/<distribution>/<distribution_version>/',
         views.fetch_snippets, name='base.fetch_snippets'),
    path('preview/', views.preview_snippet, name='base.preview'),
    path('preview-asr/<str:uuid>/', views.preview_asr_snippet, name='asr-preview'),
    path('show/<int:snippet_id>/', views.show_snippet, name='base.show'),
    path('show/uuid/<str:snippet_id>/', views.show_snippet, {'uuid': True}, name='base.show_uuid'),
    path('csp-violation-capture', views.csp_violation_capture, name='csp-violation-capture'),
    path('healthz/', watchman_views.ping, name='watchman.ping'),
    path('readiness/', watchman_views.status, name='watchman.status'),
    path('feeds/snippets.ics', feed.SnippetsFeed(), name='ical-feed'),
]
