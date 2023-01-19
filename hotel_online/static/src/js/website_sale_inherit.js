odoo.define('hotel_online.cart', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var WebsiteSale = require('website_sale.website_sale')
    const wUtils = require('website.utils');

    publicWidget.registry.WebsiteSale.include({

        /**
         * @override
         */
        _onClickAdd: function (ev) {
            ev.preventDefault();
            var self = this
            this.getCartHandlerOptions(ev);
            var $form = $(ev.currentTarget).closest('form')
            
            var productID = $form.find('.product_id').val()
            var qty_id = $form.find('.quantity').val()
            
            wUtils.sendRequest('/shop/cart/update', {
                product_id: productID,
                add_qty:qty_id,
                express: true,

            });
            
            return self._super.apply(this, arguments)

        },
    })

});