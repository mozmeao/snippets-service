import json

from snippets.base.models import JSONSnippet


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
            countries = [country.code.upper() for country in obj.countries.all()]
            if countries:
                data['target_geo'] = countries[0]
                data['countries'] = countries
            return data
        return super(JSONSnippetEncoder, self).default(obj)
