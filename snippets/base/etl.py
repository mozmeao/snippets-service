import collections
import json

from urllib.parse import urlencode

from django.conf import settings
from django.db.transaction import atomic
from redash_dynamic_query import RedashDynamicQuery

from snippets.base.models import CHANNELS, DailyImpressions, JobDailyPerformance, Job


REDASH_QUERY_IDS = {
    'bq-job': 72139,
    'bq-impressions': 72140,

    # Not currently used but kept here for reference.
    'redshift-job': 68135,
    'redshift-impressions': 68345,
}

redash = RedashDynamicQuery(
    endpoint=settings.REDASH_ENDPOINT,
    apikey=settings.REDASH_API_KEY,
    max_wait=settings.REDASH_MAX_WAIT)


def redash_source_url(query_id_or_name, **params):
    query_id = REDASH_QUERY_IDS.get(query_id_or_name, query_id_or_name)
    url = f'{settings.REDASH_ENDPOINT}/queries/{query_id}/source'
    if params:
        url += '?' + urlencode({f'p_{key}_{query_id}': value
                                for key, value in params.items()})
    return url


def redash_rows(query_name, date):
    query_id = REDASH_QUERY_IDS[query_name]
    bind_data = {'date': str(date)}
    result = redash.query(query_id, bind_data)
    return result['query_result']['data']['rows']


def prosses_rows(rows, key='message_id'):
    job_ids = [str(x) for x in Job.objects.all().values_list('id', flat=True)]
    new_rows = []
    for row in sorted(rows, key=lambda x: x[key]):
        # Remove rows with invalid Job IDs
        if row['message_id'] not in job_ids:
            continue

        # Redash uses {} instead of null
        if row['event_context'] == '{}':
            row['event_context'] = ''

        # Sometimes data in Telemetry populate `event_context`, some
        # other times it uses `additional_properties['value']` to
        # place the event context. Extract information from both
        # places to identify the event.
        properties = json.loads(row.get('additional_properties', '{}'))
        event = row['event_context'] or properties.get('value', '') or row['event']

        if event in ['CLICK_BUTTON', 'CLICK']:
            event = 'click'
        elif event == 'IMPRESSION':
            event = 'impression'
        elif event == 'BLOCK':
            event = 'block'
        elif event == 'DISMISS':
            event = 'dismiss'
        elif event == 'scene1-button-learn-more':
            event = 'go_to_scene2'
        elif event in ['subscribe-success',
                       'subscribe-error',
                       'conversion-subscribe-activation']:
            event = event.replace('-', '_')
        else:
            # Ignore invalid event
            continue

        row['event'] = event

        # Normalize channel name, based on what kind of snippets they get.
        channel = row['channel']
        if not channel:
            channel = 'release'
        row['channel'] = next(
            (item for item in CHANNELS if
             channel.startswith(item)), 'release'
        )

        # Normalize country
        country_code = row['country_code']
        if country_code in ['ERROR', None]:
            row['country_code'] = 'XX'

        # Not needed anymore
        row.pop('event_context', None)
        row.pop('additional_properties', None)

        new_rows.append(row)

    # Aggregate counts of same events for the global count.
    processed = collections.defaultdict(dict)
    for row in new_rows:
        event = row['event']
        processed[row[key]][event] = processed[row[key]].get(event, 0) + row['counts']
        processed[row[key]][f'{event}_no_clients'] = (
            processed[row[key]].get(f'{event}_no_clients', 0) + row['no_clients'])
        processed[row[key]][f'{event}_no_clients_total'] = (
            processed[row[key]].get(f'{event}_no_clients_total', 0) + row['no_clients_total'])

        detail = [{
            'event': row['event'],
            'channel': row['channel'],
            'country': row['country_code'],
            'counts': row['counts'],
            'no_clients': row['no_clients'],
            'no_clients_total': row['no_clients_total'],
        }]

        if not processed[row[key]].get('details'):
            processed[row[key]]['details'] = detail
        else:
            for drow in processed[row[key]]['details']:
                if ((drow['event'] == row['event'] and
                     drow['channel'] == row['channel'] and
                     drow['country'] == row['country_code'])):
                    drow['counts'] += row['counts']
                    drow['no_clients'] += row['no_clients']
                    drow['no_clients_total'] += row['no_clients_total']
                    break
            else:
                processed[row[key]]['details'] += detail

    # Last pass for multi-scene snippets: Click events here refer to
    #  clicks of secondary links listed on the template that go to
    #  terms of services or additional information and are displayed
    #  in the small text below the input element. These do not count
    #  clicking on `Learn more` (i.e. going from scene 1 to scene 2)
    #  or the main Call To Action. The later is measured in
    #  `conversion_subscribe_activation` and this is the value which
    #  is important to us and thus we rename this to `clicks`.
    for k, v in processed.items():
        if 'conversion_subscribe_activation' in v:
            processed[k]['other_click'] = processed[k].get('click', 0)
            processed[k]['other_click_no_clients'] = processed[k].get('click_no_clients', 0)
            processed[k]['other_click_no_clients_total'] = \
                processed[k].get('click_no_clients_total', 0)
            processed[k]['click'] = processed[k].pop('conversion_subscribe_activation')
            processed[k]['click_no_clients'] = \
                processed[k].pop('conversion_subscribe_activation_no_clients')
            processed[k]['click_no_clients_total'] = \
                processed[k].pop('conversion_subscribe_activation_no_clients_total')
            for row in processed[k]['details']:
                if row['event'] == 'click':
                    row['event'] = 'other_click'
                elif row['event'] == 'conversion_subscribe_activation':
                    row['event'] = 'click'

    return processed


def update_job_metrics(date):
    rows = redash_rows('bq-job', date)
    processed = prosses_rows(rows, key='message_id')
    with atomic():
        JobDailyPerformance.objects.filter(date=date).delete()
        for job, data in processed.items():
            JobDailyPerformance.objects.create(
                date=date,
                job=Job.objects.get(id=job),
                **data
            )
    return len(processed) > 0


def update_impressions(date):
    """Fetch number of Impressions per channel and per duration.

    This information is used to determine the number of actually viewed
    Snippets by disgarding Impressions the lasted too few seconds.

    """
    rows = redash_rows('bq-impressions', date)
    details = []
    for row in rows:
        # Normalize channel name, based on what kind of snippets they get.
        channel = row['channel']
        if not channel:
            channel = 'release'
        channel = next(
            (item for item in CHANNELS if
             channel.startswith(item)), 'release'
        )

        # Aggregate counts of the same duration and the same channel.
        for item in details:
            if (item['channel'] == channel and item['duration'] == row['duration']):
                item['counts'] += row['counts']
                break
        else:
            details.append({
                'channel': channel,
                'duration': row['duration'],
                'counts': row['counts'],
                'no_clients': row['no_clients'],
            })

    with atomic():
        DailyImpressions.objects.filter(date=date).delete()
        DailyImpressions.objects.create(
            date=date,
            details=details
        )

    return len(details)
