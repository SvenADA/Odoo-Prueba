odoo.define('hotel_online.date', function (require) {
	"use strict";
	//
	var core = require('web.core');
	var rpc = require("web.rpc");
	var _t = core._t;


    $('#dpd1').datepicker({
	    format: 'dd/mm/yyyy'
	 });
	$('#dpd2').datepicker({
	    format: 'dd/mm/yyyy'
	 });
});