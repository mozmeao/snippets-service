;(function($, nunjucks) {
    var VARIABLE_TYPES = {
        text: 0,
        image: 1
    };

    // Setup Nunjucks
    if (!nunjucks.env) {
        // If not precompiled, create an environment with an HTTP loader.
        var loader = new nunjucks.HttpLoader('/static/templates');
        nunjucks.env = new nunjucks.Environment(loader);
    }
    var nj = nunjucks.env;

    /**
     * Initialize a snippet data widget in the given element.
     *
     * @param elem Element to use as the data widget container. This is
     *             expected to have a data-select-name attribute and a
     *             data-input-name attribute.
     */
    function SnippetDataWidget(elem) {
        this.$container = $(elem);
        var selectName = this.$container.data('selectName');
        var inputName = this.$container.data('inputName');

        this.$templateSelect = $('select[name="' + selectName + '"]');
        this.$dataInput = $('input[name="' + inputName + '"]');

        // Throw an error if we can't find the elements we need.
        if (!(this.$templateSelect.exists() && this.$dataInput.exists())) {
            throw ('Snippet data widget error: Template select or data ' +
                   'input not found!');
        }

        // Attempt to load the original snippet data if possible.
        this.originalData = {};
        try {
            this.originalData = JSON.parse(this.$dataInput.val());
        } catch(e) {
            // Do nothing.
        }

        // Hide the original input, bind events for the new widget, and trigger
        // onTemplateChange to insert the initial fields for the widget.
        this.$dataInput.hide();
        this.bindEvents();
        this.onTemplateChange();
    }

    SnippetDataWidget.prototype = {
        bindEvents: function() {
            var self = this;

            this.$templateSelect.change(function() {
                self.onTemplateChange();
            });

            this.$container.parents('form').submit(function() {
                self.onFormSubmit();
            });

            this.$container.on('change', '.image-input', function() {
                self.onImageFieldChange(this);
            });
        },

        /**
         * When the template select changes, update the data widget with new
         * fields for the variables from the new template.
         */
        onTemplateChange: function() {
            this.$container.empty();

            var $selected = this.$templateSelect.find(':selected');
            var variables = $selected.data('variables');
            if (variables) {
                this.$container.html(nj.render('snippetDataWidget.html', {
                    variables: variables,
                    types: VARIABLE_TYPES,
                    originalData: this.originalData
                }));
            }
        },

        /**
         * Update the image in an image field when the file input changes.
         */
        onImageFieldChange: function(input) {
            if (input.files.length < 1) {
                return;
            }

            // Check to see if this is an image
            var file = input.files[0];
            if (!file.type.match(/image.*/)) {
                return;
            }

            // Load file.
            var preview = $(input).siblings('img')[0];
            var reader = new FileReader();
            reader.onload = function(e) {
                preview.src = e.target.result;
            };
            reader.readAsDataURL(file);
        },

        /**
         * When the form is submitted, serialize the widget to JSON and fill in
         * the original data input.
         */
        onFormSubmit: function() {
            var data = {};
            this.$container.find('.variable').each(function() {
                var $item = $(this);
                var variable = $item.data('variable');

                switch ($item.data('type')) {
                    case VARIABLE_TYPES.text:
                        data[variable] = $item.find('input').val();
                        break;
                    case VARIABLE_TYPES.image:
                        data[variable] = $item.find('img').attr('src');
                        break;
                }
            });

            this.$dataInput.val(JSON.stringify(data));
        }
    };

    // Create widgets once the page is finished loading.
    $(function() {
        $('.template-data-widget').each(function() {
            new SnippetDataWidget(this);
        });
    });

    // Utility functions
    $.fn.exists = function() {
        return this.length !== 0;
    };
})(jQuery, nunjucks);
