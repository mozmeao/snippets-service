import json

from snippets.base.models import JSONSnippet


class SnippetEncoder(json.JSONEncoder):
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
        return super(SnippetEncoder, self).default(obj)
