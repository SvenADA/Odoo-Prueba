# -*- encoding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError

class reservation_detail_report1(models.AbstractModel):
    _name = 'report.hotel_management.hotel_reservation_report'
    _description = 'report hotel_management hotel_reservation_report'

    # @api.multi
    def _get_report_values(self, docids, data=None):
        order = self.env['hotel.reservation.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'hotel.reservation.wizard',
            'data': data,
            'docs': order,
            'time': time,
            'get_data': self.get_data,
        }

    # @api.multi
    def get_data(self, obj):
        res = self.env['hotel.reservation.line'].search([('checkin', '>=', obj.date_start), ('checkout', '<=', obj.date_end)])
        rec = []
        for data_list in res:
            if data_list.line_id.state in ['confirm', 'done']:
                rec.append(data_list)
        # print(rec, '=====================rec===================')
        return rec


class reservation_detail_report2(models.AbstractModel):
    _name = 'report.hotel_management.hotel_reservation_checkin_report'
    _description= 'report hotel_management hotel_reservation_checkin_report'

    # @api.multi
    def _get_report_values(self, docids, data=None):
        order = self.env['hotel.reservation.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'hotel.reservation.wizard',
            'data': data,
            'docs': order,
            'time': time,
            'get_checkin': self.get_checkin,
        }

    # @api.multi
    def get_checkin(self, obj):
        res = self.env['hotel.reservation.line'].search(
            [('checkin', '>=', obj.date_start), ('checkin', '<=', obj.date_end)])
        rec = []
        for data_list in res:
            if data_list.line_id.state in ['confirm', 'done']:
                rec.append(data_list)
        return rec


class reservation_detail_report3(models.AbstractModel):
    _name = 'report.hotel_management.hotel_reservation_checkout_report'
    _description ='report hotel_management hotel_reservation_checkout_report'


    # @api.multi
    def _get_report_values(self, docids, data=None):
        order = self.env['hotel.reservation.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'hotel.reservation.wizard',
            'data': data,
            'docs': order,
            'time': time,
            'get_checkout': self.get_checkout,
        }
    
    # @api.multi
    def get_checkout(self, obj):
        # print ("Chck outttttttt    ",obj)
        res = self.env['hotel.reservation.line'].search([('checkout', '>=', obj.date_start), ('checkout', '<=', obj.date_end)])
        rec = []
        for data_list in res:
            if data_list.line_id.state in ['confirm', 'done']:
                rec.append(data_list)
        return rec


class reservation_detail_report4(models.AbstractModel):
    _name = 'report.hotel_management.hotel_reservation_room_report'
    _description = 'hotel reservation room report'

    # @api.multi
    def _get_report_values(self, docids, data=None):
        order = self.env['hotel.reservation.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'hotel.reservation.wizard',
            'data': data,
            'docs': order,
            'time': time,
            'get_room1': self.get_room1,
        }


    # @api.multi
    def get_room1(self, obj):
        res = self.env['hotel.reservation.line'].search([('checkin', '>=', obj.date_start), ('checkout', '<=', obj.date_end)])
        room_list = []
        rec = []
        for room in res:
            if room.line_id.state in ['confirm', 'done']:
                rec.append(room)
                present = False
                for room_list_data in room_list:
                    if room_list_data == room.room_number.name:
                        present = True
                if present == False:
                    room_list.append(room.room_number.name)
        result = []
       
        for room_data in room_list:
            count = 0
            for room in rec:
                if room.room_number.name == room_data:
                    count += 1
            res22 = {
                'room_data': room_data,
                'no_of_times': count
            }
            result.append(res22)
        if not result:
            res22 = {
                'room_data': '',
                'no_of_times': ''
            }
            result.append(res22)
        return result
