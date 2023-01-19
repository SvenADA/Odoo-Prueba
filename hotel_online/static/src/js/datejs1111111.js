$(document).ready(function() {
    console.log("11111111111111111111111111111");
    console.log($('#start_filter'));
    $('#start_filter').datepicker({ dateFormat: "dd.mm.yy", firstDay: 1 });
    $('#end_filter').datepicker({ dateFormat: "dd.mm.yy", firstDay: 1 });
});