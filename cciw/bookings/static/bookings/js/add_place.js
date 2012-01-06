(function($) {
     $(document).ready(function() {
         var readonly = ($('#readonly').val() == '1');
         var placesJsonUrl = $('#placesJsonUrl').val();
         var accountJsonUrl = $('#accountJsonUrl').val();
         var formInstanceId = $('#formInstanceId').val();

         if (readonly) {
             $('input,select,textarea').attr('disabled', 'disabled');
         } else {
             var userData = [];

             var escape = function(t) {
                 return t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&apos;");
             };

             var handleExistingPlacesData = function(json) {
                 var places = json['places'];
                 userData['places'] = places;
                 if (places.length > 0) {
                     var cont = $('#id_use_existing_radio_container');
                     $('#id_use_existing_btn').show();
                     for (var i=0; i < places.length; i++) {
                         var place = places[i];
                         var html = ("<label><input type='radio' name='use_which_booking' value='" +
                             i.toString() + "'>" + escape(place.first_name + " " + place.last_name)
                             + " " + place.created.substr(0,4) + "<br/>" +
                             "&nbsp;&nbsp; Post code: " + escape(place.post_code) + "<br/>" +
                             "&nbsp;&nbsp; GP: " + escape(place.gp_name) + "</label><br/>" );
                         cont.append(html);
                     }
                     var btn = $('#id_use_existing_radio_container input');
                     if (btn.length == 1) {
                         btn.attr('checked', 'checked');
                     }
                 }
             };

             var handleAccountData = function(json) {
                 var account = json['account'];
                 userData['account'] = account;
                 /* Easiest way to get them where we want is to move it using javascript */
                 var btn1 = $('#id_use_account_1_btn');
                 btn1.prependTo(btn1.prev('div.form').find('div.formrow'));
                 btn1.css({'float':'right'}).show();

                 var btn2 = $('#id_use_account_2_btn');
                 btn2.prependTo(btn2.prev('div.form').find('div.formrow'));
                 btn2.css({'float':'right'}).show();
             };

             var useExistingDataShow = function(ev) {
                 ev.preventDefault();
                 var popup = $('#id_use_existing_data_popup');
                 popup.css({
                     "position": "fixed",
                     "top": ($(window).height()/2 - popup.height()/2).toString() + "px",
                     "left": ($(window).width()/2 - popup.width()/2).toString() + "px"
                  });
                  popup.fadeIn("fast");
                  $('#id_popup_background').fadeIn('fast');
             };

             var useExistingDataClose = function(ev) {
                 $('#id_use_existing_data_popup').fadeOut('fast');
                 $('#id_popup_background').fadeOut('fast');
             };

             var address_attrs = [
                 'address',
                 'post_code',
                 'phone_number',
                 'contact_address',
                 'contact_post_code',
                 'contact_phone_number'
             ];

             var gp_info_attrs = [
                 'gp_name',
                 'gp_address',
                 'gp_phone_number'
             ];

             var all_attrs = [].concat(address_attrs, gp_info_attrs, [
                 'first_name',
                 'last_name',
                 'sex',
                 'date_of_birth',
                 'church',
                 'south_wales_transport',
                 'dietary_requirements',
                 'medical_card_number',
                 'last_tetanus_injection',
                 'allergies',
                 'regular_medication_required',
                 'learning_difficulties',
                 'serious_illness'
             ]);

             var useData = function(attrs) {
                 var radios = $('input[name=use_which_booking]');
                 var chosen = null;
                 for (var i=0; i < radios.length; i++) {
                     if (radios[i].checked) {
                         chosen = parseInt(radios[i].value, 10);
                         var place = userData['places'][chosen];
                         var mainform = document.addplaceform;
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

             var useAccountData = function(nameList, prefix) {
                 // exploit the fact that we've named things nicely.
                 $.each(nameList, function(idx, val) {
                     var control_id = '#id_' + prefix + val;
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
                 useAccountData(['address', 'post_code', 'phone_number'], '');
             };

             var useAccountForContactDetailsClick = function(ev) {
                 ev.preventDefault();
                 // copy contact_address, contact_post_code, contact_phone_number
                 useAccountData(['address', 'post_code', 'phone_number'], 'contact_');
             };

             $('#id_popup_close_btn').click(useExistingDataClose);
             $('#id_use_existing_btn').click(useExistingDataShow);
             $('#id_use_all_btn').click(useAllBtnClick);
             $('#id_use_address_btn').click(useAddressBtnClick);
             $('#id_use_gp_info_btn').click(useGPInfoBtnClick);
             $('#id_use_account_1_btn').click(useAccountForCamperAddressClick);
             $('#id_use_account_2_btn').click(useAccountForContactDetailsClick);

             // Typing enter on text boxes shouldn't activate the 'Use existing
             // data' button
             $('#id_addplaceform input[type=text]').keypress(function(ev) {
                 var code = (ev.keyCode || e.which);
                 if (code == 13) {
                     ev.preventDefault();
                 }
             });

             /* Load data about existing places */
             $.ajax({
                 type: "GET",
                 url: placesJsonUrl + '?exclude=' + formInstanceId,
                 dataType: "json",
                 success: handleExistingPlacesData
             });

             /* Load account data */
             $.ajax({
                 type: "GET",
                 url: accountJsonUrl,
                 dataType: "json",
                 success: handleAccountData
             });
         }
     });
})(jQuery);