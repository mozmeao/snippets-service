import itertools
import json

from collections import defaultdict

from django import forms
from django.conf import settings
from django.db.models import Q
from django.utils.html import escape
from django.utils.safestring import mark_safe

from snippets.base.models import (ClientMatchRule, Snippet,
                                  SnippetTemplateVariable)

CLIENT_MATCH_RULE_SETS = (('Release', 'Beta', 'Aurora', 'Nightly'),
                          ('Firefox', 'Fennec'),
                          ('StartPageV1', 'StartPageV2', 'StartPageV3',
                           'StartPageV4'))
COMBINATIONS = []
for set in CLIENT_MATCH_RULE_SETS:
    for i in range(1, len(set) + 1):
        COMBINATIONS += [' and '.join(k) for k in
                         itertools.combinations(set, i)]


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
            <div class="template-data-widget"
                 data-select-name="{0}"
                 data-input-name="{1}">
            </div>
        """.format(self.template_select_name, name)]))

    class Media:
        css = {
            'all': ('css/templateDataWidget.css',)
        }
        js = filter(None, [
            'js/lib/jquery-2.0.0.js',
            'js/lib/nunjucks{0}.js'.format('-dev' if settings.DEBUG else ''),
            'templates/compiled.js' if not settings.DEBUG else None,
            'js/templateDataWidget.js'
        ])


class SnippetAdminForm(forms.ModelForm):
    Release = forms.BooleanField(required=False)
    Beta = forms.BooleanField(required=False)
    Aurora = forms.BooleanField(required=False)
    Nightly = forms.BooleanField(required=False)
    Firefox = forms.BooleanField(required=False)
    Fennec = forms.BooleanField(required=False)
    StartPageV1 = forms.BooleanField(required=False)
    StartPageV2 = forms.BooleanField(required=False)
    StartPageV3 = forms.BooleanField(required=False)
    StartPageV4= forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(SnippetAdminForm, self).__init__(*args, **kwargs)
        if self.instance.id:
            rules = self.instance.client_match_rules
            for match in rules.filter(description__in=COMBINATIONS):
                for option in match.description.split(' and '):
                    self.fields[option].initial = True
        else:
            for field in ['Release', 'Firefox',
                          'StartPageV2', 'StartPageV3', 'StartPageV4']:
                self.fields[field].initial = True

    def clean_client_match_rules(self):
        results = []
        for set in CLIENT_MATCH_RULE_SETS:
            result = (' and '.join(
                filter(lambda option: self.cleaned_data.get(option), set)))
            results.append(result)

        matches = (ClientMatchRule.objects
                   .filter(Q(pk__in=self.cleaned_data['client_match_rules']))
                   .exclude(description__in=COMBINATIONS))
        matches |= ClientMatchRule.objects.filter(Q(description__in=results))
        return matches

    class Meta:
        model = Snippet
        widgets = {
            'template': TemplateSelect,
            'data': TemplateDataWidget('template'),
        }
