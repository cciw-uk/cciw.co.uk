$(document).ready(function () {

    $("[data-officer-stats-chart-placeholder]").each(function (index, elem) {
        var $elem = $(elem);
        var data = JSON.parse($elem.attr('data-chart'));
        data.title = null;
        $.extend(data.legend, {
            align: "left",
            verticalAlign: "top",
            layout: "vertical",
            backgroundColor: "#F0F0F0",
            borderColor: "#E0E0E0",
            borderWidth: 1,
            floating: true
        });
        data.yAxis = [{
            min: 0,
            opposite: true,
            title: {
                enabled: false
            }
        }];
        data.credits = {
            enabled: false
        };
        $elem.highcharts(data);
    });

    $('[data-officer-stats-trend-chart-placeholder]').each(function (index, elem) {
        var $elem = $(elem);
        var data = JSON.parse($elem.attr('data-chart'));
        data.title = null;
        data.yAxis = [{
            min: 0,
            max: 100,
            title: {
                enabled: false
            }
        }];
        $elem.highcharts(data);
    });

    $('[data-booking-progress-stats-chart-placeholder]').each(function (index, elem) {
        var $elem = $(elem);
        var data = JSON.parse($elem.attr('data-chart'));
        data.title = null;
        data.yAxis = [{
            min: 0,
            title: {
                text: "Number of bookings"
            }
        }];
        $elem.highcharts(data);
    });

    $('[data-booking-summary-stats-chart-placeholder]').each(function (index, elem) {
        var $elem = $(elem);
        var data = JSON.parse($elem.attr('data-chart'));
        $.extend(data, {
            title: null,
            chart: {
                type: 'column'
            },
            tooltip: {
                headerFormat: '<b>{point.x}</b><br/>',
                pointFormat: '{series.name}: {point.y}<br/>Total: {point.stackTotal}'
            },
            plotOptions: {
                column: {
                    stacking: 'normal',
                    dataLabels: {
                        enabled: true,
                    }
                }
            },
            yAxis: [{
                min: 0,
                title: {
                    text: "Places"
                },
                stackLabels: {
                    enabled: true,
                    style: {
                        fontWeight: 'bold',
                    }
                }
            }]
        });
        $elem.highcharts(data);
    });
});
