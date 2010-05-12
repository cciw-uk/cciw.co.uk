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
            accept = $.inArray(type, ["file", "submit", "reset", "button", "image"]) != -1;
        }
        return accept;
    };

    var add_form_onchange_handlers = function(form_id, mk_input_change_handler) {
        // Summary: Adds 'onchange' handlers to all inputs in a form
        // form_id: id of the form in the DOM
        // mk_input_change_handler: when called with one of the
        //   form elements, returns a handler to be connected to
        //   that element.
        var form = $('#' + form_id);
        if (form == null) {
            return null;
        }
        var inputs = form.find('input,textarea,select');
        inputs.each(function(i, elem) {
            if (submittableControl(elem)) {
                $(elem).change(mk_input_change_handler(elem));
            }
        });
        return null;
    };

    var django_normalise_control_id = function(control_id) {
        // Summary: returns the id/name that corresponds to
        // the whole Django widget.  For MultiWidgets,
        // this strips the trailing _0, _1 etc.
        return control_id.replace(/^(.*)(_\d+)$/, "$1");
    };

    // standardform_* functions depend on the HTML in CciwFormMixin
    var standardform_display_error = function(control_id, errors) {
        var row = $('#div_' + control_id);
        if (row.size() == 0) {
            return;
        }
        if (!row.hasClass("validationErrorBottom")) {
            // insert <ul> before it
            var content = $("<div class='validationErrorTop'><ul class='errorlist'></ul</div>");
            $.each(errors, function(i, val) {
                       content.find("ul").append("<li>").html(val);
                   });
            row.before(content);
            row.addClass("validationErrorBottom");
        }
    };

    var standardform_clear_error = function(control_id) {
        var row = $('#div_' + control_id);
        if (row.size() == 0) {
            return;
        }
        if (row.hasClass("validationErrorBottom")) {
            row.removeClass("validationErrorBottom");
            // there will be a previous sibling
            // which holds the error message
            row.prev().remove();
        }
    };

    var standardform_get_validator_callback = function(control_name, control_id) {
        // Summary: returns a callback that should be called when
        // the AJAX validation request returns with data.
        var control_name_n = django_normalise_control_id(control_name);
        var control_id_n = django_normalise_control_id(control_id);
        var handler = function(json) {
            var errors = json[control_name_n];
            if (errors != null && errors != undefined) {
                standardform_clear_error(control_id_n);
                standardform_display_error(control_id_n, errors);
            } else {
                standardform_clear_error(control_id_n);
            }
        };
        return handler;
    };

    var standardform_get_input_change_handler = function(form_id, control_name, control_id) {
        // Summary: returns an event handler to be added to a control,
        // form_id: id of the form the control belongs to
        // control_name: the name of the control
        // control_id: id of the control
        var on_input_change = function(ev) {
            $.ajax({
                type: "POST",
                data: $('#' + form_id).serialize(),
                url: "?format=json",
                dataType: "json",
                success: standardform_get_validator_callback(control_name, control_id)
            });
        };
        return on_input_change;
    };

    // Public interface:
    pub.standardform_add_onchange_handlers = function(form_id) {
        add_form_onchange_handlers(form_id, function(input) {
            return standardform_get_input_change_handler(form_id, input.name, input.id);
        });
    };

    // To keep XHTML validation, we have to avoid
    // 'target', so use this hack instead.
    pub.externalLinks = function() {
        $("a[href][rel=external]").each(function(i, elem) {
                                            elem.target = "_blank";
                                        });
    };

    return pub;
})(cciw || {}, jQuery);
