;$(function() {
    'use strict';

    function showTemplate() {
        let value = $('#id_template_chooser').val();
        if (value) {
            $('.inline-template').hide();
            $('.' + value).show();
        }
    }

    if ($('.inline-template').length > 1) {
        $('.inline-template').hide();

        // Show correct template on load
        showTemplate();

        // Show correct template on change
        $('#id_template_chooser').change(function() {
            showTemplate();
        });
    }
});
