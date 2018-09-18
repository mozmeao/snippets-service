from django.core.exceptions import ValidationError
from django.forms import ChoiceField, MultiValueField, MultipleChoiceField

from .widgets import RangeWidget


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


class JEXLRangeField(MultiValueField):
    def __init__(self, attr_name, choices, **kwargs):
        self.attr_name = attr_name
        self.jexl = {
            'minimum': '{minimum} <= {attr_name}',
            'maximum': '{attr_name} < {maximum}'
        }
        self.jexl = kwargs.pop('jexl', self.jexl)
        fields = (
            ChoiceField(choices=choices),
            ChoiceField(choices=choices),
        )
        kwargs['widget'] = RangeWidget(choices=choices)
        super().__init__(fields, **kwargs)

    def compress(self, data_list):
        return ','.join(data_list)

    def to_jexl(self, value):
        final_jexl = []
        if value:
            minimum, maximum = value.split(',')
            if minimum:
                final_jexl.append(
                    self.jexl['minimum'].format(attr_name=self.attr_name, value=minimum)
                )
            if maximum:
                final_jexl.append(
                    self.jexl['maximum'].format(attr_name=self.attr_name, value=maximum)
                )
        return ' && '.join(final_jexl)

    def validate(self, value):
        minimum, maximum = value.split(',')
        self.fields[0].validate(minimum)
        self.fields[1].validate(maximum)

        if minimum and maximum and int(minimum) > int(maximum):
            raise ValidationError('Minimum value must be lower or equal to maximum value.')
        return value
