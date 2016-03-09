import json
import os

from collections import defaultdict

from django import forms
from django.conf import settings
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.urlresolvers import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe

from snippets.base import ENGLISH_LANGUAGE_CHOICES
from snippets.base.models import JSONSnippet, Snippet, SnippetTemplateVariable, UploadedFile


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
        js = ('js/lib/jquery-2.0.0.js',
              'js/iconWidget.js')


class BaseSnippetAdminForm(forms.ModelForm):
    locales = forms.MultipleChoiceField(
        required=False,
        choices=ENGLISH_LANGUAGE_CHOICES,
        widget=FilteredSelectMultiple('locales', is_stacked=False))

    def __init__(self, *args, **kwargs):
        super(BaseSnippetAdminForm, self).__init__(*args, **kwargs)

        # Populates the list of locales from the snippet's existing values.
        locales = self.instance.locale_set.all()
        self.fields['locales'].initial = [l.locale for l in locales]


class SnippetAdminForm(BaseSnippetAdminForm):

    class Meta:
        model = Snippet
        fields = ('name', 'template', 'data', 'priority', 'disabled',
                  'countries', 'publish_start', 'publish_end',
                  'on_release', 'on_beta', 'on_aurora', 'on_nightly',
                  'on_startpage_1', 'on_startpage_2', 'on_startpage_3', 'on_startpage_4',
                  'weight', 'client_match_rules', 'exclude_from_search_providers',
                  'campaign')
        widgets = {
            'template': TemplateSelect,
            'data': TemplateDataWidget('template'),
        }


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
