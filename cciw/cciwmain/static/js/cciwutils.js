// Misc extensions to jQuery and CCiW specific functions.

(function($) {
    // Define filteredDiv jQuery plugin
    $.fn.filteredDiv = function(containerDivSelector) {
        var filterbox = this;
        var containerDiv = $(containerDivSelector);

        var filter = function() {
            var term = $.trim(filterbox.val().toLowerCase());
            containerDiv.children().each(function(i, elem) {
                var $elem = $(elem);
                if (!term || $elem.text().toLowerCase().indexOf(term) != -1) {
                    $elem.show();
                } else {
                    $elem.hide();
                }
            });
        };

        filter();
        this.keyup(filter);

        // If the contents are changed, the clone needs to be refreshed, so the
        // 'refresh' event should be triggered on the filterbox.
        this.bind('refresh', function() {
            filter();
        });
        return this;

    };

    $(document).ajaxSend(function(event, xhr, settings) {
        function getCookie(name) {
            var cookieValue = null;
            if (document.cookie && document.cookie != '') {
                var cookies = document.cookie.split(';');
                for (var i = 0; i < cookies.length; i++) {
                    var cookie = $.trim(cookies[i]);
                    // Does this cookie string begin with the name we want?
                    if (cookie.substring(0, name.length + 1) == (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
        function sameOrigin(url) {
            // url could be relative or scheme relative or absolute
            var host = document.location.host; // host + port
            var protocol = document.location.protocol;
            var sr_origin = '//' + host;
            var origin = protocol + sr_origin;
            // Allow absolute or scheme relative URLs to same origin
            return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
                (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
                // or any other URL that isn't scheme relative or absolute i.e relative.
                !(/^(\/\/|http:|https:).*/.test(url));
        }
        function safeMethod(method) {
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        }

        if (!safeMethod(settings.type) && sameOrigin(settings.url)) {
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    });
})(jQuery);

var cciw = (function(pub, $) {

    var standardformClearError = function(control_id) {
        var row = $('#div_' + control_id);
        if (row.length == 0) {
            return;
        }
        if (row.hasClass("validationErrors")) {
            row.removeClass("validationErrors");
            // there will be a child which holds the error message
            row.find('.fieldMessages').remove();
        }
    };

    var genericAjaxErrorHandler = function(jqXHR, textStatus, errorThrown) {
        if (jqXHR.status === 400) {
            var json = $.parseJSON(jqXHR.responseText);
            var message = "";
            var errors = json.errors;
            var fields = Object.keys(errors);
            for (var i = 0; i < fields.length; i++) {
                var field = fields[i];
                var errs = errors[field];
                for (var j = 0; j < errs.length; j++) {
                    message += field + ": " + errs[j] + "\n";
                }
            }
            alert("Data not saved: \n" + message);
        } else {
            alert("Data not saved: " + textStatus);
        }
    };

    var openTemporaryWindow = function(url, windowName, windowFeatures) {
        if (url.indexOf("?") < 0) {
            url += "?";
        } else {
            url += "&";
        }
        url += "_temporary_window=1";
        return window.open(url, windowName, windowFeatures)
    }


    pub.standardformClearError = standardformClearError;
    pub.genericAjaxErrorHandler = genericAjaxErrorHandler;
    pub.openTemporaryWindow = openTemporaryWindow;

    return pub;
})(cciw || {}, jQuery);

(function($) {
    $(document).ready(function() {

        $('#menutoggle a').on('click', function(ev) {
            $('#menubar ul li').toggleClass('expanded');
        })

        // JS confirmation for destructive actions
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
