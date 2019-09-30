////
// Move template inlines at a higher place in the page.
////
;
// Pure JS implementation of $(document).ready()
//
// Deals with DJango Admin loading first this file and then initializing jQuery.
document.addEventListener(
    'DOMContentLoaded',
    function() {
        django.jQuery('.inline-template').each(function(index) {
            django.jQuery(this).insertAfter(django.jQuery('.template-fieldset'));
        });
    },
    false
);
