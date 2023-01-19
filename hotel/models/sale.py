
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from odoo.addons import decimal_precision as dp
from odoo import netsvc
from odoo.exceptions import ValidationError


class sale_shop(models.Model):
    _name = "sale.shop"
    _description = "Sales Shop"

    name = fields.Char('Hotel Name', required=True)
    payment_default_id = fields.Many2one(
        'account.payment.term', 'Default Payment Term', required=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist')
    project_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account', domain=[('partner_id', '!=', False)])
    company_id = fields.Many2one('res.company', 'Company', required=False, default=lambda self: self.env[
        'res.company']._company_default_get('sale.shop'))
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')



