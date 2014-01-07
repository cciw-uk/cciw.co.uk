
$(document).ready(function() {
    "use strict";

    var getCurrentAccountId = function() {
        var val = $('#id_hidden_account').val();
        val = parseInt(val, 10);
        // NaN madness
        if (val == val) {
            return val;
        } else {
            return undefined;
        }
    }

    var useAccountAddressForCamper = function(ev) {
        ev.preventDefault();
        var accId = getCurrentAccountId();
        if (accId == undefined) return;
        $.ajax({
            type: "GET",
            url: cciw.allAccountJsonUrl + "?id=" + accId.toString(),
            dataType: "json",
            success: function(json) {
                $('#id_address').val(json.account.address);
                $('#id_post_code').val(json.account.post_code);
                $('#id_phone_number').val(json.account.phone_number);
            }
        })
    };

    var useAccountAddressForContact = function(ev) {
        ev.preventDefault();
        var accId = getCurrentAccountId();
        if (accId == undefined) return;
        $.ajax({
            type: "GET",
            url: cciw.allAccountJsonUrl + "?id=" + accId.toString(),
            dataType: "json",
            success: function(json) {
                $('#id_contact_address').val(json.account.address);
                $('#id_contact_post_code').val(json.account.post_code);
                $('#id_contact_phone_number').val(json.account.phone_number);
            }
        })
    };

    var getBookingId = function () {
        var bookingId = document.location.pathname.split("/").slice(-2,-1)[0];
        if (bookingId === "add") {
            return null;
        } else {
            return bookingId;
        }
    };

    var getBookingProblems = function() {
        var formData = $('#booking_form').serialize();
        var bookingId = getBookingId();
        if (bookingId != null) {
            formData = formData + "&booking_id=" + bookingId;
        }
        $.ajax({
            type: "POST",
            url: cciw.bookingProblemsJsonUrl,
            dataType: "json",
            data: formData,
            success: function(json) {
                if (json.valid) {
                    if (json.problems.length == 0) {
                        $('#id_problems').html('<p>No problems found</p>');
                    } else {
                        $('#id_problems').html('<ul></ul>');
                        $.each(json.problems, function(idx, val) {
                            var html = $('<li></li>').text(val);
                            $('#id_problems ul').append(html);
                        });
                    }
                } else {
                    $('#id_problems').html('<i>Form has validation errors, ' +
                                           'please correct first. You can see validation errors ' +
                                           'by pressing "Save"</i>');
                }
            }});
    }

    var getPlaceAvailability = function() {
        var campId = $('#id_camp').val();
        if (campId == undefined || campId == "") {
            $('#place-availability').html('');
            return;
        }
        $.ajax({
            type: "GET",
            url: cciw.placeAvailabilityJsonUrl + '?camp_id=' + campId,
            dataType: "json",
            success: function(json) {
                if (json.status == 'success') {
                    var html = ('Places available: total=' + json.result.total.toString() +
                                ', male=' + json.result.male.toString() +
                                ', female=' + json.result.female.toString())
                    $('#place-availability').html(html);
                }
            }
        })
    };

    var getExpectedAmountDue = function() {
        $.ajax({
            type: "POST",
            url: cciw.getExpectedAmountDue,
            data: $('#booking_form').serialize(),
            dataType: "json",
            success: function(json) {
                if (json.status == 'success') {
                    if (json.amount == null) {
                        $('#id_amount_due_auto').hide();
                    } else {
                        $('#id_amount_due_auto').show().val('Set to £' + json.amount.toString());
                        $('#id_amount_due_auto').click(function(ev) {
                            ev.preventDefault();
                            $('#id_amount_due').val(json.amount.toString()).trigger('change');
                        });
                    }
                }
            }
        });
    };

    // Page changes
    $('#id_address').parent().append('<input type="submit" value="Copy address details from account"' +
                                     'id="id_use_account_for_camper">');
    $('#id_contact_address').parent().append('<input type="submit" value="Copy contact details from account"' +
                                     'id="id_use_account_for_contact">');
    $('div.field-camp').append('<div id="place-availability">');
    $('#id_amount_due').after('<input type="submit" id="id_amount_due_auto" value="">');
    $('#id_amount_due_auto').hide();


    // Wiring for event handlers

    $('#id_use_account_for_camper').click(useAccountAddressForCamper);
    $('#id_use_account_for_contact').click(useAccountAddressForContact);

    getBookingProblems();
    $('input,select,textarea').change(getBookingProblems);

    getPlaceAvailability();
    $('#id_camp').change(getPlaceAvailability);

    getExpectedAmountDue();
    $('#id_south_wales_transport,#id_price_type,#id_camp').change(getExpectedAmountDue);

});

