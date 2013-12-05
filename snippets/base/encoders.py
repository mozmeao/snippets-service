import json

from snippets.base.models import JSONSnippet


class SnippetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, JSONSnippet):
            return {'id': obj.id,
                    'text': obj.text,
                    'icon': obj.icon,
                    'url': obj.url,
                    'target_geo': obj.country.upper()}
        return super(SnippetEncoder, self).default(obj)
