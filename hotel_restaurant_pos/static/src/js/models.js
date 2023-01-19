odoo.define('hotel_restaurant_pos.models', function (require) {
	"use strict";

	// console.log("Models   =======");
	// alert();

	var models = require('point_of_sale.models');
	var d = new Date();
    var field_utils = require('web.field_utils');
	var current_date = String(d.getFullYear()) + "-" + String(d.getMonth() + 1) + "-" + String(d.getDate());

	// console.log("Current Date  ", current_date)
	models.load_fields('pos.config', ['shop_id']);

	models.load_models({
		model: 'hotel.room.booking.history',
		fields: ['partner_id', 'history_id', 'id', 'name', 'check_in_date', 'check_out_date', 'booking_id'],
		domain: function (self) { return [[String('check_in_date'), '<=', current_date], [String('check_out_date'), '>=', current_date]]; },
		loaded: function (self, hotel_room_book_history) {
			self.hotel_room_book_history = hotel_room_book_history;
		},
	});

	models.load_models({
		model: 'sale.shop',
		fields: ['name', 'id', 'shop_img'],
		domain: function (self) { return [['id', '=', self.config.shop_id[0]]]; },
		loaded: function (self, sale_shop) {
			self.sale_shop = sale_shop;
		},

	});

	models.load_models({
		model: 'hotel.restaurant.tables',
		fields: ['id', 'name', 'shop_id', 'state', 'avl_state'],
		domain: function (self) { return [['state', '=', 'confirmed'], ['shop_id', '=', self.sale_shop[0].id], ['avl_state', '=', 'available']]; },
		loaded: function (self, hotel_rest_table) {
			self.hotel_rest_table = hotel_rest_table;
		},
	});

	models.load_models({
		model: 'hotel.restaurant.kitchen.order.tickets',
		fields: ['orderno', 'resno'],
		loaded: function (self, hotel_rest_kitchen) {
			self.hotel_rest_kitchen = hotel_rest_kitchen;
		},
	});

	models.load_models({
		model: 'hotel.restaurant.reservation',
		fields: ['name', 'start_date', 'end_date', 'tableno', 'cname'],
		domain: function (self) { return [['state', 'in', ['draft', 'confirm']]]; },
		loaded: function (self, hotel_rest_reserve) {
			self.hotel_rest_reserve = hotel_rest_reserve;
		},
	});

	models.load_models({
		model: 'hotel.reservation',
		fields: ['id', 'name', 'folio_id'],
		domain: function (self) { return [['state', 'in', ['confirm']]]; },
		loaded: function (self, hotel_reserve) {
			self.hotel_reserve = hotel_reserve;
		},
	});

	models.load_models({
		model: 'hotel.folio',
		fields: ['id', 'name', 'reservation_id', 'state', 'room_lines', 'order_id', 'partner_id'],
		loaded: function (self, hotel_folio) {
			self.hotel_folio = hotel_folio;
		},
	});

	models.load_models({
		model: 'hotel_folio.line',
		fields: ['id', 'folio_id', 'order_line_id', 'checkin_date', 'checkout_date', 'categ_id'],
		loaded: function (self, hotel_folio_line) {
		    hotel_folio_line.forEach(function(line) {
    		    var checkin_date = field_utils.format.datetime(moment(line.checkin_date), null, {timezone: true});
    		    var checkout_date = field_utils.format.datetime(moment(line.checkout_date), null, {timezone: true});
                line.checkin_date = checkin_date
    		    line.checkout_date = checkout_date
            });
			self.hotel_folio_line = hotel_folio_line;
		},
	});


	// Extended the Order model
	var _super_order = models.Order.prototype;
	models.Order = models.Order.extend({
		initialize: function (attr, options) {
			_super_order.initialize.call(this, attr, options);
			this.folio_line_id = this.folio_line_id || false;
			this.folio_ids = this.folio_ids || false;
			this.room_name = this.room_name || false;
			this.env = this.get('env');
		},

		set_folio_line_id: function (folio) {
			this.folio_line_id = folio;
		},
		get_folio_line_id: function () {
			return this.folio_line_id;
		},

		set_folio_ids: function (folio_id) {
			this.folio_ids = folio_id;
		},
		get_folio_ids: function () {
			return this.folio_ids;
		},

		set_room_name: function (room) {
			this.room_name = room;
		},
		get_room_name: function () {
			return this.room_name;
		},

		init_from_JSON: function (json) {
			_super_order.init_from_JSON.call(this, json);
			this.folio_line_id = json.folio_line_id;
			this.folio_ids = json.folio_ids;
			this.room_name = json.room_name;
		},

		export_as_JSON: function () {
			var orderJson = _super_order.export_as_JSON.call(this);
			orderJson.folio_line_id = this.get_folio_line_id();
			orderJson.folio_ids = this.get_folio_ids();
			orderJson.room_name = this.get_room_name();
			return orderJson;
		},

		export_for_printing: function () {
			var Json = _super_order.export_for_printing.call(this);
			Json.folio_line_id = this.get_folio_line_id();
			Json.folio_ids = this.get_folio_ids();
			Json.room_name = this.get_room_name();
			return Json;
		},

	});

});

