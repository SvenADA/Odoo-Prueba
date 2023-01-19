# -*- coding: utf-8 -*-

from functools import partial
from odoo.exceptions import UserError
from odoo import models, fields, api, _


class PosComboProducts(models.Model):
    _name = 'pos.combo.product'

    is_required = fields.Boolean(string='Is Required')
    category = fields.Many2one('pos.category', string='Category')
    products = fields.Many2many('product.product', 'product_combo_rel')
    combo_id = fields.Many2one('product.template')
    item_count = fields.Integer(string='Item Count')

    @api.onchange('is_required', 'item_count', 'products')
    def check_combo_selection_limit(self):
        for record in self:
            if record.is_required:
                record.item_count = len(record.products)
            if not record.is_required:
                if record.item_count > len(record.products):
                    raise UserError(_("Combo selection item count exceeds number of products."))


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_combo = fields.Boolean(string='Is Combo', default=False)
    combo_items = fields.One2many('pos.combo.product', 'combo_id', string='Combo')

    @api.onchange('is_combo', 'type')
    def set_combo_product_type(self):
        for rec in self:
            if rec.is_combo:
                rec.type = 'service'


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        combo_list = []
        if ui_order['lines']:
            for l in ui_order['lines']:
                for combo in l[2]['combo_items']:
                    combo_list.append([0, 0, {
                        'product_id': combo['id'],
                        'qty': l[2]['qty'],
                        'price_unit': float(0.0),
                        'price_subtotal': float(0.0),
                        'price_subtotal_incl': float(0.0),
                    }])
        order_fields['lines'] = order_fields['lines'] + combo_list
        return order_fields
