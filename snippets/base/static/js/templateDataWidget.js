/* global nunjucks:false */
;(function($, nunjucks) {
    'use strict';

    var VARIABLE_TYPES = {
        text: 0,
        image: 1,
        smalltext: 2,
        checkbox: 3,
        body: 4
    };

    // Setup Nunjucks
    if (!nunjucks.env) {
        // If not precompiled, create an environment with an HTTP loader.
        var loader = new nunjucks.HttpLoader('/static/templates');
        nunjucks.env = new nunjucks.Environment(loader, {
            autoescape: true
        });
    } else {
        nunjucks.env.autoesc = true;
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
        var self = this;

        this.$container = $(elem);
        this.dataListeners = [];
        this.dataChanged = false;

        var selectName = this.$container.data('selectName');
        var inputName = this.$container.data('inputName');

        this.$templateSelect = $('select[name="' + selectName + '"]');
        this.$dataInput = $('input[name="' + inputName + '"]');

        this.snippetSizeThreshold = this.$container.data('snippetSizeLimit')
        this.snippetImgSizeThreshold = this.$container.data('snippetImgSizeLimit');

        // Throw an error if we can't find the elements we need.
        if (!(this.$templateSelect.exists() && this.$dataInput.exists())) {
            throw ('Snippet data widget error: Template select or data ' +
                   'input not found!');
        }

        // Attempt to load the original snippet data if possible.
        this.originalData = {};
        try {
            this.originalData = JSON.parse(this.$dataInput.val());
        } catch (e) {
            // Do nothing.
        }

        // Hide the original input, bind events for the new widget, and trigger
        // onTemplateChange to insert the initial fields for the widget.
        this.$dataInput.hide();
        this.bindEvents();
        this.onTemplateChange();

        // Set an interval to run the dataListeners when the data has changed.
        // This helps avoid triggering on each and every keypress.
        setInterval(function() {
            if (self.dataChanged) {
                self.dataChanged = false;
                for (var k = 0; k < self.dataListeners.length; k++) {
                    self.dataListeners[k].call();
                }
            }
        }, 500);
    }

    SnippetDataWidget.prototype = {
        bindEvents: function() {
            var self = this;

            $(document).ready(function() {
                self.$container.find('img').each(function(_, img) {
                    if (!img.src) return;
                    var data = img.src.split(',')[1];
                    if (!data) return;
                    var binary = atob(data.replace(/\s/g, ''));

                    if (binary.length / 1024 > self.snippetImgSizeThreshold) {
                        var msg = 'Icon file too large. Consider using a smaller ' +
                                  'icon. (Under ' + self.snippetImgSizeThreshold + 'kb)';
                        $(img).siblings('.fileSize').html(msg).css('color', 'red');
                    } else {
                        $(img).siblings('.fileSize').html('');
                    }
                });
            });

            this.$templateSelect.change(function() {
                self.onTemplateChange();
            });

            this.$container.parents('form').submit(function() {
                return self.onFormSubmit();
            });

            this.$container.on('change', '.image-input', function() {
                self.onImageFieldChange(this);
            });

            this.$container.on('click', '.image-input-remove', function(event) {
                event.preventDefault();
                var imageInput = $(event.target).siblings('input')[0];
                $(imageInput).val('');
                self.onImageFieldChange(imageInput);
            });

            this.$container.on('input', 'textarea', function() {
                self.triggerDataChange();
            });

            this.$container.on('input', 'input', function() {
                self.triggerDataChange();
            });

            this.$container.on('change', 'input[type="checkbox"]', function() {
                self.triggerDataChange();
            });
        },

        /**
         * Register a callback to be run whenever the template data changes.
         */
        onDataChange: function(callback) {
            this.dataListeners.push(callback);
        },

        /**
         * Notify listeners that the template data has changed.
         */
        triggerDataChange: function() {
            this.dataChanged = true;
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

            this.triggerDataChange();
        },

        /**
         * Update the image in an image field when the file input changes.
         */
        onImageFieldChange: function(input) {
            var self = this;
            var preview = $(input).siblings('img')[0];
            if (input.files.length < 1) {
                preview.src = '';
                preview.style.display = 'none';
                self.triggerDataChange();
                return;
            }
            preview.style.display = 'block';

            // Check to see if this is an image
            var file = input.files[0];
            if (!file.type.match(/image.*/)) {
                return;
            }

            if (file.size / 1024 > self.snippetImgSizeThreshold) {
                var msg = 'Icon file too large. Consider using a smaller ' +
                          'icon. (Under ' + self.snippetImgSizeThreshold + 'kb)';
                $(input).siblings('.fileSize').html(msg).css('color', 'red');
            } else {
                $(input).siblings('.fileSize').html('');
            }

            // Load file.
            var reader = new FileReader();
            reader.onload = function(e) {
                preview.src = e.target.result;
                self.triggerDataChange();
            };
            reader.readAsDataURL(file);
        },

        /**
         * Generate an object containing the currently entered template data.
         */
        generateData: function() {
            var data = {};
            this.$container.find('.variable').each(function() {
                var $item = $(this);
                var variable = $item.data('variable');

                switch ($item.data('type')) {
                    case VARIABLE_TYPES.body:
                    case VARIABLE_TYPES.text:
                        data[variable] = $item.find('textarea').val();
                        break;
                    case VARIABLE_TYPES.image:
                        data[variable] = $item.find('img').attr('src');
                        break;
                    case VARIABLE_TYPES.smalltext:
                        data[variable] = $item.find('input').val();
                        break;
                    case VARIABLE_TYPES.checkbox:
                        data[variable] = $item.find('input[type="checkbox"]').is(':checked');
                        break;
                }
            });
            return data;
        },

        getTemplateId: function() {
            return this.$templateSelect.val();
        },

        /**
         * When the form is submitted, serialize the widget to JSON and fill in
         * the original data input.
         */
        onFormSubmit: function() {
            var confirmed;
            var self = this;
            this.$dataInput.val(JSON.stringify(this.generateData()));
            this.$activityStreamInput = this.$form.find('input[name="activity_stream"]');
            var data = (this.$dataInput.serialize() + '&template_id=' + this.$templateSelect.val() +
                        '&skip_boilerplate=true' + '&activity_stream=' + $activityStreamInput);
            $.ajax({
                type: 'POST',
                url:'/preview/',
                data: data,
                async: false,
                success: function(data, textStatus, request) {
                    var size = new Blob([data], {type: 'text/html'}).size / 1024;
                    if (size > self.snippetSizeThreshold) {
                        var msg = "This snippet is over " + self.snippetSizeThreshold + "kb threshold! (" +
                            size.toFixed() + "kb) Are you sure you want to save it?";
                        confirmed = confirm(msg);
                    }
                }
            });
            return confirmed;
        }
    };

    /**
     * Initialize a snippet preview in the given element.
     *
     * @param elem Element to use as the container for the preview.
     */
    function SnippetPreview(elem, dataWidget) {
        var self = this;
        this.dataWidget = dataWidget;

        this.$container = $(elem);
        this.$form = $(nj.render('snippetPreviewForm.html', {
            preview_url: this.$container.data('previewUrl')
        }));
        this.$container.append(this.$form);

        this.$dataInput = this.$form.find('input[name="data"]');
        this.$templateIdInput = this.$form.find('input[name="template_id"]');
        this.$activityStreamInput = this.$form.find('input[name="activity_stream"]');

        this.$form.submit(function() {
            self.onFormSubmit();
        });
    }

    SnippetPreview.prototype = {
        onFormSubmit: function() {
            var data = JSON.stringify(this.dataWidget.generateData());
            this.$dataInput.val(data);
            this.$templateIdInput.val(this.dataWidget.getTemplateId());
            this.$activityStreamInput.val(document.querySelector('#id_on_startpage_5').checked);
        }
    };

    // Initialize the data widget and preview frame when the page loads.
    $(function() {
        var dataWidget = new SnippetDataWidget($('.template-data-widget'));
        new SnippetPreview($('.snippet-preview-container'), dataWidget);
    });

    // Utility functions
    $.fn.exists = function() {
        return this.length !== 0;
    };
})(jQuery, nunjucks);
