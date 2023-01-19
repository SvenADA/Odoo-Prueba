odoo.define('hotel_restaurant_pos.RoomListScreenWidget', function (require) {
    "use strict";
    // console.log("Screens  =======   ");
    const { Gui } = require('point_of_sale.Gui');
    var models = require('point_of_sale.models');
    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useState, useRef, useContext } = owl.hooks;

    class RoomListScreenWidget extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({
                uiState: 'LOADING', // 'LOADING' | 'READY' | 'CLOSING'
                debugWidgetIsShown: true,
                hasBigScrollBars: false,
                sound: { src: null },
            });

            this.loading = useState({
                message: 'Loading',
                skipButtonIsShown: false,
            });

            this.mainScreen = useState({ name: null, component: null });
            this.mainScreenProps = {};

            this.tempScreen = useState({ isShown: false, name: null, component: null });
            this.tempScreenProps = {};

            this.progressbar = useRef('progressbar');

        }
        mounted() {
            this.show();
        }
        destroy() {
            super.destroy(...arguments);
            this.env.pos.destroy();
        }
        catchError(error) {
            console.error(error);
        }
        render_room_list(rooms) {
            var d = new Date();
            var current_date = new Date(String(d.getFullYear()) + "-" + String(d.getMonth() + 1) + "-" + String(d.getDate())).setHours(0, 0, 0, 0);
            var contents = document.querySelector('.room-list-contents');

            contents.innerHTML = "";
            var hotel_folio = this.env.pos.hotel_folio;
            for (var i = 0, len = Math.min(rooms.length, 1000); i < len; i++) {
//                console.log(rooms[i].folio_id)
                var room = rooms[i];
                var checkin = room.checkin_date;
                var checkin_dt = new Date(checkin.split(" ")[0]).setHours(0, 0, 0, 0);
                var checkout = room.checkout_date;
                var checkout_dt = new Date(checkout.split(" ")[0]).setHours(0, 0, 0, 0);
//                if (checkin_dt <= current_date && checkout_dt >= current_date) {
                    for (var j = 0; j < hotel_folio.length; j++) {
                        if ((hotel_folio[j].state === 'draft')&&(room.folio_id[0] === hotel_folio[j].id)) {
                            if (room) {
                                var roomline_html = QWeb.render('RoomLine', { room: rooms[i] });
                                var roomline = document.createElement('tbody');
                                roomline.innerHTML = roomline_html;
                                roomline = roomline.childNodes[1];
                            }

                            if (room === this.old_room) {
                                roomline.classList.add('highlight');
                            } else {
                                roomline.classList.remove('highlight');
                            }
                            contents.appendChild(roomline);
                        }
                    }
//                }
            }
        }
        back() {
            this.showScreen('PaymentScreen');
        }
        show() {
            var self = this;
            // this._super();
            // this.renderElement();
            this.details_visible = false;

            // this.$('.back').click(function () {
            //     self.gui.back();
            // });

            // this.$('.next').click(function () {
            //     self.save_changes();
            //     self.gui.back();    // FIXME HUH ?
            // });

            var rooms = this.env.pos.hotel_folio_line;
            var hotel_folio = this.env.pos.hotel_folio
            /**
                Loading partner id and partner name in room object
            */
            for (var i = 0, len = Math.min(rooms.length, 1000); i < len; i++) {
                var room = rooms[i];
                for (var j = 0; j < hotel_folio.length; j++) {
                    if (hotel_folio[j].state === 'draft') {
                        if (room.folio_id[0] === hotel_folio[j].id) {
                            room['partner_id'] = hotel_folio[j].partner_id[0];
                            room['partner_name'] = hotel_folio[j].partner_id[1];
                            break;
                        }
                    }
                }
            }

            /**
                Rendering Room object
            */
            this.render_room_list(rooms);

            $(function () {
                $(document).delegate('.room-line', 'click', function (event) {
                    var line_data;
                    var room_name;
                    var customer_name;
                    var pricelist_name;
                    var folio_line_id;
                    var folio_ids;
                    var partner

                    var partner_id = $($(this).children()[2]).data('cust-id');

                    self.env.pos.get_order().set_client(self.env.pos.db.get_partner_by_id(parseInt(partner_id)));
                    customer_name = $($(this).children()[2]).text();
                    room_name = $($(this).children()[0]).text();
                    folio_ids = $($(this).children()[1]).data('folio-id');
                    folio_line_id = parseInt($(this).data('id'));
                    self.env.pos.get_order().set_folio_ids(folio_ids);
                    self.env.pos.get_order().set_folio_line_id(folio_line_id);
                    self.env.pos.get_order().set_room_name(room_name);
                    $('.js_room_name').text(room_name ? room_name : _t('Room'));
                    $('.js_customer_name').text(customer_name ? customer_name : _t('Customer'));
                    $('.set-customer').text(customer_name ? customer_name : _t('Customer'));
                    partner = self.env.pos.db.get_partner_by_id(partner_id)
                    self.env.pos.get_order().updatePricelist(partner)
                    self.back();
                });
            });
        }
    }
    RoomListScreenWidget.template = 'RoomListScreenWidget';

    Registries.Component.add(RoomListScreenWidget);

    return RoomListScreenWidget;
});
