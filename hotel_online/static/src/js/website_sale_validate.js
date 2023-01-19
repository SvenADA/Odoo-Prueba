odoo.define('hotel_online.validate', function (require) {
	"use strict";
	//
	var ajax = require('web.ajax');
	var Dialog = require('web.Dialog');
	var core = require('web.core');
	var rpc = require("web.rpc");
	var _t = core._t;

	$(document).ready(function () {
		if ($(".checkout_autoformat").length) {
			$('.oe_website_sale').on('change', "select[name='country_id']", function () {
				setTimeout(function () {
					//	            	alert("Comingggggg");
					if ($("#country_id").val()) {
						ajax.jsonRpc("/shop/country_infos/" + $("#country_id").val(),
							'call', {
							mode: 'shipping',
						}).then(
							function (data) {
								// placeholder phone_code
								var selectStates = $("select[name='state_id']");

								// dont reload state at first loading (done in qweb)
								if (selectStates.data('init') === 0 || selectStates.find('option').length === 1) {
									if (data.states.length) {
										selectStates.html('');
										_.each(data.states, function (x) {
											var opt = $('<option>').text(x[1])
												.attr('value', x[0])
												.attr('data-code', x[2]);
											selectStates.append(opt);
										});
										selectStates.parent('div').show();
									}
									else {
										selectStates.val('').parent('div').hide();
									}
									selectStates.data('init', 0);
								}
								else {
									selectStates.data('init', 0);
								}

								// manage fields order / visibility
								if (data.fields) {
									if ($.inArray('zip', data.fields) > $.inArray('city', data.fields)) {
										$(".div_zip").before($(".div_city"));
									}
									else {
										$(".div_zip").after($(".div_city"));
									}
									var all_fields = ["street", "zip", "city", "country_name"]; // "state_code"];
									_.each(all_fields, function (field) {
										$(".checkout_autoformat .div_" + field.split('_')[0]).toggle($.inArray(field, data.fields) >= 0);
									});
								}
							}
						);
					}
				}, 500);
			});
		}
		$("select[name='country_id']").change();

		$('.reservation_payment').click(function (ev) {
			var self = this
			var room_id = $('#room_id').val();
			ev.stopPropagation()
			ev.preventDefault();

			console.log("PPPPPPPP", room_id, room_id.length);
			if (room_id.length) {
				ajax.jsonRpc('/custom/search/read', 'call', {room_id}).then(function (data) {
					if (data == 'false') {

						Dialog.alert(self, _t("Ohh ! Looks like you took long to make a reservation. Please re check the availability."), {
							title: _t('Warning'),
							confirm_callback: function () {
								window.location.href = '/page/hotel_online.product_show'
							},
						});
					}
					else {
						window.location.href = '/partner/checkout'
					}


				});

		
				
				// rpc.query({
				// 	model: 'hotel.reservation',
				// 	method: 'search_read',
				// 	fields: ['state'],
				// 	domain: [['id', '=', room_id]]
				// }).then(function (data) {
				// 	console.log("******************")
				// 	if (data[0].state == 'cancel') {

				// 		Dialog.alert(self, _t("Ohh ! Looks like you took long to make a reservation. Please re check the availability."), {
				// 			title: _t('Warning'),
				// 			confirm_callback: function () {
				// 				window.location.href = '/page/hotel_online.product_show'
				// 			},
				// 		});
				// 	}
				// 	else {
				// 		window.location.href = '/partner/checkout'
				// 	}
				// });
			}
			return true;
		})

		$('.checkout_process').click(function (ev) {
			var self = this
			var room_id = $('#room_id').val();
			ev.stopPropagation()
			ev.preventDefault();

			console.log("PPPPPPPP", room_id, room_id.length);
			if (room_id.length) {
				ajax.jsonRpc('/custom/search/read', 'call', {room_id}).then(function (data) {
					if (data == 'false') {

						Dialog.alert(self, _t("Ohh ! Looks like you took long to make a reservation. Please re check the availability."), {
							title: _t('Warning'),
							confirm_callback: function () {
								window.location.href = '/page/hotel_online.product_show'
							},
						});
					}
					else {
						window.location.href = '/partner/checkout'
					}


				});

			}
			return true;
		})


		$('.js_delete_product').click(function (ev) {
			var self = this
			var other_items_id = $('.product_display_id').attr('data-id');
			ev.stopPropagation()
			ev.preventDefault();

			console.log("PPPPPPPP",other_items_id);
		
			ajax.jsonRpc('/other/items/unlink', 'call', {other_items_id}).then(function (data) {
				if (data == 'false') {

					Dialog.alert(self, _t("Ohh ! Looks like you took long to make a reservation. Please re check the availability."), {
						title: _t('Warning'),
						confirm_callback: function () {
							window.location.href = '/page/hotel_online.product_show'
						},
					});
				}
				else {
					window.location.href = '/shop/payment'
				}


			});

			return true;
		})


	});
});