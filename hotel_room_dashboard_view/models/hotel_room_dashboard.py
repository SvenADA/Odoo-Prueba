# -*- coding: utf-8 -*-
import pytz

from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import time
from datetime import date
from datetime import datetime, timedelta
from dateutil.parser import *
import pytz
import math

utc_time = datetime.utcnow()
import logging

_logger = logging.getLogger(__name__)


class hotel_room_dashboard(models.Model):
    """ Class for showing Rooms Dashboard"""
    _name = 'hotel.room.dashboard'
    _description = 'Room Dashboard'

    name = fields.Char('Name')

    def open_dashboard(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/hotel_room_dashboard/web/',
            'target': 'self',
        }


class hotel_reservation(models.Model):
    _inherit = 'hotel.reservation'

    """ Inherited to set default values in reservation form"""

    def action_folio_confirm(self):
        search_id = self.env['hotel.folio'].search([('reservation_id', '=', self.id)])
        if search_id and search_id.state == 'draft':
            search_id.action_confirm()
        return True

    def action_folio_checkout(self):
        search_id = self.env['hotel.folio'].search([('reservation_id', '=', self.id)])
        if search_id and search_id.state == 'progress':
            search_id.action_checkout()

    def action_folio_done(self):
        search_id = self.env['hotel.folio'].search([('reservation_id', '=', self.id)])
        if search_id and search_id.state == 'check_out':
            search_id.action_done()

    def write(self, vals):

        # print("ffffffffffffffffffffffffffff", vals)

        return super(hotel_reservation, self).write(vals)

    def get_folio_status(self):
        folio_record = self.env['hotel.folio'].search([('reservation_id', '=', self.id)])
        if folio_record:
            return folio_record.state

        return False

    # def update_reservation_old(self, resourceId, description):
    #     print("fffffffffffffffff", resourceId, description)

    def update_reservation_line(self, description, start, end, resourceId, start_only_date, end_only_date):
        _logger.info("UPDATE RESERVATION LINE===>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        reservation = self.env['hotel.reservation'].search([('reservation_no', '=', description)])

        # print("reservation::::::::::::::::", reservation, resourceId)

        if resourceId:
            room_id = self.env['product.product'].search([('id', '=', resourceId)])
            # print("room_id:::::::::", room_id)
        for line_id in reservation:
            for line in line_id.reservation_line:
                if line.room_number.id == room_id.id:

                    # print("line_id::::::::::::", line_id.folio_id)
                    if start:
                        line.write({'checkin': start})
                    if end:
                        line.write({'checkout': end})

                if reservation.state == 'confirm':
                    # print("reservation:::::::::::::::::", reservation.state)

                    hotel_history = self.env['hotel.room.booking.history'].search([('booking_id', '=', reservation.id)])
                    # print("hotel_history::::::::::::::::::", hotel_history)
                    for hotel_history_line in hotel_history:
                        # print("hotel_history_line.product_id.id::::::::;", hotel_history_line.product_id,
                        #       line.room_number.name)
                        if hotel_history_line.product_id == line.room_number.id and hotel_history.booking_id.id == line.line_id.id:
                            if hotel_history_line.name == line.room_number.name:
                                if start:
                                    hotel_history_line.write({"check_in": start})
                                    hotel_history_line.write({"check_in_date": start_only_date})
                                if end:
                                    hotel_history_line.write({"check_out": end})
                                    hotel_history_line.write({"check_out_date": end_only_date})

        if reservation:
            folio = self.env['hotel.folio'].search([('reservation_id', '=', reservation.reservation_no)])
            # print("folio:::::::::::::", folio)

            for folio_line in folio.room_lines:
                # print("folio_line::::::::::;", folio_line.product_id, room_id.id)

                if folio_line.product_id.id == room_id.id:
                    if start:
                        folio_line.write({'checkin_date': start})
                    if end:
                        folio_line.write({'checkout_date': end})
                    folio_line.on_change_checkout()

    def update_room(self, description, resourceId, start1, end1, old_id, start_only_date, end_only_date):
        # print("resourceId::::::::::::", description, resourceId, start1, end1, old_id, start_only_date, end_only_date)
        # print("ffffffffffffff",)
        _logger.info("UPDATE ROOM===>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        if resourceId:
            room_id = self.env['product.product'].search([('id', '=', resourceId)])
            # print("room_id:::::::::", room_id)
        if old_id:
            room_id_old = self.env['product.product'].search([('id', '=', old_id)])
            # print("room_id:::::::::", room_id_old)

        reservation = self.env['hotel.reservation'].search([('reservation_no', '=', description)])

        # print("reservation::::::::::::::::", reservation, resourceId)

        if resourceId:
            room_id = self.env['product.product'].search([('id', '=', resourceId)])
            # print("room_id:::::::::", room_id)
        for line_id in reservation:
            for line in line_id.reservation_line:

                if room_id_old:
                    if line.room_number.id == room_id_old.id:

                        # print("line_id::::::::::::", line_id.folio_id)
                        if start1:
                            line.write({'checkin': start1})
                        if end1:
                            line.write({'checkout': end1})

                        if room_id:
                            line.write({'room_number': room_id.id})
                            line.write({'categ_id': room_id.categ_id.id})
                if reservation.state != 'draft':
                    # print("reservation:::::::::::.::::::",reservation.state)

                    hotel_history = self.env['hotel.room.booking.history'].search([('booking_id', '=', reservation.id)])
                    hotel_room = self.env['hotel.room'].search([('product_id', '=', room_id.id)])
                    # print("hotel_history::::::::::::::::::", hotel_history)
                    for hotel_history_line in hotel_history:
                        # print("hotel_history_line.product_id.id::::::::;",hotel_history_line.product_id,room_id_old.id)
                        if hotel_history_line.product_id == room_id_old.id and hotel_history.booking_id.id == line.line_id.id:
                            # print("hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh")
                            if start1:
                                hotel_history_line.write({"check_in": start1})
                                hotel_history_line.write({"check_in_date": start_only_date})
                            if end1:
                                hotel_history_line.write({"check_out": end1})
                                hotel_history_line.write({"check_out_date": end_only_date})
                            if hotel_room:
                                hotel_history_line.write({"history_id": hotel_room.id})
                                hotel_history_line.write({"name": hotel_room.name})
                            if room_id:
                                hotel_history_line.write({"product_id": room_id.id})
                                hotel_history_line.write({"category_id": room_id.categ_id.id})

        if reservation:
            folio = self.env['hotel.folio'].search([('reservation_id', '=', reservation.reservation_no)])
            # print("folio:::::::::::::", folio)

            for line in folio.room_lines:
                # print("line:::::::::", line)
                if room_id_old:
                    if line.product_id.id == room_id_old.id:
                        # print("line:::::::::::::::::::::::", line)

                        if room_id:
                            line.write({"product_id": room_id.id})
                            line.write({"name": room_id.name})
                            line.write({"categ_id": room_id.categ_id.id})

                        if end1:
                            # print("ffffffffffffffffffffffff2", end1)
                            line.write({'checkout_date': end1})

                        if start1:
                            # print("ffffffffffffffffffffffff", start1)
                            line.write({'checkin_date': start1})

                        line.on_change_checkout()

                else:
                    if room_id:
                        line.write({"product_id": room_id.id})
                        line.write({"name": room_id.name})
                        line.write({"categ_id": room_id.categ_id.id})

                    if end1:
                        # print("ffffffffffffffffffffffff2", end1)
                        line.write({'checkout_date': end1})

                    if start1:
                        # print("ffffffffffffffffffffffff", start1)
                        line.write({'checkin_date': start1})
                    line.on_change_checkout()

    def set_checkin_checkout(self, vals):
        _logger.info("CHECK IN CHECKOUT===>>>>>>>>>>{}".format(vals))
        if self.env.user:
            user_id = self.env.user
            tz = pytz.timezone(user_id.tz)
            time_difference = tz.utcoffset(utc_time).total_seconds()
            _logger.info("#################{}".format(self._context))
            if self._context.get('shop_id'):
                checkout_policy_id = self.env['checkout.configuration'].search(
                    [('shop_id', '=', self._context.get('shop_id'))])
                _logger.info("Checkout Policy===>>>{}".format(checkout_policy_id))

                if checkout_policy_id.name == 'custom':
                    time = int(checkout_policy_id.time)

                    checkin = vals.get('checkin')
                    check_in_from_string = fields.Datetime.from_string(vals.get('checkin'))
                    checkin = datetime(check_in_from_string.year, check_in_from_string.month, check_in_from_string.day)
                    checkin = checkin + timedelta(hours=int(time))

                    checkout = vals.get('checkout')
                    checkout_from_string = fields.Datetime.from_string(vals.get('checkout'))
                    checkout = datetime(checkout_from_string.year, checkout_from_string.month, checkout_from_string.day)
                    checkout = checkout + timedelta(hours=int(time))

                    checkout = checkout - timedelta(seconds=time_difference)
                    checkin = checkin - timedelta(seconds=time_difference)

                    _logger.info("\n\n\n\n\nVALS=====>>>>>>>>>>>>>>>>>>{}".format(checkout))
                    vals.update({'checkout': checkout, 'checkin': checkin})
        return vals
