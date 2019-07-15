import json
from collections import defaultdict

from django import forms
from django.conf import settings
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.forms.widgets import Textarea
from django.urls import reverse
from django.utils.safestring import mark_safe

from product_details import product_details
from product_details.version_compare import Version, version_list

from snippets.base.admin import fields
from snippets.base import models
from snippets.base.slack import send_slack
from snippets.base.validators import MinValueValidator, validate_xml_variables


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

PROFILE_AGE_CHOICES_ASR = (
    (None, 'No limit'),
    (None, '----------'),
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
    (None, '-----------'),
    (4, 'One Month'),
    (9, 'Two Months'),
    (13, 'Three Months'),
    (17, 'Four Months'),
    (21, 'Five Months'),
    (26, 'Six Months'),
    (None, '-----------'),
    (52, 'One Year'),
    (104, 'Two Years'),
)

BOOKMARKS_COUNT_CHOICES = (
    (-1, 'No limit'),
    (-2, '----------'),
    (1, '1'),
    (10, '10'),
    (50, '50'),
    (100, '100'),
    (500, '500'),
    (1000, '1,000'),
    (5000, '5,000'),
    (10000, '10,000'),
    (50000, '50,000'),
    (100000, '100,000'),
    (500000, '500,000'),
    (1000000, '1,000,000'),
)

BOOKMARKS_COUNT_CHOICES_ASR = (
    (None, 'No limit'),
    (None, '----------'),
    (1, '1'),
    (10, '10'),
    (50, '50'),
    (100, '100'),
    (500, '500'),
    (1000, '1,000'),
    (5000, '5,000'),
    (10000, '10,000'),
    (50000, '50,000'),
    (100000, '100,000'),
    (500000, '500,000'),
    (1000000, '1,000,000'),
)

NUMBER_OF_SYNC_DEVICES = (
    (None, 'No limit'),
    (None, '----------'),
    (1, '1'),
    (2, '2'),
    (5, '5'),
    (10, '10'),
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
            for variable in models.SnippetTemplateVariable.objects.all():
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
    def __init__(self, select_name, include_preview_button=True, *args, **kwargs):
        self.template_select_name = select_name
        self.include_preview_button = include_preview_button
        return super(TemplateDataWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        widget_code = super(TemplateDataWidget, self).render(
            name, value, attrs)
        extra_code = """
            <div class="widget-container">
              <div class="template-data-widget"
                   data-select-name="{select_name}"
                   data-input-name="{input_name}"
                   data-snippet-size-limit="{size_limit}"
                   data-snippet-img-size-limit="{img_size_limit}">
              </div>
        """
        if self.include_preview_button:
            extra_code += """
              <div class="snippet-preview-container"
                   data-preview-url="{preview_url}">
              </div>
            """
        extra_code += '</div>'
        return mark_safe(''.join([
            widget_code, extra_code.format(
                select_name=self.template_select_name,
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
            'js/lib/jquery-3.3.1.min.js',
            'js/lib/nunjucks.min.js',
            'js/templateDataWidget.js'
        ]


class TemplateChooserWidget(forms.Select):
    class Media:
        js = [
            'js/lib/jquery-3.3.1.min.js',
            'js/templateChooserWidget.js',
        ]


class IconWidget(forms.TextInput):
    def render(self, name, value, attrs=None, renderer=None):
        if not attrs:
            attrs = {}
        attrs['style'] = 'display:none'
        original_widget_code = super(IconWidget, self).render(name, value, attrs)
        widget_code = """
        <div id="{name}-container">
          <img src="{value}">
          <input type="file" class="image-input">
          {original_widget_code}
        </div>
        """.format(name=name, value=value,
                   original_widget_code=original_widget_code)
        return mark_safe(widget_code)

    class Media:
        js = ('js/lib/jquery-3.3.1.min.js',
              'js/iconWidget.js')


class PublishPermissionFormMixIn:
    def _publish_permission_check(self, cleaned_data):
        """If Snippet is Published or the current form sets it to Published verify that
        user has permission to publish on all the selected publication
        channels.

        This permission model allows users without any publish permissions to
        edit a Snippet and select the publication channels but prevents them
        from publishing the snippets.

        A user with publish permission will later review the snippet and set
        Snippet.published to True. After this point, only users with publish
        permissions on all selected publication channels are allowed to edit
        the Snippet, including editing content, un-publishing, alter targeting,
        etc.
        """
        if self.instance.published or cleaned_data.get('published'):
            for channel in models.CHANNELS:
                on_channel = 'on_{}'.format(channel)
                if ((cleaned_data.get(on_channel) is True or
                     getattr(self.instance, on_channel, False) is True)):
                    if not self.current_user.has_perm('base.can_publish_on_{}'.format(channel)):
                        msg = ('You are not allowed to edit or publish '
                               'on {} channel.'.format(channel.title()))
                        raise forms.ValidationError(msg)

    def _publish_permission_check_asr(self, cleaned_data):
        """If Snippet is Published or the current form sets it to Published verify that
        user has permission to publish on all the selected publication
        channels.

        This permission model allows users without any publish permissions to
        edit a Snippet and select the publication channels but prevents them
        from publishing the snippets.

        A user with publish permission will later review the snippet and set
        Snippet.published to True. After this point, only users with publish
        permissions on all selected publication channels are allowed to edit
        the Snippet, including editing content, un-publishing, alter targeting,
        etc.
        """
        if ((self.instance.status == models.STATUS_CHOICES['Published'] or
             cleaned_data.get('status') == models.STATUS_CHOICES['Published'])):

            for channel in models.CHANNELS:
                on_channel = 'on_{}'.format(channel)

                for target in self.instance.targets.all() | self.cleaned_data['targets']:
                    if getattr(target, on_channel) is True:
                        if not self.current_user.has_perm('base.publish_on_{}'.format(channel)):
                            msg = ('You are not allowed to edit or publish '
                                   'on {} channel.'.format(channel.title()))
                            raise forms.ValidationError(msg)


class BaseSnippetAdminForm(forms.ModelForm, PublishPermissionFormMixIn):
    pass


class SnippetChangeListForm(forms.ModelForm, PublishPermissionFormMixIn):
    class Meta:
        model = models.Snippet
        fields = ('body',)

    body = forms.CharField(required=False, widget=Textarea(attrs={'cols': '120', 'rows': '8'}))

    def __init__(self, *args, **kwargs):
        super(SnippetChangeListForm, self).__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if not instance:
            return

        try:
            self.body_variable = (instance.template
                                  .variable_set.get(type=models.SnippetTemplateVariable.BODY).name)
        except models.SnippetTemplateVariable.DoesNotExist:
            self.fields['body'].disabled = True
            self.body_variable = None
        else:
            text = instance.dict_data.get(self.body_variable, '')
            self.fields['body'].initial = text

    def clean(self):
        cleaned_data = super(SnippetChangeListForm, self).clean()
        self._publish_permission_check(cleaned_data)
        return cleaned_data

    def save(self, *args, **kwargs):
        if self.body_variable:
            self.instance.set_data_property(self.body_variable, self.cleaned_data['body'])

        return super(SnippetChangeListForm, self).save(*args, **kwargs)


class SnippetAdminForm(BaseSnippetAdminForm):
    template = forms.ModelChoiceField(
        queryset=models.SnippetTemplate.objects.exclude(hidden=True).filter(startpage__lt=6),
        widget=TemplateSelect)
    on_startpage_5 = forms.BooleanField(required=False, initial=True, label='Activity Stream')
    client_option_version_lower_bound = forms.ChoiceField(
        label='Firefox Version at least',
        choices=[('any', 'No limit'),
                 ('current_release', 'Current release')])
    client_option_version_upper_bound = forms.ChoiceField(
        label='Firefox Version less than',
        choices=[('any', 'No limit'),
                 ('older_than_current_release', 'Older than current release')])
    client_option_has_fxaccount = forms.ChoiceField(
        label='Firefox Account / Sync',
        choices=(('any', 'Show to all users'),
                 ('yes', 'Show only to FxA users with Sync enabled'),
                 ('no', 'Show only to users without Sync enabled')))
    client_option_is_developer = forms.ChoiceField(
        label='Is Developer',
        choices=(('any', 'Show to all users'),
                 ('yes', 'Show only to Developers (i.e. users who have opened Dev Tools)'),
                 ('no', 'Show only to non Developers (i.e. users who haven\'t opened Dev Tools')),
        help_text=('This filter works for browsers version >= 60. Older browsers will not '
                   'display snippets with this option set, unless "Show to all users" '
                   'is selected.'),
    )
    client_option_is_default_browser = forms.ChoiceField(
        label='Default Browser',
        help_text=('If we cannot determine the status we will act '
                   'as if Firefox <em>is</em> the default browser'),
        choices=(('any', 'Show to all users'),
                 ('yes', 'Show only to users with Firefox as default browser'),
                 ('no', 'Show only to users with Firefox as second browser')))
    client_option_screen_resolutions = fields.MultipleChoiceFieldCSV(
        label='Show on screens',
        help_text='Select all the screen resolutions you want this snippet to appear on.',
        widget=forms.CheckboxSelectMultiple(),
        initial=['0-1024', '1024-1920', '1920-50000'],  # Show to all screens by default
        choices=(('0-1024', 'Screens with less than 1024 vertical pixels. (low)'),
                 ('1024-1920', 'Screens with less than 1920 vertical pixels. (hd)'),
                 ('1920-50000', 'Screens with more than 1920 vertical pixels (full-hd, 4k)')))
    client_option_sessionage_lower_bound = forms.ChoiceField(
        label='Previous session closed at least',
        help_text=('Available from Firefox version 61. '
                   'Snippets using this option will be ignored on previous versions.'),
        choices=PROFILE_AGE_CHOICES,
        validators=[
            MinValueValidator(
                -1, message='Select a value or "No limit" to disable this filter.')
        ],
    )
    client_option_sessionage_upper_bound = forms.ChoiceField(
        label='Previous session closed less than',
        help_text=('Available from Firefox version 61. '
                   'Snippets using this option will be ignored on previous versions.'),
        choices=PROFILE_AGE_CHOICES,
        validators=[
            MinValueValidator(
                -1, message='Select a value or "No limit" to disable this filter.')
        ],
    )
    client_option_profileage_lower_bound = forms.ChoiceField(
        label='Profile age at least',
        help_text=('Available from Firefox version 55. '
                   'Snippets using this option will be ignored on previous versions.'),
        choices=PROFILE_AGE_CHOICES,
        validators=[
            MinValueValidator(
                -1, message='Select a value or "No limit" to disable this filter.')
        ],
    )
    client_option_profileage_upper_bound = forms.ChoiceField(
        label='Profile age less than',
        help_text=('Available from Firefox version 55. '
                   'Snippets using this option will be ignored on previous versions.'),
        choices=PROFILE_AGE_CHOICES,
        validators=[
            MinValueValidator(
                -1, message='Select a value or "No limit" to disable this filter.')
        ],
    )
    client_option_addon_check_type = forms.ChoiceField(
        label='Add-on Check',
        help_text=('Available from Firefox version 60. '
                   'Snippets using this option will be ignored on previous versions.'),
        choices=(
            ('any', 'No check'),
            ('installed', 'Installed'),
            ('not_installed', 'Not installed')),
    )
    client_option_addon_name = forms.CharField(
        label='Add-on Name',
        help_text=('Add-on name. For example @testpilot-addon. Available from Firefox version 60. '
                   'Snippets using this option will be ignored on previous versions.'),
        required=False,
        strip=True,
    )
    client_option_bookmarks_count_lower_bound = forms.ChoiceField(
        label='Bookmarks count at least',
        help_text=('Available from Firefox version 61. '
                   'Snippets using this option will be ignored on previous versions.'),
        choices=BOOKMARKS_COUNT_CHOICES,
        validators=[
            MinValueValidator(
                -1, message='Select a value or "No limit" to disable this filter.')
        ],
    )
    client_option_bookmarks_count_upper_bound = forms.ChoiceField(
        label='Bookmarks count less than',
        help_text=('Available from Firefox version 61. '
                   'Snippets using this option will be ignored on previous versions.'),
        choices=BOOKMARKS_COUNT_CHOICES,
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

    class Meta:
        model = models.Snippet
        fields = ('name', 'template', 'data', 'published', 'countries',
                  'publish_start', 'publish_end', 'on_release', 'on_beta',
                  'on_aurora', 'on_nightly', 'on_esr', 'on_startpage_1',
                  'on_startpage_2', 'on_startpage_3', 'on_startpage_4',
                  'on_startpage_5', 'weight', 'client_match_rules',
                  'exclude_from_search_providers', 'campaign')
        widgets = {
            'data': TemplateDataWidget('template'),
        }

    def clean(self):
        cleaned_data = super(SnippetAdminForm, self).clean()

        if any([cleaned_data['on_startpage_4'], cleaned_data['on_startpage_3'],
                cleaned_data['on_startpage_2'], cleaned_data['on_startpage_1']]):
            validate_xml_variables(cleaned_data['data'])

        version_upper_bound = cleaned_data.get('client_option_version_upper_bound', 'any')
        version_lower_bound = cleaned_data.get('client_option_version_lower_bound', 'any')

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

        sessionage_lower_bound = int(cleaned_data.get('client_option_sessionage_lower_bound', -1))
        sessionage_upper_bound = int(cleaned_data.get('client_option_sessionage_upper_bound', -1))

        cleaned_data['client_option_sessionage_lower_bound'] = sessionage_lower_bound
        cleaned_data['client_option_sessionage_upper_bound'] = sessionage_upper_bound

        if ((sessionage_lower_bound > -1 and sessionage_upper_bound > -1 and
             sessionage_upper_bound <= sessionage_lower_bound)):
            raise forms.ValidationError('Profile age upper bound must be bigger than lower bound.')

        bookmarks_count_lower_bound = int(
            cleaned_data.get('client_option_bookmarks_count_lower_bound', -1))
        bookmarks_count_upper_bound = int(
            cleaned_data.get('client_option_bookmarks_count_upper_bound', -1))

        cleaned_data['client_option_bookmarks_count_lower_bound'] = bookmarks_count_lower_bound
        cleaned_data['client_option_bookmarks_count_upper_bound'] = bookmarks_count_upper_bound

        if ((bookmarks_count_lower_bound > -1 and bookmarks_count_upper_bound > -1 and
             bookmarks_count_upper_bound <= bookmarks_count_lower_bound)):
            raise forms.ValidationError('Bookmarks count upper bound must be '
                                        'bigger than lower bound.')

        if not any([cleaned_data['on_release'], cleaned_data['on_beta'],
                    cleaned_data['on_aurora'], cleaned_data['on_nightly'], cleaned_data['on_esr']]):
            raise forms.ValidationError('Select at least one channel to publish this snippet on.')

        if ((cleaned_data.get('on_startpage_5') and
             any([cleaned_data['on_startpage_4'], cleaned_data['on_startpage_3'],
                  cleaned_data['on_startpage_2'], cleaned_data['on_startpage_1']]))):

            raise forms.ValidationError('Activity Stream cannot be combined '
                                        'with Startpage Versions 1-4.')

        if not any([cleaned_data.get('on_startpage_4'), cleaned_data.get('on_startpage_3'),
                    cleaned_data.get('on_startpage_2'), cleaned_data.get('on_startpage_1'),
                    cleaned_data.get('on_startpage_5')]):
            raise forms.ValidationError('Select at least one Startpage to publish this snippet on.')

        if ((cleaned_data.get('client_option_addon_name') and
             cleaned_data.get('client_option_addon_check_type') == 'any')):
            raise forms.ValidationError('Select an add-on check or remove add-on name.')

        if ((not cleaned_data.get('client_option_addon_name') and
             cleaned_data.get('client_option_addon_check_type', 'any') != 'any')):
            raise forms.ValidationError('Type add-on name to check or remove add-on check.')

        self._publish_permission_check(cleaned_data)

        return cleaned_data

    def save(self, *args, **kwargs):
        snippet = super(SnippetAdminForm, self).save(commit=False)

        if not self.initial:
            snippet.creator = self.current_user

        if 'ready_for_review' in self.changed_data and self.instance.ready_for_review is True:
            send_slack('legacy_ready_for_review', snippet)

        if 'published' in self.changed_data and self.instance.published is True:
            send_slack('legacy_published', snippet)

        return snippet


class SnippetTemplateVariableInlineFormset(forms.models.BaseInlineFormSet):
    def clean(self):
        main_body_count = sum([form.cleaned_data['type'] == models.SnippetTemplateVariable.BODY
                               for form in self.forms])
        if main_body_count > 1:
            raise forms.ValidationError(
                'There can be only one Main Text variable type per template')


class AutoTranslatorWidget(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        """For each key available in each Locale.translation JSON dictionary, create an
        `translation-{key}` attribute. The attribute will be used by
        `autoTranslatorWidget.js` to translate fields on Locale selection.

        """
        option = super().create_option(name, value, label, selected,
                                       index, subindex=None, attrs=None)
        if value:
            option['attrs']['translations'] = models.Locale.objects.get(id=value).translations

        return option

    class Media:
        js = [
            'js/lib/jquery-3.3.1.min.js',
            'js/autoTranslatorWidget.js',
        ]


class SimpleTemplateForm(forms.ModelForm):

    class Meta:
        model = models.SimpleTemplate
        exclude = []


class FundraisingTemplateForm(forms.ModelForm):

    class Meta:
        model = models.FundraisingTemplate
        exclude = []


class FxASignupTemplateForm(forms.ModelForm):

    class Meta:
        model = models.FxASignupTemplate
        exclude = []


class NewsletterTemplateForm(forms.ModelForm):

    class Meta:
        model = models.NewsletterTemplate
        exclude = []


class SendToDeviceTemplateForm(forms.ModelForm):

    class Meta:
        model = models.SendToDeviceTemplate
        exclude = []


class SimpleBelowSearchTemplateForm(forms.ModelForm):

    class Meta:
        model = models.SimpleBelowSearchTemplate
        exclude = []


class ASRSnippetAdminForm(forms.ModelForm, PublishPermissionFormMixIn):
    template_chooser = forms.ChoiceField(
        choices=(
            ('', 'Select Template'),
            ('simple_snippet', 'Simple'),
            ('eoy_snippet', 'Fundraising'),
            ('fxa_signup_snippet', 'Firefox Accounts Sign Up'),
            ('newsletter_snippet', 'Newsletter Sign Up'),
            ('send_to_device_snippet', 'Send to Device'),
            ('simple_below_search_snippet', 'Simple Below Search'),
        ),
        widget=TemplateChooserWidget,
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.id and getattr(self.instance, 'template_ng', None):
            self.fields['template_chooser'].disabled = True
            self.fields['template_chooser'].initial = self.instance.template_ng.code_name

    class Meta:
        model = models.ASRSnippet
        exclude = ['creator', 'created', 'modified']
        widgets = {
            'locale': AutoTranslatorWidget,
        }

    class Media:
        js = [
            'js/lib/jquery-3.3.1.min.js',
            'js/admin/inlineMover.js',
        ]

    def clean(self):
        cleaned_data = super().clean()
        self._publish_permission_check_asr(cleaned_data)
        return cleaned_data

    def save(self, *args, **kwargs):
        snippet = super().save(*args, **kwargs)

        if (('status' in self.changed_data and
             self.instance.status == models.STATUS_CHOICES['Ready for review'])):
            send_slack('asr_ready_for_review', snippet)

        if (('status' in self.changed_data and
             self.instance.status == models.STATUS_CHOICES['Published'])):
            send_slack('asr_published', snippet)

        return snippet


class TargetAdminForm(forms.ModelForm):
    filtr_is_default_browser = fields.JEXLChoiceField(
        'isDefaultBrowser',
        choices=((None, "I don't care"),
                 ('true', 'Yes',),
                 ('false', 'No')),
        label_suffix='?',
        label='Is Firefox the default browser',
        help_text='User has set Firefox as their default browser.',
        required=False)
    filtr_profile_age_created = fields.JEXLRangeField(
        'profileAgeCreated',
        # profileAgeCreated is in milliseconds. We first calculate the
        # difference from currentDate and then we convert to week.
        jexl={
            'minimum': '((currentDate|date - profileAgeCreated) / 604800000) >= {value}',
            'maximum': '((currentDate|date - profileAgeCreated) / 604800000) < {value}',
        },
        choices=PROFILE_AGE_CHOICES_ASR,
        required=False,
        label='Firefox Profile Age',
        help_text='The age of the browser profile must fall between those two limits.'
    )
    filtr_firefox_version = fields.JEXLFirefoxRangeField(
        required=False,
        label='Firefox Version',
        help_text='The version of the browser must fall between those two limits.'
    )
    filtr_previous_session_end = fields.JEXLRangeField(
        'previousSessionEnd',
        # previousSessionEnd is in milliseconds. We first calculate the
        # difference from currentDate and then we convert to week.
        jexl={
            'minimum': '((currentDate|date - previousSessionEnd) / 604800000) >= {value}',
            'maximum': '((currentDate|date - previousSessionEnd) / 604800000) < {value}',
        },
        choices=PROFILE_AGE_CHOICES_ASR,
        required=False,
        label='Previous Session End',
        help_text='How many weeks since the last time Firefox was used?'
    )
    filtr_uses_firefox_sync = fields.JEXLChoiceField(
        '(isFxAEnabled == undefined || isFxAEnabled == true) && usesFirefoxSync',
        choices=((None, "I don't care"),
                 ('true', 'Yes',),
                 ('false', 'No')),
        label_suffix='?',
        label='Uses Firefox Sync',
        help_text='User has a Firefox account which is connected to their browser.',
        required=False)
    filtr_country = fields.JEXLCountryField(
        'region',
        label='Countries',
        widget=FilteredSelectMultiple('Countries', False),
        help_text='Display Snippet to users in the selected countries.',
        queryset=models.TargetedCountry.objects.all(),
        required=False,
    )
    filtr_is_developer = fields.JEXLChoiceField(
        'devToolsOpenedCount',
        # devToolsOpenedCount reads from devtools.selfxss.count which is capped
        # to 5. We consider the user a developer if they have opened devtools
        # at least 5 times, non-developer otherwise.
        jexl='{attr_name} - 5 {value} 0',
        choices=((None, "I don't care"),
                 ('==', 'Yes',),
                 ('<', 'No')),
        label_suffix='?',
        label='Is developer',
        help_text='User has opened Developer Tools more than 5 times.',
        required=False)
    filtr_updates_enabled = fields.JEXLChoiceField(
        'browserSettings.update.enabled',
        choices=((None, "I don't care"),
                 ('true', 'Yes',),
                 ('false', 'No')),
        required=False,
        label='Has updates enabled',
        label_suffix='?',
    )
    filtr_updates_autodownload_enabled = fields.JEXLChoiceField(
        'browserSettings.update.autoDownload',
        choices=((None, "I don't care"),
                 ('true', 'Yes',),
                 ('false', 'No')),
        required=False,
        label='Is auto-downloading updates',
        label_suffix='?',
    )
    filtr_current_search_engine = fields.JEXLChoiceField(
        'searchEngines.current',
        jexl='{attr_name} == "{value}"',
        choices=((None, "I don't care"),
                 ('google', 'Google',),
                 ('bing', 'Bing',),
                 ('amazondotcom', 'Amazon',),
                 ('ddg', 'DuckDuckGo',),
                 ('twitter', 'Twitter',),
                 ('wikipedia', 'Wikipedia',)),
        label_suffix='?',
        label='Currently used search engine',
        required=False)
    filtr_browser_addon = fields.JEXLAddonField(
        label='Browser Add-on',
        required=False)
    filtr_total_bookmarks_count = fields.JEXLRangeField(
        'totalBookmarksCount',
        choices=BOOKMARKS_COUNT_CHOICES_ASR,
        required=False,
        label='Number of bookmarks',
        help_text='The number of bookmarks must fall between those two limits.'
    )
    filtr_desktop_devices_count = fields.JEXLRangeField(
        'sync.desktopDevices',
        choices=NUMBER_OF_SYNC_DEVICES,
        required=False,
        label='Desktop Syncing Devices',
        help_text='Number of Desktop Devices connected to Sync.'
    )
    filtr_mobile_devices_count = fields.JEXLRangeField(
        'sync.mobileDevices',
        choices=NUMBER_OF_SYNC_DEVICES,
        required=False,
        label='Mobile Syncing Devices',
        help_text='Number of Mobile Devices connected to Sync.'
    )
    filtr_total_devices_count = fields.JEXLRangeField(
        'sync.totalDevices',
        choices=NUMBER_OF_SYNC_DEVICES,
        required=False,
        label='Total Syncing Devices',
        help_text='Total number of Devices (Mobile and Desktop) connected to Sync.'
    )

    class Meta:
        model = models.Target
        exclude = ['creator', 'created', 'modified']

    def save(self, *args, **kwargs):
        jexl_expr_array = []

        for name, field in self.fields.items():
            if name.startswith('filtr_'):
                value = self.cleaned_data[name]
                if value:
                    jexl_expr_array.append(field.to_jexl(value))
        self.instance.jexl_expr = ' && '.join([x for x in jexl_expr_array if x])

        return super().save(*args, **kwargs)
