odoo.define('hotel_online.payment', function (require) {
	"use strict";

	var ajax = require('web.ajax');

	$(document).ready(function () {
		// When choosing an acquirer, display its Pay Now button
		var $payment = $("#payment_method_list");
		$payment.on("click", "input[name='acquirer1']", function (ev) {
			var payment_id = $(ev.currentTarget).val();
			$("div.oe_sale_acquirer_button[data-id]", $payment).addClass("hidden");
			$("div.oe_sale_acquirer_button[data-id='" + payment_id + "']", $payment).removeClass("hidden");
		});

		/*		// $.find("input[name='acquirer1']:checked")[0].click();
				// When clicking on payment button: create the tx using json then continue to the acquirer
				var $payment1 = $("#payment_method1");
		
				$payment.on("click", 'button[type="submit"],button[name="submit"]', function(ev) {
					ev.preventDefault();
					ev.stopPropagation();
					var $form = $(ev.currentTarget).parents('form');
					console.log("$form------------------", $form);
					var acquirer_id = $(ev.currentTarget).parents('div.oe_sale_acquirer_button').first().data('id');
					console.log("yuppppppppp aquied id--------********", acquirer_id);
					if (!acquirer_id) {
						return false;
					}
					ajax.jsonRpc('/shop/payment/transaction123/' + acquirer_id, 'call', {}).then(function() {
						$form.submit();
					});
				});
				*/

		// When choosing an acquirer, display its Pay Now button
		var $payment = $("#payment_method");
		$payment.on("click", "input[name='acquirer'], a.btn_payment_token", function (ev) {
			var ico_off = 'fa-circle-o';
			var ico_on = 'fa-dot-circle-o';

			var payment_id = $(ev.currentTarget).val() || $(this).data('acquirer');
			var token = $(ev.currentTarget).data('token') || '';

			$("div.oe_sale_acquirer_button[data-id='" + payment_id + "']", $payment).attr('data-token', token);
			$("div.js_payment a.list-group-item").removeClass("list-group-item-info");
			$('span.js_radio').switchClass(ico_on, ico_off, 0);
			if (token) {
				$("div.oe_sale_acquirer_button div.token_hide").hide();
				$(ev.currentTarget).find('span.js_radio').switchClass(ico_off, ico_on, 0);
				$(ev.currentTarget).parents('li').find('input').prop("checked", true);
				$(ev.currentTarget).addClass("list-group-item-info");
			}
			else {
				$("div.oe_sale_acquirer_button div.token_hide").show();
			}
			$("div.oe_sale_acquirer_button[data-id]", $payment).addClass("hidden");
			$("div.oe_sale_acquirer_button[data-id='" + payment_id + "']", $payment).removeClass("hidden");

		})



	});

});



odoo.define('hotel_online.payment', function (require) {
	"use strict";

	var ajax = require('web.ajax');
	$(document).ready(function () {
		// When choosing an acquirer, display its Pay Now button
		var $payment = $("#payment_method_list");
		$payment.on("click", "input[name='acquirer1']", function (ev) {
			var payment_id = $(ev.currentTarget).val();
			$("div.oe_sale_acquirer_button[data-id]", $payment).addClass("hidden");
			$("div.oe_sale_acquirer_button[data-id='" + payment_id + "']", $payment).removeClass("hidden");
		});

		// $.find("input[name='acquirer1']:checked")[0].click();
		// When clicking on payment button: create the tx using json then continue to the acquirer
		var $payment1 = $("#payment_method1");

		$payment.on("click", 'button[type="submit"],button[name="submit"]', function (ev) {
			ev.preventDefault();
			ev.stopPropagation();
			var $form = $(ev.currentTarget).parents('form');
			console.log("$form------------------", $form);
			//			var acquirer_id = $(ev.currentTarget).parents('div.oe_sale_acquirer_button').first().data('id');
			var acquirer_id_obj = $('input[name=pm_id]:checked')
			var acquirer_id = acquirer_id_obj[0].attributes[6].value

			console.log("yuppppppppp aquied id--------111111********", acquirer_id);
			if (!acquirer_id) {
				return false;
			}
			ajax.jsonRpc('/shop/payment/transaction123/' + acquirer_id, 'call', {}).then(function () {
				console.log("wpas aya re !!!!!!!!!!!!!!!!!!")
				$form.submit();
			});
		});



	});

});
