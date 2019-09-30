;
// Pure JS implementation of $(document).ready()
//
// Deals with DJango Admin loading first this file and then initializing jQuery.
document.addEventListener(
    'DOMContentLoaded',
    function() {
        var clipboard = new ClipboardJS('.btn');
        clipboard.on('success', function(e) {
            e.trigger.innerText='Copied!';
            setTimeout(function() { e.trigger.innerText=e.trigger.attributes.originalText.nodeValue; }, 1000);
            e.clearSelection();
        });
    },
    false
);
