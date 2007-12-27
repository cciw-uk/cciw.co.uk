// Borrowed from Dojo, ported to MochiKit


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
