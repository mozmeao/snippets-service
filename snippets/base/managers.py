from django.db.models import Manager
from django.db.models.query import QuerySet

from snippets.base import LANGUAGE_VALUES
from snippets.base.util import first


class ClientMatchRuleQuerySet(QuerySet):
    def evaluate(self, client):
        passed_rules, failed_rules = [], []
        for rule in self:
            if rule.matches(client):
                passed_rules.append(rule)
            else:
                failed_rules.append(rule)
        return passed_rules, failed_rules


class ClientMatchRuleManager(Manager):
    def get_query_set(self):
        return ClientMatchRuleQuerySet(self.model)


class SnippetManager(Manager):
    def match_client(self, client):
        from snippets.base.models import (
            CHANNELS, CLIENT_NAMES, STARTPAGE_VERSIONS)

        filters = {}

        # Retrieve the first channel that starts with the client's channel.
        # Allows things like "release-cck-mozilla14" to match "release".
        client_channel = first(CHANNELS, client.channel.startswith)
        if client_channel:
            filters.update(**{'on_{0}'.format(client_channel): True})

        # Same matching for the startpage version.
        startpage_version = first(STARTPAGE_VERSIONS,
                                  client.startpage_version.startswith)
        if startpage_version:
            filters.update(
                **{'on_startpage_{0}'.format(startpage_version): True})

        # Only filter the client name here if it matches our whitelist.
        client_name = CLIENT_NAMES.get(client.name, False)
        if client_name:
            filters.update(**{'on_{0}'.format(client_name): True})

        # Only filter by locale if they pass a valid locale.
        locale = first(LANGUAGE_VALUES, client.locale.lower().startswith)
        if locale:
            filters.update(locale_set__locale=client.locale)

        return self.filter(**filters)
