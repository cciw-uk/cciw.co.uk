// We can assume:
// - DOM is already loaded, because we are using `defer`,
// - all dependencies are loaded because of django-compressor and putting
//   this script last.

(function () {
    document.body.addEventListener("htmx:afterSettle", function(detail) {
        for (const dialog of detail.target.querySelectorAll('dialog[data-js-onload-showmodal]')) {
            dialog.addEventListener("close", () => {
                // Cleanup and avoid interaction issues by removing entirely
                dialog.remove();
            });
            dialog.showModal();
        };
    });

    document.body.addEventListener('jsCloseModal', function() {
        document.querySelector('dialog[open]').close();
    });

})();
