import json
from datetime import datetime

from snippets.base.models import JSONSnippet, Snippet


class JSONSnippetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, JSONSnippet):
            data = {
                'id': obj.id,
                'text': obj.text,
                'icon': obj.icon,
                'url': obj.url,
                'weight': obj.weight,
            }
            if obj.country:
                data['target_geo'] = obj.country.upper()
            return data
        return super(JSONSnippetEncoder, self).default(obj)


class ActiveSnippetsEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, JSONSnippet):
            data = {
                'id': obj.id,
                'type': 'JSON Snippet',
                'template': 'default',
                'publish_start': obj.publish_start,
                'publish_end': obj.publish_end,
                'on_release': obj.on_release,
                'on_beta': obj.on_beta,
                'on_aurora': obj.on_aurora,
                'on_nightly': obj.on_nightly,
            }
            return data
        elif isinstance(obj, Snippet):
            data = {
                'id': obj.id,
                'type': 'Desktop Snippet',
                'template': obj.template.id,
                'publish_start': obj.publish_start,
                'publish_end': obj.publish_end,
                'on_release': obj.on_release,
                'on_beta': obj.on_beta,
                'on_aurora': obj.on_aurora,
                'on_nightly': obj.on_nightly,
            }
            return data
        elif isinstance(obj, datetime):
            return obj.isoformat()

        return super(ActiveSnippetsEncoder, self).default(obj)
