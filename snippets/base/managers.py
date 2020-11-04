from django.db.models import Q
from django.db.models.query import QuerySet

from snippets.base.util import first


class JobQuerySet(QuerySet):
    def match_client(self, client):
        from snippets.base.models import CHANNELS, Target

        # Retrieve the first channel that starts with the client's channel.
        # Allows things like "release-cck-mozilla14" to match "release".
        if client.channel == 'default':
            client_channel = 'nightly'
        else:
            client_channel = first(CHANNELS, client.channel.startswith) or 'release'

        targets = Target.objects.filter(**{'on_{0}'.format(client_channel): True}).distinct()

        # Include both Jobs with Snippets targeted at the specific full locale (e.g.
        # en-us) but also Snippets targeted to all territories (en)
        full_locale = ',{},'.format(client.locale.lower())
        splitted_locale = ',{},'.format(client.locale.lower().split('-', 1)[0])
        jobs = self.filter(Q(snippet__locale__code__contains=splitted_locale) |
                           Q(snippet__locale__code__contains=full_locale))
        jobs = jobs.filter(targets__in=targets)

        return jobs
