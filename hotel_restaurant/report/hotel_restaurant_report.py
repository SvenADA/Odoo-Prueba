# -*- encoding: utf-8 -*-

import time
from odoo import models, api


class hotel_restaurant_report(models.AbstractModel):
    _name = 'report.hotel_restaurant.hotel_restaurant_reservation_report123'
    _description = 'report hotel restaurant hotel restaurant reservation report'

#     @api.model
#     def render_html(self, docids, data=None):
#     @api.multi
    def get_report_values(self, docids, data=None):
        order = self.env['hotel.restaurant.reservation.wizard'].browse(docids)
        return  {
            'doc_ids': docids,
            'doc_model': 'hotel.restaurant.reservation.wizard',
            'data': data,
            'docs': order,
            'time': time,
            'get_res_data': self.get_res_data,
        }
#         return self.env['report'].render('hotel_restaurant.hotel_restaurant_reservation_report123', docargs)

    def get_res_data(self, obj):
        res = self.env['hotel.restaurant.reservation'].search(
            [('start_date', '>=', obj.date_start), ('end_date', '<=', obj.date_end)])
        # print ('^^^^^^^^^^^^^^^^^^^^^^^res^^^^^^^^^^^', res)
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
