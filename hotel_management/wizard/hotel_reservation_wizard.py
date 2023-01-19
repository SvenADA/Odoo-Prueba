from odoo import fields, models, api
import time
# from mx import DateTime
import datetime


class hotel_reservation_wizard(models.TransientModel):
    _name = 'hotel.reservation.wizard'

    _description = 'Hotel reservation Wizard'

    date_start = fields.Date('From Date', required=True)
    date_end = fields.Date('To Date', required=True)


    # @api.multi
    def print_report(self):
        datas = {} 
        return self.env.ref('hotel_management.hotel_reservation_details_report').report_action(self, data=datas, config=False)
        

    # @api.multi
    def print_checkin(self):
        datas = {} 
        return self.env.ref('hotel_management.hotel_checkin_details_report').report_action(self, data=datas, config=False)

    
    # @api.multi
    def print_checkout(self):
        datas = {} 
        return self.env.ref('hotel_management.hotel_checkout_details_report').report_action(self, data=datas, config=False)


    # @api.multi
    def print_room_used(self):
        datas = {} 
        return self.env.ref('hotel_management.max_hotel_room_report').report_action(self, data=datas, config=False)
