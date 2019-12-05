;
// Pure JS implementation of $(document).ready()
//
// Deals with DJango Admin loading first this file and then initializing jQuery.
document.addEventListener(
    'DOMContentLoaded',
    function() {
        function showTemplate() {
            django.jQuery('.inline-template').hide();

            let value = django.jQuery('#id_template_chooser').val();
            if (value) {
                django.jQuery('.' + value).show();
                autoTranslate();
            }
            // Template Chooser value is empty in two cases: a. When no template
            // has been selected yet and b. when user has view-only permissions.
            // In the later case there's a populated inline template which can
            // be matched with the query bellow.
            else {
                django.jQuery('.inline-related.has_original').parent('.inline-template').show();
            }
        }

        // Show correct template on load
        showTemplate();

        // Show correct template on change
        django.jQuery('#id_template_chooser').change(function() {
            showTemplate();
        });
    },
    false
);
