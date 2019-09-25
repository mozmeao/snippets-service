///
//
// Finds all template fields that match `translation-` attributes of the
// selected #id_locale option and sets their value.
//
// All template fields start with `id_template_relation-` because Templates are
// StackedInline objects.
//
// Gets triggered every time the user changes locale.
///
;
function autoTranslate() {
    let selected_locale = django.jQuery('option:selected', '#id_locale')[0];
    if (! selected_locale.value) {
        return;
    }
    let attributes = selected_locale.attributes;
    let translations = JSON.parse(attributes.translations.nodeValue);
    Object.keys(translations).forEach(key => {
        django.jQuery("[id^='id_template_relation-']").filter(":visible").each(function(i, obj) {
            if (obj.name.endsWith('-' + key)) {
                django.jQuery(obj).val(translations[key]);
            }
        });
    });
}

// Pure JS implementation of $(document).ready()
//
// Deals with DJango Admin loading first this file and then initializing jQuery.
document.addEventListener(
    'DOMContentLoaded',
    function() {
        // Translate content on locale select or template type select
        django.jQuery('#id_locale').change(function() {
            autoTranslate();
        });
    },
    false
);
