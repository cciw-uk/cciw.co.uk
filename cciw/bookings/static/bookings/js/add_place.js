(function($, cciw) {
     $(document).ready(function() {
         // Note: Some part of this code are used by both admin interface and
         // user facing interface

         var readonly = ($('#readonly').val() == '1');

         if (readonly) {
             $('input,select,textarea').attr('disabled', 'disabled');
         } else {
             var userData = [];

             var escape = function(t) {
                 return t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&apos;");
             };

             var getAccountId = function () {
                 var elem = $('#id_account');
                 if (elem.length) {
                     // /admin/bookings/booking/.../
                     // See also getCurrentAccountId in admin_booking.js

                     var val = $('#id_account').val();
                     val = parseInt(val, 10);
                     // NaN madness
                     if (val == val) {
                         return val;
                     } else {
                         return undefined;
                     }
                 } else {
                     // /bookings/add-camper-details
                     return '';
                 }
             };

             var getAddPlaceForm = function () {
                 var elem = $('#booking_form');
                 if (elem.length) {
                     // /admin/bookings/booking/.../
                     return elem[0];
                 } else {
                     // /bookings/add-camper-details
                     return $('#id_addplaceform')[0];
                 }
             };

             var getCurrentBookingId = function () {
                 return $('#formInstanceId').val();
             }

             var handleExistingPlacesData = function(json) {
                 var places = json['places'];
                 userData['places'] = places;
                 if (places.length > 0) {
                     var cont = $('#id_use_existing_radio_container');
                     cont.empty();
                     $('.use_existing_btn').show();
                     for (var i=0; i < places.length; i++) {
                         var place = places[i];
                         var html = ("<label><input type='radio' name='use_which_booking' value='" +
                             i.toString() + "'>" + escape(place.first_name + " " + place.last_name)
                             + " " + place.created.substr(0,4) + "<br/>" +
                             "&nbsp;&nbsp; Post code: " + escape(place.address_post_code) + "<br/>" +
                             "&nbsp;&nbsp; GP: " + escape(place.gp_name) + "</label>" );
                         cont.append(html);
                     }
                     var btn = $('#id_use_existing_radio_container input');
                     if (btn.length == 1) {
                         btn.attr('checked', 'checked');
                     }
                 } else {
                     $('.use_existing_btn').hide();
                 }
             };

             var handleAccountData = function(json) {
                 var account = json['account'];
                 userData['account'] = account;
                 var btn1 = $('#id_use_account_1_btn');
                 btn1.show();

                 var btn2 = $('#id_use_account_2_btn');
                 btn2.show();
             };

             var useExistingDataShow = function(ev) {
                 ev.preventDefault();
                 var popup = $('#id_use_existing_data_popup');
                 popup.css({
                     "position": "fixed",
                     "top": Math.max($(window).height()/2 - popup.height()/2, 0).toString() + "px",
                     "left": Math.max($(window).width()/2 - popup.width()/2, 0).toString() + "px",
                     "max-height": ($(window).height()).toString() + "px",
                     "overflow": "auto"
                  });
                  popup.fadeIn("fast");
                  $('#id_popup_background').fadeIn('fast');
             };

             var useExistingDataClose = function(ev) {
                 $('#id_use_existing_data_popup').fadeOut('fast');
                 $('#id_popup_background').fadeOut('fast');
                 if (ev != undefined) {
                     // for links
                     ev.preventDefault();
                 }
             };

             var address_attrs = [
                 'address_line1',
                 'address_line2',
                 'address_city',
                 'address_county',
                 'address_country',
                 'address_post_code',
                 'phone_number',
                 'contact_name',
                 'contact_line1',
                 'contact_line2',
                 'contact_city',
                 'contact_county',
                 'contact_country',
                 'contact_post_code',
                 'contact_phone_number'
             ];

             var gp_info_attrs = [
                 'gp_name',
                 'gp_line1',
                 'gp_line2',
                 'gp_city',
                 'gp_county',
                 'gp_country',
                 'gp_post_code',
                 'gp_phone_number'
             ];

             var all_attrs = [].concat(address_attrs, gp_info_attrs, [
                 'first_name',
                 'last_name',
                 'sex',
                 'date_of_birth',
                 'church',
                 'dietary_requirements',
                 'medical_card_number',
                 'last_tetanus_injection',
                 'allergies',
                 'regular_medication_required',
                 'illnesses',
                 'can_swim_25m',
                 'learning_difficulties',
                 'serious_illness'
             ]);

             var leave_empty_fields = [
                 'dietary_requirements',
                 'church',
                 'allergies',
                 'regular_medication_required',
                 'illnesses',
                 'learning_difficulties'
             ];

             var useData = function(attrs) {
                 var radios = $('input[name=use_which_booking]');
                 var chosen = null;
                 for (var i=0; i < radios.length; i++) {
                     if (radios[i].checked) {
                         chosen = parseInt(radios[i].value, 10);
                         var place = userData['places'][chosen];
                         var mainform = getAddPlaceForm();
                         for (var j=0; j < attrs.length; j++) {
                             var attr = attrs[j];
                             if (mainform[attr].type == 'checkbox') {
                                 mainform[attr].checked = place[attr];
                             } else {
                                 if (place[attr] == null) {
                                     place[attr] = "";
                                 }
                                 mainform[attr].value = place[attr];
                             }
                             // If details are copied from something saved,
                             // value is guaranteed to be good. So we clear
                             // errors.
                             cciw.standardformClearError(mainform[attr].id);

                         }
                     }
                 }
                 if (chosen === null) {
                     alert('Please select a set of details on the left');
                 } else {
                     useExistingDataClose();
                 }
             };

             var useAllBtnClick = function(ev) {
                 ev.preventDefault();
                 useData(all_attrs);
             };

             var useAddressBtnClick = function(ev) {
                 ev.preventDefault();
                 useData(address_attrs);
             };

             var useGPInfoBtnClick = function(ev) {
                 ev.preventDefault();
                 useData(gp_info_attrs);
             };

             var useAccountData = function(nameList, mapping) {
                 $.each(nameList, function(idx, val) {
                     var control_id;
                     if (mapping != undefined) {
                         control_id = '#id_' + mapping[idx];
                     } else {
                         control_id = '#id_' + val;
                     }
                     $(control_id).val(userData['account'][val]);

                     // Data is not quite guaranteed to be good in this case
                     // (e.g. Booking.contact_phone_number is required, but
                     // BookingAccount.phone_number is not), so we trigger AJAX
                     // validation. With fewer fields than for copying place data,
                     // this is only a few AJAX calls.

                     $(control_id).change();
                 });
             };

             var useAccountForCamperAddressClick = function(ev) {
                 ev.preventDefault();
                 useAccountData(['address_line1',
                                 'address_line2',
                                 'address_city',
                                 'address_county',
                                 'address_country',
                                 'address_post_code',
                                 'phone_number']);
             };

             var useAccountForContactDetailsClick = function(ev) {
                 ev.preventDefault();
                 useAccountData(['name',
                                 'address_line1',
                                 'address_line2',
                                 'address_city',
                                 'address_county',
                                 'address_country',
                                 'address_post_code',
                                 'phone_number'],
                                ['contact_name',
                                 'contact_line1',
                                 'contact_line2',
                                 'contact_city',
                                 'contact_county',
                                 'contact_country',
                                 'contact_post_code',
                                 'contact_phone_number'])
             };

             $('#id_popup_close_btn').click(useExistingDataClose);
             $('.use_existing_btn').click(useExistingDataShow);
             $('#id_use_all_btn').click(useAllBtnClick);
             $('#id_use_address_btn').click(useAddressBtnClick);
             $('#id_use_gp_info_btn').click(useGPInfoBtnClick);
             $('#id_use_account_1_btn').click(useAccountForCamperAddressClick);
             $('#id_use_account_2_btn').click(useAccountForContactDetailsClick);

             // Typing enter on text boxes shouldn't activate the 'Use existing
             // data' button
             $('#id_addplaceform input[type=text]').keypress(function(ev) {
                 var code = (ev.keyCode || ev.which);
                 if (code == 13) {
                     ev.preventDefault();
                 }
             });

             var BAD_EMPTY_VALS = [
                 "n/a",
                 "not applicable",
                 "none",
                 "no",
                 "no diet",
                 "na",
                 "nil",
                 "no allergies",
                 "n0",
                 "none known",
                 "no known allergies",
                 "non",
                 "none that i know of",
                 "no medication",
                 "no known difficulties"
             ]

             var emptyFieldWarning = function ($elem) {
                 var $label = $elem.closest('div.field').find('label');
                 var val = $elem.val();
                 var normVal = $.trim(val).replace(/[\/\\\.\-]*$/, "").toLowerCase();
                 $label.find('.emptywarning').remove();
                 if (BAD_EMPTY_VALS.indexOf(normVal) != -1 ||
                     (normVal == "" && val != "")) {
                     $label.append('<span class="emptywarning"><br>Please leave empty if not applicable.</span>');
                 }
             };

             $.each(leave_empty_fields, function (idx, name) {
                 var $elem = $('#id_' + name);
                 emptyFieldWarning($elem);
                 $elem.bind('change', function (ev) {
                     emptyFieldWarning($(this));
                 });
             });

             /* Load data about existing places */
             var loadExistingPlacesData = function () {
                 $.ajax({
                     type: "GET",
                     data: {
                         'exclude': getCurrentBookingId(),
                         'id': getAccountId() // ignored by place_json, used by all_place_json
                     },
                     url: cciw.placesJsonUrl,
                     dataType: "json",
                     success: handleExistingPlacesData
                 });

                 /* Load account data */
                 $.ajax({
                     type: "GET",
                     data: {
                         'id': getAccountId() // ignored by account_json, used by all_account_json
                     },
                     url: cciw.accountJsonUrl,
                     dataType: "json",
                     success: handleAccountData
                 });
             };
             loadExistingPlacesData();
             $('#booking_form').on('change', '#id_account', loadExistingPlacesData);
         }
     });
})(jQuery, cciw);
