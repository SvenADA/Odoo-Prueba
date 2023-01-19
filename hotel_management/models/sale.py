from odoo import fields, models


class sale_shop(models.Model):
    """Sale shop inherited for Image"""
    _inherit = "sale.shop"
    _description = "sale shop used for territory name"

    shop_img = fields.Binary("Image", help="This field holds the image for this shop, limited to 1024x1024px")
