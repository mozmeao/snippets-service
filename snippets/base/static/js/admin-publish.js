django.jQuery(document).ready(function() {
    django.jQuery('[data-tool-name="publish_object"]').on("click", function(event) {
        function confirmation() {
            let answer = confirm("Really publish Snippet?");
            if (!answer) {
                event.preventDefault();
            }
        }
        confirmation();
    });
});
