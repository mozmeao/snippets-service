import factory
from test_utils import TestCase as BaseTestCase

from snippets.base import models


class TestCase(BaseTestCase):
    pass  # Will be filled in when we need this, which we usually do.


class SnippetTemplateFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.SnippetTemplate
    name = factory.Sequence(lambda n: 'Test Template {0}'.format(n))
    code = factory.Sequence(lambda n: '<p>Test Snippet {0}</p>'.format(n))

    @factory.post_generation
    def variable_set(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.variable_set.add(*extracted)


class SnippetTemplateVariableFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.SnippetTemplateVariable
    name = factory.Sequence(lambda n: 'test_var_{0}'.format(n))
    template = factory.SubFactory(SnippetTemplateFactory)


class SnippetFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.Snippet
    name = factory.Sequence(lambda n: 'Test Snippet {0}'.format(n))
    template = factory.SubFactory(SnippetTemplateFactory)
    disabled = False

    @factory.post_generation
    def client_match_rules(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.client_match_rules.add(*extracted)

    @factory.post_generation
    def locale_set(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.locale_set.add(*extracted)
        else:
            self.locale_set.create(locale='en-us')


class ClientMatchRuleFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.ClientMatchRule
    description = factory.Sequence(lambda n: 'Client Match Rule {0}'.format(n))
