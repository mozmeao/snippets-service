from datetime import timedelta
from urlparse import urlparse

from django.conf import settings

from django_ical.views import ICalFeed
from snippets.base.models import Snippet


class EnabledSnippetsFeed(ICalFeed):
    product_id = '//{}/EnabledSnippets'.format(urlparse(settings.SITE_URL).netloc)
    timezone = 'UTC'
    title = 'Snippets (enabled)'

    def items(self):
        return Snippet.objects.exclude(published=False).order_by('publish_start')

    def item_title(self, item):
        return item.name

    def item_description(self, item):
        return item.name

    def item_start_datetime(self, item):
        return item.publish_start or item.created

    def item_end_datetime(self, item):
        return item.publish_end or (self.item_start_datetime(item) + timedelta(days=365))

    def item_created(self, item):
        return item.created

    def item_updateddate(self, item):
        return item.modified
