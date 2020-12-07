import collections
import json
from datetime import timedelta

from django.conf import settings
from django.db.models import Sum, Q
from django.db.transaction import atomic
from redash_dynamic_query import RedashDynamicQuery

from snippets.base.models import CHANNELS, DailyImpressions, JobDailyPerformance, Job


REDASH_QUERY_IDS = {
    'bq-job': 72139,
    'bq-impressions': 72140,
    'bq-total-clients': 72341,

    # Not currently used but kept here for reference.
    'redshift-job': 68135,
    'redshift-impressions': 68345,
}

redash = RedashDynamicQuery(
    endpoint=settings.REDASH_ENDPOINT,
    apikey=settings.REDASH_API_KEY,
    max_wait=settings.REDASH_MAX_WAIT)


def redash_rows(query_name, **params):
    query_id = REDASH_QUERY_IDS[query_name]
    for k, v in params.items():
        params[k] = str(v)
    result = redash.query(query_id, params)
    return result['query_result']['data']['rows']


def process_rows(rows, date, key='message_id'):
    # To fight Telemetry spam, process metrics for Jobs currently Published or
    # Completed the last 7 days.
    jobs = Job.objects.filter(
        # Still published
        Q(status=Job.PUBLISHED) |
        # Or completed during the last 7 days from date
        Q(completed_on__gte=date - timedelta(days=7))
    )
    job_ids = [str(x) for x in jobs.values_list('id', flat=True)]
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

        # Fundraising metrics need special treatment.
        if row['event_context'] == 'EOYSnippetForm' and row['event'] == 'CLICK_BUTTON':
            event = 'CLICK'
        else:
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
        if event == 'impression':
            processed[row[key]]['impression_no_clients_total'] = (
                processed[row[key]].get('impression_no_clients_total', 0) +
                row['no_clients_total']
            )

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
            processed[k]['click'] = processed[k].pop('conversion_subscribe_activation')
            for row in processed[k]['details']:
                if row['event'] == 'click':
                    row['event'] = 'other_click'
                elif row['event'] == 'conversion_subscribe_activation':
                    row['event'] = 'click'

    return processed


def update_job_metrics(date):
    tomorrow = date + timedelta(days=1)
    rows = redash_rows('bq-job', date=date)
    # Find all finished Jobs with Impressions but no total clients
    # that completed on `date`
    query = (Job.objects
             .filter(Q(status=Job.COMPLETED) | Q(status=Job.CANCELED))
             .filter(completed_on__gte=f'{date.year}-{date.month}-{date.day} 00:00:00',
                     completed_on__lt=f'{tomorrow.year}-{tomorrow.month}-{tomorrow.day} 00:00:00')
             .annotate(no_clients_total=Sum('metrics__impression_no_clients_total'),
                       impressions=Sum('metrics__impression'))
             .filter(impressions__gt=0)
             .filter(no_clients_total=0))

    for job in query:
        # If `publish_start` is more than 30 days earlier than completed on, we
        # skip fetching total number of clients because that's scanning too much
        # data and costs too much.
        if (job.completed_on - job.publish_start).days > 30:
            continue

        rows += redash_rows(
            'bq-total-clients',
            message_id=job.id,
            start_date=job.publish_start,
            end_date=job.completed_on)

    processed = process_rows(rows, date, key='message_id')
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
    rows = redash_rows('bq-impressions', date=date)
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
