import json
import os
from collections import defaultdict

from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe

from product_details import product_details
from product_details.version_compare import Version, version_list

from snippets.base.fields import MultipleChoiceFieldCSV
from snippets.base.models import (JSONSnippet, Snippet, SnippetTemplate,
                                  SnippetTemplateVariable, UploadedFile)


class TemplateSelect(forms.Select):
    """
    Select box used for choosing a template. Adds extra metadata to each
    <option> element detailing the template variables available in the
    corresponding template.
    """
    def render(self, *args, **kwargs):
        # Retrieve data about the currently available template variables from
        # the database prior to rendering the options.
        self.variables_for = defaultdict(list)
        for variable in SnippetTemplateVariable.objects.all():
            self.variables_for[variable.template.id].append({
                'name': variable.name,
                'type': variable.type,
                'description': variable.description,
            })

        return super(TemplateSelect, self).render(*args, **kwargs)

    def render_option(self, selected_choices, option_value, option_label):
        output = super(TemplateSelect, self).render_option(
            selected_choices, option_value, option_label)

        # Attach a list of template variables for the template this option
        # represents as a data attribute.
        try:
            attr_value = json.dumps(self.variables_for[int(option_value)])
            attr = 'data-variables="{0}"'.format(escape(attr_value))
            output = output.replace('<option', '<option {0}'.format(attr))
        except ValueError:
            pass  # Value wasn't an int, no need for an attribute.

        return mark_safe(output)


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
        label='Firefox Version at most',
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
        fields = ('name', 'template', 'data', 'priority', 'disabled',
                  'countries', 'publish_start', 'publish_end',
                  'on_release', 'on_beta', 'on_aurora', 'on_nightly',
                  'on_startpage_1', 'on_startpage_2', 'on_startpage_3', 'on_startpage_4',
                  'weight', 'client_match_rules', 'exclude_from_search_providers',
                  'campaign')
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
        fields = ('name', 'priority', 'disabled', 'icon', 'text', 'url', 'countries',
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
