from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    remove_draft_web_reservation = fields.Integer(
        string='Remove Draft Web Reservation',
        config_parameter='remove_draft_web_reservation', default=30)
