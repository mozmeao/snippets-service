from product_details import product_details


ENGLISH_LANGUAGE_CHOICES = sorted(
    [(key.lower(), u'{0} ({1})'.format(key, value['English']))
     for key, value in product_details.languages.items()]
)
LANGUAGE_VALUES = [choice[0] for choice in ENGLISH_LANGUAGE_CHOICES]

ENGLISH_COUNTRY_CHOICES = sorted(
    [(code, u'{0} ({1})'.format(name, code)) for code, name in
     product_details.get_regions('en-US').items()],
    cmp=lambda x, y: cmp(x[1], y[1])
)
