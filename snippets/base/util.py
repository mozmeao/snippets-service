def get_object_or_none(model_class, **filters):
    """
    Identical to Model.get, except instead of throwing exceptions, this returns
    None.
    """
    try:
        return model_class.objects.get(**filters)
    except (model_class.DoesNotExist, model_class.MultipleObjectsReturned):
        return None
