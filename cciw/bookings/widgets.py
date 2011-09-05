from autocomplete.widgets import AutoCompleteWidget


class AccountAutoCompleteWidget(AutoCompleteWidget):
    AC_TEMPLATE = u'''
        <input type="hidden" name="%(name)s" id="id_hidden_%(name)s" value="%(hidden_value)s" />
        <input type="text" value="%(value)s" %(attrs)s />
        <a href="javascript:void(0)" class="add-another" id="add_id_account"> New account </a> | 

        <a href="javascript:void(0)" class="add-another" id="edit_id_account"> Edit </a>


<script type="text/javascript">
var %(var_name)s = new autocomplete("%(name)s", "%(url)s", %(force_selection)s);

// For 'add another', we need slightly customised behaviour instead of showAddAnotherPopup

function showAddAnotherAccountPopup(ev) {
    ev.preventDefault();
    var name = 'id_account';
    name = id_to_windowname(name);
    var href = '/admin/bookings/bookingaccount/add/?_popup=1&name=' + encodeURIComponent($('#id_account').val());
    var win = window.open(href, name, 'height=500,width=800,resizable=yes,scrollbars=yes');
    win.focus();
}

function showEditAccountPopup(ev) {
    ev.preventDefault();
    var name = 'id_account';
    name = id_to_windowname(name);
    var account_id = $('#id_hidden_account').val();
    if (/^\d+$/.test(account_id)) {
        var href = '/admin/bookings/bookingaccount/' + account_id + '/?_popup=1';
        var win = window.open(href, name, 'height=500,width=800,resizable=yes,scrollbars=yes');
    } else {
        alert('No account selected');
    }
    win.focus();
}


// Hack: we need dismissAddAnotherPopup to do something different,
// so we monkey patch it.

var originalDismissAddAnotherPopup = window.dismissAddAnotherPopup;
window.dismissAddAnotherPopup = function(win, newId, newRepr) {
    newId = html_unescape(newId);
    newRepr = html_unescape(newRepr);
    var name = windowname_to_id(win.name);
    var elem = document.getElementById(name);
    if (name == 'id_account') {
        $('#id_hidden_account').val(newId);
        $('#id_account').val(newRepr);
        win.close();
    } else {
        originalDismissAddAnotherPopup(win, newId, newRepr);
    }
}

$(document).ready(function(ev){
    $('#add_id_account').click(showAddAnotherAccountPopup);
    $('#edit_id_account').click(showEditAccountPopup);
    // autocomplete doesn't do quite what we want with focusout:
    $('#id_account').unbind('focusout');
});

</script>
'''

    class Media:
        extend = False
        css = {'all': ('https://ajax.googleapis.com/ajax/libs/jqueryui/1.8/themes/base/jquery-ui.css',),
               }
        js = (
            "https://ajax.googleapis.com/ajax/libs/jquery/1.4/jquery.js",
            "https://ajax.googleapis.com/ajax/libs/jqueryui/1.8/jquery-ui.js",
            "js/jquery_autocomplete.js")

