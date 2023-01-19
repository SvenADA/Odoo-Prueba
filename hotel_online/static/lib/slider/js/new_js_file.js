$(document).ready(function() {
    $.urlParam = function(name) {
        console.log(name);
        var results = new RegExp('[/?&]' + name + '=([^&#]*)').exec(window.location.href);
        console.log("Results", results)
        return results;
    }

    var from_date = $.urlParam('from_date');
    if (from_date === null) {
        console.log("###############", from_date)
        from_date = '0'
    } else {
        type = typeof(from_date);
        console.log(type)
        from_date = decodeURIComponent(from_date[1])
    }
    console.log("After IFFFFFFFFFFFF==>>", from_date)
    $.urlParam('to_date');
    var minDate = new Date();
    $('#datePicker').datepicker({
        format: 'mm/dd/yyyy',
        minDate: minDate,
        setDate: new Date(),
        "autoclose": true,
    }).on('changeDate', function(e) {});

    var checkin = $('#dpd1').datepicker({
        startDate: new Date(),

    }).on('changeDate', function(ev) {
        var to_date = $.urlParam('to_date');
        if (to_date === null) {
            var date2 = $('#dpd1').datepicker('getDate', '+1d');
            date2.setDate(date2.getDate() + 1);
        } else {
            var date2 = decodeURIComponent(to_date[1])
        }
        var checkout = $('#dpd2').datepicker({
            startDate: date2
        }).datepicker('setDate', date2);
    }).datepicker('setDate', from_date);

});