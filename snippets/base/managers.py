from django.db.models import Manager
from django.db.models.query import QuerySet


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
        from snippets.base.models import (CHANNELS, CLIENT_NAMES,
                                          STARTPAGE_VERSIONS)
        filters = {}
        # Retrieve the first item that starts with an available item. Allows
        # things like "release-cck-mozilla14" to match "release".
        client_channel = next((channel for channel in CHANNELS if
                               client.channel.startswith(channel)), False)
        if client_channel:
            filters.update(**{'on_{0}'.format(client_channel):True})

        client_startpage_version = next(
            (version for version in STARTPAGE_VERSIONS if
             client.startpage_version.startswith(version)), False)
        if client_startpage_version:
            filters.update(
                **{'on_startpage_{0}'.format(client_startpage_version):True})

        client_name = CLIENT_NAMES.get(client.name, False)
        if client_name:
            filters.update(**{'on_{0}'.format(client_name):True})

        return self.filter(**filters)
