import copy
import json
from datetime import datetime

from django.test import RequestFactory

from snippets.base.admin import actions
from snippets.base.admin.legacy import SnippetAdmin
from snippets.base import models
from snippets.base.tests import (ASRSnippetFactory, ClientMatchRuleFactory, SnippetFactory,
                                 SnippetTemplateFactory, TestCase, UserFactory)


class PublishSnippetsActions(TestCase):
    def test_base(self):
        to_be_published = ASRSnippetFactory.create_batch(2, status=models.STATUS_CHOICES['Draft'])
        already_published = ASRSnippetFactory(status=models.STATUS_CHOICES['Published'])
        ASRSnippetFactory.create_batch(2, status=models.STATUS_CHOICES['Draft'])

        queryset = models.ASRSnippet.objects.filter(id__in=[
            to_be_published[0].id,
            to_be_published[1].id,
            already_published.id
        ])
        actions.publish_snippets_action(None, None, queryset)

        self.assertEqual(
            set(models.ASRSnippet.objects.filter(status=models.STATUS_CHOICES['Published'])),
            set(to_be_published + [already_published])
        )


class MigrateSnippetActionTests(TestCase):
    def setUp(self):
        request_factory = RequestFactory()
        self.request = request_factory.post('/')
        self.request.user = UserFactory.create()

        self.template = SnippetTemplateFactory(name='[Activity Stream] Simple snippets with Button')
        SnippetTemplateFactory(name='[AS Router] Simple Snippet with Button')

        # Following import must happen here, or messages middleware initialization fails.
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(self.request, 'session', 'session')
        messages = FallbackStorage(self.request)
        setattr(self.request, '_messages', messages)

        self.client_options = {
            'version_lower_bound': 'any',
            'version_upper_bound': 'any',
            'has_fxaccount': 'any',
            'is_developer': 'any',
            'is_default_browser': 'any',
            'profileage_lower_bound': -1,
            'profileage_upper_bound': -1,
            'sessionage_lower_bound': -1,
            'sessionage_upper_bound': -1,
            'addon_check_type': 'any',
            'addon_name': '',
            'bookmarks_count_lower_bound': -1,
            'bookmarks_count_upper_bound': -1,
        }

    def test_base(self):
        snippet = SnippetFactory(
            campaign='Test Campaign',
            template=self.template,
            publish_start=datetime.now(),
            publish_end=datetime.now(),
            weight=100,
            published=True,
            data=json.dumps({
                'text': '<a href="about:accounts">Click</a> for accounts',
                'blockable': True
            }),
            locales=['en', 'el'],
            client_options=self.client_options,
        )
        queryset = models.Snippet.objects.all()
        actions.migrate_snippets_action(SnippetAdmin, self.request, queryset)

        self.assertEqual(models.ASRSnippet.objects.all().count(), 1)
        asrsnippet = models.ASRSnippet.objects.all()[0]

        self.assertEqual(snippet.name, asrsnippet.name)

        self.assertEqual(snippet.campaign, asrsnippet.campaign.name)

        self.assertEqual(snippet.publish_start, asrsnippet.publish_start)
        self.assertEqual(snippet.publish_end, asrsnippet.publish_end)

        self.assertEqual(snippet.weight, asrsnippet.weight)

        self.assertEqual(asrsnippet.status, models.STATUS_CHOICES['Published'])

        data = json.loads(asrsnippet.data)
        self.assertFalse(data['do_not_autoblock'])

        # RTL is not included in original data in purpose.
        self.assertTrue('rtl' not in data)
        self.assertTrue('blockable' not in data)

        self.assertEqual(data['text'], '<a href="special:accounts">Click</a> for accounts')

        self.assertEqual(set(asrsnippet.locales.all()), set(snippet.locales.all()))

        self.assertTrue(asrsnippet.target.on_startpage_6)

        snippet.refresh_from_db()
        self.assertEqual(snippet.migrated_to, asrsnippet)

        message = next(iter(self.request._messages))
        self.assertEqual(
            message.message,
            'Selected Snippets (1) were successfully migrated to ASRSnippets.')

    def test_not_published_snippet(self):
        SnippetFactory(
            template=self.template,
            published=False,
            client_options=self.client_options,
        )
        queryset = models.Snippet.objects.all()
        actions.migrate_snippets_action(SnippetAdmin, self.request, queryset)
        asrsnippet = models.ASRSnippet.objects.all()[0]
        self.assertEqual(asrsnippet.status, models.STATUS_CHOICES['Draft'])

    def test_ready_for_review_snippet(self):
        SnippetFactory(
            name='Snippet Test Name',
            template=self.template,
            published=False,
            ready_for_review=True,
            client_options=self.client_options,
        )
        queryset = models.Snippet.objects.all()
        actions.migrate_snippets_action(SnippetAdmin, self.request, queryset)

        asrsnippet = models.ASRSnippet.objects.all()[0]
        self.assertEqual(asrsnippet.status, models.STATUS_CHOICES['Ready for review'])

    def test_already_migrated(self):
        asrsnippet = ASRSnippetFactory()
        snippet = SnippetFactory(
            template=self.template,
            published=False,
            migrated_to=asrsnippet,
            client_options=self.client_options,
        )
        queryset = models.Snippet.objects.all()
        actions.migrate_snippets_action(SnippetAdmin, self.request, queryset)

        snippet.refresh_from_db()
        self.assertEqual(snippet.migrated_to, asrsnippet)

        message = next(iter(self.request._messages))
        self.assertEqual(message.message, 'Skipped 1 already migrated Snippets.')

    def test_no_as_snippet(self):
        SnippetFactory(
            on_startpage_4=True,
            on_startpage_5=False,
        )

        queryset = models.Snippet.objects.all()
        actions.migrate_snippets_action(SnippetAdmin, self.request, queryset)

        message = next(iter(self.request._messages))
        self.assertEqual(message.message, 'Only Activity Stream Snippets can be migrated.')

    def _prepare_target_channels(self, channels):
        params = {
            'template': self.template,
            'client_options': self.client_options,
        }
        params.update(channels)
        SnippetFactory(**params)

        queryset = models.Snippet.objects.all()
        actions.migrate_snippets_action(SnippetAdmin, self.request, queryset)

        asrsnippet = models.ASRSnippet.objects.all()[0]
        return asrsnippet

    def test_target_channel_release(self):
        channels = {
            'on_release': True,
            'on_esr': False,
            'on_beta': False,
            'on_aurora': False,
            'on_nightly': False,
        }
        asrsnippet = self._prepare_target_channels(channels)
        self.assertTrue(asrsnippet.target.on_release)
        self.assertFalse(asrsnippet.target.on_esr)
        self.assertFalse(asrsnippet.target.on_beta)
        self.assertFalse(asrsnippet.target.on_aurora)
        self.assertFalse(asrsnippet.target.on_nightly)

    def test_target_channel_esr(self):
        channels = {
            'on_release': False,
            'on_esr': True,
            'on_beta': False,
            'on_aurora': False,
            'on_nightly': False,
        }
        asrsnippet = self._prepare_target_channels(channels)
        self.assertFalse(asrsnippet.target.on_release)
        self.assertTrue(asrsnippet.target.on_esr)
        self.assertFalse(asrsnippet.target.on_beta)
        self.assertFalse(asrsnippet.target.on_aurora)
        self.assertFalse(asrsnippet.target.on_nightly)

    def test_target_channel_beta(self):
        channels = {
            'on_release': False,
            'on_esr': False,
            'on_beta': True,
            'on_aurora': False,
            'on_nightly': False,
        }
        asrsnippet = self._prepare_target_channels(channels)
        self.assertFalse(asrsnippet.target.on_release)
        self.assertFalse(asrsnippet.target.on_esr)
        self.assertTrue(asrsnippet.target.on_beta)
        self.assertFalse(asrsnippet.target.on_aurora)
        self.assertFalse(asrsnippet.target.on_nightly)

    def test_target_channel_aurora(self):
        channels = {
            'on_release': False,
            'on_esr': False,
            'on_beta': False,
            'on_aurora': True,
            'on_nightly': False,
        }
        asrsnippet = self._prepare_target_channels(channels)
        self.assertFalse(asrsnippet.target.on_release)
        self.assertFalse(asrsnippet.target.on_beta)
        self.assertFalse(asrsnippet.target.on_esr)
        self.assertTrue(asrsnippet.target.on_aurora)
        self.assertFalse(asrsnippet.target.on_nightly)

    def test_target_channel_nightly(self):
        channels = {
            'on_release': False,
            'on_esr': False,
            'on_beta': False,
            'on_aurora': False,
            'on_nightly': True,
        }
        asrsnippet = self._prepare_target_channels(channels)
        self.assertFalse(asrsnippet.target.on_release)
        self.assertFalse(asrsnippet.target.on_beta)
        self.assertFalse(asrsnippet.target.on_esr)
        self.assertFalse(asrsnippet.target.on_aurora)
        self.assertTrue(asrsnippet.target.on_nightly)

    def _prepare_target_client_options(self, extended_client_options):
        client_options = copy.copy(self.client_options)
        client_options.update(extended_client_options)
        SnippetFactory(
            template=self.template,
            client_options=client_options,
        )

        queryset = models.Snippet.objects.all()
        actions.migrate_snippets_action(SnippetAdmin, self.request, queryset)

        asrsnippet = models.ASRSnippet.objects.all()[0]
        return asrsnippet

    def test_target_version(self):
        client_options = {
            'version_lower_bound': 'any',
            'version_upper_bound': '65.0',
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertEqual(asrsnippet.target.jexl['filtr_firefox_version'], ',65')

        client_options = {
            'version_lower_bound': '64.0',
            'version_upper_bound': 'any',
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertEqual(asrsnippet.target.jexl['filtr_firefox_version'], '64,')

        client_options = {
            'version_lower_bound': '64.0',
            'version_upper_bound': '65.0',
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertEqual(asrsnippet.target.jexl['filtr_firefox_version'], '64,65')

    def test_target_is_default_browser(self):
        client_options = {
            'is_default_browser': 'any'
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertTrue('filtr_is_default_browser' not in asrsnippet.target.jexl)

        client_options = {
            'is_default_browser': 'yes'
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertEqual(asrsnippet.target.jexl['filtr_is_default_browser'], 'true')

        client_options = {
            'is_default_browser': 'no'
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertEqual(asrsnippet.target.jexl['filtr_is_default_browser'], 'false')

    def test_target_is_developer(self):
        client_options = {
            'is_developer': 'any'
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertTrue('filtr_is_developer' not in asrsnippet.target.jexl)

        client_options = {
            'is_developer': 'yes'
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertEqual(asrsnippet.target.jexl['filtr_is_developer'], '==')

        client_options = {
            'is_developer': 'no'
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertEqual(asrsnippet.target.jexl['filtr_is_developer'], '<')

    def test_target_has_fxaccount(self):
        client_options = {
            'has_fxaccount': 'any'
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertTrue('filtr_uses_firefox_sync' not in asrsnippet.target.jexl)

        client_options = {
            'has_fxaccount': 'yes'
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertEqual(asrsnippet.target.jexl['filtr_uses_firefox_sync'], 'true')

        client_options = {
            'has_fxaccount': 'no'
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertEqual(asrsnippet.target.jexl['filtr_uses_firefox_sync'], 'false')

    def test_target_bookmarks(self):
        client_options = {
            'bookmarks_count_lower_bound': -1,
            'bookmarks_count_upper_bound': 1000,
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertEqual(asrsnippet.target.jexl['filtr_total_bookmarks_count'], ',1000')

        client_options = {
            'bookmarks_count_lower_bound': 1000,
            'bookmarks_count_upper_bound': -1,
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertEqual(asrsnippet.target.jexl['filtr_total_bookmarks_count'], '1000,')

        client_options = {
            'bookmarks_count_lower_bound': 1000,
            'bookmarks_count_upper_bound': 5000,
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertEqual(asrsnippet.target.jexl['filtr_total_bookmarks_count'], '1000,5000')

    def test_target_profile_age(self):
        client_options = {
            'profileage_lower_bound': -1,
            'profileage_upper_bound': 3,
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertEqual(asrsnippet.target.jexl['filtr_profile_age_created'], ',3')

        client_options = {
            'profileage_lower_bound': 4,
            'profileage_upper_bound': 20,
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        # 21 here is not a mistake, we're translating to PROFILE_AGE_ASR
        self.assertEqual(asrsnippet.target.jexl['filtr_profile_age_created'], '4,21')

        client_options = {
            'profileage_lower_bound': 17,
            'profileage_upper_bound': -1,
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertEqual(asrsnippet.target.jexl['filtr_profile_age_created'], '17,')

    def test_target_session_age(self):
        client_options = {
            'sessionage_lower_bound': -1,
            'sessionage_upper_bound': 3,
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertEqual(asrsnippet.target.jexl['filtr_previous_session_end'], ',3')

        client_options = {
            'sessionage_lower_bound': 4,
            'sessionage_upper_bound': 20,
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        # 21 here is not a mistake, we're translating to PROFILE_AGE_ASR
        self.assertEqual(asrsnippet.target.jexl['filtr_previous_session_end'], '4,21')

        client_options = {
            'sessionage_lower_bound': 17,
            'sessionage_upper_bound': -1,
        }
        asrsnippet = self._prepare_target_client_options(client_options)
        self.assertEqual(asrsnippet.target.jexl['filtr_previous_session_end'], '17,')

    def test_cmr(self):
        cmr = ClientMatchRuleFactory()
        SnippetFactory(
            template=self.template,
            published=False,
            client_options=self.client_options,
            client_match_rules=[cmr],
        )
        queryset = models.Snippet.objects.all()
        actions.migrate_snippets_action(SnippetAdmin, self.request, queryset)
        asrsnippet = models.ASRSnippet.objects.all()[0]
        self.assertEqual(asrsnippet.target.client_match_rules.all().count(), 1)
        self.assertEqual(asrsnippet.target.client_match_rules.all()[0], cmr)
