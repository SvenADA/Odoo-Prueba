from odoo import api, models, fields
import time
# from mx import DateTime
import datetime
# from openerp import pooler
from odoo.tools import config
from odoo import netsvc


class hotel_restaurant_wizard(models.TransientModel):
    _name = 'hotel.restaurant.wizard'
    _description = 'hotel_restaurant_wizard'

    grouped = fields.Boolean('Group the kots')

hotel_restaurant_wizard()


class hotel_restaurant_reservation_wizard(models.TransientModel):
    _name = 'hotel.restaurant.reservation.wizard'

    _description = 'hotel_restaurant_reservation_wizard'

    date_start = fields.Date('From Date', required=True)
    date_end = fields.Date('To Date', required=True)

    # @api.multi
    def print_report(self):
        datas = {} 
#         value = self.env['report'].get_action(self, 'hotel_restaurant.hotel_restaurant_reservation_report123',data=datas)
#         return value
        return self.env.ref('hotel_restaurant.hotel_restaurant_reservation_report1').report_action(self, data=datas)

