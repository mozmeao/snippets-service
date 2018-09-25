from django.core.exceptions import ValidationError
from django.forms import ChoiceField, ModelChoiceField, MultiValueField, MultipleChoiceField

from snippets.base.models import Addon

from .widgets import JEXLMultiWidget


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
        self.jexl = '{attr_name} == {value}'
        self.jexl = kwargs.pop('jexl', self.jexl)
        return super().__init__(*args, **kwargs)

    def to_jexl(self, value):
        if value:
            return self.jexl.format(attr_name=self.attr_name, value=value)
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
        super().__init__(fields, **kwargs)
        self.widget = JEXLMultiWidget(widgets=[f.widget for f in self.fields],
                                      template_name='widgets/jexlrange.html')

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


class JEXLAddonField(MultiValueField):
    def __init__(self, **kwargs):
        choices = (
            (None, "I don't care"),
            ('not_installed', 'Not Installed'),
            ('installed', 'Installed'),
        )
        fields = (
            ChoiceField(choices=choices),
            ModelChoiceField(queryset=Addon.objects.all(), required=False),
        )
        super().__init__(fields, **kwargs)
        self.widget = JEXLMultiWidget(widgets=[f.widget for f in self.fields])

    def compress(self, data_list):
        if data_list:
            return '{},{}'.format(data_list[0], getattr(data_list[1], 'id', ''))
        return ''

    def to_jexl(self, value):
        check, addon_id = value.split(',')
        if not check or not addon_id:
            return ''

        addon = Addon.objects.get(id=addon_id)
        if check == 'not_installed':
            jexl = '("{}" in addonsInfo.addons|keys) == false'.format(addon.guid)
        elif check == 'installed':
            jexl = '("{}" in addonsInfo.addons|keys) == true'.format(addon.guid)

        return jexl

    def validate(self, value):
        check, addon_id = value.split(',')

        self.fields[0].validate(check)
        self.fields[1].validate(addon_id)

        if check and not addon_id:
            raise ValidationError('You must select an add-on')

        if not check and addon_id:
            raise ValidationError('You must select a check')

        return value
