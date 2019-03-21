;$(function() {
    'use strict';

    function showTemplate() {
        let value = $('#id_template_chooser').val();
        $('.inline-template').hide();
        if (value) {
            $('.' + value).show();
        }
    }

    // Show correct template on load
    showTemplate();

    // Show correct template on change
    $('#id_template_chooser').change(function() {
        showTemplate();
    });
});
