////
// Move template inlines at a higher place in the page.
////
;$(function() {
    'use strict';
    $('.inline-template').each(function(index) {
        $(this).insertAfter($('.template-fieldset'));
    });
});
