odoo.define('pos_combo_product.combo_product_popup', function (require) {
    'use strict';

    const { useState } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class ComboProductPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.selected = [];
            var self = this;
            _.each(this.props.required, function (category_option) {
            self.selected.push(...category_option.combo_products);
        });
        }
    click_cancel() {
        var order_line = this.env.pos.get_order();
        var selected_line = this.env.pos.get_order().get_selected_orderline();
        order_line.remove_orderline(selected_line);
        this.trigger('close-popup');
    }
    click_confirm() {
        var self = this;
        var execute = true;
        var selected_line = this.props.line;
        var order = this.props.line;
        var optional =  this.props.optional;
        var required =  this.props.required;
        var products_info = [];
         _.each(optional, function (optional) {
            if (optional.limit == 0){
                self.selected = [];
                _.each(required, function (category_required) {
                    _.each(category_required.combo_products, function (combo_product) {
                        self.selected.push(combo_product)
                    })
                })
        }
         })
        if (optional.length == 0){
            self.selected = [];
            _.each(required, function (category_required) {
                    _.each(category_required.combo_products, function (combo_product) {
                        self.selected.push(combo_product)
                    })
                })
        }
        var order_line = this.env.pos.get_order();
        _.each(optional, function (category_option) {
            if (execute){
                var selection_count = 0;
                _.each(category_option.combo_products, function (combo_product) {
                    if (combo_product.selected){
                        selection_count += 1;
                    }
                });
                if (category_option.limit != selection_count){
                    alert("Please choose your optional products");
                    execute = false;
                }
                for(var i=0;i<order.length;i++){
                    for(var j=0;j<order[i].combo_products.length;j++){
                       if(order[i]['selected'] || required[i]){
                           var product = self.env.pos.db.get_product_by_id(order[i].combo_products[j].id);
                           if(product){
                            products_info.push({
                                "product": product,
                                "id":order[i].combo_products[j]['id']
                            });
                        }
                    }
                }
            }
            }
            });
            if (! execute){
            return false;
        }
        var selected_line = this.env.pos.get_order().get_selected_orderline();
        this.quantity = selected_line.quantity
        this.combo_items = this.selected
        selected_line.combo_items = this.selected;
        selected_line.trigger('change', selected_line);
        selected_line.trigger('update:OrderLine');
        this.env.pos.trigger('change:selectedOrder', this.env.pos, this.env.pos.get_order());
        self.trigger('close-popup');
    }
    select_optional_products(e){
        var self = this;
        var order_line = this.props.line;
        var optional =  this.props.optional;
        var required = this.props.required;
        var $target = $(e.currentTarget);
        var combo = $target.data('combo-id');
        var category = $target.data('category-id');
        var product = $target.data('product-id');
        var product_list = [];
        _.each(optional, function (category_option) {
            product_list.push(product)

            if (category_option['id'] === combo && category_option['category'] === category){
                var selection_count = 0;
                _.each(category_option.combo_products, function (combo_product) {
                    if (combo_product.selected){
                        selection_count += 1;
                    }
                });
                _.each(category_option.combo_products, function (combo_product) {
                    if(combo_product['id'] === product){
                        if (combo_product['selected']){
                            combo_product['selected'] = false;
                            $target.find('.combo-selected-tag').hide();
                            var index = self.selected.indexOf(combo_product);
                            if (index > -1) {
                                   self.selected.splice(index, 1);
                            }
                        }
                        else if (selection_count < category_option.limit){
                            combo_product['selected'] = true;
                            $target.find('.combo-selected-tag').text("Selected").show('fast');
                            self.selected.push(combo_product);
                        }
                        else{
                            alert("Already selected enough options for this category");
                        }
                     }
                     });
                }
            })
    }
    }
    ComboProductPopup.template = 'ComboProductPopup';
    ComboProductPopup.defaultProps = {
        confirmText: 'Confirm',
        cancelText: 'Close',
        title: 'Combo Products',
        body: '',
        list: [],
    };
    Registries.Component.add(ComboProductPopup);
    return ComboProductPopup;
});
