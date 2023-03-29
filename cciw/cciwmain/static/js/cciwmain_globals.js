
(function($) {
    $(document).ready(function() {

        // JS confirmation for destructive actions
        // TODO this can probably be replaced with htmx and `hx-confirm`
        $('input[type=submit][data-js-confirm]').on('click', function(ev) {
            var msg = $(ev.target).attr('data-js-confirm-message');
            if (msg == undefined) {
                msg = "Are you sure?";
            }
            if (!confirm(msg)) {
                ev.preventDefault();
            }
        })

    });
})(jQuery);

// New style

// We can assume:
// - DOM is already loaded, because we are using `defer`,
// - all dependencies are loaded because of django-compressor and putting
//   this script last.

(function () {
    document.body.addEventListener("htmx:afterSettle", function(detail) {
        for (const dialog of detail.target.querySelectorAll('dialog[data-onload-showmodal]')) {
            dialog.addEventListener("close", () => {
                // Cleanup and avoid interaction issues by removing entirely
                dialog.remove();
            });
            dialog.showModal();
        };
    });

    document.body.addEventListener('closeModal', function() {
      $('dialog[open]')[0].close();
    });

})();
