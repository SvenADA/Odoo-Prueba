# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.tools.translate import _


class hotel_management_config_settings(models.TransientModel):
    _name = 'hotel.management.config.settings'
    _inherit = 'res.config.settings'
    _description = 'hotel management config settings'

    test = fields.Boolean('Do nat make separate Invoices')


    @api.model
    def default_get(self, fields):
        res = {}
        con_obj = self.search([])
        for con in [con_obj[-1]]:
            if con.test:
                res.update(test=True)
        if not con_obj:
            config_obj = self.env["hotel.restaurant.order"]
            config_ids = config_obj.search([])
            if config_ids:
                for config in config_obj:
                    if config.flag:
                        res.update(test=True)
        return res


    # @api.onchange('test')
    # def onchange_test(self):
    #     ir_values = self.env['ir.default'].sudo()
    #     result = {}
    #
    #     if self.test:
    #         ir_values.set_default('hotel.folio', 'flag', True)
    #         ir_values.set_default('laundry.management', 'flag', True)
    #         ir_values.set_default('hotel.restaurant.order', 'flag', True)
    #         ir_values.set_default('hotel.reservation.order', 'flag1', True)
    #     if not self.test:
    #         ir_values.set_default('hotel.folio', 'flag', False)
    #         ir_values.set_default('laundry.management', 'flag', False)
    #         ir_values.set_default('hotel.restaurant.order', 'flag', False)
    #         ir_values.set_default('hotel.reservation.order', 'flag1', False)
    #     return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
