from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple

from snippets.base.admin import fields
from snippets.base import models
from snippets.base.slack import send_slack

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

NUMBER_OF_ADDONS = (
    (None, 'No limit'),
    (None, '----------'),
    (10, '10'),
    (15, '15'),
    (20, '20'),
    (30, '30'),
)


class TemplateChooserWidget(forms.Select):
    class Media:
        js = [
            'js/admin/templateChooserWidget.js',
        ]


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
            'js/admin/autoTranslatorWidget.js',
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

    class Media:
        css = {
            'all': ('css/admin/sms-country-toggle.css',),
        }

        js = [
            'js/admin/sms-country-toggle.js',
        ]


class SimpleBelowSearchTemplateForm(forms.ModelForm):

    class Meta:
        model = models.SimpleBelowSearchTemplate
        exclude = []


class ASRSnippetAdminForm(forms.ModelForm):
    template_chooser = forms.ChoiceField(
        choices=(
            ('', 'Select Template'),
            ('simple_snippet', 'Simple'),
            ('eoy_snippet', 'Fundraising'),
            ('fxa_signup_snippet', 'Firefox Accounts Sign Up'),
            ('newsletter_snippet', 'Newsletter Sign Up'),
            ('send_to_device_snippet', 'Send to Device'),
            ('send_to_device_scene2_snippet', 'Send to Device Single Scene'),
            ('simple_below_search_snippet', 'Simple Below Search'),
        ),
        widget=TemplateChooserWidget,
        label='Template',
    )
    locale = forms.ModelChoiceField(
        queryset=models.Locale.objects.all(),
        empty_label='Select Locale',
        widget=AutoTranslatorWidget,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.id and getattr(self.instance, 'template_ng', None):
            self.fields['template_chooser'].disabled = True
            self.fields['template_chooser'].initial = self.instance.template_ng.code_name

    class Meta:
        model = models.ASRSnippet
        exclude = ['creator', 'created', 'modified']

    class Media:
        js = [
            'js/admin/inlineMover.js',
        ]

    def save(self, *args, **kwargs):
        snippet = super().save(*args, **kwargs)

        if (('status' in self.changed_data and
             self.instance.status == models.STATUS_CHOICES['Ready for review'])):
            send_slack('asr_ready_for_review', snippet)

        return snippet


class TargetAdminCustomForm(forms.ModelForm):
    class Meta:
        model = models.Target
        fields = ['name', 'jexl_expr']


class TargetAdminForm(forms.ModelForm):
    filtr_channels = fields.JEXLChannelField(
        'browserSettings.update.channel',
        choices=[
            ('release', 'Release'),
            ('esr', 'ESR'),
            ('beta', 'Beta'),
            ('aurora', 'Dev'),
            ('nightly', 'Nightly')
        ],
        widget=forms.CheckboxSelectMultiple(),
        required=False,
    )
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
    filtr_needs_update = fields.JEXLChoiceField(
        'needsUpdate',
        choices=((None, "I don't care"),
                 ('false', 'Yes',),
                 ('true', 'No')),
        required=False,
        label='Runs the latest version',
        label_suffix='?',
    )
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
    filtr_can_install_addons = fields.JEXLChoiceField(
        'xpinstallEnabled',
        choices=((None, "I don't care"),
                 ('true', 'Yes',),
                 ('false', 'No')),
        required=False,
        label='Can install Addons',
        label_suffix='?',
        help_text='Can the user install new Addons or is the functionality blocked by their Admin?'
    )
    filtr_total_addons = fields.JEXLRangeField(
        '',
        jexl={
            'minimum': 'addonsInfo.isFullData && {value} <= addonsInfo.addons|keys|length',  # noqa
            'maximum': 'addonsInfo.isFullData && addonsInfo.addons|keys|length < {value}' # noqa
        },
        choices=NUMBER_OF_ADDONS,
        required=False,
        label='Total installed Addons',
        help_text=("Total number of installed Addons. If you're suggesting more "
                   "Addons to the user make sure to select `Yes` in the "
                   "`Can install Addons?` filter."),
    )
    filtr_browser_addon = fields.JEXLAddonField(
        label='Browser Add-on',
        required=False,
        help_text=("If you're suggesting more Addons to the user make sure to select `Yes` in the "
                   "`Can install Addons?` filter."),
    )
    filtr_firefox_service = fields.JEXLFirefoxServicesField(
        label='Service Accounts',
        required=False,
    )
    filtr_operating_system = fields.JEXLChoiceField(
        'platformName',
        choices=(
            (None, "I don't care"),
            ('"win"', 'Windows',),
            ('"macosx"', 'macOS'),
            ('"linux"', 'Linux'),
        ),
        required=False,
        label='Operating System',
        label_suffix='?',
        help_text='User\'s operating system.'
    )

    class Meta:
        model = models.Target
        exclude = ['creator', 'created', 'modified']

    def generate_jexl_expr(self, data):
        jexl_expr_array = []
        for name, field in self.fields.items():
            if name.startswith('filtr_'):
                value = data[name]
                if value:
                    jexl_expr_array.append(field.to_jexl(value))
        return ' && '.join([x for x in jexl_expr_array if x])

    def save(self, *args, **kwargs):
        self.instance.jexl_expr = self.generate_jexl_expr(self.cleaned_data)
        return super().save(*args, **kwargs)


class JobAdminForm(forms.ModelForm):
    distribution = forms.ModelChoiceField(
        queryset=models.Distribution.objects.filter(
            distributionbundle__enabled=True
        ).distinct(),
        empty_label='Select Distribution',
        help_text=('Set a Distribution for this Job. It should be normally '
                   'left to Default. Useful for running Normandy experiments.'),
    )
