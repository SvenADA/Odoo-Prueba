# -*- coding: utf-8 -*-

from odoo import models, fields


class room_guestwise_wizard(models.TransientModel):
    _name = 'room.guestwise.wizard'
    _description = 'Room wise Guest wise Wizard'

    date_start = fields.Date('From Date', required=True)
    date_end = fields.Date('To Date', required=True)

    def print_report(self):
        datas = {}
        return self.env.ref('hotel_management.roomwise_guestwise_qweb').report_action(self, data=datas, config=False)

    def _get_report_base_filename(self):
        return "Room-Guest-WiseReport"
