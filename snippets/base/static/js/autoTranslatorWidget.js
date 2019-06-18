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
;$(function() {
    'use strict';

    function autoTranslate() {
        let attributes = $('option:selected', '#id_locale')[0].attributes;
        let translations = JSON.parse(attributes.translations.nodeValue);
        Object.keys(translations).forEach(key => {
            $("[id^='id_template_relation-']").each(function(i, obj) {
                if (obj.name.endsWith('-' + key)) {
                    $(obj).val(translations[key]);
                }
            });
        });
    }

    // Translate content on locale select
    $('#id_locale').change(function() {
        autoTranslate();
    });
});
