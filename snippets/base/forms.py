import json
import os
from collections import defaultdict

from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

from product_details import product_details
from product_details.version_compare import Version, version_list

from snippets.base.fields import MultipleChoiceFieldCSV
from snippets.base.models import (JSONSnippet, Snippet, SnippetTemplate,
                                  SnippetTemplateVariable, UploadedFile)
from snippets.base.validators import MinValueValidator


PROFILE_AGE_CHOICES = (
    (-1, 'No limit'),
    (-2, '----------'),
    (1, 'One week'),
    (2, 'Two weeks'),
    (3, 'Three weeks'),
    (4, 'Four weeks'),
    (5, 'Five weeks'),
    (6, 'Six weeks'),
    (7, 'Seven weeks'),
    (8, 'Eight weeks'),
    (9, 'Nine weeks'),
    (10, 'Ten weeks'),
    (11, 'Eleven weeks'),
    (12, 'Twelve weeks'),
    (13, 'Thirteen weeks'),
    (14, 'Fourteen weeks'),
    (15, 'Fifteen weeks'),
    (16, 'Sixteen weeks'),
    (17, 'Seventeen weeks'),
    (-2, '-----------'),
    (4, 'One Month'),
    (8, 'Two Months'),
    (12, 'Three Months'),
    (16, 'Four Months'),
    (20, 'Five Months'),
    (24, 'Six Months'),
    (-2, '-----------'),
    (48, 'One Year'),
    (96, 'Two Years'),
)


class TemplateSelect(forms.Select):
    """
    Select box used for choosing a template. Adds extra metadata to each
    <option> element detailing the template variables available in the
    corresponding template.
    """
    def __init__(self, *args, **kwargs):
        self.variables_for = defaultdict(list)
        return super(TemplateSelect, self).__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        if not self.variables_for:
            # We can't use the orm in init without having a fully working
            # database which breaks management commands unrelated to the
            # database like collectstatic.
            for variable in SnippetTemplateVariable.objects.all():
                self.variables_for[variable.template.id].append({
                    'name': variable.name,
                    'type': variable.type,
                    'order': variable.order,
                    'description': variable.description,
                })

        data = super(TemplateSelect, self).create_option(name, value, label, selected,
                                                         index, subindex, attrs)
        if value in self.variables_for:
            data['attrs']['data-variables'] = json.dumps(self.variables_for[value])

        return data


class TemplateDataWidget(forms.TextInput):
    """
    A widget that links up with a TemplateSelect and shows fields for each of
    the template variables available for the currently selected template. These
    fields are combined into a JSON string when the form is submitted.
    """
    def __init__(self, select_name, *args, **kwargs):
        self.template_select_name = select_name
        return super(TemplateDataWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        widget_code = super(TemplateDataWidget, self).render(
            name, value, attrs)
        return mark_safe(u''.join([widget_code, u"""
            <div class="widget-container">
              <div class="template-data-widget"
                   data-select-name="{select_name}"
                   data-input-name="{input_name}"
                   data-snippet-size-limit="{size_limit}"
                   data-snippet-img-size-limit="{img_size_limit}">
              </div>
              <div class="snippet-preview-container"
                   data-preview-url="{preview_url}">
              </div>
            </div>
        """.format(select_name=self.template_select_name,
                   input_name=name,
                   preview_url=reverse('base.preview'),
                   size_limit=settings.SNIPPET_SIZE_LIMIT,
                   img_size_limit=settings.SNIPPET_IMAGE_SIZE_LIMIT)
        ]))

    class Media:
        css = {
            'all': ('css/templateDataWidget.css',)
        }
        js = [
            'js/lib/jquery-2.2.1.min.js',
            'js/lib/nunjucks.min.js',
            'js/templateDataWidget.js'
        ]


class IconWidget(forms.TextInput):
    def render(self, name, value, attrs=None):
        if not attrs:
            attrs = {}
        attrs['style'] = 'display:none'
        original_widget_code = super(IconWidget, self).render(name, value, attrs)
        widget_code = u"""
        <div id="{name}-container">
          <img src="{value}">
          <input type="file" class="image-input">
          {original_widget_code}
        </div>
        """.format(name=name, value=value,
                   original_widget_code=original_widget_code)
        return mark_safe(widget_code)

    class Media:
        js = ('js/lib/jquery-2.2.1.min.js',
              'js/iconWidget.js')


class BaseSnippetAdminForm(forms.ModelForm):
    pass


class SnippetAdminForm(BaseSnippetAdminForm):
    template = forms.ModelChoiceField(queryset=SnippetTemplate.objects.exclude(hidden=True),
                                      widget=TemplateSelect)
    client_option_version_lower_bound = forms.ChoiceField(
        label='Firefox Version at least',
        choices=[('any', 'No limit'),
                 ('current_release', 'Current release')])
    client_option_version_upper_bound = forms.ChoiceField(
        label='Firefox Version less than',
        choices=[('any', 'No limit'),
                 ('older_than_current_release', 'Older than current release')])
    client_option_has_fxaccount = forms.ChoiceField(
        label='Firefox Account',
        choices=(('any', 'Show to all users'),
                 ('yes', 'Show only to users with an enabled Firefox Account'),
                 ('no', 'Show only to users without an enabled Firefox Account')))
    client_option_has_testpilot = forms.ChoiceField(
        label='Test Pilot',
        choices=(('any', 'Show to all users'),
                 ('yes', 'Show only to users with TestPilot'),
                 ('no', 'Show only to users without TestPilot')))
    client_option_is_default_browser = forms.ChoiceField(
        label='Default Browser',
        help_text=('If we cannot determine the status we will act '
                   'as if Firefox <em>is</em> the default browser'),
        choices=(('any', 'Show to all users'),
                 ('yes', 'Show only to users with Firefox as default browser'),
                 ('no', 'Show only to users with Firefox as second browser')))
    client_option_screen_resolutions = MultipleChoiceFieldCSV(
        label='Show on screens',
        help_text='Select all the screen resolutions you want this snippet to appear on.',
        widget=forms.CheckboxSelectMultiple(),
        initial=['0-1024', '1024-1920', '1920-50000'],  # Show to all screens by default
        choices=(('0-1024',  'Screens with less than 1024 vertical pixels. (low)'),
                 ('1024-1920',  'Screens with less than 1920 vertical pixels. (hd)'),
                 ('1920-50000', 'Screens with more than 1920 vertical pixels (full-hd, 4k)')))
    client_option_profileage_lower_bound = forms.ChoiceField(
        label='Profile age at least',
        choices=PROFILE_AGE_CHOICES,
        validators=[
            MinValueValidator(
                -1, message='Select a value or "No limit" to disable this filter.')
        ],
    )
    client_option_profileage_upper_bound = forms.ChoiceField(
        label='Profile age less than',
        choices=PROFILE_AGE_CHOICES,
        validators=[
            MinValueValidator(
                -1, message='Select a value or "No limit" to disable this filter.')
        ],
    )

    def __init__(self, *args, **kwargs):
        super(SnippetAdminForm, self).__init__(*args, **kwargs)

        version_choices = [
            (x, x) for x in version_list(product_details.firefox_history_major_releases)
        ]
        self.fields['client_option_version_lower_bound'].choices += version_choices
        self.fields['client_option_version_upper_bound'].choices += version_choices

        if self.instance.client_options:
            for key in self.fields.keys():
                if key.startswith('client_option_'):
                    self.fields[key].initial = self.instance.client_options.get(
                        key.split('client_option_', 1)[1], None)

    class Meta:
        model = Snippet
        fields = ('name', 'template', 'data', 'disabled', 'countries',
                  'publish_start', 'publish_end', 'on_release', 'on_beta',
                  'on_aurora', 'on_nightly', 'on_startpage_1',
                  'on_startpage_2', 'on_startpage_3', 'on_startpage_4',
                  'on_startpage_5', 'weight', 'client_match_rules',
                  'exclude_from_search_providers', 'campaign')
        widgets = {
            'data': TemplateDataWidget('template'),
        }

    def clean(self):
        cleaned_data = super(SnippetAdminForm, self).clean()

        version_upper_bound = cleaned_data['client_option_version_upper_bound']
        version_lower_bound = cleaned_data['client_option_version_lower_bound']

        if (version_upper_bound == 'older_than_current_release' and
                version_lower_bound == 'current_release'):
            raise forms.ValidationError(
                "It doesn't make sense to combine those two Firefox version filters")

        if 'any' not in [version_lower_bound, version_upper_bound]:
            if Version(version_upper_bound) < Version(version_lower_bound):
                raise forms.ValidationError(
                    'Firefox version upper bound must be bigger than lower bound.')

        profileage_lower_bound = int(cleaned_data.get('client_option_profileage_lower_bound', -1))
        profileage_upper_bound = int(cleaned_data.get('client_option_profileage_upper_bound', -1))

        cleaned_data['client_option_profileage_lower_bound'] = profileage_lower_bound
        cleaned_data['client_option_profileage_upper_bound'] = profileage_upper_bound

        if ((profileage_lower_bound > -1 and profileage_upper_bound > -1 and
             profileage_upper_bound <= profileage_lower_bound)):
            raise forms.ValidationError('Profile age upper bound must be bigger than lower bound.')

        if not any([cleaned_data['on_release'], cleaned_data['on_beta'],
                    cleaned_data['on_aurora'], cleaned_data['on_nightly']]):
            raise forms.ValidationError('Select at least one channel to publish this snippet on.')

        if ((cleaned_data['on_startpage_5'] and
             any([cleaned_data['on_startpage_4'], cleaned_data['on_startpage_3'],
                  cleaned_data['on_startpage_2'], cleaned_data['on_startpage_1']]))):

            raise forms.ValidationError('Activity Stream cannot be combined '
                                        'with Startpage Versions 1-4.')

        if not any([cleaned_data['on_startpage_4'], cleaned_data['on_startpage_3'],
                    cleaned_data['on_startpage_2'], cleaned_data['on_startpage_1'],
                    cleaned_data['on_startpage_5']]):
            raise forms.ValidationError('Select at least one Startpage to publish this snippet on.')

        return cleaned_data

    def save(self, *args, **kwargs):
        snippet = super(SnippetAdminForm, self).save(commit=False)

        client_options = {}
        for key, value in self.cleaned_data.items():
            if key.startswith('client_option_'):
                client_options[key.split('client_option_', 1)[1]] = value
        snippet.client_options = client_options
        snippet.save()

        return snippet


class JSONSnippetAdminForm(BaseSnippetAdminForm):
    class Meta:
        model = JSONSnippet
        fields = ('name', 'disabled', 'icon', 'text', 'url', 'countries',
                  'publish_start', 'publish_end',
                  'on_release', 'on_beta', 'on_aurora', 'on_nightly',
                  'on_startpage_1', 'weight', 'client_match_rules',)
        widgets = {
            'text': forms.Textarea,
            'icon': IconWidget,
        }


class UploadedFileAdminForm(forms.ModelForm):
    def clean_file(self):
        current_ext = os.path.splitext(self.instance.file.name)[1]
        new_ext = os.path.splitext(self.cleaned_data['file'].name)[1]

        if current_ext and current_ext != new_ext:
            raise forms.ValidationError(
                'File extensions do not match! You tried to upload a {0} file'
                ' in the place of a {1} file.'.format(new_ext, current_ext)
            )
        return self.cleaned_data['file']

    class Meta:
        model = UploadedFile
        fields = ('file', 'name')
