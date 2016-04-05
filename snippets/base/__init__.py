from django.utils.functional import lazy

from product_details import product_details


ENGLISH_LANGUAGE_CHOICES = sorted(
    [(key.lower(), u'{0} ({1})'.format(key, value['English']))
     for key, value in product_details.languages.items()]
)


def language_values():
    return (key.lower() for key in product_details.languages.keys())
LANGUAGE_VALUES = lazy(language_values, tuple)()

ENGLISH_COUNTRY_CHOICES = sorted(
    [(code, u'{0} ({1})'.format(name, code)) for code, name in
     product_details.get_regions('en-US').items()],
    cmp=lambda x, y: cmp(x[1], y[1])
)

ENGLISH_COUNTRIES = product_details.get_regions('en-US')
