# -*- coding: utf-8 -*-

from odoo import models


class arrival_dept_guest(models.AbstractModel):
    _name = 'report.hotel_management.arrival_dept_guest'
    _description = 'arrival dept guest'

    def get_guest_arrival_dept_information(self, objects):
        start_date = objects.date_start
        arrival_depart = objects.arrival_dept
        history_ids = []
        res = []
        sn = 1

        if arrival_depart == "arrival":
            history_ids = self.env['hotel.room.booking.history'].search([
                ('check_in_date', '>=', start_date), ('booking_id.company_id', '=', self.env.user.company_id.id)])
        else:
            history_ids = self.env['hotel.room.booking.history'].search([
                ('check_out_date', '>=', start_date), ('booking_id.company_id', '=', self.env.user.company_id.id)])

        if history_ids:
            for room in history_ids:
                cus_res = {
                    'checkin': room.check_in,
                    'booking_ref': room.booking_id.reservation_no,
                    'adults': room.booking_id.adults,
                    'children': room.booking_id.childs,
                    'guest_name': room.partner_id.name,
                    'room_name': room.history_id.name,
                    'sn': sn,
                }

                if arrival_depart == "depart":
                    cus_res['checkin'] = room.check_out
                res.append(cus_res)
                sn += 1
        # print('__________ {} '.format(res))
        return res

    def _get_report_values(self, docids, data=None):
        order = self.env['arrival.dept.guest.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'arrival.dept.guest.wizard',
            'data': data,
            'docs': order,
            'get_guest_arrival_dept_information': self.get_guest_arrival_dept_information,
        }
