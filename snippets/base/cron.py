import json

from cronjobs import register
from django.db import transaction

from snippets.base import ENGLISH_LANGUAGE_CHOICES
from snippets.base.models import (ClientMatchRule, Snippet, SnippetLocale,
                                  SnippetTemplate, SnippetTemplateVariable)


class DoesNotExist(Exception):
    pass


def find_client_match_rule(data, id):
    """Search data for ClientMatchRule with  id and return description."""
    for entry in data:
        if (entry['model'] == 'homesnippets.clientmatchrule'
            and entry['pk'] == id):
            return entry['fields']['description']
    raise DoesNotExist('Cannot find ClientMatchRule {0}'.format(id))


@register
@transaction.commit_on_success
def import_v1_data(filename):
    """Import data from snippets service version 1."""

    with open(filename, 'r') as f:
        old_data = json.load(f)

    # Create Basic Template.
    basic_template, created = SnippetTemplate.objects.get_or_create(
        name='Basic Import Template', code='{{ data|safe }}')
    SnippetTemplateVariable.objects.get_or_create(
        template=basic_template, name='data',
        type=SnippetTemplateVariable.TEXT)

    # Import Common Match Rules.
    for entry in old_data:
        if entry['model'] == 'homesnippets.clientmatchrule':
            data = entry['fields'].copy()

            created = data.pop('created')
            modified = data.pop('modified')

            # Rename fields.
            data['is_exclusion'] = data.pop('exclude')
            cmr, _ = ClientMatchRule.objects.get_or_create(**data)

            # Force created and modified timestamps.
            ClientMatchRule.objects.filter(pk=cmr.pk).update(modified=modified,
                                                             created=created)

    # Import Snippets
    for index, entry in enumerate(old_data):
        if entry['model'] == 'homesnippets.snippet':
            data = entry['fields'].copy()

            created = data.pop('created')
            modified = data.pop('modified')

            # Delete legacy fields.
            for key in ['preview', 'client_match_rules']:
                del data[key]

            data.update({
                # Rename fields.
                'publish_start': data.pop('pub_start'),
                'publish_end': data.pop('pub_end'),
                'data': json.dumps({'data': data.pop('body')}),

                # Set default values.
                'template': basic_template,
                'on_release': True,
                'on_beta': True,
                'on_aurora': True,
                'on_nightly': True,
                'on_startpage_1': True,
                'on_startpage_2': True,
                'on_startpage_3': True,
                'on_startpage_4': True,
                })

            # Generate a unique name if needed.
            if Snippet.objects.filter(name=data['name']).exists():
                data['name'] = 'Renamed [{0}]: {1}'.format(index, data['name'])

            # Force id.
            data['id'] = entry['pk']

            snippet = Snippet.objects.create(**data)

            # Link Match Rules.
            client_match_rules = entry['fields']['client_match_rules']
            if not client_match_rules:
                snippet.disabled = True
                snippet.save()
            else:
                for rule in client_match_rules:
                    cmr_description = find_client_match_rule(old_data, rule)
                    cmr = ClientMatchRule.objects.get(description=cmr_description)
                    snippet.client_match_rules.add(cmr)


            # Allow all locales. Will be filtered using Client Match
            # Rules.
            for locale_code, locale_name in ENGLISH_LANGUAGE_CHOICES:
                SnippetLocale.objects.create(snippet=snippet, locale=locale_code)

            # Force created and modified timestamps.
            (Snippet.objects.filter(pk=snippet.pk).update(modified=modified,
                                                          created=created))
