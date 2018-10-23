import logging

from django.conf import settings
from django.template.loader import render_to_string

import requests

logger = logging.getLogger(__name__)


def send_slack(template_name, snippet):
    data = render_to_string('slack/{}.jinja.json'.format(template_name),
                            context={'snippet': snippet})
    _send_slack(data)


def _send_slack(data):
    if not (settings.SLACK_ENABLE and settings.SLACK_WEBHOOK):
        logger.info('Slack is not enabled.')
        return

    response = requests.post(settings.SLACK_WEBHOOK, data=data,
                             headers={'Content-Type': 'application/json'})
    response.raise_for_status()
