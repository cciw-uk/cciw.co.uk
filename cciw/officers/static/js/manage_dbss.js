$(document).ready(function() {
    "use strict";
    $('form.dbs-form-sent').each(function (i, elem) {
        var $form = $(this);
        var officerId = $form.find('input[name=officer_id]').val();
        $form.submit(function (ev) {
            ev.preventDefault();
            jQuery.ajax({
                type: "POST",
                url: $form.attr('action'),
                data: $form.serialize(),
                dataType: 'json',
                success: function(data) {
                    // We need undo information, and we need to update the 'DBS form
                    // sent' column. We store undo information in a stack, on the undo
                    // button itself.
                    var btn = jQuery('#id_undo_' + officerId);
                    var lastSentCell = jQuery('#id_last_dbs_form_sent_' + officerId);
                    var highlightDiv = jQuery('tr.officer_dbs_row[data-officer-id="' + officerId + '"]');
                    if (btn.data('undoIdList') == null) {
                        btn.data('undoIdList', new Array);
                    }
                    if (btn.data('undoLastSentList') == null) {
                        btn.data('undoLastSentList', new Array);
                    }
                    var undoIdList = btn.data('undoIdList');
                    var undoLastSentList = btn.data('undoLastSentList');
                    undoIdList.push(data.dbsActionLogId);
                    undoLastSentList.push(lastSentCell.html());
                    lastSentCell.html('Just now');
                    highlightDiv.removeClass("requires_action");

                    // Add callback to undo button
                    btn.unbind();
                    btn.click(function() {
                        // Delete server side
                        jQuery.ajax({
                            type: "POST",
                            url: btn.attr('action'),
                            data: "dbsactionlog_id=" + undoIdList.pop().toString(),
                            dataType: 'json'
                        });
                        // Fix up cell client side
                        var lastSentCellContents = undoLastSentList.pop();
                        lastSentCell.html(lastSentCellContents);
                        if (undoIdList.length == 0) {
                            btn.hide();
                        }
                        if (lastSentCellContents.replace(/\n|\r| /g, '') == "Never") {
                            highlightDiv.addClass("requires_action");
                        }

                    });
                    btn.show();
                }
            });
        });
    });

    $('form.alert-leaders').each(function (idx, elem) {
        var $form = $(this);
        $form.submit(function (ev) {
            ev.preventDefault();
            var data = $form.serialize();
            var url = $form.attr('action');
            var newWindow =
                cciw.openTemporaryWindow(url + '?' + data,
                                         '_blank',
                                         "toolbar=yes,height=600,width=900,location=yes,menubar=yes,scrollbars=yes,resizable=yes");

            // Refresh the row when the child window is closed.
            var checkClosed = function () {
                if (newWindow.closed) {
                    console.log("Window closed, refreshing");
                    window.clearInterval(checkClosed);
                    refreshRow($form.closest('tr.officer_dbs_row'));
                }
            }
            window.setInterval(checkClosed, 200);
        });
    });

    function refreshRow ($row) {
        var officerId = $row.attr('data-officer-id');
        console.log("refreshing " + officerId);
        jQuery.ajax({
            type: 'GET',
            url: $('#id_officer_table').attr('data-url'),
            data: {'officer_id': officerId},
            dataType: 'text',
            success: function (data, textStatus, xhr) {
                console.log("Replacing with " + data);
                $row.replaceWith(jQuery(data));
            }
        });
    }

    // convert 'data-camps' into jQuery data
    $('#id_officer_table tr.officer_dbs_row').each(function(idx, elem) {
        $(elem).data('camps', $(elem).attr('data-camps').split(','));
    });

    function getSelectedCamps() {
        var selectedCamps = []
        $('#id_campselector input[type=checkbox]:checked').each(function(idx, elem) {
            selectedCamps.push($(elem).val());
        });
        return selectedCamps;
    }

    var initalSelectedCamps = getSelectedCamps();

    // Handler for camp checkboxes
    function selectedCampsChanged(ev) {
        var selectedCamps = getSelectedCamps();
        updateVisibleRows(selectedCamps);
        if (Modernizr.history) {
            var url = '';
            if (selectedCamps.length == 0) {
                // Special case - server side if there are no 'camp' query params,
                // we treat this as if all camps are selected. To get behaviour to
                // match, we specify an invalid camp slug
                url = '?camp=0';
            } else {
                url = "?" + $.map(selectedCamps,
                                  function(c) { return ("camp=" + c); }).join("&");
            }
            history.pushState({selectedCamps:selectedCamps}, '', url);
        } else {
            $('#id_campselector input[type=submit]').removeAttr('disabled');
        }
    }

    function updateVisibleRows(selectedCamps) {
        // Now go through all rows
        $('#id_officer_table tr.officer_dbs_row').each(function(idx, elem) {
            var show = false;
            var tr = $(elem);
            $.each(tr.data('camps'), function(idx, val) {
                if ($.inArray(val, selectedCamps) != -1) {
                    show = true;
                    return false;
                }
            });
            if (show) {
                tr.show();
            } else {
                tr.hide();
            }
        });
    }

    function updateCheckBoxes(selectedCamps) {
        $('#id_campselector input[type=checkbox]').each(function(idx, elem) {
            elem.checked = ($.inArray(elem.value, selectedCamps) != -1);
        });
    }

    function handleHistoryPopState(ev) {
        var state = ev.originalEvent.state;
        var selectedCamps;
        if (state == null) {
            selectedCamps = initalSelectedCamps;
        } else {
            selectedCamps = state.selectedCamps;
        }
        updateCheckBoxes(selectedCamps);
        updateVisibleRows(selectedCamps);
    }

    // Add event handler
    $('#id_campselector input[type=checkbox]').bind('change', selectedCampsChanged);

    if (Modernizr.history) {
        // Don't need the 'update' button at all, we can use history.pushState
        // to update the URL.
        $('#id_campselector input[type=submit]').hide();
        $(window).bind('popstate', handleHistoryPopState);
    } else {
        // Change the caption on 'update' box, because with javascript enabled it is
        // only useful for updating the URL, as other updates happen immediately.
        $('#id_campselector input[type=submit]').attr('disabled', 'disabled').val('Update page address');
    }

    // Run update on page load:
    updateVisibleRows(getSelectedCamps());

});
