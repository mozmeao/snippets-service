from django.forms import ChoiceField, MultipleChoiceField


class MultipleChoiceFieldCSV(MultipleChoiceField):
    # To be used with in snippets.base.forms.SnippetAdminForm and in
    # combination with DynamicField. We don't directly save() this field in the
    # database so get_prep_value has not been implemented.

    def prepare_value(self, value):
        value = super(MultipleChoiceFieldCSV, self).prepare_value(value)
        if not isinstance(value, list):
            value = value.split(';')
        return value

    def clean(self, value):
        value = super(MultipleChoiceFieldCSV, self).clean(value)
        return ';'.join(value)


class JEXLChoiceField(ChoiceField):
    def __init__(self, attr_name, *args, **kwargs):
        self.attr_name = attr_name
        return super().__init__(*args, **kwargs)

    def to_jexl(self, value):
        if value:
            return '{} == {}'.format(self.attr_name, value)
        return None
