from django.core.exceptions import ValidationError
from django.forms import (ChoiceField, ModelChoiceField, ModelMultipleChoiceField,
                          MultiValueField, MultipleChoiceField)

from snippets.base.models import Addon, TargetedCountry

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


class JEXLBaseField():
    def to_jexl(self, value):
        if value:
            return self.jexl.format(attr_name=self.attr_name, value=value)

        return None


class JEXLChoiceField(JEXLBaseField, ChoiceField):
    def __init__(self, attr_name, *args, **kwargs):
        self.attr_name = attr_name
        self.jexl = '{attr_name} == {value}'
        self.jexl = kwargs.pop('jexl', self.jexl)
        return super().__init__(*args, **kwargs)

    def to_jexl(self, value):
        if value:
            return self.jexl.format(attr_name=self.attr_name, value=value)


class JEXLModelMultipleChoiceField(JEXLBaseField, ModelMultipleChoiceField):
    def __init__(self, attr_name, *args, **kwargs):
        self.attr_name = attr_name
        self.jexl = '{attr_name} in {value}'
        self.jexl = kwargs.pop('jexl', self.jexl)
        return super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        if isinstance(value, str):
            value = value.split(';')
        return super().prepare_value(value)

    def clean(self, value):
        value = super().clean(value)
        return ';'.join([str(x.id) for x in value])


class JEXLCountryField(JEXLModelMultipleChoiceField):
    def to_jexl(self, value):
        if value:
            values = TargetedCountry.objects.filter(id__in=value.split(";"))
            return f'region in {[x.code for x in values]}'
        return None


class JEXLRangeField(JEXLBaseField, MultiValueField):
    def __init__(self, attr_name, choices, **kwargs):
        self.attr_name = attr_name
        self.jexl = {
            'minimum': '{value} <= {attr_name}',
            'maximum': '{attr_name} < {value}'
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


class JEXLFirefoxRangeField(JEXLRangeField):
    def __init__(self, **kwargs):
        # Include only versions greater than 63, where ASRSnippets exist.
        min_version = 64
        # Need to be able to dynamically change this, probably using
        # product_details. Issue #855
        max_version = 84

        choices = (
            [(None, 'No limit')] +
            [(x, x) for x in reversed(range(min_version, max_version + 1))]
        )
        super().__init__('firefoxVersion', choices, **kwargs)

    def validate(self, value):
        minimum, maximum = value.split(',')
        self.fields[0].validate(minimum)
        self.fields[1].validate(maximum)

        if minimum and maximum and minimum > maximum:
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


class JEXLFirefoxServicesField(MultiValueField):
    def __init__(self, **kwargs):
        check_choices = (
            (None, "I don't care"),
            ('no_account', "User hasn't signed up for"),
            ('has_account', 'User has signed up for'),
        )
        service_choices = (
            (None, '---------'),
            ('Firefox Lockwise', 'Firefox Lockwise'),
            ('Firefox Monitor', 'Firefox Monitor'),
            ('Firefox Send', 'Firefox Send'),
            ('Firefox Private Network', 'Firefox Private Network'),
            ('Notes', 'Notes'),
            ('Pocket', 'Pocket'),
        )
        fields = (
            ChoiceField(choices=check_choices),
            ChoiceField(choices=service_choices),
        )
        super().__init__(fields, **kwargs)
        self.widget = JEXLMultiWidget(widgets=[f.widget for f in self.fields])

    def compress(self, data_list):
        if data_list:
            return f'{data_list[0]},{data_list[1]}'
        return ''

    def to_jexl(self, value):
        check, service_name = value.split(',')
        if not check or not service_name:
            return ''

        if check == 'no_account':
            jexl = f'("{service_name}" in attachedFxAOAuthClients|mapToProperty("name")) == false'
        elif check == 'has_account':
            jexl = f'("{service_name}" in attachedFxAOAuthClients|mapToProperty("name")) == true'

        return jexl

    def validate(self, value):
        check, service_name = value.split(',')

        self.fields[0].validate(check)
        self.fields[1].validate(service_name)

        if check and not service_name:
            raise ValidationError('You must select an Service.')

        if not check and service_name:
            raise ValidationError('You must select a check.')
        return value
