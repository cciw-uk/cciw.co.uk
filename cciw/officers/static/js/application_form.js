$(document).ready(function() {
    // Various silly things that people do. These are almost certainly
    // errors, but we can't be sure, so just do warnings with Javascript.

    var checkField = function($field) {
        var val = $field.val();
        var errors = [];
        var validators = $field[0].validators || [];
        if (validators.length == 0) {
            return;
        }

        $.each(validators, function(idx, validator) {
            var msg = validator($field, val);
            if (msg) {
                errors.push(msg)
            }
        });

        var $container = $field.closest('div').find('.validation-warning');
        if (errors.length == 0) {
            $container.remove();
        } else {
            if ($container.length == 0) {
                $container = $('<span class="validation-warning"></span>');
                $container.insertAfter($field);
            }
            $container.text(errors.join(' '));
        }

    };


    var addValidator = function(field_selectors, validator) {
        $(field_selectors).each(function(idx, elem) {
            if (elem.validators === undefined) {
                elem.validators = [];
            }
            elem.validators.push(validator);
        });
    };

    var CHECK_BLOCK_CAPITAL_FIELDS = '#id_full_name, #id_birth_place, #id_address_firstline, #id_address_town, #id_address_county, #id_address_country, #id_referee1_name, #id_referee2_name, #id_referee1_address, #id_referee2_address, #id_christian_experience, #id_youth_experience';

    addValidator(CHECK_BLOCK_CAPITAL_FIELDS, function($field, val) {
        if (val.trim().length > 0) {
            if (val.trim() == "N/A") {
                return null;
            }
            if (val.trim() === "UK" && $field.attr('id') === "id_address_country") {
                return null;
            }
            if (val.match(/[A-Z]/) !== null) {
                if (val.toUpperCase() === val) {
                    return "Please ensure you are using mixed capitals, not block capitals.";
                }
            }
        }
        return null;
    });

    var REFEREE_NAME_FIELDS = '#id_referee1_name, #id_referee2_name';
    var CHECK_TITLE_FIELDS = REFEREE_NAME_FIELDS;

    var TITLES = ["dr", "rev", "reverend", "pastor", "mr", "ms", "mrs", "prof"];  // See also close_enough_referee_match
    addValidator(CHECK_TITLE_FIELDS, function($field, val) {
        if (val.trim().length > 0) {
            var firstWord = val.trim().split(/ /)[0].toLowerCase().replace(".", "");
            if (TITLES.indexOf(firstWord) != -1) {
                return "Please do not include titles such as " + firstWord.toUpperCase() + " in this field.";
            }
        }
        return null;
    });

    addValidator(REFEREE_NAME_FIELDS, function($field, val) {
        if (val.match(/[\[\]\(\),]/)) {
            return "Please only include the name in this field."
        }
        return null;
    });

    addValidator('#id_full_name', function($field, val) {
        if (val.trim().match(/ /) === null) {
            return "Please include your full name here, not just your first name.";
        }
    })

    var NA_SYNONYMS = ["N/A", "NOT APPLICABLE"];
    addValidator('input, textarea', function($field, val) {
        if (NA_SYNONYMS.indexOf(val.trim().toUpperCase()) !== -1) {
            return "Please leave blank if there is nothing applicable for this field."
        }
    });


    $("input, textarea").each(function(idx, elem) {
        if (elem.validators !== undefined) {
            var $field = $(elem);
            checkField($field);
            $field.on('change', function(ev) { checkField($field); });
        }
    });

    var setSaveAndContinueBtn = function() {
        $('input[name=_continue]').toggle(!$('input#id_finished').is(':checked'))
    };

    setSaveAndContinueBtn();
    $('input#id_finished').on('change', setSaveAndContinueBtn);

    // Move qualifications section to before declarations:
    $("fieldset.applicationillness").prepend(
        $('#qualifications-group')
    );

});
