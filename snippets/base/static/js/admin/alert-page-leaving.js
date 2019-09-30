;
// Pure JS implementation of $(document).ready()
//
// Deals with DJango Admin loading first this file and then initializing jQuery.
document.addEventListener(
    'DOMContentLoaded',
    function() {
        // Translate content on locale select or template type select
        django.jQuery('form').areYouSure();
    },
    false
);
