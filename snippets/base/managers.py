from datetime import datetime

from django.db.models import Manager, get_model

from caching.base import CachingQuerySet

from snippets.base import LANGUAGE_VALUES
from snippets.base.util import first


class ClientMatchRuleQuerySet(CachingQuerySet):
    def evaluate(self, client):
        passed_rules, failed_rules = [], []
        for rule in self:
            if rule.matches(client):
                passed_rules.append(rule)
            else:
                failed_rules.append(rule)
        return passed_rules, failed_rules


class ClientMatchRuleManager(Manager):
    def get_queryset(self):
        return ClientMatchRuleQuerySet(self.model)


class SnippetQuerySet(CachingQuerySet):
    def filter_by_available(self):
        """Datetime filtering of snippets.

        Filter by date in python to avoid caching based on the passing
        of time.
        """
        now = datetime.utcnow()
        matching_snippets = [
            snippet for snippet in self if
            (not snippet.publish_start or snippet.publish_start <= now) and
            (not snippet.publish_end or snippet.publish_end >= now)
        ]
        return matching_snippets

    def match_client(self, client):
        from snippets.base.models import (
            CHANNELS, FENNEC_STARTPAGE_VERSIONS, FIREFOX_STARTPAGE_VERSIONS)

        filters = {}

        # Retrieve the first channel that starts with the client's channel.
        # Allows things like "release-cck-mozilla14" to match "release".
        client_channel = ('nightly' if client.channel == 'default'
                          else first(CHANNELS, client.channel.startswith))
        if client_channel:
            filters.update(**{'on_{0}'.format(client_channel): True})

        # Same matching for the startpage version.
        STARTPAGE_VERSIONS = FIREFOX_STARTPAGE_VERSIONS
        if client.name.lower() == 'fennec':
            STARTPAGE_VERSIONS = FENNEC_STARTPAGE_VERSIONS
        startpage_version = first(STARTPAGE_VERSIONS,
                                  client.startpage_version.startswith)
        if startpage_version:
            filters.update(
                **{'on_startpage_{0}'.format(startpage_version): True})

        # Only filter by locale if they pass a valid locale.
        locales = filter(client.locale.lower().startswith, LANGUAGE_VALUES)
        if locales:
            filters.update(locale_set__locale__in=locales)
        else:
            # If the locale is invalid, only match snippets with no
            # locales specified.
            filters.update(locale_set__isnull=True)

        snippets = self.filter(**filters).distinct()
        JSONSnippet = get_model('base', 'JSONSnippet')
        if issubclass(self.model, JSONSnippet):
            filtering = {'jsonsnippet__in': snippets}
        else:
            filtering = {'snippet__in': snippets}

        # Filter based on ClientMatchRules
        ClientMatchRule = get_model('base', 'ClientMatchRule')
        passed_rules, failed_rules = (ClientMatchRule.cached_objects
                                      .filter(**filtering)
                                      .distinct()
                                      .evaluate(client))

        return snippets.exclude(client_match_rules__in=failed_rules)


class SnippetManager(Manager):
    def get_queryset(self):
        return SnippetQuerySet(self.model)

    def match_client(self, client):
        return self.get_queryset().match_client(client)
