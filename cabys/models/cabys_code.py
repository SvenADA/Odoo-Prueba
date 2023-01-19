from odoo import _,fields, models, api, tools


class cabys(models.Model):
    _inherit = ['product.template']

    codigo_cabys = fields.Char(string="Código CAByS")