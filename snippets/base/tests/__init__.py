import factory
from test_utils import TestCase as BaseTestCase

from snippets.base import models


class TestCase(BaseTestCase):
    pass  # Will be filled in when we need this, which we usually do.


class SnippetFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.Snippet
    name = factory.Sequence(lambda n: 'Test Snippet {0}'.format(n))
    body = factory.Sequence(lambda n: 'Test body {0}'.format(n))
    disabled = False

    @factory.post_generation
    def client_match_rules(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.client_match_rules.add(*extracted)


class ClientMatchRuleFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.ClientMatchRule
    description = 'Client Match Rule'
