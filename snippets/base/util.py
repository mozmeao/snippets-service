import hashlib

from product_details import product_details
from product_details.version_compare import version_list


def get_object_or_none(model_class, **filters):
    """
    Identical to Model.get, except instead of throwing exceptions, this returns
    None.
    """
    try:
        return model_class.objects.get(**filters)
    except (model_class.DoesNotExist, model_class.MultipleObjectsReturned):
        return None


def first(collection, callback):
    """
    Find the first item in collection that, when passed to callback, returns
    True. Returns None if no such item is found.
    """
    return next((item for item in collection if callback(item)), None)


def hashfile(filepath):
    sha1 = hashlib.sha1()
    with open(filepath, 'rb') as fp:
        sha1.update(fp.read())
    return sha1.hexdigest()


def create_locales():
    from snippets.base.models import TargetedLocale

    for code, name in product_details.languages.items():
        locale = TargetedLocale.objects.get_or_create(code=code.lower())[0]
        name = name['English']
        if locale.name != name:
            locale.name = name
            locale.save()


def create_countries():
    from snippets.base.models import TargetedCountry

    for code, name in product_details.get_regions('en-US').items():
        country = TargetedCountry.objects.get_or_create(code=code)[0]
        if country.name != name:
            country.name = name
            country.save()


def current_firefox_major_version():
    full_version = version_list(
        product_details.firefox_history_major_releases)[0]

    return full_version.split('.', 1)[0]
