;
// Pure JS implementation of $(document).ready()
//
// Deals with DJango Admin loading first this file and then initializing jQuery.
document.addEventListener(
    'DOMContentLoaded',
    function() {
        function showTemplate() {
            let value = django.jQuery('#id_template_chooser').val();
            django.jQuery('.inline-template').hide();
            if (value) {
                django.jQuery('.' + value).show();
            }
            autoTranslate();
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
