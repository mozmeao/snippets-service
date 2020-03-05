from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.test.utils import override_settings

from snippets.base import etl
from snippets.base.models import DailyImpressions, JobDailyPerformance
from snippets.base.tests import JobFactory


class TestRedashRows(TestCase):
    @patch('snippets.base.etl.redash.query',
           return_value={'query_result': {'data': {'rows': ['mock rows']}}})
    def test_base(self, query):
        d = date(2019, 12, 19)
        query_name, query_id = next(iter(etl.REDASH_QUERY_IDS.items()))
        assert etl.redash_rows(query_name, d) == ['mock rows']
        bind_data = {'date': str(d)}
        query.assert_called_with(query_id, bind_data)


class TestRedashSourceURL(TestCase):
    @override_settings(REDASH_ENDPOINT='https://sql.telemetry.mozilla.org')
    def test_base(self):
        url = 'https://sql.telemetry.mozilla.org/queries/68136/source'
        assert etl.redash_source_url('bq-job') == url
        url += '?p_date_68136=2019-12-19'
        assert etl.redash_source_url('bq-job', date='2019-12-19') == url


class TestUpdateJobMetrics(TestCase):
    def test_base(self):
        JobFactory.create(id=1000)
        JobFactory.create(id=2000)

        rows = [
            [
                {
                    'message_id': '1000',
                    'event_context': '{}',
                    'event': 'CLICK_BUTTON',
                    'channel': 'release',
                    'country_code': 'GR',
                    'counts': 5,
                },
                {
                    'message_id': '1000',
                    'event_context': '{}',
                    'event': 'IMPRESSION',
                    'channel': 'release',
                    'country_code': 'ES',
                    'counts': 30,
                },
                {
                    'message_id': '1000',
                    'event_context': '{}',
                    'event': 'IMPRESSION',
                    'channel': 'release',
                    'country_code': 'IT',
                    'counts': 50,
                },
                {
                    'message_id': '1000',
                    'event_context': '{}',
                    'event': 'BLOCK',
                    'channel': 'releases',
                    'country_code': 'UK',
                    'counts': 23,
                },
                {
                    'message_id': '1000',
                    'event_context': '{}',
                    'event': 'BLOCK',
                    'channel': 'beta-test',
                    'country_code': 'SW',
                    'counts': 27,
                },
                # To be discarded
                {
                    'message_id': '500',
                    'event_context': '{}',
                    'event': 'CLICK',
                    'channel': 'demo',
                    'country_code': 'GR',
                    'counts': 5,
                }
            ],
            [
                {
                    'message_id': '1000',
                    'event_context': '',
                    'event': 'CLICK',
                    'channel': 'release',
                    'country_code': 'GR',
                    'counts': 6,
                },
                {
                    'message_id': '2000',
                    'event_context': '{}',
                    'event': 'CLICK_BUTTON',
                    'additional_properties': '{"value": "scene1-button-learn-more", "foo": "bar"}',
                    'channel': 'release',
                    'country_code': 'GR',
                    'counts': 44,
                },
                {
                    'message_id': '2000',
                    'event_context': '{}',
                    'event': 'CLICK_BUTTON',
                    'channel': 'release',
                    'country_code': 'BG',
                    'counts': 3,
                },
                {
                    'message_id': '2000',
                    'event_context': '{}',
                    'event': 'CLICK_BUTTON',
                    'channel': 'release',
                    'country_code': 'AL',
                    'counts': 1,
                },
                {
                    'message_id': '2000',
                    'event_context': 'conversion-subscribe-activation',
                    'event': 'CLICK_BUTTON',
                    'additional_properties': '{"foo": "bar"}',
                    'channel': 'release',
                    'country_code': 'GR',
                    'counts': 5,
                },
                {
                    'message_id': '2000',
                    'event_context': 'subscribe-error',
                    'event': 'CLICK_BUTTON',
                    'additional_properties': '{"foo": "bar"}',
                    'channel': 'release',
                    'country_code': 'GR',
                    'counts': 3,
                },
                {
                    'message_id': '2000',
                    'event_context': 'subscribe-success',
                    'event': 'CLICK_BUTTON',
                    'channel': 'release',
                    'country_code': 'ERROR',
                    'counts': 9,
                },
                {
                    'message_id': '2000',
                    'event_context': '',
                    'event': 'DISMISS',
                    'channel': 'beta',
                    'country_code': 'ERROR',
                    'counts': 1,
                },
            ],
        ]

        with patch('snippets.base.etl.redash_rows') as redash_rows_mock:
            redash_rows_mock.side_effect = rows
            result = etl.update_job_metrics('2020-01-10')

        self.assertTrue(result)
        self.assertEqual(JobDailyPerformance.objects.count(), 2)

        jdp1 = JobDailyPerformance.objects.get(job_id=1000)
        self.assertEqual(jdp1.impression, 80)
        self.assertEqual(jdp1.click, 11)
        self.assertEqual(jdp1.block, 50)
        self.assertEqual(jdp1.dismiss, 0)
        self.assertEqual(jdp1.go_to_scene2, 0)
        self.assertEqual(jdp1.subscribe_error, 0)
        self.assertEqual(jdp1.subscribe_success, 0)
        self.assertEqual(jdp1.other_click, 0)
        self.assertEqual(len(jdp1.details), 5)
        for detail in [
                {'event': 'click', 'counts': 11, 'channel': 'release', 'country': 'GR'},
                {'event': 'impression', 'counts': 30, 'channel': 'release', 'country': 'ES'},
                {'event': 'impression', 'counts': 50, 'channel': 'release', 'country': 'IT'},
                {'event': 'block', 'counts': 23, 'channel': 'release', 'country': 'UK'},
                {'event': 'block', 'counts': 27, 'channel': 'beta', 'country': 'SW'}
        ]:
            self.assertTrue(detail in jdp1.details)

        jdp2 = JobDailyPerformance.objects.get(job_id=2000)
        self.assertEqual(jdp2.impression, 0)
        self.assertEqual(jdp2.click, 5)
        self.assertEqual(jdp2.block, 0)
        self.assertEqual(jdp2.dismiss, 1)
        self.assertEqual(jdp2.go_to_scene2, 44)
        self.assertEqual(jdp2.subscribe_error, 3)
        self.assertEqual(jdp2.subscribe_success, 9)
        self.assertEqual(jdp2.other_click, 4)
        self.assertEqual(len(jdp2.details), 7)
        for detail in [
                {'event': 'go_to_scene2', 'counts': 44, 'channel': 'release', 'country': 'GR'},
                {'event': 'other_click', 'counts': 3, 'channel': 'release', 'country': 'BG'},
                {'event': 'other_click', 'counts': 1, 'channel': 'release', 'country': 'AL'},
                {'event': 'click', 'counts': 5, 'channel': 'release', 'country': 'GR'},
                {'event': 'subscribe_error', 'counts': 3, 'channel': 'release', 'country': 'GR'},
                {'event': 'subscribe_success', 'counts': 9, 'channel': 'release', 'country': 'XX'},
                {'event': 'dismiss', 'counts': 1, 'channel': 'beta', 'country': 'XX'}
        ]:
            self.assertTrue(detail in jdp2.details)


class TestUpdateImpressions(TestCase):
    def test_base(self):
        with patch('snippets.base.etl.redash_rows') as rr_mock:
            rr_mock.side_effect = [
                [
                    {
                        'channel': 'release',
                        'counts': 100,
                        'duration': '4',
                    },
                    {
                        'channel': 'foo',
                        'counts': 33,
                        'duration': '4',
                    },
                    {
                        'channel': 'nightlyz',  # ending `z` on purpose
                        'counts': 10,
                        'duration': '5',
                    },
                ],
                [
                    {
                        'channel': 'release',
                        'counts': 2,
                        'duration': '6',
                    },

                ],
            ]
            self.assertEqual(etl.update_impressions('2019-12-20'), 3)
        self.assertEqual(DailyImpressions.objects.all().count(), 1)

        di = DailyImpressions.objects.all()[0]
        self.assertTrue(
            {'channel': 'release', 'duration': '4', 'counts': 133}
            in di.details
        )
        self.assertTrue(
            {'channel': 'release', 'duration': '6', 'counts': 2}
            in di.details
        )
        self.assertTrue(
            {'channel': 'nightly', 'duration': '5', 'counts': 10}
            in di.details
        )
