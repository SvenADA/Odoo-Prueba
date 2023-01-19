odoo.define('hotel_restaurant_pos.DB', function(require) {
	"use strict";

	var PosDB = require('point_of_sale.DB');
//	var _super_ = PosDB.prototype.add_products;
	var Screen = require('point_of_sale.screens');

	var _super_init_ = PosDB.prototype.init;
	
	
	PosDB.prototype.init = function(options) {
		_super_init_.call(this, options);
		this.limit = 1000;
		this.room_sorted = [];
		this.room_by_id = {};
	};
	
	PosDB.include({
		
		get_room_by_id: function(id){
	        return this.room_by_id[id];
	    },
		
		
		get_rooms_sorted: function(max_count){
	        max_count = max_count ? Math.min(this.room_sorted.length, max_count) : this.room_sorted.length;
	        var rooms = [];
	        for (var i = 0; i < max_count; i++) {
	            rooms.push(this.room_by_id[this.room_sorted[i]]);
	        }
	        return rooms;
	    },
	});
	
	
});