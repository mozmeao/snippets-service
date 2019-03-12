;$(function() {
    'use strict';

    if ($('.inline-template').length > 1) {
        $('.inline-template').hide();
        $('#id_template_chooser').change(function() {
            let template = $(this).val();
            $('.inline-template').hide();
            if (template) {
                $inline = $('.' + template).show();
            }
        });
    }
});
