// A lot borrowed from Dojo, ported to MochiKit

function inArray(arr, value) {
	return findValue(arr, value) != -1;
}

function defaultFormFilter(/*DOMNode*/node) {
	// Used by encodeForm
	var type = (node.type||"").toLowerCase();
	var accept = false;
	if(node.disabled || !node.name) {
		accept = false;
	} else {
		// We don't know which button was 'clicked',
		// so we can't include any as an element to submit
		// Also can't submit files
		accept = !inArray(["file", "submit", "reset", "button", "image"], type);
	}
	return accept; //boolean
}

function encodeForm (/*DOMNode*/formNode, /*Function?*/formFilter){
	//summary: Converts the names and values of form elements into an URL-encoded
	//string (name=value&name=value...).
	//formNode: DOMNode
	//formFilter: Function?
	//	A function used to filter out form elements. The element node will be passed
	//	to the formFilter function, and a boolean result is expected (true indicating
	//	indicating that the element should have its name/value included in the output).
	//	If no formFilter is specified, then defaultFormFilter() will be used.
	if((!formNode)||(!formNode.tagName)||(!formNode.tagName.toLowerCase() == "form")){
		throw new Error("Attempted to encode a non-form element.");
	}
	if(!formFilter) { formFilter = defaultFormFilter; }
	var enc = encodeURIComponent;
	var values = [];

	for(var i = 0; i < formNode.elements.length; i++){
		var elm = formNode.elements[i];
		if(!elm || elm.tagName.toLowerCase() == "fieldset" || !formFilter(elm)) { continue; }
		var name = enc(elm.name);
		var type = elm.type.toLowerCase();

		if(type == "select-multiple"){
			for(var j = 0; j < elm.options.length; j++){
				if(elm.options[j].selected) {
					values.push(name + "=" + enc(elm.options[j].value));
				}
			}
		}else if(inArray(["radio", "checkbox"], type)){
			if(elm.checked){
				values.push(name + "=" + enc(elm.value));
			}
		}else{
			values.push(name + "=" + enc(elm.value));
		}
	}

	// now collect input type="image", which doesn't show up in the elements array
	var inputs = formNode.getElementsByTagName("input");
	for(var i = 0; i < inputs.length; i++) {
		var input = inputs[i];
		if(input.type.toLowerCase() == "image" && input.form == formNode
			&& formFilter(input)) {
			var name = enc(input.name);
			values.push(name + "=" + enc(input.value));
			values.push(name + ".x=0");
			values.push(name + ".y=0");
		}
	}
	return values.join("&") + "&"; //String
}


function add_form_onchange_handlers(form_id, mk_input_change_handler) {
	// Summary: Adds 'onchange' handlers to all inputs in a form
	// form_id: id of the form in the DOM
	// mk_input_change_handler: when called with one of the 
	//   form elements, returns a handler to be connected to 
	//   that element.
	var form = $(form_id);
	if (form == null) { 
		logError("Could not find form '" + form_id + "'.") ; 
		return null;
	}
	var inputs = form.elements;
	for (var i = 0; i < inputs.length; i++) {
		if (defaultFormFilter(inputs[i])) {
			connect(inputs[i], 'onchange', mk_input_change_handler(inputs[i]));
		}
	}
}

function cciw_validate_form(form_id) {
	// Summary: do AJAX validation of the form, using normal conventions,
	// returns a MochiKit Deferred object.
	var data = encodeForm($(form_id));
	var d = doXHR("?format=json", 
			{
				method:'POST', 
				sendContent: data,
				headers: {
				  "Content-Type": "application/x-www-form-urlencoded"
				} 
			}
	);
	return d;
}

function django_normalise_control_id(control_id) {
	// Summary: returns the id/name that corresponds to
	// the whole Django widget.  For MultiWidgets,
	// this strips the trailing _0, _1 etc.
	return control_id.replace(/^(.*)(_\d+)$/, "$1");
}

// standardform_* functions depend on the HTML in CciwFormMixin
function standardform_get_form_row(control_id) {
	var rowId = 'div_' + control_id;
	var row = $(rowId);

	if (row != null) { return row; }

	logError("Row for control " + control_id + " could not be found.");
	return null;
}

function standardform_display_error(control_id, errors) {
	var row = standardform_get_form_row(control_id);
	if (row == null) {
		return;
	}
	if (!hasElementClass(row, "validationErrorBottom")) {
		// insert <ul> before it
		var newnodes = DIV({'class':'validationErrorTop'}, 
				UL({'class':'errorlist'}, 
				    map(partial(LI, null), errors)));
		row.parentNode.insertBefore(newnodes, row)
		addElementClass(row, "validationErrorBottom");
	}
}

function standardform_clear_error(control_id) {
	var row = standardform_get_form_row(control_id);
	if (row == null) {
		return;
	}
	if (hasElementClass(row, "validationErrorBottom")) {
		removeElementClass(row, "validationErrorBottom");
		// there will be a previous sibling
		// which holds the error message
		removeEmptyTextNodes(row.parentNode);
		row.parentNode.removeChild(row.previousSibling);
	}
}

function standardform_get_validator_callback(control_name, control_id) {
	// Summary: returns a callback that should be called when
	// the AJAX validation request returns with data.
	var control_name_n = django_normalise_control_id(control_name);
	var control_id_n = django_normalise_control_id(control_id);
	function handler(req) {
		var json = evalJSONRequest(req);
		logDebug("JSON: " + req.responseText);
		var errors = json[control_name_n];
		if (errors != null && errors != undefined) {
			standardform_clear_error(control_id_n);
			standardform_display_error(control_id_n, errors);
		} else {
			standardform_clear_error(control_id_n);
		}
	};
	return handler;
}

function standardform_ajax_error_handler(err) { 
	logError("Err " + repr(err));
}

function standardform_get_input_change_handler(form_id, control_name, control_id) {
	// Summary: returns an event handler to be added to a control,
	// form_id: id of the form the control belongs to
	// control_name: the name of the control
	// control_id: id of the control
	function on_input_change(ev) {
		d = cciw_validate_form(form_id);
		d.addCallbacks(standardform_get_validator_callback(control_name, control_id), 
			       standardform_ajax_error_handler);
	};
	return on_input_change;
}

function standardform_add_onchange_handlers(form_id) {
	add_form_onchange_handlers(form_id, function(input) {
			return standardform_get_input_change_handler(form_id, input.name, input.id);
		});
}
