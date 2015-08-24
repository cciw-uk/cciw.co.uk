$(document).ready(function () {

    var objToArray = function (obj) {
        var a = $.map(obj, function(value, index) { return [[parseInt(index, 10), value]]; });
        a.sort();
        return a;
    };

    var showTooltip = function (x, y, contents) {
        $('<div id="tooltip">' + contents + '</div>').css( {
            position: 'absolute',
            display: 'none',
            top: y + 5,
            left: x + 18,
            border: '1px solid #ddd',
            padding: '2px',
            'background-color': '#eee',
            opacity: 0.90
        }).appendTo("body").fadeIn(200);
    }

    var setupOfficerStatsChart = function ($placeholder) {
        var dataArrived = function (stat) {
        // Halve the references number to make it match the others.
            var ref_dates_data = $.map(objToArray(stat['Reference count']),
                                       function (val, index) {
                                           return [[val[0], val[1]/2]];
                                       });
            $.plot("#" + $placeholder.attr('id'),
                   [
                       {label: "<a href='" + $placeholder.attr('data-url-officer-list') + "' target='_blank'>Officer list</a>",
                        data: objToArray(stat['Officer list count'])},
                       {label: "<a href='" + $placeholder.attr('data-url-manage-crbs') + "' target='_blank'>Any DBSs</a>",
                        data: objToArray(stat['Any DBS count'])},
                       {label: "Up-to-date DBSs",
                        data: objToArray(stat['Valid DBS count'])},
                       {label: "<a href='" + $placeholder.attr('data-url-manage-applications') + "' target='_blank'>Applications</a>",
                        data: objToArray(stat['Application count'])},
                       {label: "<a href='" + $placeholder.attr('data-url-manage-references') + "' target='_blank'>References</a> \u00F7 2",
                        data: ref_dates_data}
                   ],
                   { xaxis: { mode: "time",
                              ticks: 12 },
                     yaxis: { min: 0 },
                     legend: { position: "nw" },
                     grid: { hoverable: true }
                   });
            var previousPoint = null;
            $placeholder.bind("plothover", function (event, pos, item) {
                if (item) {
                    if (previousPoint == null || (previousPoint.dataIndex != item.dataIndex || previousPoint.series != item.series)) {
                        previousPoint = item;
                        $("#tooltip").remove();
                        var d = new Date(item.datapoint[0]);
                        var num = item.datapoint[1];
                        var label = $('<div>' + item.series.label + '</div>').text();
                        var stat = num.toFixed(0);
                        if (item.series.label.match(/References/)) {
                            label = "References";
                            stat = (num * 2).toFixed(0);
                        }
                        showTooltip(item.pageX, item.pageY,
                                    label + ": <b>" + stat + "</b>" +
                                    "<br/><i>" + d.toLocaleDateString() + "</i>");
                    }
                } else {
                    $("#tooltip").remove();
                    previousPoint = null;
                }
            });
        }

        $.ajax({
            type: "GET",
            url: $placeholder.attr('data-url-officer-stats-json'),
            dataType: 'json',
            success: dataArrived
        });
    }

    $("[data-officer-stats-chart-placeholder]").each(function (index, elem) {
        setupOfficerStatsChart($(elem));
    });
});
