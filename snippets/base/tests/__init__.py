import factory
from test_utils import TestCase as BaseTestCase

from snippets.base import models


class TestCase(BaseTestCase):
    pass


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


class BaseSnippetFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.Snippet
    name = factory.Sequence(lambda n: 'Test Snippet {0}'.format(n))
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

        if extracted is not None:
            self.locale_set.add(*extracted)
        else:
            self.locale_set.create(locale='en-us')


class SnippetFactory(BaseSnippetFactory):
    FACTORY_FOR = models.Snippet
    template = factory.SubFactory(SnippetTemplateFactory)

    @factory.post_generation
    def countries(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            countries = [models.TargetedCountry.objects.get_or_create(code=code)[0]
                         for code in extracted]
            self.countries.add(*countries)


class JSONSnippetFactory(BaseSnippetFactory):
    FACTORY_FOR = models.JSONSnippet


class ClientMatchRuleFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.ClientMatchRule
    description = factory.Sequence(lambda n: 'Client Match Rule {0}'.format(n))


class UploadedFileFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.UploadedFile
    name = factory.Sequence(lambda n: 'Uploaded File {0}'.format(n))
    # factory.django.FileField is broken and doesn't save filename. We
    # set file to None to prevent factory from taking any action and mock
    # it as needed in the tests.
    file = None


class SearchProviderFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.SearchProvider
    name = factory.Sequence(lambda n: 'Search Provider {0}'.format(n))
    identifier = factory.Sequence(lambda n: 'search-provider-{0}'.format(n))
