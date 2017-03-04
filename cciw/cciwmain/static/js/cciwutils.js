// Misc extensions to jQuery and CCIW specific functions.

(function($) {
    // Define filteredDiv jQuery plugin
    $.fn.filteredDiv = function (containerDivSelector) {
        var filterbox = this;
        var containerDiv = $(containerDivSelector);

        var filter = function () {
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

    var submittableControl = function(node) {
        var type = (node.type || "").toLowerCase();
        var accept = false;
        if (node.disabled || !node.name) {
            accept = false;
        } else {
            // We don't know which button was 'clicked',
            // so we can't include any as an element to submit
            // Also can't submit files
            accept = $.inArray(type, ["file", "submit", "reset", "button", "image"]) == -1;
        }
        return accept;
    };

    var addFormOnchangeHandlers = function(form, mk_input_change_handler) {
        // Summary: Adds 'onchange' handlers to all inputs in a form
        // form: jQuery object containing the form
        // mk_input_change_handler: when called with one of the
        //   form elements, returns a handler to be connected to
        //   that element.
        var inputs = form.find('input,textarea,select');
        inputs.each(function(i, elem) {
            if (submittableControl(elem)) {
                $(elem).change(mk_input_change_handler(elem));
            }
        });
        return null;
    };

    var djangoNormaliseControlId = function(control_id) {
        // Summary: returns the id/name that corresponds to
        // the whole Django widget.  For MultiWidgets,
        // this strips the trailing _0, _1 etc.
        return control_id.replace(/^(.*)(_\d+)$/, "$1");
    };

    // standardform_* functions depend on the HTML in CciwFormMixin
    var standardformDisplayError = function(control_id, errors) {
        var row = $('#div_' + control_id);
        if (row.size() == 0) {
            return;
        }
        if (!row.hasClass("validationErrors")) {
            // insert <ul> inside it
            var content = $("<div class='fieldMessages'><ul class='errorlist'></ul></div>");
            $.each(errors, function(i, val) {
                       content.find("ul").append($('<li></li>').html(val));

                   });
            row.prepend(content);
            row.addClass("validationErrors");
        }
    };

    var standardformClearError = function(control_id) {
        var row = $('#div_' + control_id);
        if (row.size() == 0) {
            return;
        }
        if (row.hasClass("validationErrors")) {
            row.removeClass("validationErrors");
            // there will be a child which holds the error message
            row.find('.fieldMessages').remove();
        }
    };

    var standardformGetValidatorCallback = function(control_name, control_id) {
        // Summary: returns a callback that should be called when
        // the AJAX validation request returns with data.
        var control_name_n = djangoNormaliseControlId(control_name);
        var control_id_n = djangoNormaliseControlId(control_id);
        var handler = function(json) {
            var errors = json[control_name_n];
            if (errors != null && errors != undefined) {
                standardformClearError(control_id_n);
                standardformDisplayError(control_id_n, errors);
            } else {
                standardformClearError(control_id_n);
            }
        };
        return handler;
    };

    var standardformGetInputChangeHandler = function(form, control_name, control_id) {
        // Summary: returns an event handler to be added to a control,
        // form: jQuery object containing the form the control belongs to
        // control_name: the name of the control
        // control_id: id of the control
        var on_input_change = function(ev) {
            $.ajax({
                type: "POST",
                data: form.serialize(),
                url: "?format=json",
                dataType: "json",
                success: standardformGetValidatorCallback(control_name, control_id)
            });
        };
        return on_input_change;
    };

    var genericAjaxErrorHandler = function (jqXHR, textStatus, errorThrown) {
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

    var openTemporaryWindow = function (url, windowName, windowFeatures) {
        if (url.indexOf("?") < 0) {
            url += "?";
        } else {
            url += "&";
        }
        url += "_temporary_window=1";
        return window.open(url, windowName, windowFeatures)
    }

    // Public interface:
    pub.standardformAddOnchangeHandlers = function(form) {
        addFormOnchangeHandlers(form, function(input) {
            return standardformGetInputChangeHandler(form, input.name, input.id);
        });
    };

    pub.standardformClearError = standardformClearError;
    pub.genericAjaxErrorHandler = genericAjaxErrorHandler;
    pub.openTemporaryWindow = openTemporaryWindow;

    return pub;
})(cciw || {}, jQuery);

(function ($) {
    $(document).ready(function() {

        // Ajax callbacks for labelled forms
        $('form.ajaxify').each(function(i, elem) {
            cciw.standardformAddOnchangeHandlers($(this));
        });

        $('#menutoggle a').on('click', function (ev) {
            $('#menubar ul li').toggleClass('expanded');
        })

        // JS confirmation for destructive actions
        $('input[type=submit][data-js-confirm]').on('click', function (ev) {
            var msg = $(ev.target).attr('data-js-confirm-message');
            if (msg == undefined) {
                msg = "Are you sure?";
            }
            if (!confirm(msg)) {
                ev.preventDefault();
            }
        })

        // placeholder fallback for older browsers:
        var i = document.createElement('input');
        if (!('placeholder' in i)) {
            $('[placeholder]').focus(function() {
                var input = $(this);
                if (input.val() == input.attr('placeholder')) {
                    input.val('');
                    input.removeClass('placeholder');
                }
            }).blur(function() {
                var input = $(this);
                if (input.val() == '' || input.val() == input.attr('placeholder')) {
                    input.addClass('placeholder');
                    input.val(input.attr('placeholder'));
                }
            }).blur();
            $('[placeholder]').parents('form').submit(function() {
                $(this).find('[placeholder]').each(function() {
                    var input = $(this);
                    if (input.val() == input.attr('placeholder')) {
                        input.val('');
                    }
                });
            });
        }
    });
})(jQuery);
