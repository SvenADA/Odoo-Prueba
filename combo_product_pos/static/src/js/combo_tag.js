odoo.define('combo_product_pos.combo_product_tag', function (require) {
"use strict";
     const ProductItem = require('point_of_sale.ProductItem');
     const Registries = require('point_of_sale.Registries');
     var core = require('web.core');
     var QWeb = core.qweb;
     var _t = core._t;
     var task;

     const ComboProductTag = (ProductItem) =>
        class extends ProductItem{
            get imageUrl() {
                var self = this;
                var done = $.Deferred();
                clearInterval(task);
                task = setTimeout(function () {
                        self.env.pos.enable_combo();
                    done.resolve();
                }, 100);
                const product = this.props.product;
                return `/web/image?model=product.product&field=image_128&id=${product.id}&write_date=${product.write_date}&unique=1`;
        }
        }
        Registries.Component.extend(ProductItem, ComboProductTag);
        return ComboProductTag;
});