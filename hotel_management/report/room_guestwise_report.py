# -*- coding: utf-8 -*-

from odoo import models


class room_guest(models.AbstractModel):
    _name = 'report.hotel_management.roomwise_guestwise_report_view'
    _description = 'Room wise Guest wise Report view'

    def get_roomtype_guest_information(self, data):
        start_date = data.date_start
        end_date = data.date_end
        history_search = self.env['hotel.room.booking.history'].search([
            ('check_in_date', '>=', start_date), ('check_out_date', '<=', end_date),
            ('booking_id.company_id', '=', self.env.user.company_id.id)])
        final_res = {}
        result_acc = []
        cus_res = {}
        key_list = []
        for roomtype in history_search:
            if not roomtype.history_id.name in key_list:
                key_list.append(roomtype.history_id.name)
        for key in key_list:
            res = []
            for room in history_search:
                if room.history_id.name == key:
                    address = ''
                    if room.partner_id.street:
                        address += room.partner_id.street + ' '
                    if room.partner_id.street2:
                        address += room.partner_id.street2 + ' '
                    if room.partner_id.city:
                        address += room.partner_id.city + ' '
                    if room.partner_id.zip:
                        address += room.partner_id.zip + ' '

                    folio_id = self.env['hotel.folio'].search([('reservation_id', '=', room.booking_id.id)])
                    is_checkin = 'No'
                    is_checkout = "No"
                    if folio_id:
                        is_checkin = "Yes"
                    folio_out_id = self.env['hotel.folio'].search(
                        [('reservation_id', '=', room.booking_id.id), ('state', 'in', ['check_out', 'done'])])
                    if folio_out_id:
                        is_checkout = 'Yes'
                    cus_res = {
                        'checkin': room.check_in,
                        'checkout': room.check_out,
                        'guest_name': room.partner_id.name,
                        'address': address,
                        'is_checkin': is_checkin,
                        'is_checkout': is_checkout,
                    }
                    res.append(cus_res)
            final_res = {
                'room_name': key,
                'data': res
            }
            result_acc.append(final_res)
        if not result_acc:
            new_res = []
            cus_res = {
                'checkin': '',
                'checkout': '',
                'guest_name': '',
                'address': "",
                'is_checkin': "",
                'is_checkout': "",
            }
            new_res.append(cus_res)
            final_res = {
                'room_name': '',
                'data': new_res,
            }
            result_acc.append(final_res)

        return result_acc

    def _get_report_values(self, docids, data=None):
        order = self.env['room.guestwise.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'room.guestwise.wizard',
            'data': data,
            'docs': order,
            'get_roomtype_guest_information': self.get_roomtype_guest_information,
        }
