// Misc extensions to jQuery and CCIW specific functions.

(function($) {
    $.fn.insertAtCaret = function(text) {
        return this.each(function(){
            if (document.selection) {
                //IE support
                this.focus();
                var sel = document.selection.createRange();
                sel.text = text;
                this.focus();
            }else if (this.selectionStart || this.selectionStart == '0') {
                //MOZILLA/NETSCAPE support
                var startPos = this.selectionStart;
                var endPos = this.selectionEnd;
                var scrollTop = this.scrollTop;
                this.value = this.value.substring(0, startPos) + text + this.value.substring(endPos,this.value.length);
                this.focus();
                this.selectionStart = startPos + text.length;
                this.selectionEnd = startPos + text.length;
                this.scrollTop = scrollTop;
            } else {
                this.value += text;
                this.focus();
            }
        });
    };

    $.fn.wrapAtCaret = function(startText, endText) {
        return this.each(function(){
            if (document.selection) {
                //IE support
                this.focus();
                var sel = document.selection.createRange();
                sel.text = startText + sel.text + endText;
                this.focus();
            } else if (this.selectionStart || this.selectionStart == '0') {
                //MOZILLA/NETSCAPE support
                var startPos = this.selectionStart;
                var endPos = this.selectionEnd;
                var scrollTop = this.scrollTop;
                var origText = this.value.substring(startPos, endPos);
                this.value = this.value.substring(0, startPos) + startText + origText + endText + this.value.substring(endPos,this.value.length);
                this.focus();
                if (origText.length == 0) {
                    this.selectionStart = startPos + startText.length;
                } else {
                    this.selectionStart = startPos + startText.length + origText.length + endText.length;
                }
                this.selectionEnd = this.selectionStart;
                this.scrollTop = scrollTop;
            } else {
                this.value += startText + endText;
                this.focus();
            }
        });
    };

    // Define multiSelectFilter jQuery plugin
    $.fn.multiSelectFilter = function(selectElem){
        var filterbox = this;
        // Make clone that stores options
        var select = $(selectElem);
        var clone;

        var init = function() {
            if (clone != undefined) {
                clone.remove();
            }
            clone = select.clone();
            clone.removeAttr('id').removeAttr('name').hide();
            clone.appendTo(select.parent());
        };

        var filter = function(){
            select.children().remove();
            var term = $.trim(filterbox.val().toLowerCase());
            var tmp = [];
            clone.children().each(function(i, elem) {
                                      if (!term || elem.text.toLowerCase().indexOf(term) != -1) {
                                          tmp.push($('<div>').append($(elem).eq(0).clone()).html());
                                      }
                                  });
            select.append(tmp.join(''));
        };

        init();
        this.keyup(filter);

        // If the contents are changed, the clone needs to be refreshed, so the
        // 'refresh' event should be triggered on the filterbox.
        this.bind('refresh', function() {
            init();
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
                    var cookie = jQuery.trim(cookies[i]);
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

    // Public interface:
    pub.standardformAddOnchangeHandlers = function(form) {
        addFormOnchangeHandlers(form, function(input) {
            return standardformGetInputChangeHandler(form, input.name, input.id);
        });
    };

    // To keep XHTML validation, we have to avoid
    // 'target', so use this hack instead.
    pub.externalLinks = function() {
        $("a[href][rel=external]").each(function(i, elem) {
                                            elem.target = "_blank";
                                        });
    };

    pub.standardformClearError = standardformClearError;

    $(document).ready(function() {
        $('form.ajaxify').each(function(i, elem) {
            pub.standardformAddOnchangeHandlers($(this));
        });
    });

    return pub;
})(cciw || {}, jQuery);
