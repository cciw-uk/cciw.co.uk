(function($) {
    $(document).ready(function() {
        "use strict";

        var getCurrentAccountId = function() {
            var val = $('#id_account').val();
            val = parseInt(val, 10);
            // NaN madness
            if (val == val) {
                return val;
            } else {
                return undefined;
            }
        }

        var getBookingId = function() {
            var bookingId = document.location.pathname.split("/").slice(-3, -2)[0];
            if (bookingId === "booking") {
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
                }
            });
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
            var data = $('#booking_form').serialize();
            var objId = parseInt(window.location.pathname.split('/').slice(-2, -1), 10);
            if (objId > 0) { // not NaN
                data = data + '&id=' + objId.toString()
            }
            $.ajax({
                type: "POST",
                url: cciw.getExpectedAmountDueUrl,
                data: data,
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
        $('div.field-camp').append('<div id="place-availability">');
        $('#id_amount_due').after('<input type="submit" id="id_amount_due_auto" value="">');
        $('#id_amount_due_auto').hide();

        // Wiring for event handlers
        getBookingProblems();
        $('input,select,textarea').change(getBookingProblems);

        getPlaceAvailability();
        $('#id_camp').change(getPlaceAvailability);

        getExpectedAmountDue();
        $('#id_price_type, #id_camp, #id_state').change(getExpectedAmountDue);

    });

})(jQuery || django.jQuery)
