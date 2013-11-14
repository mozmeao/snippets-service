(function($) {
    $(document).on('change', '.image-input', function() {
        if (this.files.length < 1) {
            return;
        }

        // Check to see if this is an image
        var file = this.files[0];
        if (!file.type.match(/image.*/)) {
            return;
        }

        // Load file.
        var $this = $(this);
        var preview = $this.siblings('img')[0];
        var store = $this.siblings('input')[0];
        var reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            store.value = e.target.result;
        };
        reader.readAsDataURL(file);
    });
})(jQuery);
