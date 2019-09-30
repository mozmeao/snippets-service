from datetime import timedelta
from textwrap import dedent
from urllib.parse import urlparse

from django.conf import settings
from django.db.models import Q

from django_ical.views import ICalFeed

from snippets.base import filters, models


class JobsFeed(ICalFeed):
    timezone = 'UTC'
    title = 'Snippet Jobs'

    def __call__(self, request, *args, **kwargs):
        self.request = request
        return super().__call__(request, *args, **kwargs)

    @property
    def product_id(self):
        return '//{}/SnippetJobs?{}'.format(urlparse(settings.SITE_URL).netloc,
                                            self.request.GET.urlencode())

    def items(self):
        queryset = (models.Job.objects
                    .filter(Q(status=models.Job.PUBLISHED) | Q(status=models.Job.SCHEDULED))
                    .order_by('publish_start'))
        filtr = filters.JobFilter(self.request.GET, queryset=queryset)
        return filtr.qs

    def item_title(self, item):
        return item.snippet.name

    def item_link(self, item):
        return item.get_admin_url()

    def item_description(self, item):
        description = dedent('''\
        Channels: {}
        Locale: {}'
        Preview Link: {}
        '''.format(', '.join(item.channels),
                   item.snippet.locale,
                   item.snippet.get_preview_url()))
        return description

    def item_start_datetime(self, item):
        return item.publish_start or item.created

    def item_end_datetime(self, item):
        return item.publish_end or (self.item_start_datetime(item) + timedelta(days=365))

    def item_created(self, item):
        return item.created

    def item_updateddate(self, item):
        return item.modified
