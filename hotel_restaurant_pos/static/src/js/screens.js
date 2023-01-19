odoo.define('hotel_restaurant_pos.screens', function (require) {
	"use strict";
	var models = require('point_of_sale.models');
	// alert();
	const PaymentScreen = require('point_of_sale.PaymentScreen');
	const Registries = require('point_of_sale.Registries');

	const MyPaymentScreen = PaymentScreen =>
		class extends PaymentScreen {
			constructor() {
				super(...arguments);
			}
			mounted() {
				var self = this;
				// console.log($('.js_room_name'));
				// console.log("Room name",room);
				var room = self.env.pos.get_order().get_room_name();
				if (room) {
					$('.js_room_name').text(room ? room : _t('Room'));
				}
				console.log($('.o_pricelist_button'))
			}

			click_set_room() {
				// console.log("Set Room Function")

				this.showScreen('RoomListScreenWidget');
				// this.$('.js_room_name').text(client ? client.name : _t('Customer'));
			}

			finalize_validation() {
				// console.log('\n\n\n new method finalize_validation === this =', this);
				var self = this;
				var order = this.pos.get_order();
				// console.log('\n\n\n finalize_validation order ====', order);
				if (order.is_paid_with_cash() && this.pos.config.iface_cashdrawer) {

					this.pos.proxy.open_cashbox();
				}

				order.initialize_validation_date();
				if (order.is_to_invoice()) {
					// console.log('\n\n\n finalize_validation == order after ==', order);
					var invoiced = this.pos.push_and_invoice_order(order);
					// console.log('\n\n\n finalize_validation == invoiced ==', invoiced);
					this.invoicing = true;

					invoiced.fail(function (error) {
						self.invoicing = false;
						if (error.message === 'Missing Customer') {
							self.gui.show_popup('confirm', {
								'title': _t('Please select the Customer'),
								'body': _t('You need to select the customer before you can invoice an order.'),
								confirm: function () {
									self.gui.show_screen('clientlist');
								},
							});
						} else if (error.code < 0) {        // XmlHttpRequest Errors
							self.gui.show_popup('error', {
								'title': _t('The order could not be sent'),
								'body': _t('Check your internet connection and try again.'),
							});
						} else if (error.code === 200) {    // OpenERP Server Errors
							self.gui.show_popup('error-traceback', {
								'title': error.data.message || _t("Server Error"),
								'body': error.data.debug || _t('The server encountered an error while receiving your order.'),
							});
						} else {                            // ???
							self.gui.show_popup('error', {
								'title': _t("Unknown Error"),
								'body': _t("The order could not be sent to the server due to an unknown error"),
							});
						}
					});

					invoiced.done(function () {
						self.invoicing = false;
						if (order.room_name != '' && order.folio_ids != '') {
							order.finalize();
							self.gui.show_screen('products');
						} else {
							self.gui.show_screen('receipt');
						}
					});
				} else {
					this.pos.push_order(order);
					this.gui.show_screen('receipt');
				}
			}


		}
	Registries.Component.extend(PaymentScreen, MyPaymentScreen);

	return MyPaymentScreen;
});
