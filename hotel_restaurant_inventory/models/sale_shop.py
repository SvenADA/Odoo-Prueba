from odoo import api, fields, models, _


class SaleShop(models.Model):
    _inherit = "sale.shop"

    picking_type_id = fields.Many2one('stock.picking.type', 'Restaurant Picking type')
