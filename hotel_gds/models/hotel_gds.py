from odoo import fields, models, api
import time
import datetime
from odoo.tools.translate import _
from odoo.exceptions import Warning
from odoo import netsvc
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import config, UserError
from odoo.tools.translate import _
# from mx.DateTime import RelativeDateTime, now, DateTime, localtime
import calendar


# @api.multi
def get_price(self, pricelist_ids, price):
    price_amt = 0.0
    pricelist_item_ids = []
    if self._context is None:
        self._context = {}

    date = time.strftime('%Y-%m-%d')
    if 'date' in self._context:
        date = self._context['date']

    currency_obj = self.env['res.currency']
    product_pricelist_version_obj = self.env['product.pricelist.item']
    user_browse = self.env['res.users']
    company_obj = self.env['res.company']
    company_id = company_obj.browse(user_browse.company_id.id)
    pricelist_obj = self.env['product.pricelist'].browse(pricelist_ids)
    if pricelist_ids:
        pricelist_item_ids.append(pricelist_ids)
        pricelist_obj = self.env['product.pricelist'].browse(pricelist_ids)

    pricelist_item_ids = list(set(pricelist_item_ids))
    plversions_search_args = [
        ('pricelist_id', 'in', pricelist_item_ids),
        '|',
        ('date_start', '=', False),
        ('date_start', '<=', date),
        '|',
        ('date_end', '=', False),
        ('date_end', '>=', date),
    ]

    plversion_ids = product_pricelist_version_obj.search(
        plversions_search_args)
    if not plversion_ids:
        msg = "At least one pricelist item has not declared !\nPlease create pricelist item."
        raise Warning(_('Warning !'), _(msg))

    self._cr.execute(
        'SELECT i.* '
        'FROM product_pricelist_item AS i '
        'WHERE id = ' + str(plversion_ids[0].id) + '')

    res1 = self._cr.dictfetchall()
    if pricelist_obj:
        price = currency_obj.compute(price, pricelist_obj.currency_id, round=False)
    for res in res1:
        if res:
            price_limit = price
            x = (1.0 + (res['price_discount'] or 0.0))
            price = price * (1.0 + (res['price_discount'] or 0.0))
            price += (res['price_surcharge'] or 0.0)
            if res['price_min_margin']:
                price = max(price, price_limit + res['price_min_margin'])
            if res['price_max_margin']:
                price = min(price, price_limit + res['price_max_margin'])
            break

    price_amt = price
    return price_amt


class hotel_reservation(models.Model):
    _inherit = "hotel.reservation"
    _description = "Reservation"

    meal_id = fields.Selection(
        [('no_meal', 'No Meal Included'), ('cont_break', 'Continental Breakfast'), ('buff_break', 'Buffet Breakfast'), (
            'half_board', 'Half-board'), ('full_board', 'Full-board')], 'Meal Type', readonly=True,
        states={'draft': [('readonly', False)]})

    def gds_reservation_check(self):
        for reservation in self:
            for line in reservation.reservation_line:
                reservation_start_date = line.checkin
                reservation_end_date = line.checkout
                config_id = self.env['hotel.reservation.through.gds.configuration'].search([])
                config_browse = config_id
                # print(config_browse, "config_browse=======================")
                if config_browse and reservation.source != 'through_gds':
                    for record in config_browse:
                        config_start_date = record.name
                        config_end_date = record.to_date
                        # config_start_date = datetime.strptime(config_start_date, '%Y-%m-%d %H:%M:%S')
                        # config_end_date = datetime.strptime(config_end_date, '%Y-%m-%d %H:%M:%S')
                        # print(reservation_start_date, "reservation_start_date", reservation_end_date, type(reservation_end_date))
                        if (config_start_date <= reservation_start_date < config_end_date) or (
                                config_start_date < reservation_end_date <= config_end_date) or (
                                (reservation_start_date < config_start_date) and (
                                reservation_end_date > config_end_date)):
                            for rec in record.line_ids:
                                room_list = []
                                for room in rec.room_number:
                                    room_list.append(room.id)
                                # print(room_list, "room_list")
                                if line.room_number.id in room_list:
                                    raise Warning(
                                        "Warning! Room  %s is reserved in this reservation period for GDS reservation !" % (
                                            line.room_number.name))
        return True

    def update_history(self):
        # print("update_history======")
        self.gds_reservation_check()
        so = super(hotel_reservation, self).update_history()
        return so

    def create_folio(self):
        self.gds_reservation_check()
        so = super(hotel_reservation, self).create_folio()
        return so

    def confirmed_reservation(self):
        # print("confirmed_reservation====================")
        self.gds_reservation_check()
        so = super(hotel_reservation, self).confirmed_reservation()
        return so


class hotel_reservation_through_gds_configuration(models.Model):
    _name = 'hotel.reservation.through.gds.configuration'
    _description = 'Configuration through gds'

    name = fields.Datetime('From Date', required=True, )
    to_date = fields.Datetime('To Date', required=True)
    shop_id = fields.Many2one('sale.shop', 'Hotel', required=True, )
    company_id = fields.Many2one(
        'res.company', related='shop_id.company_id', string='Company', store=True)
    line_ids = fields.One2many(
        'hotel.reservation.through.gds.line', 'name', 'Line ID')

    _sql_constraints = [
        ('date_shop_id_uniq', 'unique(name,to_date,shop_id)',
         'Combination Of From date, To date and shop must be unique !'),
    ]

    @api.constrains('to_date')
    def _check_duration(self):
        obj_period = self.browse(self._ids[0])
        if obj_period.to_date < obj_period.name:
            return False
        return True

        # for obj_period in self:
        #     pids = self.search([('to_date', '>=', obj_period.name), (
        #         'name', '<=', obj_period.to_date), ('id', '<>', obj_period.id)])
        #     for period in pids:
        #         if period.shop_id.id == obj_period.shop_id.id:
        #             return False
        # return True

    @api.constrains('to_date')
    def _check_year_limit(self):
        for obj_period in self:
            pids = self.search([('to_date', '>=', obj_period.name), (
                'name', '<=', obj_period.to_date), ('id', '<>', obj_period.id)])
            for period in pids:
                if period.shop_id.id == obj_period.shop_id.id:
                    return False
        return True


#     _constraints = [
#         (_check_duration,'Error!\nThe duration of the Period(s) is/are invalid.', ['to_date']),
#         (_check_year_limit,'Error!\nThe period is invalid.Some periods are overlapping .', ['to_date'])
#     ]


class hotel_reservation_through_gds_line(models.Model):
    _name = 'hotel.reservation.through.gds.line'
    _description = 'Configuration through gds line'
    room_number = fields.Many2many('product.product', 'hotel_gds_reservation_rel', 'product_id', 'line_id', 'Room',
                                   domain="[('isroom','=',True),('categ_id','=',categ_id)]",
                                   help="Will list out all the rooms that belong to selected shop.")
    categ_id = fields.Many2one('product.category', 'Room Type', domain="[('isroomtype','=',True)]")
    name = fields.Many2one('hotel.reservation.through.gds.configuration', 'Line Id')


class hotel_reservation_line(models.Model):
    _inherit = "hotel.reservation.line"
    _description = "Reservation Line"

    @api.onchange('room_number')
    @api.depends('checkin', 'checkout', 'banquet_id.pricelist_id', 'banquet_id', 'line_id.partner_id', 'number_of_days',
                 'banquet_id.source')
    def onchange_room_id(self):
        # print("selffffffffff",self)
        v = {}
        res_list = []
        warning = ''

        if self.room_number:
            # print(self.room_number.id, "room_number")
            product_browse = self.room_number
            product_id = product_browse.id
            price = product_browse.lst_price
            if price is False:
                raise Warning("Couldn't find a pricelist line matching this product!")
            pricelist = self.line_id.pricelist_id.id

            ctx = self._context and self._context.copy() or {}
            ctx.update({'date': self.checkin})

            if pricelist:
                price = self.env['product.pricelist'].with_context(ctx).price_get(
                    self.room_number.id, self.number_of_days, {
                        'uom': product_browse.uom_id.id,
                        'date': self.checkin,
                    })[pricelist]

            v['price'] = price
            tax_ids = []
            for tax_line in product_browse.taxes_id:
                tax_ids.append(tax_line.id)
            v['taxes_id'] = [(6, 0, tax_ids)]
            v['checkin'] = self.checkin
            v['checkout'] = self.checkout

            reservation_start_date = self.checkin

            reservation_end_date = self.checkout

            config_id = self.env['hotel.reservation.through.gds.configuration'].search([])
            config_browse = config_id
            if config_browse and self.line_id.source != 'through_gds':
                for record in config_browse:
                    config_start_date = record.name
                    # print("config_start_date::::::::::::",config_start_date)

                    config_end_date = record.to_date
                    # print("config_end_date::::::::::::::::::",config_end_date)
                    config_start_date = datetime.strptime(str(config_start_date), '%Y-%m-%d %H:%M:%S')
                    config_end_date = datetime.strptime(str(config_end_date), '%Y-%m-%d %H:%M:%S')

                    # print("11111111111111111111111111111111111111111111jdkfjsdjfdskfjdsjfk", config_start_date,type(config_start_date),reservation_start_date,type(reservation_start_date),config_end_date,type(config_end_date,),reservation_end_date,type(reservation_end_date))

                    if (config_start_date <= reservation_start_date < config_end_date) or (
                            config_start_date < reservation_end_date <= config_end_date) or (
                            (reservation_start_date < config_start_date) and (reservation_end_date > config_end_date)):
                        # print("inside if")
                        for line in record.line_ids:
                            room_list = []
                            for room in line.room_number:
                                room_list.append(room.id)
                            if self.room_number.id in room_list:
                                # print('room********', self.room_number.id)
                                raise UserError("Room  is reserved in this period for GDS reservation!")
            room_line_id = self.env['hotel.room'].search([('product_id', '=', product_id)])

            housekeeping_room = self.env['hotel.housekeeping'].search([('room_no', '=', room_line_id.product_id.id)])
            if housekeeping_room:
                for house1 in housekeeping_room:
                    house = house1
                    house_current_date = house.current_date
                    house_current_date = datetime.combine(house_current_date, datetime.min.time())
                    house_current_date = datetime.strptime(str(house_current_date), '%Y-%m-%d %H:%M:%S')

                    house_end_date = house.end_date
                    house_end_date = datetime.combine(house_end_date, datetime.min.time())
                    house_end_date = datetime.strptime(str(house_end_date), '%Y-%m-%d %H:%M:%S')

                    start_reser = self.checkin
                    end_reser = self.checkout

                    if (((start_reser < house_current_date) and (end_reser > house_end_date)) or (
                            house_current_date <= start_reser < house_end_date) or (
                                house_current_date < end_reser <= house_end_date)) and (house.state == 'dirty'):
                        raise UserError("Warning! Room  %s is not clean for reservation period !" % (room_line_id.name))

            if room_line_id.room_folio_ids:
                for history in room_line_id.room_folio_ids:
                    if history.state == 'done':
                        history_start_date = history.check_in
                        history_end_date = history.check_out

                        room_line_id = self.env['hotel.room'].search([('product_id', '=', product_id)])
                        housekeeping_room = self.env['hotel.housekeeping'].search([
                            ('room_no', '=', room_line_id.product_id.id), ('state', '=', 'dirty')])
                        if housekeeping_room:
                            for house1 in housekeeping_room:
                                # print(" i am innnnnn")
                                house = house1
                                house_current_date = (datetime.strptime(str(house.current_date), '%Y-%m-%d')).date()
                                house_end_date = (datetime.strptime(str(house.end_date), '%Y-%m-%d')).date()
                                start_reser = datetime.strptime(str(self.checkin), '%Y-%m-%d %H:%M:%S').date()
                                end_reser = datetime.strptime(str(self.checkout), '%Y-%m-%d %H:%M:%S').date()
                                if (house_current_date <= start_reser <= house_end_date) or (
                                        house_current_date <= end_reser <= house_end_date) or (
                                        (start_reser < house_current_date) and (end_reser > house_end_date)):
                                    raise UserError("Room  %s is not clean for reservation period !" % (
                                        room_line_id.name))

                        if (history_start_date <= reservation_start_date < history_end_date) or (
                                history_start_date < reservation_end_date <= history_end_date) or (
                                (reservation_start_date < history_start_date) and (
                                reservation_end_date > history_end_date)):
                            # print("cccccc",history_start_date,reservation_start_date,history_end_date,history_end_date)
                            if not (self.line_id.id == history.booking_id.id):
                                raise UserError("Room  %s is booked in this reservation period !" % (room_line_id.name))
        return {'value': v, 'warning': warning}
