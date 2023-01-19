odoo.define('combo_product_pos.combo_product', function (require) {
"use strict";

    var models = require('point_of_sale.models');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const { Gui } = require('point_of_sale.Gui');
    models.load_models({
    model:  'pos.combo.product',
    fields: [],
    loaded: function(self, combo_list){
        self.combo_list = combo_list;
        _.each(combo_list, function(item){
            self.combo_item_id[item.id] = item;
        });
    },
});
models.load_fields("product.product", ["is_combo", "combo_items"]);

var _super_pos = models.PosModel.prototype;
models.PosModel = models.PosModel.extend({
    initialize: function() {
        var self = this;
        _super_pos.initialize.apply(this, arguments);
        this.combo_item_id = {};
    },
    enable_combo: function () {
        var self = this;
        $('.product-list').find('.combo-tag').each(function () {
            var $product = $(this).parents('.product');
            var id = parseInt($product.attr('data-product-id'));
            var product = self.db.get_product_by_id(id);
            if (! product.is_combo){
                $(this).hide();
            }
            else{
                $(this).text("Combo Product").show('fast');
            }
        });
    },
    get_product_image_url: function (product) {
        return window.location.origin + '/web/image?model=product.product&field=image_128&id=' + product.id;
    }
});
     const ComboProductScreen = (ProductScreen) =>
     class extends ProductScreen {
     constructor() {
            super(...arguments);
            useListener('click-product', this._clickComboProduct);
        }
     async _clickComboProduct(event){
        var self = this;
        var selected = false;
        var product_selected = event.detail;
        var required = [];
        var optional = [];
        var combo_ids = product_selected.combo_product_ids
        var selected_combo_products = [];
        var combo_selection = false;
        if(product_selected.is_combo){
            _.each(product_selected.combo_items, function(item){
                var combo_item = self.env.pos.combo_item_id[item];
                var combo_products = [];
                _.each(combo_item.products, function(product_id){
                    var product = self.env.pos.db.product_by_id[product_id];
                    var product_image =   window.location.origin + "/web/image/product.product/" + product.id + "/image_128";
                    combo_products.push({
                        'id': product['id'],
                        'name':product['display_name'],
                        'selected': false,
                        'image_url': product_image
                    })
                });
                var combo_item_details = {
                    'id': combo_item.id,
                    'category': combo_item.category[0],
                    'name':combo_item.category[1],
                    'limit': combo_item.item_count,
                    'combo_products': combo_products
                }
                selected_combo_products.push(combo_item_details)
                if(!combo_item.is_required){
                    combo_selection = true;
                    selected = false;
                    optional.push(combo_item_details);
                }
                else{
                    required.push(combo_item_details);
                    selected = true;
                }
            });

        const { confirmed } = await this.showPopup('ComboProductPopup', {
            title: this.env._t('Combo Products'),
            required: required,
            optional: optional,
            combo_selection: combo_selection,
            product_name: product_selected['display_name'],
            line: selected_combo_products
            });
        }
     }
     }
     Registries.Component.extend(ProductScreen, ComboProductScreen);
     var _super_orderline = models.Orderline.prototype;
     models.Orderline = models.Orderline.extend({
        initialize: function(attr,options){
            _super_orderline.initialize.call(this, attr, options);
            this.combo_items = this.combo_items || [];

        },
        init_from_JSON: function(json) {
            _super_orderline.init_from_JSON.apply(this,arguments);
            this.combo_items = json.combo_items || [];
        },
        export_as_JSON: function () {
            var json = _super_orderline.export_as_JSON.apply(this, arguments);
            json.combo_items = this.combo_items || [];
            return json;
        },
        can_be_merged_with: function(orderline) {
            if (orderline.product.is_combo) {
                return false;
            } else {
                return _super_orderline.can_be_merged_with.apply(this,arguments);
            }
        },
        get_combo_items: function () {
        return this.combo_items;

    },
        export_for_printing: function(){
            var lines = _super_orderline.export_for_printing.call(this);
            lines.combo_items = this.get_combo_items();
            return lines;
        },


     })
     return ComboProductScreen;
})