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
