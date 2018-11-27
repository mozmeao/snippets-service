import json

from django.contrib import messages
from django.db import IntegrityError, transaction

from raven.contrib.django.models import client as sentry_client

from snippets.base.models import (STATUS_CHOICES, Addon, ASRSnippet, Campaign,
                                  SnippetTemplate, Target)
from snippets.base.forms import PROFILE_AGE_CHOICES, PROFILE_AGE_CHOICES_ASR, TargetAdminForm


@transaction.atomic
def duplicate_snippets_action(modeladmin, request, queryset):
    for snippet in queryset:
        snippet.duplicate(request.user)
duplicate_snippets_action.short_description = 'Duplicate selected snippets'  # noqa


@transaction.atomic
def migrate_snippets_action(modeladmin, request, queryset):
    for snippet in queryset:
        if not snippet.on_startpage_5:
            messages.error(request, 'Only Activity Stream Snippets can be migrated.')
            return

    migrated_snippets = 0
    skipped = 0
    try:
        with transaction.atomic():
            for snippet in queryset:
                # Skip already migrated
                if snippet.migrated_to:
                    skipped += 1
                    continue

                data = json.loads(snippet.data)

                data['do_not_autoblock'] = False

                # `rtl` and `blockable` variables are not used in ASR templates
                data.pop('rtl', None)
                data.pop('blockable', None)

                asrsnippet = ASRSnippet(
                    id=snippet.id,
                    creator=snippet.creator or request.user,
                    name=snippet.name,
                    data=json.dumps(data),
                    publish_start=snippet.publish_start,
                    publish_end=snippet.publish_end,
                    weight=snippet.weight,
                )

                _migrate_amp(asrsnippet)
                _migrate_campaign_to_asr(snippet, asrsnippet, request.user)
                _migrate_template(snippet, asrsnippet)
                _migrate_status(snippet, asrsnippet)
                _migrate_special_links(asrsnippet)
                asrsnippet.save()
                _migrate_locales(snippet, asrsnippet)
                _migrate_targeting(snippet, asrsnippet, request.user)
                snippet.migrated_to = asrsnippet
                snippet.save()
                asrsnippet.save()

                migrated_snippets += 1
    except (IntegrityError, KeyError):
        sentry_client.captureException()
        messages.error(request, 'Failed to migrate selected Snippets to ASRSnippets.')
        messages.error(request, f'Error while migrating {snippet.id}.')
    else:
        if migrated_snippets > 0:
            messages.success(
                request,
                (f'Selected Snippets ({migrated_snippets}) were successfully '
                 'migrated to ASRSnippets.'))

        if skipped:
            messages.info(
                request,
                f'Skipped {skipped} already migrated Snippets.')

migrate_snippets_action.short_description = 'Migrate to ASR Snippet'  # noqa


def _migrate_amp(asrsnippet):
    asrsnippet.data = asrsnippet.data.replace('&amp;', '&')


def _migrate_special_links(asrsnippet):
    asrsnippet.data = asrsnippet.data.replace('about:accounts', 'special:accounts')
    asrsnippet.data = asrsnippet.data.replace('uitour:showMenu:appMenu', 'special:appMenu')


def _migrate_targeting(snippet, asrsnippet, creator):
    def _transalate_yes_no_to_true_false(value):
        if value == 'any':
            return None
        elif value == 'yes':
            return 'true'
        elif value == 'no':
            return 'false'

    def _translate_bookmarks(value):
        if value < 0:
            return None
        return value

    def _translate_age(value):
        text = next(x[1] for x in PROFILE_AGE_CHOICES if x[0] == value)
        new_value = next(x[0] for x in PROFILE_AGE_CHOICES_ASR if x[1] == text)
        return new_value

    def _translate_any_to_none(value):
        if value == 'any':
            return None
        return value

    def _translate_version(value):
        value = _translate_any_to_none(value)
        if value:
            value = value.split('.', 1)[0]
        return value

    def _translate_is_developer(value):
        value = _translate_any_to_none(value)
        if value == 'yes':
            return '=='
        elif value == 'no':
            return '<'
        return value

    co = snippet.client_options

    addon = None
    if co['addon_check_type'] != 'any':
        name = co['addon_name']
        addon, _ = Addon.objects.get_or_create(name=name,
                                               guid=name,
                                               url=f'https://addons.mozilla.org/{name}')

    target = Target(creator=creator)
    data = {
        'name': f'Target for {snippet.name}',
        'on_release': snippet.on_release,
        'on_beta': snippet.on_beta,
        'on_aurora': snippet.on_aurora,
        'on_nightly': snippet.on_nightly,
        'on_esr': snippet.on_esr,
        'filtr_is_default_browser': _transalate_yes_no_to_true_false(co['is_default_browser']),
        'filtr_profile_age_created_0': _translate_age(co['profileage_lower_bound']),
        'filtr_profile_age_created_1': _translate_age(co['profileage_upper_bound']),
        'filtr_firefox_version_0': _translate_version(co['version_lower_bound']),
        'filtr_firefox_version_1': _translate_version(co['version_upper_bound']),
        'filtr_previous_session_end_0': _translate_age(co['sessionage_lower_bound']),
        'filtr_previous_session_end_1': _translate_age(co['sessionage_upper_bound']),
        'filtr_uses_firefox_sync': _transalate_yes_no_to_true_false(co['has_fxaccount']),
        'filtr_country': snippet.countries.all(),
        'filtr_is_developer': _translate_is_developer(co['is_developer']),
        'filtr_browser_addon_0': _translate_any_to_none(co['addon_check_type']),
        'filtr_browser_addon_1': addon.id if addon else None,
        'filtr_total_bookmarks_count_0': _translate_bookmarks(co['bookmarks_count_lower_bound']),
        'filtr_total_bookmarks_count_1': _translate_bookmarks(co['bookmarks_count_upper_bound']),
        # Search engine filter has not been used in AS Snippet.
        'filtr_current_search_engine': None,
        'client_match_rules': snippet.client_match_rules.all(),
    }

    form = TargetAdminForm(instance=target, data=data)
    form.is_valid()
    target = form.save()

    asrsnippet.target = target


def _migrate_locales(snippet, asrsnippet):
    for locale in snippet.locales.all():
        asrsnippet.locales.add(locale)


def _migrate_status(snippet, asrsnippet):
    if snippet.published:
        asrsnippet.status = STATUS_CHOICES['Published']
    elif snippet.ready_for_review:
        asrsnippet.status = STATUS_CHOICES['Ready for review']
    else:
        asrsnippet.status = STATUS_CHOICES['Draft']


def _migrate_template(snippet, asrsnippet):
    TEMPLATE_MAP = {
        '[Activity Stream] FxA sign up/sign in': '[AS Router] FxA sign up/sign in',
        '[Activity Stream] Fundraising': '[AS Router] Fundraising',
        '[Activity Stream] Newsletter Signup': '[AS Router] Newsletter',
        '[Activity Stream] Send to Device': '[AS Router] Send to Device',
        '[Activity Stream] Simple snippets with Button': '[AS Router] Simple Snippet with Button',
    }

    try:
        new_template_name = TEMPLATE_MAP[snippet.template.name]
    except KeyError:
        return None

    template = SnippetTemplate.objects.get(name=new_template_name)
    asrsnippet.template = template


def _migrate_campaign_to_asr(snippet, asrsnippet, creator):
    if snippet.campaign:
        campaign, created = Campaign.objects.get_or_create(
            name=snippet.campaign,
            slug=snippet.campaign,
            creator=creator,
        )
        asrsnippet.campaign = campaign
