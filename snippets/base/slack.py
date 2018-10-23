import logging

from django.conf import settings
from django.template.loader import render_to_string

import requests
from raven.contrib.django.models import client as sentry_client

logger = logging.getLogger(__name__)


def send_slack(template_name, snippet):
    data = render_to_string('slack/{}.jinja.json'.format(template_name),
                            context={'snippet': snippet})
    _send_slack(data)


def _send_slack(data):
    if not (settings.SLACK_ENABLE and settings.SLACK_WEBHOOK):
        logger.info('Slack is not enabled.')
        return

    try:
        response = requests.post(settings.SLACK_WEBHOOK, data=data,
                                 headers={'Content-Type': 'application/json'},
                                 timeout=4)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        sentry_client.captureException()
