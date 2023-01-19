# -*- encoding: utf-8 -*-

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import math
import pytz
from dateutil.parser import *
import time
from dateutil.relativedelta import relativedelta
import datetime
from datetime import date
from odoo import fields, models, api, SUPERUSER_ID
from odoo.exceptions import ValidationError, Warning, UserError
from odoo.exceptions import UserError
from odoo.tools import config
import odoo.addons.decimal_precision as dp
from odoo.tools.translate import _
from odoo.tools import format_amount
import calendar
from datetime import datetime, timedelta, timezone
import logging

_logger = logging.getLogger(__name__)

utc_time = datetime.utcnow()


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
    pricelist_obj = self.env[
        'product.pricelist'].browse(pricelist_ids)
    if pricelist_ids:
        pricelist_item_ids.append(pricelist_ids)
        pricelist_obj = self.env[
            'product.pricelist'].browse(pricelist_ids)

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
        price = currency_obj.compute(
            price, pricelist_obj.currency_id.id, round=False)
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


# Class creation for ID Master


class id_master(models.Model):
    _name = 'id.master'
    _description = 'Clients ID details'

    name = fields.Char('ID Name', required=True)
    id_code = fields.Char('ID Code', required=True)


class checkout_configuration(models.Model):
    _name = 'checkout.configuration'
    _description = 'Checkout Configuration'

    name = fields.Selection([('custom', 'Custom'), ('24hour', '24 Hours')],
                            'Checkout Time', default='24hour', required=True)
    time = fields.Selection([
        ('01', '1 AM'), ('02', '2 AM'), ('03', '3 AM'), ('04', '4 AM'), ('05', '5 AM'), (
            '06', '6 AM'), ('07', '7 AM'), ('08', '8 AM'), ('09', '9 AM'), ('10', '10 AM'),
        ('11', '11 AM'), ('12', '12 Noon'), ('13', '1 PM'), ('14', '2 PM'), ('15', '3 PM'), (
            '16', '4 PM'), ('17', '5 PM'), ('18', '6 PM'), ('19', '7 PM'), ('20', '8 PM'),
        ('21', '9  PM'), ('22', '10 PM'), ('23',
                                           '11 PM'), ('24', '12 Mid Night')
    ], 'Time', default='10')
    shop_id = fields.Many2one('sale.shop', 'Hotel', required=True,
                              help="Will show list of shop that belongs to allowed companies of logged-in user. \n -Assign a shop to configure shop-wise check out policy.")
    company_id = fields.Many2one(
        'res.company', related='shop_id.company_id', string='Company', store=True)

    # _sql_constraints = [
    #     ('shop_id_uniq', 'unique(shop_id)', 'Shop must be unique !'),
    # ]


class sale_order(models.Model):
    _inherit = "sale.order"
    _description = "Sale Order Inherit "

    def _amount_line_tax(self, line):
        val = 0.0
        taxes = line.tax_id.compute_all(
            line.price_unit * (1 - (line.discount or 0.0) / 100.0), None, line.product_uom_qty)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    def _amount_all(self):
        for order in self:
            order.update({
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            })
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
                val1 += line.price_subtotal
                val += self._amount_line_tax(line)
            if cur:
                total = cur.round(val1) + cur.round(val)
                order.update({
                    'amount_untaxed': cur.round(val1),
                    'amount_tax': cur.round(val),
                    'amount_total': total,
                })

    state = fields.Selection(selection_add=[
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'To Invoice'),
        ('progress', 'In Progress'),
        ('check_out', 'CheckOut'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Order State', readonly=True, index=True)

    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     tracking=5)

    amount_tax = fields.Monetary(
        string='Taxes', store=True, readonly=True, compute='_amount_all')

    amount_total = fields.Monetary(
        string='Total', store=True, readonly=True, compute='_amount_all')

    transfer_invoice_ids = fields.Many2many('account.move', 'sale_transfer_account_invoice_rel', 'sale_id',
                                            'invoice_id', "Transfer Invoice Details")


class hotel_reservation(models.Model):
    _name = "hotel.reservation"
    _description = "Reservation"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    def unlink(self):
        for record in self:
            if record.state in ['confirm', 'done']:
                raise UserError(
                    "Reservation could not be Deleted once it is Confirm")
            else:
                for hotel_id in record:
                    hotel_id.reservation_line.unlink()
        return super(hotel_reservation, self).unlink()

    def hotel_reservation_web_unlink(self):
        hotel_reservation_ids = self.search(
            [('state', '=', 'draft')])
        remove_web_draft = self.env['ir.config_parameter'].get_param(
            'remove_draft_web_reservation')
        # print(remove_web_draft)
        time_diff = 0
        for reservation in hotel_reservation_ids:

            current_datetime = fields.Datetime.now()
            reservation_line = self.env['hotel.reservation.line'].search(
                [('line_id', '=', reservation.id)], limit=1)
            if reservation_line.checkin:
                diff = current_datetime - reservation_line.checkin
                time_diff = int(diff.seconds // 60)
            # print(type(remove_web_draft),remove_web_draft,type(time_diff),time_diff)
            if remove_web_draft:
                if time_diff > int(remove_web_draft):
                    reservation.cancel_reservation()

    # @api.multi

    def action_set_to_dirty(self):
        self.write({'state': 'draft'})

        return True

    @api.depends('total_cost1', )
    def _get_advance_payment(self):
        sum = 0.00
        remaining = 0.00
        for obj in self:
            obj.update({
                'total_advance': 0.0,
                'remaining_amt': 0.0,
            })
            sum = 0
            for line in obj.account_move_ids:
                move_lines = self.env['account.move.line'].search(
                    [('move_id', '=', line.id)])
                if move_lines:
                    for mv in move_lines:
                        sum = sum + mv.debit
            obj.update({
                'total_advance': sum,
                'remaining_amt': obj.total_cost1 - sum
            })

    def advance_payment(self):
        reservation = self
        res_id = reservation.id
        value = {}
        data_id = self.env['ir.model.data']._xmlid_to_res_id(
            'hotel_management.advance_payment_wizard1')
        if self._context is None:
            self._context = {}
        ctx = dict(self._context)
        ctx['active_ids'] = [reservation]
        ctx['reservation_id'] = res_id
        if data_id:
            view_id1 = data_id

        value = {
            'name': _('Deposit amount entry'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'advance.payment.wizard',
            'view_id': view_id1,
            'context': ctx,
            'views': [(view_id1, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',

        }

        return value

    def update_resevation(self):
        for reservation in self:
            room_his_id_search = self.env['hotel.room.booking.history'].search(
                [('booking_id', '=', reservation.id)])
            room_his_id_search.unlink()
            if not reservation.reservation_line:
                raise ValidationError("Reservation line Details are missing.")
            for line in reservation.reservation_line:
                room_line_id = self.env['hotel.room'].search(
                    [('product_id', '=', line.room_number.id)])
                ###############################################by pornima######
                housekeeping_room = self.env['hotel.housekeeping'].search([
                    ('room_no', '=', room_line_id.product_id.id), ('state', '=', 'dirty')])
                if housekeeping_room:
                    for house1 in housekeeping_room:
                        # house = self.env['hotel.housekeeping'].browse(house1)
                        house = house1

                        house_current_date = (datetime.strptime(
                            str(house.current_date), '%Y-%m-%d')).date()
                        house_end_date = (datetime.strptime(
                            str(house.end_date), '%Y-%m-%d')).date()
                        start_reser = datetime.strptime(
                            str(line.checkin), '%Y-%m-%d %H:%M:%S').date()
                        end_reser = datetime.strptime(
                            str(line.checkout), '%Y-%m-%d %H:%M:%S').date()
                        if (house_current_date <= start_reser <= house_end_date) or (
                                house_current_date <= end_reser <= house_end_date) or (
                                (start_reser < house_current_date) and (end_reser > house_end_date)):
                            # if (((start_reser < house_current_date) and (end_reser > house_end_date)) or (house_current_date <= start_reser < house_end_date) or (house_current_date < end_reser <= house_end_date)) and (house.state == 'dirty'):
                            # print "i am in if loop--------------"
                            raise ValidationError(
                                "Room  %s is not clean for reservation period !" % (room_line_id.name))

                ###############################################

                if room_line_id.room_folio_ids:
                    for history in room_line_id.room_folio_ids:
                        if history.state == 'done':
                            history_start_date = history.check_in
                            history_end_date = history.check_out
                            reservation_start_date = datetime.strptime(
                                str(line.checkin), '%Y-%m-%d %H:%M:%S')
                            reservation_end_date = datetime.strptime(
                                str(line.checkout), '%Y-%m-%d %H:%M:%S')
                            if (history_start_date <= reservation_start_date < history_end_date) or (
                                    history_start_date < reservation_end_date <= history_end_date) or (
                                    (reservation_start_date < history_start_date) and (
                                    reservation_end_date > history_end_date)):
                                # print "Already Reserved......."
                                if not (reservation.id == history.booking_id.id):
                                    raise UserError("Room  %s is booked in this reservation period !" % (
                                        room_line_id.name,))
            for line in reservation.reservation_line:
                #                 print reservation,"reservation"
                room_line_id = self.env['hotel.room'].search(
                    [('product_id', '=', line.room_number.id)])
                room_his_id = self.env['hotel.room.booking.history'].create({
                    'partner_id': reservation.partner_id.id,
                    'check_in': line.checkin,
                    'check_out': line.checkout,
                    'history_id': room_line_id.id,
                    'product_id': line.room_number.id,
                    'booking_id': reservation.id,
                    'state': 'done',
                    'category_id': room_line_id.categ_id.id,
                    'name': line.room_number.name,
                    'check_in_date': (line.checkin).date(),
                    'check_out_date': (line.checkout).date(),
                })

    def write(self, vals):
        ret = super(hotel_reservation, self).write(vals)
        for res in self:
            if res:
                no_of_adults_room = 0
                no_of_child_room = 0
                if res.reservation_line:
                    for line in res.reservation_line:
                        if line:
                            no_of_adults_room += line.room_number.max_adult
                            no_of_child_room += line.room_number.max_child
                    _logger.info('\n\n\n{}\n{}\n{}\n\n\n'.format(
                        res.name, res.adults, vals))
                    if res.adults <= 0:
                        raise ValidationError(
                            'Please set no of adults for reservation')

                    if res.adults > no_of_adults_room:
                        raise ValidationError('You can not exceed the number of adults than the set limit on '
                                              'individual room.')

                    if res.childs > no_of_child_room:
                        raise ValidationError('You can not exceed the number of children than the set limit on '
                                              'individual room.')
        return ret

    @api.model
    def create(self, vals):

        vals['name'] = self.env['ir.sequence'].next_by_code(
            'hotel.reservation') or _('New')
        vals['reservation_no'] = vals['name']
        res = super(hotel_reservation, self).create(vals)
        if res:
            no_of_adults_room = 0
            no_of_child_room = 0
            if res.reservation_line:
                for line in res.reservation_line:
                    if line:
                        no_of_adults_room += line.room_number.max_adult
                        no_of_child_room += line.room_number.max_child

                if res.adults <= 0:
                    raise ValidationError(
                        'Please set no of adults for reservation')

                if res.adults > no_of_adults_room:
                    raise ValidationError('You can not exceed the number of adults than the set limit on '
                                          'individual room.')

                if res.childs > no_of_child_room:
                    raise ValidationError('You can not exceed the number of children than the set limit on '
                                          'individual room.')
        return res

    # @api.multi
    def _count_total_rooms(self):
        for order in self:
            count = 0
            for line in order.reservation_line:
                count += 1
            order.update({
                'number_of_rooms': count,
            })

    @api.onchange('pricelist_id')
    def onchange_pricelist_id(self):
        self.show_update_pricelist = True
        if 'checkin' in self._context and 'checkout' in self._context:
            room_obj = self.env['product.product']
            # print("ccccccccccccccccccccc",str(self._context['booking_data'][0]).split("_")[0])
            room_brw = room_obj.search(
                [('id', '=', self._context['hotel_resource'])])
            pricelist = self.env['sale.shop'].browse(
                int(self._context['shop_id'])).pricelist_id.id
            if pricelist == False:
                raise UserError(
                    ('Please set the Pricelist on the shop  %s to proceed further') % room_brw.shop_id.name)
            ctx = self._context and self._context.copy() or {}
            ctx.update({'date': self._context['checkin']})
            from dateutil import parser
            day_count1 = parser.isoparse(
                self._context['checkout']) - parser.isoparse(self._context['checkin'])

            day_count2 = day_count1.total_seconds()
            _logger.info("DIFF SECONDS===>>>>>>>>>{}".format(day_count2))
            day_count2 = day_count2 / 86400
            day_count2 = "{:.2f}".format(day_count2)
            day_count2 = math.ceil(float(day_count2))

            _logger.info("SELF CONTEXT====>>>>>{}".format(
                self._context['checkin']))
            res_line = {
                'categ_id': room_brw.categ_id.id,
                'room_number': room_brw.id,
                'checkin': parser.isoparse(self._context['checkin']),
                'checkout': parser.isoparse(self._context['checkout']),
                'number_of_days': int(day_count2),
                'price': self.env['product.pricelist'].with_context(ctx).price_get(room_brw.id, 1, {
                    'uom': room_brw.uom_id.id,
                })[pricelist]
            }
            if self.reservation_line:
                self.reservation_line.write(res_line)
            else:
                _logger.info("RES LINE===>>>>>>>>>>>>>>>{}".format(res_line))
                self.reservation_line = [[0, 0, res_line]]
        if not self.pricelist_id:
            return {}
        if not self.reservation_line:
            return {}
        if len(self.reservation_line) != 1:
            warning = {
                'title': _('Pricelist Warning!'),
                'message': _(
                    'If you change the pricelist of this order (and eventually the currency), prices of existing order lines will not be updated.')
            }
            return {'warning': warning}

    def update_prices(self):
        lines_to_update = []
        for line in self.reservation_line:
            product = line.room_number.with_context(
                quantity=line.number_of_days,
                date=line.checkin,
                pricelist=self.pricelist_id.id,
            )
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                line._get_display_price(product), line.room_number.taxes_id, line.taxes_id, line.company_id)
            if self.pricelist_id.discount_policy == 'without_discount' and price_unit:
                discount = max(0, (price_unit - product.price)
                               * 100 / price_unit)
            else:
                discount = 0
            lines_to_update.append(
                (1, line.id, {'price': price_unit, 'discount': discount}))
        self.update({'reservation_line': lines_to_update})
        self.show_update_pricelist = False
        self.message_post(body=_(
            "Product prices have been recomputed according to pricelist <b>%s<b> " % self.pricelist_id.display_name))

    def _amount_line_tax(self, line):
        val = 0.0
        taxes = line.taxes_id.compute_all(
            line.price * (1 - (line.discount or 0.0) / 100.0), quantity=line.number_of_days)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    # @api.multi
    def _get_subtotal_amount(self):
        total = 0.0
        for obj in self:
            for line in obj.reservation_line:
                total += line.sub_total1
                # print('Line Subtotal : ', line.sub_total1)
            obj.update({
                'untaxed_amt': obj.pricelist_id.currency_id.round(total),
            })

    # @api.multi
    def _get_total_tax(self):
        # get total tax on the room
        val1 = 0.0
        total1 = 0.0
        for obj in self:
            for line in obj.reservation_line:
                total1 += line.sub_total1
                val1 += self._amount_line_tax(line)
            if obj.pricelist_id:
                obj.update({
                    'total_tax': obj.pricelist_id.currency_id.round(val1),
                })

    @api.depends('reservation_line')
    def _get_total_rental_cost(self):
        # total amount after deduction by tax
        for order in self:
            order.update({
                'total_cost1': 0.0,
            })
            total1 = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.reservation_line:
                total1 += line.sub_total1
                val1 += self._amount_line_tax(line)
            if cur:
                sum = cur.round(total1) + cur.round(val1)
            order.update({
                'total_cost1': sum,
            })

    # @api.multi
    @api.depends('adv_amount')
    def _get_advance_cost(self):
        total = 0
        for obj in self:
            total = 0
            if obj.adv_amount:
                total = obj.adv_amount
            obj.update({
                'deposit_cost2': total,
            })

    # @api.multi
    def _get_default_shop(self):
        user = self.env['res.users'].browse(self._uid)
        company_id = user.company_id.id
        shop_ids = self.env['sale.shop'].search(
            [('company_id', '=', company_id)])
        if not shop_ids:
            raise UserError(
                'There is no default shop for the current user\'s company!')
        return shop_ids[0]

    @api.onchange('shop_id')
    def onchange_shop(self):
        if self.shop_id:
            shop = self.shop_id
            if shop.pricelist_id:
                self.pricelist_id = shop.pricelist_id.id

    @api.onchange('partner_id')
    def onchange_patner(self):
        if self.partner_id:
            partner = self.partner_id
            if partner.property_product_pricelist:
                self.pricelist_id = partner.property_product_pricelist.id

    name = fields.Char('Event type', default=lambda self: _('New'))
    gds_id = fields.Char('GDS ID', readonly=True,
                         states={'draft': [('readonly', False)]})
    reservation_no = fields.Char(
        'Reservation No', readonly=True, index=True)
    date_order = fields.Datetime('Date Ordered', required=True, default=datetime.today(), readonly=True,
                                 states={'draft': [('readonly', False)]})
    shop_id = fields.Many2one('sale.shop', 'Hotel', required=True,
                              default=_get_default_shop, readonly=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one(
        'res.partner', 'Guest Name', required=True, readonly=True, states={'draft': [('readonly', False)]})
    pricelist_id = fields.Many2one(
        'product.pricelist', 'Pricelist', required=True, readonly=True, states={'draft': [('readonly', False)]})
    #                 'checkin': fields.datetime('Expected-Date-Arrival',required=True,readonly=True, states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
    #                 'checkout': fields.datetime('Expected-Date-Departure',required=True, readonly=True, states={'draft':[('readonly',False)],'confirm':[('readonly',False)]}),
    adults = fields.Integer('Adults', )
    childs = fields.Integer('Children',)
    reservation_line = fields.One2many(
        'hotel.reservation.line', 'line_id', 'Reservation Line', readonly=False, states={'done': [('readonly', True)]})
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), (
        'done', 'Done'), ('cancel', 'Cancelled')], 'State', default='draft', readonly=True)
    folio_id = fields.Many2many(
        'hotel.folio', 'hotel_folio_reservation_rel', 'order_id', 'invoice_id', 'Folio')
    dummy = fields.Datetime('Dummy')
    source = fields.Selection([('internal_reservation', 'Internal Reservation'), ('through_web', 'Through Web'), (
        'through_gds', 'Through GDS')], 'Source', default='internal_reservation', index=True, readonly=True,
        states={'draft': [('readonly', False)]})
    number_of_rooms = fields.Integer(
        compute="_count_total_rooms", string="Number Of Rooms")
    untaxed_amt = fields.Float(
        compute="_get_subtotal_amount", string="Untaxed Amount")

    total_tax = fields.Float(string="Reservation Tax",
                             compute="_get_total_tax")
    deposit_cost1 = fields.Float(string="deposit cost", )
    total_cost1 = fields.Float(
        string="Total Reservation cost", compute="_get_total_rental_cost", readonly=True)
    company_id = fields.Many2one(
        'res.company', related='shop_id.company_id', string='Company', store=True)

    id_line_ids = fields.One2many('hotel.resv.id.details', 'reservation_id',
                                  'ID Line', readonly=False, states={'done': [('readonly', True)]})
    via = fields.Selection([('direct', 'Direct'), ('agent', 'Agent')], "Via",
                           readonly=True, default='direct', states={'draft': [('readonly', False)]}, )
    agent_id = fields.Many2one('res.partner', 'Agent', readonly=True, states={
        'draft': [('readonly', False)]}, )
    invoiced = fields.Boolean('Invoiced', default=False)
    adv_amount = fields.Float("Advance Amount")

    deposit_recv_acc = fields.Many2one(
        'account.account', string="Deposit Account", required=False)

    deposit_cost2 = fields.Float(
        compute="_get_advance_cost", string="Advance Payment", store=True)
    agent_comm = fields.Float("Commision")
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id.id)
    note = fields.Text(string='Note')
    account_move_ids = fields.Many2many('account.move', 'reservation_account_move_rel', 'reservation_id', 'move_id',
                                        "Payment Details")
    total_advance = fields.Float(
        compute="_get_advance_payment", string="Total Advance Payment", )
    remaining_amt = fields.Float(
        compute="_get_advance_payment", string="Total Remaining Amount", )
    show_update_pricelist = fields.Boolean(string='Has Pricelist Changed')

    folio_count = fields.Integer(
        compute="_compute_folio", string='Folio Count', copy=False, default=0, readonly=True)
    folio_ids = fields.Many2many('hotel.folio', compute="_compute_folio", string='Invoices', copy=False,
                                 readonly=True)
    reference = fields.Char('Rederence')

    def _compute_folio(self):
        for order in self:
            folio = self.env['hotel.folio'].search(
                [('reservation_id', '=', order.id)])
            order.folio_ids = folio
            order.folio_count = len(folio)

    def action_view_folio(self):
        folio = self.mapped('folio_ids')
        action = self.env.ref(
            'hotel.open_hotel_folio1_form_tree').sudo().read()[0]
        if len(folio) > 1:
            action['domain'] = [('id', 'in', folio.ids)]
        elif len(folio) == 1:
            form_view = [
                (self.env.ref('hotel.view_hotel_folio1_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + \
                    [(state, view)
                     for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = folio.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    # @api.multi

    def compute(self):
        total = 0
        val = 0
        for obj in self:
            for line in obj.reservation_line:
                line.count_price()
                total += line.sub_total1
                val += self._amount_line_tax(line)
        self.total_tax = self.pricelist_id.currency_id.round(val)
        self.untaxed_amt = self.pricelist_id.currency_id.round(total)
        sum = self.total_tax + self.untaxed_amt
        self.total_cost1 = sum
        return True

    # @api.multi
    def onchange_partner_id(self, cr, uid, ids, part):
        if not part:
            return {'value': {'partner_invoice_id': False, 'partner_shipping_id': False, }}
        addr = self.pool.get('res.partner').address_get(
            cr, uid, [part], ['delivery', 'invoice', 'contact'])
        result = {}
        warning = {}
        title = False
        message = False
        partner = self.pool.get('res.partner').browse(cr, uid, part)
        if partner.reservation_warn != 'no-message':
            if partner.reservation_warn == 'block':
                raise UserError(
                    _('Alert for %s!') % (partner.name), partner.reservation_msg)
            title = _("Warning for %s") % partner.name
            message = partner.reservation_msg
            warning = {
                'title': title,
                'message': message
            }

        if result.get('warning', False):
            warning['title'] = title and title + ' & ' + \
                result['warning']['title'] or result['warning']['title']
            warning['message'] = message and message + ' ' + \
                result['warning']['message'] or result['warning']['message']

        return {'value': {'partner_invoice_id': addr['invoice'], 'partner_shipping_id': addr['delivery'],
                          'value1': result.get('value', {}), },
                'warning': warning}

    @api.onchange('adv_amount')
    def onchange_adv_amount(self):
        if self.adv_amount:
            self.deposite = self.adv_amount

    # @api.multi
    def cancel_reservation(self):
        for reservation in self:
            if reservation.state in ['draft', 'confirm']:
                room_his_id_search = self.env['hotel.room.booking.history'].search(
                    [('booking_id', '=', reservation.id)])
                room_his_id_search.unlink()
        self.write({'state': 'cancel'})

    def back_to_dashboard(self):
        return {
            'type': 'ir.actions.act_url',
            'url': 'localhost:3000/dashboards',
            'target': 'current'
        }

    # @api.multi
    def confirmed_reservation(self):
        for reservation in self:
            if reservation.source == 'internal_reservation':
                if not reservation.reservation_line:
                    raise UserError(_('Please Select Room'))
            if reservation.total_cost1 < reservation.deposit_cost2:
                raise ValidationError(
                    "Advance Amount Should not be greater than Total Reservation Cost.")
            if not reservation.reservation_line:
                raise ValidationError("Reservation line Details are missing.")
            for line in reservation.reservation_line:
                room_line_id = self.env['hotel.room'].search(
                    [('product_id', '=', line.room_number.id)])
                ###############################################by pornima######
                housekeeping_room = self.env['hotel.housekeeping'].search([
                    ('room_no', '=', room_line_id.product_id.id), ('state', '=', 'dirty')])
                if housekeeping_room:
                    for house1 in housekeeping_room:
                        house_brw = self.env[
                            'hotel.housekeeping'].browse(house1)
                        house = house_brw.id
                        house_current_date = (datetime.strptime(
                            str(house.current_date), '%Y-%m-%d')).date()
                        house_end_date = (datetime.strptime(
                            str(house.end_date), '%Y-%m-%d')).date()
                        start_reser = datetime.strptime(
                            str(line.checkin), '%Y-%m-%d %H:%M:%S').date()
                        end_reser = datetime.strptime(
                            str(line.checkout), '%Y-%m-%d %H:%M:%S').date()
                        if (house_current_date <= start_reser <= house_end_date) or (
                                house_current_date <= end_reser <= house_end_date) or (
                                (start_reser < house_current_date) and (end_reser > house_end_date)):
                            raise ValidationError(
                                "Room  %s is not clean for reservation period !" % (room_line_id.name))
                #
                ###############################################
                if room_line_id.room_folio_ids:
                    for history in room_line_id.room_folio_ids:
                        if history.state == 'done':
                            history_start_date = history.check_in
                            history_end_date = history.check_out
                            reservation_start_date = line.checkin
                            reservation_end_date = line.checkout
                            if (history_start_date <= reservation_start_date < history_end_date) or (
                                    history_start_date < reservation_end_date <= history_end_date) or (
                                    (reservation_start_date < history_start_date) and (
                                    reservation_end_date >= history_end_date)):
                                if not (reservation.id == history.booking_id.id):
                                    raise UserError("Room  %s is booked in this reservation period !" % (
                                        room_line_id.name))

            for line in reservation.reservation_line:
                room_line_id = self.env['hotel.room'].search(
                    [('product_id', '=', line.room_number.id)])
                room_his_id = self.env['hotel.room.booking.history'].create({
                    'partner_id': reservation.partner_id.id,
                    'check_in': line.checkin,
                    'check_out': line.checkout,
                    'history_id': room_line_id.id,
                    'product_id': line.room_number.id,
                    'booking_id': reservation.id,
                    'state': 'done',
                    'category_id': room_line_id.categ_id.id,
                    'name': line.room_number.name,
                    'check_in_date': line.checkin,
                    'check_out_date': line.checkout
                })

            self.write({'state': 'confirm'})
            return True

    def update_history(self):
        for reservation in self:
            room_his_id_search = self.env['hotel.room.booking.history'].search(
                [('booking_id', '=', reservation.id)])
            room_his_id_search.unlink()
            if not reservation.reservation_line:
                raise ValidationError("Reservation line Details are missing.")
            for line in reservation.reservation_line:
                room_line_id = self.env['hotel.room'].search(
                    [('product_id', '=', line.room_number.id)])
                ###############################################by pornima######
                housekeeping_room = self.env['hotel.housekeeping'].search([
                    ('room_no', '=', room_line_id.product_id.id), ('state', '=', 'dirty')])
                if housekeeping_room:
                    for house1 in housekeeping_room:
                        # house = self.env['hotel.housekeeping'].browse(house1)
                        house = house1

                        house_current_date = (datetime.strptime(
                            str(house.current_date), '%Y-%m-%d')).date()
                        house_end_date = (datetime.strptime(
                            str(house.end_date), '%Y-%m-%d')).date()
                        start_reser = datetime.strptime(
                            str(line.checkin), '%Y-%m-%d %H:%M:%S').date()
                        end_reser = datetime.strptime(
                            str(line.checkout), '%Y-%m-%d %H:%M:%S').date()
                        if (house_current_date <= start_reser <= house_end_date) or (
                                house_current_date <= end_reser <= house_end_date) or (
                                (start_reser < house_current_date) and (end_reser > house_end_date)):
                            # if (((start_reser < house_current_date) and (end_reser > house_end_date)) or (house_current_date <= start_reser < house_end_date) or (house_current_date < end_reser <= house_end_date)) and (house.state == 'dirty'):
                            # print "i am in if loop--------------"
                            raise ValidationError("Room  %s is not clean for reservation period !") % (
                                room_line_id.name)

                ###############################################

                if room_line_id.room_folio_ids:
                    for history in room_line_id.room_folio_ids:
                        if history.state == 'done':
                            history_start_date = history.check_in
                            history_end_date = history.check_out
                            reservation_start_date = datetime.strptime(
                                str(line.checkin), '%Y-%m-%d %H:%M:%S')
                            reservation_end_date = datetime.strptime(
                                str(line.checkout), '%Y-%m-%d %H:%M:%S')
                            if (history_start_date <= reservation_start_date < history_end_date) or (
                                    history_start_date < reservation_end_date <= history_end_date) or (
                                    (reservation_start_date < history_start_date) and (
                                    reservation_end_date > history_end_date)):
                                # print "Already Reserved......."
                                if not (reservation.id == history.booking_id.id):
                                    raise UserError("Room  %s is booked in this reservation period !" % (
                                        room_line_id.name,))
            for line in reservation.reservation_line:
                #                 print reservation,"reservation"
                room_line_id = self.env['hotel.room'].search(
                    [('product_id', '=', line.room_number.id)])
                room_his_id = self.env['hotel.room.booking.history'].create({
                    'partner_id': reservation.partner_id.id,
                    'check_in': line.checkin,
                    'check_out': line.checkout,
                    'history_id': room_line_id.id,
                    'product_id': line.room_number.id,
                    'booking_id': reservation.id,
                    'state': 'done',
                    'category_id': room_line_id.categ_id.id,
                    'name': line.room_number.name,
                    'check_in_date': (line.checkin).date(),
                    'check_out_date': (line.checkout).date(),
                })
        return True

    def create_folio(self):

        for reservation in self:
            room_his_id_search = self.env['hotel.room.booking.history'].search(
                [('booking_id', '=', reservation.id)])
            room_his_id_search.unlink()
            if not reservation.reservation_line:
                raise ValidationError("Reservation line Details are missing.")
            for line in reservation.reservation_line:
                room_line_id = self.env['hotel.room'].search(
                    [('product_id', '=', line.room_number.id)])

                # print("\n\nbolock")
                ###############################################by pornima######
                housekeeping_room = self.env['hotel.housekeeping'].search(
                    [('room_no', '=', room_line_id.product_id.id), ('state', '=', 'dirty')])
                # "housekeeping_room--------------------------------------------------------------------",housekeeping_room
                if housekeeping_room:
                    for house1 in housekeeping_room:
                        house_brw = self.env[
                            'hotel.housekeeping'].browse(house1)
                        house = house_brw.id
                        house_current_date = (
                            datetime.strptime(str(house.current_date), '%Y-%m-%d')).date()
                        house_end_date = (
                            datetime.strptime(str(house.end_date), '%Y-%m-%d')).date()
                        start_reser = datetime.strptime(
                            str(line.checkin), '%Y-%m-%d %H:%M:%S').date()
                        end_reser = datetime.strptime(
                            str(line.checkout), '%Y-%m-%d %H:%M:%S').date()
                        if (house_current_date <= start_reser <= house_end_date) or (
                                house_current_date <= end_reser <= house_end_date) or (
                                (start_reser < house_current_date) and (end_reser > house_end_date)):
                            # if (((start_reser < house_current_date) and (end_reser > house_end_date)) or (house_current_date <= start_reser < house_end_date) or (house_current_date < end_reser <= house_end_date)) :
                            # print "i am in if loop--------------\n\n\n\n\n"
                            raise ValidationError("Room  %s is not clean for reservation period !") % (
                                room_line_id.name)

                ###############################################

                if room_line_id.room_folio_ids:
                    for history in room_line_id.room_folio_ids:
                        if history.state == 'done':
                            history_start_date = history.check_in
                            history_end_date = history.check_out
                            reservation_start_date = line.checkin
                            reservation_end_date = line.checkout
                            if (history_start_date <= reservation_start_date < history_end_date) or (
                                    history_start_date < reservation_end_date <= history_end_date) or (
                                    (reservation_start_date < history_start_date) and (
                                    reservation_end_date > history_end_date)):

                                if not (reservation.id == history.booking_id.id):
                                    raise UserError("Room  %s is booked in this reservation period !" % (
                                        room_line_id.name,))

            line = reservation.reservation_line

            folio = self.env['hotel.folio'].create({
                'date_order': reservation.date_order,
                'shop_id': reservation.shop_id.id,
                'partner_id': reservation.partner_id.id,
                'pricelist_id': reservation.pricelist_id.id,
                'partner_invoice_id': reservation.partner_id.id,
                'partner_shipping_id': reservation.partner_id.id,

                #                 'checkin_date': line.checkin,
                #                 'checkout_date': line.checkout,
                'reservation_id': reservation.id,
                # 'duration': line1.number_of_days,
                'note': reservation.note,
                # 'service_lines': reservation.other_items_ids,
            })
            for line in reservation.reservation_line:
                room_line_id = self.env['hotel.room'].search(
                    [('product_id', '=', line.room_number.id)])
                room_his_id = self.env['hotel.room.booking.history'].create({
                    'partner_id': reservation.partner_id.id,
                    'check_in': datetime.now(),
                    'check_out': line.checkout,
                    'history_id': room_line_id.id,
                    'product_id': line.room_number.id,
                    'booking_id': reservation.id,
                    'state': 'done',
                    'category_id': line.room_number.categ_id.id,  # room_line_id.categ_id.id,
                    'name': line.room_number.name,
                    'check_in_date': line.checkin,
                    'check_out_date': line.checkout,
                })
                tax_ids = []
                for tax_line in line.taxes_id:
                    tax_ids.append(tax_line.id)
                vals = {
                    'folio_id': folio.id,
                    'product_id': line.room_number.id,
                    'name': line.room_number.name,
                    'product_uom': line.room_number.uom_id.id,
                    'price_unit': line.price,
                    'product_uom_qty': line.number_of_days,
                    'checkin_date': datetime.now(),
                    'checkout_date': line.checkout,
                    'discount': line.discount,
                    'tax_id': [(6, 0, tax_ids)],
                    'categ_id': line.room_number.categ_id.id,  # room_line_id.categ_id.id,
                    'hotel_reservation_line_id': line.id
                }
                self.env["hotel_folio.line"].create(vals)

                # for service_line in reservation.other_items_ids:
                #     product_id = self.env['product.product'].search(
                #         [('id', '=', service_line.product_id.id)])
                #     print("SERVICE LINE ID===>>>", product_id)
                #     vals = {
                #         'folio_id': folio.id,
                #         'product_id': product_id.id,
                #         'name': product_id.name,
                #         'product_uom': service_line.product_uom.id,
                #         'product_uom_qty': service_line.product_uom_qty,
                #         'price_unit': service_line.price_unit,
                #
                #     }
                #     self.env["hotel_service.line"].create(vals)

            for rec_id in reservation.id_line_ids:
                rec_id.write({'folio_id': folio.id})
            for mv in reservation.account_move_ids:
                self._cr.execute('insert into sale_account_move_rel(sale_id, move_id) values (%s,%s)',
                                 (folio.id, mv.id))

            reservation.reservation_line.write({
                'checkin': datetime.now(),
            })
            reservation.write(
                {'state': 'done', 'agent_comm': reservation.total_cost1, })
        return True

    def done(self):
        active_id = self._context.get('active_ids')
        for reservation in self:
            # print "reservation.deposit_cost2=======================",
            # reservation.total_cost1
            if reservation.deposit_cost2:
                data_obj = self.env['ir.model.data']
                data_id = data_obj._get_id(
                    'hotel_management', 'deposit_journal_entry_wizard1')
                # print data_id,"data_id=------------------------"
                view_id1 = False
                if self._context is None:
                    self_context = {}
                ctx = dict(self._context)
                ctx['active_ids'] = [reservation.id]
                ctx['booking_id'] = reservation.id
                if data_id:
                    view_id1 = data_obj.browse(data_id).res_id
                value = {
                    'name': _('Advance Payment Entry'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'deposit_journal_entry.wizard1',
                    'view_id': False,
                    'context': ctx,
                    'views': [(view_id1, 'form')],
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'nodestroy': True
                }
                return value
            else:
                so = self.create_folio()
                return so

    def _send_order_confirmation_mail(self):
        if self.env.su:
            # sending mail in sudo was meant for it being sent from superuser
            self = self.with_user(SUPERUSER_ID)
        # template_id = self._find_mail_template(force_confirmation_template=True)
        # if template_id:
        #     for order in self:
        #         order.with_context(force_send=True).message_post_with_template(template_id, composition_mode='comment', email_layout_xmlid="mail.mail_notification_paynow")


class hotel_reservation_line(models.Model):
    _name = "hotel.reservation.line"
    _description = "Reservation Line"

    def write(self, vals):
        # print('write-----------------------------------------',vals)
        res = super(hotel_reservation_line, self).write(vals)
        for ret in self:
            if 'checkin' in vals or 'checkout' in vals:
                ret.onchange_date_count_total_days()
        return res

    @api.model
    def create(self, vals):
        checkin = vals['checkin']
        checkout = vals['checkout']
        if checkout and checkin > checkout:
            raise UserError(
                'Error! Departure date must be greater than Arrival Date')
        so = super(hotel_reservation_line, self).create(vals)
        return so

    @api.onchange('checkin', 'checkout', )
    @api.depends('line_id.shop_id')
    def onchange_date_count_total_days(self):
        shop_id = None
        if not self.checkin:
            return False
        if not self.checkout:
            return False

        current_date = datetime.today().date()
        date_object = (self.checkout, '%Y-%m-%d %H:%M:%S')

        if current_date != date_object:
            if self.checkin >= self.checkout:
                checkout = self.checkin
                checkout += timedelta(days=1)
                self.checkout = checkout
                _logger.info("TYPE==>>>>%s", checkout)

        if self.line_id:
            shop_id = self.line_id.shop_id.id
            _logger.info("SHOP ID===>>>>>>>>>>>>{}".format(shop_id))
            if not shop_id:
                raise UserError('Shop must be set before selection of room.')
            policy_obj = self.env['checkout.configuration'].sudo().search(
                [('shop_id', '=', shop_id)])
            _logger.info(
                "Policy OBJ===>>>>>>>>>>>>>>>>>>{}".format(policy_obj))
            if not policy_obj:
                raise UserError(
                    'Checkout policy is not define for selected Hotel.')

        check_in = self.checkin

        check_out = self.checkout

        _logger.info("DAY COUNT====>>>>%s", check_in)
        _logger.info("DAY COUNT====>>>>%s", check_out)
        day_count1 = check_out - check_in

        day_count2 = day_count1.total_seconds()

        day_count2 = day_count2 / 86400
        day_count2 = "{:.2f}".format(day_count2)
        _logger.info("DIFFERENCE==>>>>>>>>>{}".format(day_count2))
        day_count2 = math.ceil(float(day_count2))

        _logger.info("DAY COUNT22===>>>>>>>>>>>>>>>>{}".format(day_count2))

        self.number_of_days = day_count2

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
                raise ValidationError(
                    "Couldn't find a pricelist line matching this product!")
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

            check_config = self.env['ir.model'].search(
                [('model', '=', 'hotel.reservation.through.gds.configuration')])
            if check_config:
                config_id = self.env[
                    'hotel.reservation.through.gds.configuration'].search([])
                # print("\n\n----------config_gds id\n\n",config_id)
                config_browse = config_id
                # print("\n\n----------config_gds id\n\n",config_id)
                if config_browse and self.line_id.source != 'through_gds':
                    for record in config_browse:
                        config_start_date = record.name
                        # print("config_start_date::::::::::::",config_start_date)

                        config_end_date = record.to_date
                        # print("config_end_date::::::::::::::::::",config_end_date)
                        config_start_date = datetime.strptime(
                            str(config_start_date), '%Y-%m-%d %H:%M:%S')
                        config_end_date = datetime.strptime(
                            str(config_end_date), '%Y-%m-%d %H:%M:%S')

                        # print("11111111111111111111111111111111111111111111jdkfjsdjfdskfjdsjfk", config_start_date,type(config_start_date),reservation_start_date,type(reservation_start_date),config_end_date,type(config_end_date,),reservation_end_date,type(reservation_end_date))

                        if (config_start_date <= reservation_start_date < config_end_date) or (
                                config_start_date < reservation_end_date <= config_end_date) or (
                                (reservation_start_date < config_start_date) and (
                                reservation_end_date > config_end_date)):
                            # print("inside if")
                            for line in record.line_ids:
                                room_list = []
                                for room in line.room_number:
                                    room_list.append(room.id)
                                if self.room_number.id in room_list:
                                    # print('room********', self.room_number.id)
                                    raise UserError(
                                        "Room  is reserved in this period for GDS reservation!")

            room_line_id = self.env['hotel.room'].search(
                [('product_id', '=', product_id)])

            housekeeping_room = self.env['hotel.housekeeping'].search(
                [('room_no', '=', room_line_id.product_id.id)])
            if housekeeping_room:
                for house1 in housekeeping_room:
                    house = house1
                    house_current_date = house.current_date
                    house_current_date = datetime.combine(
                        house_current_date, datetime.min.time())
                    house_current_date = datetime.strptime(
                        str(house_current_date), '%Y-%m-%d %H:%M:%S')

                    house_end_date = house.end_date
                    house_end_date = datetime.combine(
                        house_end_date, datetime.min.time())
                    house_end_date = datetime.strptime(
                        str(house_end_date), '%Y-%m-%d %H:%M:%S')

                    start_reser = self.checkin
                    end_reser = self.checkout

                    if (((start_reser < house_current_date) and (end_reser > house_end_date)) or (
                            house_current_date <= start_reser < house_end_date) or (
                                house_current_date < end_reser <= house_end_date)) and (house.state == 'dirty'):
                        raise UserError(
                            "Warning! Room  %s is not clean for reservation period !" % (room_line_id.name))

            if room_line_id.room_folio_ids:
                for history in room_line_id.room_folio_ids:
                    if history.state == 'done':
                        history_start_date = history.check_in
                        history_end_date = history.check_out

                        room_line_id = self.env['hotel.room'].search(
                            [('product_id', '=', product_id)])
                        housekeeping_room = self.env['hotel.housekeeping'].search([
                            ('room_no', '=', room_line_id.product_id.id), ('state', '=', 'dirty')])
                        if housekeeping_room:
                            for house1 in housekeeping_room:
                                # print(" i am innnnnn")
                                house = house1
                                house_current_date = (
                                    datetime.strptime(str(house.current_date), '%Y-%m-%d')).date()
                                house_end_date = (
                                    datetime.strptime(str(house.end_date), '%Y-%m-%d')).date()
                                start_reser = datetime.strptime(
                                    str(self.checkin), '%Y-%m-%d %H:%M:%S').date()
                                end_reser = datetime.strptime(
                                    str(self.checkout), '%Y-%m-%d %H:%M:%S').date()
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
                                raise UserError(
                                    "Room  %s is booked in this reservation period !" % (room_line_id.name))
        return {'value': v, 'warning': warning}

    @api.depends('number_of_days', 'discount', 'price', 'taxes_id')
    def count_sub_total1(self):
        for line in self:
            tax_amount = 0
            price = line.price * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.taxes_id.compute_all(price, line.line_id.currency_id, line.number_of_days,
                                              product=line.room_number,
                                              partner=line.line_id.partner_id)
            for tax in taxes['taxes']:
                tax_amount = tax_amount + tax['amount']
            line.update({
                'sub_total1': taxes['total_excluded'],
            })

    currency_id = fields.Many2one(
        related='line_id.currency_id', store=True, string='Currency', readonly=True)
    line_id = fields.Many2one('hotel.reservation')
    room_number = fields.Many2one('product.product', 'Room Number',
                                  domain="[('isroom','=',True),('categ_id','=',categ_id)]",
                                  help="Will list out all the rooms that belong to selected shop.", required=True)
    categ_id = fields.Many2one(
        'product.category', 'Room Type', required=True, )
    price = fields.Float("Price")
    discount = fields.Float('Discount (%)', digits=(16, 2))
    number_of_days = fields.Integer(string="Number Of Days", default=1)
    sub_total1 = fields.Float(
        string='Sub Total', store=True, readonly=True, compute='count_sub_total1')
    taxes_id = fields.Many2many('account.tax', 'reservation_taxes_rel', 'prod_id', 'tax_id', 'Taxes', domain=[
        ('type_tax_use', 'in', ['sale', 'all'])])
    checkin = fields.Datetime(
        'Checkin Date', required=True, default=lambda self: fields.Datetime.now())
    checkout = fields.Datetime('Checkout Date', required=True, )
    company_id = fields.Many2one(
        related='line_id.company_id', comodel_name='res.company', string='Company', store=True)

    @api.model
    def default_get(self, default_fields):
        # _logger.info("USER===>>>>>>>>>>>{}".format(self.env.user))
        _logger.info(
            "\n\n\n\nSELF CONTEXT===>>>>>>>>>>>>>{}".format(self._context))
        if self.env.user.id == 4:
            user_id = self.env['res.users'].search([('id', '=', 2)])
        else:
            user_id = self.env.user

        # _logger.info("TZ===>>>>>>>>>>>>>>>{}".format(user_id.tz))
        tz = pytz.timezone(user_id.tz)
        # print("\n\n\n--------------timezone------------------\n\n", tz)
        time_difference = tz.utcoffset(utc_time).total_seconds()
        # print("\n\n\n------time_difference------\n\n\n", time_difference)

        # _logger.info("TIME DIFFERENCE===>>>>>>>>>>>>>>>>>>{}".format(time_difference))

        vals = super(hotel_reservation_line, self).default_get(default_fields)
        # _logger.info("VALS===>>>>>>>>>>>>>>>>{}".format(self.room_number))
        tax_ids = []
        if self.room_number:
            for tax_line in self.room_number.taxes_id:
                tax_ids.append(tax_line.id)

        _logger.info("TAXES ID===>>>>>>>>>>>>>>{}".format(tax_ids))

        if self._context.get('shop_id'):
            sale_shop_id = self.env['sale.shop'].search(
                [('id', '=', self._context.get('shop_id'))])
            _logger.info("SALE SHOP===>>>>>{}".format(sale_shop_id))
            checkout_policy_id = self.env['checkout.configuration'].search(
                [('shop_id', '=', self._context.get('shop_id'))])
            if len(checkout_policy_id) > 1:
                raise ValidationError(
                    'It looks like you have setup multiple checkout policy for one shop.\nPlease check the configuration.')
            # _logger.info("Checkout Policy===>>>{}".format(checkout_policy_id))

            if checkout_policy_id.name == 'custom':
                time = int(checkout_policy_id.time)
                if vals.get('checkin'):
                    checkin = vals.get('checkin')
                    checkin = datetime(
                        checkin.year, checkin.month, checkin.day)
                    checkout_date = checkin + timedelta(days=1)
                    checkout = checkout_date + \
                        timedelta(hours=00, minutes=00, seconds=00)

                    to_string = fields.Datetime.to_string(checkout)
                    # _logger.info("TO STRING====>>>>{}".format(to_string))
                    from_string = fields.Datetime.from_string(to_string)
                    # _logger.info("FROM STRING====>>>>{}".format(from_string))

                    checkout = from_string
                    checkout = checkout + timedelta(hours=time)
                    checkout = checkout - timedelta(seconds=time_difference)

                    # _logger.info("\n\n\n\n\nVALS=====>>>>>>>>>>>>>>>>>>{}".format(checkout))
                    vals.update({'checkout': checkout})

                elif self._context.get('checkin'):

                    checkin = self._context.get('checkin')
                    check_in_from_string = fields.Datetime.from_string(
                        self._context.get('checkin'))
                    checkin = datetime(
                        check_in_from_string.year, check_in_from_string.month, check_in_from_string.day)
                    checkin = checkin + timedelta(hours=int(time))

                    checkout = self._context.get('checkout')
                    checkout_from_string = fields.Datetime.from_string(
                        self._context.get('checkout'))
                    checkout = datetime(
                        checkout_from_string.year, checkout_from_string.month, checkout_from_string.day)
                    checkout = checkout + timedelta(hours=int(time))

                    checkout = checkout - timedelta(seconds=time_difference)
                    checkin = checkin - timedelta(seconds=time_difference)

                    vals.update({'checkout': checkout, 'checkin': checkin})

            else:
                if vals.get('checkin'):
                    checkin = vals.get('checkin')
                    checkout_date = checkin + timedelta(days=1)
                    checkout = checkout_date
                    _logger.info(
                        "CHECKOUT ====>>>>>>>>>>>{}".format(checkout_date))
                    vals.update({'checkout': checkout, })
            if tax_ids:
                vals.update({'taxes_id': [(6, 0, tax_ids)]})
            _logger.info(
                "\n\n\n\n\n\n\n\nVals====>>>>>>>>>>>>>>>>>>>>{}".format(vals))
        return vals

    def _get_display_price(self, product):
        # TO DO: move me in master/saas-16 on sale.order
        # awa: don't know if it's still the case since we need the "product_no_variant_attribute_value_ids" field now
        # to be able to compute the full price

        # it is possible that a no_variant attribute is still in a variant if
        # the type of the attribute has been changed after creation.
        # no_variant_attributes_price_extra = [
        #     ptav.price_extra for ptav in self.product_no_variant_attribute_value_ids.filtered(
        #         lambda ptav:
        #             ptav.price_extra and
        #             ptav not in product.product_template_attribute_value_ids
        #     )
        # ]
        # if no_variant_attributes_price_extra:
        #     product = product.with_context(
        #         no_variant_attributes_price_extra=tuple(
        #             no_variant_attributes_price_extra)
        #     )

        if self.line_id.pricelist_id.discount_policy == 'with_discount':

            return product.with_context(pricelist=self.line_id.pricelist_id.id).price
        product_context = dict(self.env.context, partner_id=self.line_id.partner_id.id,
                               date=self.line_id.date_order)

        final_price, rule_id = self.line_id.pricelist_id.with_context(product_context).get_product_price_rule(
            product or self.product_id, self.product_uom_qty or 1.0, self.line_id.partner_id)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(
            product, rule_id, self.product_uom_qty, self.line_id.pricelist_id.id)
        if currency != self.line_id.pricelist_id.currency_id:
            base_price = currency._convert(
                base_price, self.line_id.pricelist_id.currency_id,
                self.line_id.company_id or self.env.company, self.line_id.date_order or fields.Date.today())
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)


class hotel_room(models.Model):
    _inherit = "hotel.room"
    _description = "room Inherit "

    room_folio_ids = fields.One2many(
        "hotel.room.booking.history", "history_id", "Room Rental History", copy=False)

    @api.onchange('shop_id')
    def on_change_shop_id(self):
        if not self.shop_id:
            return {'value': {}}
        temp = self.shop_id
        self.company_id = temp.company_id.id


class hotel_room_booking_history(models.Model):
    _name = "hotel.room.booking.history"
    _description = "Hotel Room Booking History"

    product_id = fields.Integer("Product ID", readonly=True)
    history_id = fields.Many2one("hotel.room", "Room No", readonly=True)
    name = fields.Char('Product Name', readonly=True, required=True)
    category_id = fields.Many2one(
        "product.category", "room category", readonly=True)
    check_in = fields.Datetime('CheckIn Date', readonly=True)
    check_out = fields.Datetime('CheckOut Date', readonly=True)
    check_in_date = fields.Date('Check In Date', readonly=True)
    check_out_date = fields.Date('Check Out Date', readonly=True)
    partner_id = fields.Many2one('res.partner', "Partner Name", readonly=True)
    booking_id = fields.Many2one(
        'hotel.reservation', "Booking Ref", readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'),
                              ('cancle', 'Cancel'), ('done', 'Done')], 'State', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.user.company_id)


class hotel_food_line(models.Model):
    _name = 'hotel_food.line'
    _description = 'hotel Food line'
    _inherits = {'sale.order.line': 'food_line_id'}

    food_line_id = fields.Many2one(
        'sale.order.line', 'food_line_id', required=True, ondelete='cascade')
    folio_id = fields.Many2one('hotel.folio', 'folio_id', ondelete='cascade')
    source_origin = fields.Char('Source Origin')

    @api.model
    def create(self, vals):
        folio = self.env["hotel.folio"].browse([vals['folio_id']])[0]
        # if "product_id" in vals.keys():
        # self.env["product.product"].browse(
        #     vals['product_id']).write({'state': 'sellable'})
        vals.update({'order_id': folio.order_id.id})
        res = super(hotel_food_line, self).create(vals)
        return res

    @api.onchange('product_id')
    def product_id_change(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id
            self.price_unit = self.product_id.lst_price
            self.name = self.product_id.description_sale


class hotel_folio(models.Model):
    _inherit = "hotel.folio"
    _description = "Hotel Folio"

    @api.depends('amount_total', )
    def _get_advance_payment(self):

        sum = 0.00
        remaining = 0.00
        for obj in self:
            obj.update({
                'total_advance': 0.0,
                'remaining_amt': 0.0,
            })
            sum = 0

            for line in obj.account_move_ids:
                move_lines = self.env['account.move.line'].search(
                    [('move_id', '=', line.id)])
                if move_lines:
                    for mv in move_lines:
                        sum = sum + mv.debit
            obj.update({
                'total_advance': sum,
                'remaining_amt': obj.amount_total - sum
            })

    total_advance = fields.Float(
        compute="_get_advance_payment", string="Total Advance Payment", )
    remaining_amt = fields.Float(
        compute="_get_advance_payment", string="Total Remaining Amount", )

    account_move_ids = fields.Many2many('account.move', 'sale_account_move_rel', 'sale_id', 'move_id',
                                        "Payment Details")
    is_agent_commission_created = fields.Boolean('Is Agent Commission Created')

    def _rooms_reference(self):
        for order in self:
            order_ref = ''
            for line in order.room_lines:
                if line.product_id:
                    order_ref += line.product_id.name + ','
            if order_ref and order_ref[-1] == ',':
                order.update({
                    'rooms_ref': order_ref[:-1],
                    'rooms_ref1': order_ref[:-1],
                })
            else:
                order.update({
                    'rooms_ref': order_ref,
                    'rooms_ref1': order_ref,
                })

    transport_line_ids = fields.One2many(
        'hotel_folio_transport.line', 'folio_id')
    laundry_line_ids = fields.One2many(
        'hotel_folio_laundry.line', 'folio_id', 'Folio Ref')

    reservation_id = fields.Many2one('hotel.reservation', 'Reservation Ref')
    laundry_invoice_ids = fields.Many2many(
        'account.move', 'laundry_folio_invoice_rel', 'folio_id', 'invoice_id', 'Laundry Related Invoices',
        readonly=True)
    transport_invoice_ids = fields.Many2many(
        'account.move', 'transport_folio_invoice_rel', 'folio_id', 'invoice_id', 'Transport Related Invoices',
        readonly=True)
    id_line_ids = fields.One2many(
        'hotel.resv.id.details', 'folio_id', 'ID Line')
    food_lines = fields.One2many('hotel_food.line', 'folio_id')
    rooms_ref = fields.Char(compute="_rooms_reference",
                            string="Room No", compute_sudo=False)
    rooms_ref1 = fields.Char(compute="_rooms_reference", compute_sudo=False,
                             string="Room Number", store=True)

    def advance_payment(self):
        reservation = self
        res_id = reservation.reservation_id
        data_obj = self.env['ir.model.data'].sudo().search(
            [('name', '=', 'advance_payment_wizard1')])
        data_id = data_obj.id
        view_id1 = False
        if self._context is None:
            self._context = {}
        ctx = dict(self._context)
        ctx['active_ids'] = [reservation.id]
        ctx['reservation_id'] = res_id.id
        if data_id:
            view_id1 = data_obj.browse(data_id).res_id
        value = {
            'name': _('Deposit amount entry'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'advance.payment.wizard',
            'view_id': False,
            'context': ctx,
            'views': [(view_id1, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True
        }
        return value

    # @api.multi
    def action_checkout(self):
        folio = self.browse(self._ids)[0]
        for room in folio.room_lines:
            sdate = room.checkout_date
            housekeeping_id = self.env['hotel.housekeeping'].create({
                'current_date': sdate,
                'end_date': (sdate + timedelta(1)).date(),
                'clean_type': 'checkout',
                'room_no': room.product_id.id,
                'inspector': self._uid,
                'inspect_date_time': sdate + timedelta(1),
                'state': 'dirty',
                'quality': 'clean',
            })

        self.write({'state': 'check_out'})
        return True

    # @api.multi
    def action_done(self):
        for line in self:
            # for invoice in line.invoice_ids:
            #     if (invoice.partner_id.id == line.partner_id.id) and invoice.payment_state not in ['paid',
            #                                                                                        'in_payment']:
            #         raise UserError('Invoice is not paid !')
            for invoice in line.transfer_invoice_ids:
                if invoice.payment_state != 'paid':
                    raise UserError('Transfer Invoice is not paid !')
        self.write({'state': 'done'})
        return True

    # @api.multi
    def action_cancel(self):
        today = time.strftime('%Y-%m-%d %H:%M:%S')
        today = datetime.strptime(str(today), '%Y-%m-%d %H:%M:%S')
        for obj in self:
            for room_id in obj.room_lines:
                if room_id.checkin_date <= today:
                    if obj.order_reserve_invoice_ids:
                        raise UserError(
                            'Error ! Invoice has been created, so You can not delete this record!')
                    if obj.table_order_invoice_ids:
                        raise UserError(
                            'Error ! Invoice has been created, so You can not delete this record!')
                    if obj.invoice_ids:
                        raise UserError(
                            'Error ! Invoice has been created, so You can not delete this record!')
                    if obj.picking_ids:
                        raise UserError(
                            'Error !', 'Invoice has been created, so You can not delete this record!')

                so = super(hotel_folio, self).action_cancel()
                for room in obj.room_lines:
                    room_line_id = self.env['hotel.room'].search(
                        [('product_id', '=', room.product_id.id)])
                    history_obj = self.env['hotel.room.booking.history'].search([
                        ('history_id', '=', room_line_id.id), ('booking_id', '=', obj.reservation_id.id)])
                    if history_obj:
                        history_browse = history_obj
                        history_browse.unlink()
        return so

    # @api.multi
    def action_wait(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context):
            if (not obj.invoice_ids):
                self.write(cr, uid, [obj.id], {'state': 'manual'})
            else:
                self.write(cr, uid, [obj.id], {'state': 'progress'})
            today = time.strftime('%Y-%m-%d')
            if obj.reservation_id.id:
                self.pool.get('hotel.reservation').compute(
                    cr, uid, [obj.reservation_id.id])
            for room in obj.room_lines:
                room_line_id = self.pool.get('hotel.room').search(
                    cr, uid, [('product_id', '=', room.product_id.id)])
                room_line_browse = self.pool.get(
                    'hotel.room').browse(cr, uid, room_line_id)
                history_obj = self.pool.get('hotel.room.booking.history').search(cr, uid, [
                    ('history_id', '=', room_line_browse[0].id), ('booking_id', '=', obj.reservation_id.id)])
                if history_obj:
                    history_browse = self.pool.get(
                        'hotel.room.booking.history').browse(cr, uid, history_obj)
                    self.pool.get('hotel.room.booking.history').write(cr, uid, history_browse[0].id, {
                        'check_in': room.checkin_date, 'check_out': room.checkout_date,
                        'check_in_date': room.checkin_date[0:10],
                        'check_out_date': room.checkout_date[0:10]})
        return {}

    # @api.multi
    def print_relatedinvoice(self, cr, uid, ids, context=None):
        '''
        This function prints the sales order and mark it as sent, so that we can see more easily the next step of the workflow
        '''
        id_list = []
        assert len(
            ids) == 1, 'This option should only be used for a single id at a time'
        for obj in self.browse(cr, uid, ids, context={}):
            if obj.invoice_ids:
                for invoice_id in obj.invoice_ids:
                    id_list.append(invoice_id.id)
            if obj.laundry_invoice_ids:
                for invoice_id in obj.laundry_invoice_ids:
                    id_list.append(invoice_id.id)
            if obj.transport_invoice_ids:
                for invoice_id in obj.transport_invoice_ids:
                    id_list.append(invoice_id.id)
            if obj.order_reserve_invoice_ids:
                for invoice_id in obj.order_reserve_invoice_ids:
                    id_list.append(invoice_id.id)
            if obj.table_order_invoice_ids:
                for invoice_id in obj.table_order_invoice_ids:
                    id_list.append(invoice_id.id)
        datas = {
            'model': 'account.move',
            'ids': id_list,
            'form': self.pool.get('account.move').read(cr, uid, id_list, context=context),
        }
        return {'type': 'ir.actions.report.xml', 'report_name': 'account.move', 'datas': datas, 'nodestroy': True}

    # @api.multi
    def update_folio_history(self):
        tax_ids = []
        folio = self
        if not folio.room_lines:
            raise ValidationError("Rooms line Details are missing.")
        book_search = self.env['hotel.room.booking.history'].search(
            [('booking_id', '=', folio.reservation_id.id)])
        if book_search:
            # self.env['hotel.room.booking.history'].unlink(book_search)
            book_search.unlink()
        if folio.reservation_id.reservation_line:
            # print
            # "folio.reservation_id.reservation_line=======================================",folio.reservation_id.reservation_line
            for res_line in folio.reservation_id.reservation_line:
                res_line.unlink()
        for folio_line in folio.room_lines:
            #
            for tax_line in folio_line.tax_id:
                tax_ids.append(tax_line.id)
            res_line_id = self.env['hotel.reservation.line'].create({
                'checkin': folio_line.checkin_date,
                'checkout': folio_line.checkout_date,
                'categ_id': folio_line.categ_id.id,
                'room_number': folio_line.product_id.id,
                'line_id': folio.reservation_id.id,
                'shop_id': folio.shop_id.id,
                'price': folio_line.price_unit,
                'discount': folio_line.discount,
                'taxes_id': [(6, 0, tax_ids)],
                'number_of_days': folio_line.product_uom_qty,
            })
            tax_ids = []
            room_line_id = self.env['hotel.room'].search(
                [('product_id', '=', folio_line.product_id.id)])
            room_his_id = self.env['hotel.room.booking.history'].create({
                'partner_id': folio.partner_id.id,
                'check_in': folio_line.checkin_date,
                'check_out': folio_line.checkout_date,
                'history_id': room_line_id.id,
                'product_id': folio_line.product_id.id,
                'booking_id': folio.reservation_id.id,
                'state': 'done',
                'category_id': folio_line.categ_id.id,
                'name': folio_line.product_id.name,
                'check_in_date': str(folio_line.checkin_date)[0:10],
                'check_out_date': str(folio_line.checkout_date)[0:10],
            })
        return True

    def write(self, vals):
        res = super(hotel_folio, self).write(vals)
        if 'state' in vals and vals['state'] == 'sale':
            if self.room_lines:
                for rec in self.room_lines:
                    rec.on_change_checkout()
        return res


class hotel_folio_line(models.Model):
    _inherit = 'hotel_folio.line'
    _description = 'hotel folio1 room line'

    _s = {'sale.order.line': 'order_line_id'}

    hotel_reservation_line_id = fields.Many2one(
        'hotel.reservation.line', 'hotel reservation line id=')

    @api.model
    def create(self, vals):
        checkin = vals['checkin_date']
        checkout = vals['checkout_date']
        if checkout and checkin > checkout:
            raise UserError(
                'Error! Departure date must be greater than Arrival Date')
        return super(hotel_folio_line, self).create(vals)

    @api.onchange('product_id')
    @api.depends('folio_id.pricelist_id', 'checkin_date', 'checkout_date', 'folio_id.partner_id', 'product_uom_qty',
                 'parent_id')
    def onchange_product_id(self):

        v = {}
        warning = ''
        if not self.folio_id.pricelist_id:
            raise ValidationError("PriceList is not Selected !")
        # if not (self.checkin_date and self.checkout_date):
        #     raise Warning(
        #         "Please Select Expected-Date-Arrival  and Expected-Date-Departure  before selecting room number!")
        date = str(self.checkin_date)[0:10]
        if self.product_id:
            product_browse = self.product_id
            # print(product_browse)
            price = product_browse.price
            if price is False:
                raise ValidationError(
                    "Couldn't find a pricelist line matching this product!2")

            v['price'] = price
            tax_ids = []
            for tax_line in product_browse.taxes_id:
                tax_ids.append(tax_line.id)
            v['taxes_id'] = [(6, 0, tax_ids)]
            v['checkin'] = self.checkin_date
            v['checkout'] = self.checkout_date
            room_line_id = self.env['hotel.room'].search(
                [('product_id', '=', self.product_id.id)])

            #############################Added by Pornima######################
            housekeeping_room = self.env['hotel.housekeeping'].search([
                ('room_no', '=', room_line_id.product_id.id), ('state', '=', 'dirty')])
            # print
            # "housekeeping_room--------------------------------------------------------------------",housekeeping_room
            if housekeeping_room:
                for house1 in housekeeping_room:
                    #                     print" i am innnnnn"
                    # house = self.env['hotel.housekeeping'].browse(house1.id)
                    # print("house::::::::::::;;",house)
                    # print("house.current_date:::::::::;",house.current_date,type(house.current_date))
                    house = house1

                    house_current_date = (datetime.strptime(
                        str(house.current_date), '%Y-%m-%d')).date()
                    house_end_date = (datetime.strptime(
                        str(house.end_date), '%Y-%m-%d')).date()
                    start_reser = datetime.strptime(
                        str(self.checkin_date), '%Y-%m-%d %H:%M:%S').date()
                    end_reser = datetime.strptime(
                        str(self.checkout_date), '%Y-%m-%d %H:%M:%S').date()
                    if (house_current_date <= start_reser <= house_end_date) or (
                            house_current_date <= end_reser <= house_end_date) or (
                            (start_reser < house_current_date) and (end_reser > house_end_date)):
                        raise UserError("Room  %s is not clean for reservation period !") % (
                            room_line_id.name)

            ###################################################################

            if room_line_id.room_folio_ids:
                for history in room_line_id.room_folio_ids:
                    if history.state == 'done':
                        history_start_date = history.check_in
                        history_end_date = history.check_out
                        reservation_start_date = self.checkin_date
                        reservation_end_date = self.checkout_date
                        if (history_start_date <= reservation_start_date < history_end_date) or (
                                history_start_date < reservation_end_date <= history_end_date) or (
                                (reservation_start_date < history_start_date) and (
                                reservation_end_date > history_end_date)):

                            # print "Already Reserved......."
                            # print("self.folio_id.id::::::::::",
                            #       self.folio_id, history.booking_id.id)
                            if not (self.folio_id.id == history.booking_id.id):
                                raise UserError(
                                    "Room  %s is booked in this reservation period !" % (room_line_id.name,))
            v['product_uom'] = product_browse.uom_id.id
            v['name'] = product_browse.name
            v['price_unit'] = product_browse.list_price
        return {'value': v}

    def unlink(self):
        for categ in self:
            categ.hotel_reservation_line_id.unlink()
            categ.order_line_id.unlink()
        return super(hotel_folio_line, self).unlink()


class hotel_service_line(models.Model):
    _inherit = 'hotel_service.line'
    _description = 'hotel Service line'
    _s = {'sale.order.line': 'service_line_id'}

    @api.onchange('product_id')
    def onchange_product_id(self):
        v = {}
        if self.product_id:
            date = time.strftime('%Y-%m-%d')
            self.product_uom = self.product_id.uom_id.id
            self.name = self.product_id.name if not self.product_id.description_sale else self.product_id.description_sale
            _logger.info(
                '------------- {} {}'.format(self.name, self.product_id.name))
            tax_ids = []
            for tax_line in self.product_id.taxes_id:
                tax_ids.append(tax_line.id)
            self.tax_id = [(6, 0, tax_ids)]
            self.product_uom_qty = 1
            self.price_unit = self.product_id.lst_price
        # return {'value': v}


class hotel_restaurant_tables(models.Model):
    _inherit = "hotel.restaurant.tables"
    _description = "Includes Hotel Restaurant Table"

    name = fields.Char('Table number', required=True,
                       states={'confirmed': [('readonly', True)]})
    capacity = fields.Integer(
        'Capacity', states={'confirmed': [('readonly', True)]})
    shop_id = fields.Many2one('sale.shop', 'Hotel', states={'confirmed': [('readonly', True)]},
                              help="Will show list of shop that belongs to allowed companies of logged-in user. \n -Assigning shop name to which this table no belongs to.")
    avl_state = fields.Selection([('available', 'Available'), ('book', 'Booked')], 'Availability Status',
                                 default='available', index=True, required=True,
                                 states={'confirmed': [('readonly', True)]})
    state = fields.Selection(selection_add=[('draft', 'Draft'), ('edit', 'Edit'), ('confirmed', 'Confirmed'), (
        'canceled', 'Cancel')], string='State', required=True, readonly=True,
        ondelete={'draft': 'set default', 'edit': 'set default', 'confirmed': 'set default',
                                       'canceled': 'set default'})

    company_id = fields.Many2one(
        'res.company', related='shop_id.company_id', string='Company', store=True)

    def confirm(self):
        self.write({'state': 'confirmed'})
        return True

    def cancel_supplier(self):
        self.write({'state': 'cancel'})
        return True

    def update_record(self):
        self.write({'state': 'edit'})
        return True


class hotel_restaurant_order(models.Model):
    _inherit = "hotel.restaurant.order"
    _description = "Includes Hotel Restaurant Order"

    @api.depends('order_list', 'order_list.tax_id', 'order_list.item_rate', 'order_list.item_qty')
    def _amount_tax(self):
        # print " In amount  ::::::        Tax"
        val = 0.00
        for line in self.order_list:
            taxes = line.tax_id.compute_all(
                line.item_rate, None, int(line.item_qty))
            val += taxes['total_included'] - taxes['total_excluded']
        if self.pricelist_id:
            self.amount_tax = self.pricelist_id.currency_id.round(val)
        else:
            self.amount_tax = val

    def _sub_total(self):
        # print "Sub Total ::::::        Tax"
        val = 0.00
        for line in self.order_list:
            val += line.price_subtotal
            # print "SubTotal ::::::", val
        if self.pricelist_id:
            self.amount_subtotal = self.pricelist_id.currency_id.round(val)
        else:
            self.amount_subtotal = val

    def _amount_untaxed(self):
        for line in self:
            total = sum(order.price_subtotal for order in line.order_list)
            # total += sum(fee.price_subtotal for fee in line.fees_lines)
            line.amount_untaxed = line.pricelist_id.currency_id.round(total)

    def _total(self):
        val = val1 = 0.0
        for line in self.order_list:
            taxes = line.tax_id.compute_all(
                line.item_rate, None, int(line.item_qty))
            val1 += line.price_subtotal
            # print "SubTotal -------", val1
            val += taxes['total_included'] - taxes['total_excluded']
            # print "Tax ------", val
        if self.pricelist_id:
            self.amount_tax = self.pricelist_id.currency_id.round(val)
            self.amount_untaxed = self.pricelist_id.currency_id.round(val1)
        else:
            self.amount_tax = val
            self.amount_untaxed = val1
            # print "subtotal  ------ ", self.amount_untaxed

        self.amount_total = self.amount_untaxed + self.amount_tax

    def _get_default_shop(self):
        company_id = self.env['res.users'].browse(self.env.uid).company_id.id
        shop_ids = self.env['sale.shop'].search(
            [('company_id', '=', company_id)]).ids
        if not shop_ids:
            raise UserError(
                'There is no default shop for the current user\'s company!')
        return shop_ids[0]

    @api.onchange('shop_id')
    def onchange_shop_id(self):
        v = {}
        if self.shop_id:
            shop = self.env['sale.shop'].browse(self.shop_id.id)
            if shop.pricelist_id:
                v['pricelist_id'] = shop.pricelist_id.id
                v['company_id'] = shop.company_id.id
        return {'value': v}

    waiter_name1 = fields.Many2one('res.users', 'Waiter User Name')
    partner_id = fields.Many2one('res.partner', 'Customer', required=True,
                                 help="Will show customer name corresponding to selected room no.")
    room_no = fields.Many2one(
        'hotel.room', 'Room No', help="Will show list of currently occupied room no that belongs to selected shop.")
    pricelist_id = fields.Many2one(
        'product.pricelist', 'Pricelist', required=True, readonly=True, states={'draft': [('readonly', False)]})
    shop_id = fields.Many2one('sale.shop', 'Hotel', default=_get_default_shop, required=True, readonly=True, states={
        'draft': [('readonly', False)]},
        help="Will show list of shop that belongs to allowed companies of logged-in user.")

    company_id = fields.Many2one(
        'res.company', related='shop_id.company_id', string='Company', store=True)

    state = fields.Selection(selection_add=[('draft', 'Draft'), ('confirm', 'Confirmed'), ('order', 'Order Done'), (
        'done', 'Done'), ('cancel', 'Cancelled')], string='State', index=True, required=True, readonly=True)
    flag = fields.Boolean("Flag", default=False)
    amount_subtotal = fields.Float(
        compute="_sub_total", string='SubTotal', compute_sudo=False)
    amount_tax = fields.Float(compute="_amount_tax", string='Tax')
    amount_total = fields.Float(compute="_total", string='Total')
    amount_untaxed = fields.Float(
        'Untaxed Amount', compute='_amount_untaxed', store=True)

    def confirm_order(self):
        # print("confirm")
        for obj in self:
            for line in obj.table_no:
                self.env['hotel.restaurant.tables'].write(
                    {'avl_state': 'book'})

        self.write({'state': 'confirm'})
        return True

    # @api.multi
    def generate_kot(self):

        kot_flag = True
        bot_flag = True
        kot_data = False
        bot_data = False
        check = True
        for order in self:
            table_ids = [x.id for x in order.table_no]
            for order_line in order.order_list:
                product_id = order_line.product_id
                product_nature = product_id.product_nature
                if product_nature == 'kot' and kot_flag:
                    order_data = {
                        'resno': order.order_no,
                        'kot_date': order.o_date,
                        'room_no': order.room_no.name,
                        'w_name': order.waiter_name1.name,
                        'shop_id': order.shop_id.id,
                        'tableno': [(6, 0, table_ids)] or False,
                        'product_nature': product_nature,
                        'pricelist_id': order.pricelist_id.id,
                    }
                    kot_flag = False

                if product_nature == 'kot' and order_line.states == True:
                    current_qty = int(order_line.item_qty) - \
                        order_line.previous_qty
                    res_no = order.order_no
                    product_ids = order_line.product_id.id
                    order_id = self.env['hotel.restaurant.order.list'].search(
                        [('product_id', '=', product_ids), ('kot_order_list.resno', '=', res_no)])
                    # print "after qty is----------->>",type(order_id)
                    if current_qty > 0:
                        kot_data = self.env[
                            'hotel.restaurant.kitchen.order.tickets'].create(order_data)
                        o_line = {
                            'product_id': order_line.product_id.id,
                            'kot_order_list': kot_data.id,
                            'name': order_line.product_id.name,
                            'item_qty': current_qty,
                            'item_rate': order_line.item_rate,
                            'product_nature': product_nature,
                        }
                        self.env['hotel.restaurant.order.list'].create(o_line)
                        self.env['hotel.restaurant.order.list'].write(
                            {'previous_qty': order_line.item_qty})

                if product_nature == 'kot' and order_line.states == False:
                    kot_data = self.env[
                        'hotel.restaurant.kitchen.order.tickets'].create(order_data)
                    total_qty = int(order_line.item_qty) + \
                        order_line.previous_qty

                    o_line = {
                        'product_id': order_line.product_id.id,
                        'kot_order_list': kot_data.id,
                        'name': order_line.product_id.id,
                        'item_qty': order_line.item_qty,
                        'item_rate': order_line.item_rate,
                        'product_nature': product_nature,
                        # 'total_qty': total_qty,
                    }
                    self.env['hotel.restaurant.order.list'].create(o_line)
                    self.env['hotel.restaurant.order.list'].write(
                        {'states': 'True', 'previous_qty': order_line.item_qty})

                total_qty = 0
                order_list = self.env['hotel.restaurant.order.list'].search([
                    ('product_id', '=', product_id.id), ('kot_order_list.resno', '=', order.order_no)])
                for order_qty in order_list:
                    p_qty = order_qty.item_qty
                    total_qty = total_qty + int(p_qty)
                self.env['hotel.restaurant.order.list'].write(
                    {'total': total_qty})
                if product_nature == 'bot' and bot_flag:
                    bot_order_data = {
                        'resno': order.order_no,
                        'kot_date': order.o_date,
                        'room_no': order.room_no.name,
                        'w_name': order.waiter_name1.name,
                        'shop_id': order.shop_id.id,
                        'tableno': [(6, 0, table_ids)],
                        'product_nature': product_nature,
                        'pricelist_id': order.pricelist_id.id,
                    }
                    bot_flag = False

                if product_nature == 'bot' and order_line.states == False:
                    bot_data = self.env['hotel.restaurant.kitchen.order.tickets'].create(
                        bot_order_data)
                    bot_o_line = {
                        'product_id': order_line.product_id.id,
                        'kot_order_list': bot_data.id,
                        'name': order_line.product_id.id,
                        'item_qty': order_line.item_qty,
                        'item_rate': order_line.item_rate,
                        'product_nature': product_nature,
                    }
                    self.env['hotel.restaurant.order.list'].create(bot_o_line)
                    self.env['hotel.restaurant.order.list'].write(
                        {'states': 'True', 'previous_qty': order_line.item_qty})

                if product_nature == 'bot' and order_line.states == True:
                    current_qty = int(order_line.item_qty) - \
                        order_line.previous_qty
                    if current_qty > 0:
                        bot_data = self.env[
                            'hotel.restaurant.kitchen.order.tickets'].create(bot_order_data)
                        o_line = {
                            'product_id': order_line.product_id.id,
                            'kot_order_list': bot_data,
                            'name': order_line.product_id.name,
                            'item_qty': current_qty,
                            'item_rate': order_line.item_rate,
                            'product_nature': product_nature,

                        }
                        self.env['hotel.restaurant.order.list'].create(o_line)
                        self.env['hotel.restaurant.order.list'].write(
                            {'states': 'True', 'previous_qty': order_line.item_qty})
            stock_brw = self.env['stock.picking'].search(
                [('origin', '=', order.order_no)])
            if stock_brw:
                for order_items in order.order_list:
                    order_list = self.env['hotel.restaurant.order.list'].search([
                        ('product_id', '=', order_items.product_id.id), ('kot_order_list.resno', '=', order.order_no)])
                    total_qty1 = 0
                    for order_qty in order_list:
                        p_qty1 = order_qty.item_qty
                        total_qty1 = total_qty1 + int(p_qty1)
                    product_id = self.env['hotel.menucard'].browse(
                        order_items.product_id.id).product_id.id

                    if product_id:
                        move_id = self.env['stock.move'].search(
                            [('product_id', '=', product_id), ('picking_id', '=', stock_brw.id)])
                        if move_id:
                            self.env['stock.move'].write(
                                {'product_uom_qty': total_qty1, })

        self.write({'state': 'order'})
        return True

    @api.onchange('pricelist_id')
    def onchange_pricelist_id(self):
        if not self.pricelist_id:
            return {}
        if not self.order_list or self.order_list == [(6, 0, [])]:
            return {}
        if len(self.order_list) != 1:
            warning = {
                'title': _('Pricelist Warning!'),
                'message': _(
                    'If you change the pricelist of this order (and eventually the currency), prices of existing order lines will not be updated.')
            }
            return {'warning': warning}

    @api.onchange('o_date')
    def onchange_odate(self):
        new_ids = []

        # Old Logic
        # main_obj_ids = self.env['hotel.room.booking.history'].search([
        #     ('check_in', '<=', self.o_date), ('check_out', '>=', self.o_date), ('state', '=', 'done')])
        # for dest_line in main_obj_ids:
        #     new_ids.append(dest_line.history_id.id)

        # New Logic
        room_lines = self.env['hotel.folio'].search(
            [('state', '=', 'draft')]).mapped('room_lines')
        for rec in room_lines:
            if rec.product_id:
                room_id = self.env['hotel.room'].search(
                    [('product_id', '=', rec.product_id.id)])
                if room_id:
                    new_ids.append(room_id.id)

        return {
            'domain': {
                'room_no': [('id', 'in', new_ids)],
            }}

    @api.depends('o_date')
    @api.onchange('room_no')
    def onchange_room_no(self):
        res = {}
        booking_id = 0
        # history_obj = self.env["hotel.room.booking.history"]
        if not self.room_no:
            return {'value': {'partner_id': False}}
        # for folio_hsry_id in history_obj.search([('history_id', '=', self.room_no.id), ('state', '=', 'done')]):
        #     hstry_line_id = folio_hsry_id
        #     start_dt = hstry_line_id.check_in
        #     end_dt = hstry_line_id.check_out
        #     if (start_dt <= self.o_date) and (end_dt >= self.o_date):
        #         booking_id = hstry_line_id.booking_id.id
        #         folio_obj_id = self.env["hotel.folio"].search(
        #             [('reservation_id', '=', booking_id)])
        #         if not folio_obj_id:
        #             raise UserError(
        #                 'Please create folio for selected room first.')
        #         res['folio_id'] = folio_obj_id[0].id
        #         res['partner_id'] = hstry_line_id.partner_id.id
        # new logic updated on 13-June-2022
        room_lines = self.env['hotel.folio'].search(
            [('state', '=', 'draft')]).mapped('room_lines')
        # print('room_lines : {}'.format(room_lines))
        for rec in room_lines:
            if rec.product_id.id == self.room_no.product_id.id:
                folio_id = rec.folio_id
                if folio_id:
                    res['folio_id'] = folio_id.id
                    res['partner_id'] = folio_id.partner_id.id
                    break
        return {'value': res}

        # @api.multi

    def create_invoice(self):
        for obj in self:
            for line in obj.table_no:
                self.env['hotel.restaurant.tables'].write(
                    {'avl_state': 'available'})

            acc_id = obj.partner_id.property_account_receivable_id.id
            journal_obj = self.env['account.journal'].search(
                [('type', '=', 'sale')], limit=1)

            journal_id = None
            if journal_obj[0]:
                journal_id = journal_obj[0].id

            type = 'out_invoice'

            if not obj.room_no:
                inv = {
                    # 'name': '/',
                    'invoice_origin': obj.order_no,
                    'move_type': type,
                    'ref': "Order Invoice",
                    # 'account_id': acc_id,
                    'partner_id': obj.partner_id.id,
                    'currency_id': obj.pricelist_id.currency_id.id,
                    'journal_id': journal_id,
                    # 'amount_tax': 0,
                    # 'amount_untaxed': obj.amount_total,
                    # 'amount_total': obj.amount_total,
                }
                inv_id = self.env['account.move'].create(inv)
                todo = []
                for ol in obj.order_list:
                    todo.append(ol.id)
                    if ol.product_id.categ_id:
                        a = ol.product_id.categ_id.property_account_income_categ_id.id
                        if not a:
                            raise ValidationError(_(
                                'There is no expense account defined for this product: "%s" (id:%d)') % (
                                ol.product_id.name, ol.product_id.id,))
                    else:
                        a = self.env['ir.property'].get(
                            'property_account_income_categ', 'product.category').id

                    tax_ids = []
                    for tax_line in ol.tax_id:
                        tax_ids.append(tax_line.id)
                    # il = {
                    #     'name': ol.product_id.name,
                    #     'account_id': a,
                    #     'price_unit': ol.item_rate,
                    #     'quantity': ol.item_qty,
                    #     'uos_id': False,
                    #     'origin': obj.order_no,
                    #     'invoice_id': inv_id.id,
                    #     'price_subtotal': ol.price_subtotal,
                    #     'tax_line_ids': [(6, 0, tax_ids)],
                    # }
                    # self.env['account.move.line'].create(il)
                    inv_line_values = {
                        'invoice_line_ids': [(0, 0, {
                            'name': ol.product_id.name,
                            'move_id': inv_id.id,
                            'account_id': a,
                            'price_unit': ol.item_rate,
                            'quantity': float(ol.item_qty),
                            'product_id': ol.product_id.product_id.id,

                            # 'uos_id': False,
                            # 'origin': obj.order_number,
                            # 'move_id': inv_id.id,
                            #                         'pay_date':obj.date1,
                            # 'order_amt': ol.price_subtotal,
                            'tax_ids': [(6, 0, tax_ids)],
                        })]
                    }

                    inv_id.write({

                        'invoice_line_ids': [(0, 0, {
                            'name': ol.product_id.name,
                            'move_id': inv_id.id,
                            'account_id': a,
                            'price_unit': ol.item_rate,
                            'quantity': float(ol.item_qty),
                            'product_id': ol.product_id.product_id.id,

                            # 'uos_id': False,
                            # 'origin': obj.order_number,
                            # 'move_id': inv_id.id,
                            #                         'pay_date':obj.date1,
                            # 'order_amt': ol.price_subtotal,
                            'tax_ids': [(6, 0, tax_ids)],
                        })]
                    })
        self.write({'state': 'done'})
        # service = self.browse()
        if self.folio_id.id:
            for r in self.order_list:
                tax_ids = []
                for tax_line in r.tax_id:
                    tax_ids.append(tax_line.id)
                so_line = {
                    'name': r.product_id.name,
                    'product_uom_qty': r.item_qty,
                    'product_id': r.product_id.product_id.id,
                    'price_unit': r.item_rate,
                    'product_uom': r.product_id.product_id.uom_id.id,
                    'order_id': self.folio_id.order_id.id,
                    'tax_id': [(6, 0, tax_ids)],
                }
                so_line_id = self.env['sale.order.line'].create(so_line)

                service_line = {
                    'folio_id': self.folio_id.id,
                    'food_line_id': so_line_id.id,
                    'source_origin': obj.order_no,
                }
                service_line_id = self.env[
                    'hotel_food.line'].create(service_line)

        return True


class hotel_restaurant_reservation(models.Model):
    _inherit = "hotel.restaurant.reservation"
    _description = "Includes Hotel Restaurant Reservation"

    def _get_default_shop(self):
        company_id = self.env['res.users'].browse(self.env.uid).company_id.id
        shop_ids = self.env['sale.shop'].search(
            [('company_id', '=', company_id)]).ids
        if not shop_ids:
            raise UserError(
                'There is no default shop for the current user\'s company!')
        return shop_ids[0]

    @api.onchange('shop_id')
    def onchange_shop_id(self):
        v = {}
        if self.shop_id:
            shop = self.env['sale.shop'].browse(self.shop_id.id)
            if shop.pricelist_id:
                v['pricelist_id'] = shop.pricelist_id.id
        return {'value': v}

    cname = fields.Many2one('res.partner', 'Customer Name', required=True,
                            help="Will show customer name corresponding to selected room no.")
    room_no = fields.Many2one('hotel.room', 'Room No',
                              help="Will show list of currently occupied room no that belongs to selected shop.")
    pricelist_id = fields.Many2one(
        'product.pricelist', 'Pricelist', required=True)
    shop_id = fields.Many2one('sale.shop', 'Hotel', default=_get_default_shop, required=True, states={
        'draft': [('readonly', False)]},
        help="Will show list of shop that belongs to allowed companies of logged-in user.")

    company_id = fields.Many2one(
        'res.company', related='shop_id.company_id', string='Company', store=True)

    @api.onchange('pricelist_id')
    def onchange_pricelist_id(self):
        if not self.pricelist_id:
            return {}
        if not self.order_list_ids or self.order_list_ids == [(6, 0, [])]:
            return {}
        if len(self.order_list_ids) != 1:
            warning = {
                'title': _('Pricelist Warning!'),
                'message': _(
                    'If you change the pricelist of this order (and eventually the currency), prices of existing order lines will not be updated.')
            }
            return {'warning': warning}

    @api.onchange('start_date', 'end_date')
    def onchange_date(self):
        new_ids = []

        main_obj_ids = self.env['hotel.room.booking.history'].search(
            [('check_in', '<=', self.start_date), ('check_out', '>=', self.end_date), ('state', '!=', 'cancel')])
        for dest_line in main_obj_ids:
            new_ids.append(dest_line.history_id.id)
        return {
            'domain': {
                'room_no': [('id', 'in', new_ids)],
            }}

    @api.onchange('room_no', 'start_date', 'end_date')
    def onchange_room_no(self):
        res = {}
        booking_id = 0
        history_obj = self.env["hotel.room.booking.history"]
        folio_obj = self.env["hotel.folio"]
        if not self.room_no:
            return {'value': {'partner_id': False}}
        for folio_hsry_id in history_obj.search([('history_id', '=', self.room_no.id), ('state', '=', 'done')]):
            history_start_date = folio_hsry_id.check_in
            history_end_date = folio_hsry_id.check_out
            if (history_start_date <= self.start_date < history_end_date) or (
                    history_start_date < self.end_date <= history_end_date) or (
                    (self.start_date < history_start_date) and (self.end_date >= history_end_date)):
                booking_id = folio_hsry_id.booking_id.id
                folio_obj_id = folio_obj.search(
                    [('reservation_id', '=', booking_id)])
                res['folio_id'] = folio_obj_id
                res['cname'] = folio_obj_id.partner_id.id
        return {'value': res}

    def create_order(self):
        for i in self:
            table_ids = [x.id for x in i.tableno]
            order_list_ids = [x.id for x in i.order_list_ids]
            kot_data = self.env['hotel.reservation.order'].create({
                'reservation_id': i.id,
                'date1': i.start_date,
                'partner_id': i.cname.id,
                'room_no': i.room_no.id,
                'folio_id': i.folio_id.id,
                'table_no': [(6, 0, table_ids)],
                # 'order_list_ids': [(6, 0, order_list_ids)],
                'pricelist_id': i.pricelist_id.id,
                'shop_id': i.shop_id.id,
            })

            for line in i.order_list_ids:
                line.write({'o_l': kot_data.id})
            kot_browse = self.env[
                'hotel.reservation.order'].browse(kot_data.id)
        self.write({'state': 'order'})
        return True

    def table_reserved(self):
        for reservation in self:
            self.write({'state': 'confirm'})
            return True


class hotel_reservation_order(models.Model):
    _inherit = "hotel.reservation.order"
    _description = "Includes Hotel Reservation order"

    def _sub_total(self):
        # print "In reservation order Sub_total"
        val = 0.00
        for line in self.order_list:
            val += line.price_subtotal
            # print "SubTotal ::::::", val
        self.amount_subtotal = self.pricelist_id.currency_id.round(val)
        # print "        Subtotal", self.amount_subtotal

    def _amount_tax(self):
        val = 0.00
        for line in self.order_list:
            taxes = line.tax_id.compute_all(
                line.item_rate, None, int(line.item_qty), line.product_id.product_id, False)
            val += taxes['total_included'] - taxes['total_excluded']
        self.amount_tax = self.pricelist_id.currency_id.round(val)

    def _amount_untaxed(self):
        for line in self:
            total = sum(order.price_subtotal for order in line.order_list)
            # total += sum(fee.price_subtotal for fee in line.fees_lines)
            line.amount_untaxed = line.pricelist_id.currency_id.round(total)

    def _total(self):
        val = val1 = 0.0
        for line in self.order_list:
            taxes = line.tax_id.compute_all(
                line.item_rate, None, int(line.item_qty))
            val1 += line.price_subtotal
            # print "SubTotal -------", val1
            val += taxes['total_included'] - taxes['total_excluded']
            # print "Tax ------", val
        self.amount_tax = self.pricelist_id.currency_id.round(val)
        # print "amount Tax  ------ ", self.amount_tax
        self.amount_untaxed = self.pricelist_id.currency_id.round(val1)
        # print "subtotal  ------ ", self.amount_untaxed
        self.amount_total = self.amount_untaxed + self.amount_tax
        # print "Total  ------ ", self.amount_subtotal

    def _get_default_shop(self):
        company_id = self.env['res.users'].browse(self.env.uid).company_id.id
        shop_ids = self.env['sale.shop'].search(
            [('company_id', '=', company_id)]).ids
        if not shop_ids:
            raise UserError(
                'There is no default shop for the current user\'s company!')
        return shop_ids[0]

    @api.onchange('shop_id')
    def onchange_shop_id(self):
        v = {}
        if self.shop_id:
            shop = self.env['sale.shop'].browse(self.shop_id.id)
            if shop.pricelist_id:
                v['pricelist_id'] = shop.pricelist_id.id
        return {'value': v}

    waitername1 = fields.Many2one('res.users', 'Waiter User Name')
    pricelist_id = fields.Many2one(
        'product.pricelist', 'Pricelist', required=True)
    shop_id = fields.Many2one('sale.shop', 'Hotel',
                              required=True, default=_get_default_shop)

    company_id = fields.Many2one(
        'res.company', related='shop_id.company_id', string='Company', store=True)
    flag1 = fields.Boolean("Flag", default=False)
    amount_subtotal = fields.Float(compute="_sub_total", string='Subtotal')
    amount_tax = fields.Float(compute="_amount_tax", string='Tax')
    amount_total = fields.Float(compute="_total", string='Total')
    amount_untaxed = fields.Float(
        'Untaxed Amount', compute='_amount_untaxed', store=True)

    @api.onchange('pricelist_id')
    def onchange_pricelist_id(self):
        if not self.pricelist_id:
            return {}
        if not self.order_list or self.order_list == [(6, 0, [])]:
            return {}
        if len(self.order_list) != 1:
            warning = {
                'title': _('Pricelist Warning!'),
                'message': _(
                    'If you change the pricelist of this order (and eventually the currency), prices of existing order lines will not be updated.')
            }
            return {'warning': warning}

    def confirm_order(self):
        for obj in self:
            for line in obj.table_no:
                self.env['hotel.restaurant.tables'].write(
                    {'avl_state': 'book'})

        self.write({'state': 'confirm'})
        return True

    def create_invoice(self):
        for obj in self:
            for line in obj.table_no:
                self.env['hotel.restaurant.tables'].write(
                    {'avl_state': 'available'})

            acc_id = obj.partner_id.property_account_receivable_id.id
            journal_ids = self.env['account.journal'].search(
                [('type', '=', 'sale')], limit=1)
            journal_id = None
            if journal_ids:
                journal_id = journal_ids.id
            # added this id for pricing calculation for different pricelists
            type = 'out_invoice'
            if not obj.room_no:
                inv = {
                    'name': obj.order_number,
                    'invoice_origin': obj.order_number,
                    'move_type': type,
                    'ref': "Order Invoice",
                    # 'account_id': acc_id,
                    'partner_id': obj.partner_id.id,
                    'currency_id': obj.pricelist_id.currency_id.id,
                    'journal_id': journal_id,
                    # 'amount_tax': obj.amount_tax,
                    # 'amount_untaxed': (obj.amount_total - obj.amount_tax),
                    # 'amount_total': obj.amount_total,
                }
                inv_id = self.env['account.move'].create(inv)
                todo = []
                for ol in obj.order_list:
                    todo.append(ol.id)

                    if ol.product_id.categ_id:
                        a = ol.product_id.categ_id.property_account_income_categ_id.id
                        if not a:
                            raise ValidationError(_('Error !'), _(
                                'There is no expense account defined for this product: "%s" (id:%d)') % (
                                ol.product_id.name, ol.product_id.id,))

                    else:

                        a = self.env['ir.property'].get(
                            'property_account_income_categ', 'product.category').id
                    tax_ids = []
                    for tax_line in ol.tax_id:
                        tax_ids.append(tax_line.id)
                    inv_id.write({

                        'invoice_line_ids': [(0, 0, {
                            'name': ol.product_id.name,
                            'move_id': inv_id.id,
                            'account_id': a,
                            'price_unit': ol.item_rate,
                            'quantity': float(ol.item_qty),
                            'product_id': ol.product_id.product_id.id,

                            # 'uos_id': False,
                            # 'origin': obj.order_number,
                            # 'move_id': inv_id.id,
                            #                         'pay_date':obj.date1,
                            # 'order_amt': ol.price_subtotal,
                            'tax_ids': [(6, 0, tax_ids)],
                        })]
                    })
                    # print("il---", il)
                    # self.env['account.move.line'].create(il)
        self.write({'state': 'done'})

        if self.folio_id:
            for r in self.order_list:
                tax_ids = []
                for tax_line in r.tax_id:
                    tax_ids.append(tax_line.id)
                so_line = {
                    'name': r.product_id.name,
                    'product_uom_qty': r.item_qty,
                    'product_id': r.product_id.product_id.id,
                    'price_unit': r.item_rate,
                    'product_uom': r.product_id.product_id.uom_id.id,
                    'order_id': self.folio_id.order_id.id,
                    'tax_id': [(6, 0, tax_ids)],
                }
                so_line_id = self.env['sale.order.line'].create(so_line)
                service_line = {
                    'folio_id': self.folio_id.id,
                    'food_line_id': so_line_id.id,
                    'source_origin': obj.order_number,
                }
                service_line_id = self.env[
                    'hotel_food.line'].create(service_line)
        return True

    # @api.multi
    def reservation_generate_kot(self):
        kot_flag = True
        bot_flag = True
        kot_data = False
        bot_data = False
        for order in self:
            table_ids = [x.id for x in order.table_no]
            for order_line in order.order_list:
                product_id = order_line.product_id
                product_nature = product_id.product_nature
                if product_nature == 'kot' and kot_flag:
                    order_reservation_data = {
                        'resno': order.order_number,
                        'room_no': order.room_no.name,
                        'kot_date': order.date1,
                        'w_name': order.waitername1.name,
                        'shop_id': order.shop_id.id,
                        'tableno': [(6, 0, table_ids)],
                        'product_nature': product_id.product_nature,
                        'pricelist_id': order.pricelist_id.id,
                    }
                    kot_flag = False
                if product_nature == 'kot' and order_line.states == True:
                    current_qty = int(
                        order_line.item_qty) - order_line.previous_qty
                    if current_qty > 0:
                        kot_data_reserve = self.env['hotel.restaurant.kitchen.order.tickets'].create(
                            order_reservation_data)
                        o_line = {
                            'product_id': order_line.product_id.id,
                            'name': order_line.product_id.name,
                            'item_qty': current_qty,
                            'item_rate': order_line.item_rate,
                            'kot_order_list': kot_data_reserve,
                            'product_nature': product_id.product_nature,
                        }
                        self.env['hotel.restaurant.order.list'].create(o_line)
                        self.env['hotel.restaurant.order.list'].write(
                            {'previous_qty': order_line.item_qty})
                if product_nature == 'kot' and order_line.states == False:
                    kot_data = self.env['hotel.restaurant.kitchen.order.tickets'].create(
                        order_reservation_data)
                    total_qty = int(order_line.item_qty) + \
                        order_line.previous_qty
                    o_line = {
                        'product_id': order_line.product_id.id,
                        'name': order_line.product_id.id,
                        'item_qty': order_line.item_qty,
                        'item_rate': order_line.item_rate,
                        'kot_order_list': kot_data.id,
                        'product_nature': product_id.product_nature,
                        # 'total_qty': total_qty,
                    }
                    self.env['hotel.restaurant.order.list'].create(o_line)
                    self.env['hotel.restaurant.order.list'].write(
                        {'states': 'True', 'previous_qty': order_line.item_qty})

                if product_nature == 'bot' and bot_flag:
                    order_reservation_data_bot = {
                        'resno': order.order_number,
                        'room_no': order.room_no.name,
                        'kot_date': order.date1,
                        'w_name': order.waitername1.name,
                        'shop_id': order.shop_id.id,
                        'tableno': [(6, 0, table_ids)],
                        'product_nature': product_id.product_nature,
                        'pricelist_id': order.pricelist_id.id,
                    }

                    bot_flag = False
                if product_nature == 'bot' and order_line.states == True:
                    current_qty = int(order_line.item_qty) - \
                        order_line.previous_qty
                    if current_qty > 0:
                        bot_data = self.env['hotel.restaurant.kitchen.order.tickets'].create(
                            order_reservation_data_bot)
                        o_line = {
                            'product_id': order_line.product_id.id,
                            'name': order_line.product_id.name,
                            'item_qty': current_qty,
                            'item_rate': order_line.item_rate,
                            'kot_order_list': bot_data.id,
                            'product_nature': product_id.product_nature,
                        }
                        self.env['hotel.restaurant.order.list'].create(o_line)
                        self.env['hotel.restaurant.order.list'].write(
                            {'states': 'True', 'previous_qty': order_line.item_qty})

                if product_nature == 'bot' and order_line.states == False:
                    current_qty = int(order_line.item_qty) - \
                        order_line.previous_qty
                    if current_qty > 0:
                        bot_data = self.env['hotel.restaurant.kitchen.order.tickets'].create(
                            order_reservation_data_bot)
                        o_line = {
                            'product_id': order_line.product_id.id,
                            'name': order_line.product_id.id,
                            'item_qty': order_line.item_qty,
                            'item_rate': order_line.item_rate,
                            'kot_order_list': bot_data.id,
                            'product_nature': product_id.product_nature,
                        }
                        self.env['hotel.restaurant.order.list'].create(o_line)
                        self.env['hotel.restaurant.order.list'].write(
                            {'states': 'True', 'previous_qty': order_line.item_qty})

            stock_brw = self.env['stock.picking'].search(
                [('origin', '=', order.order_number)])
            if stock_brw:
                for order_items in order.order_list:
                    order_list = self.env['hotel.restaurant.order.list'].search([(
                        'product_id', '=', order_items.product_id.id),
                        ('kot_order_list.resno', '=', order.order_number)])
                    total_qty1 = 0
                    for order_qty in order_list:
                        p_qty1 = order_qty.item_qty
                        total_qty1 = total_qty1 + int(p_qty1)
                    product_id = self.env['hotel.menucard'].browse(
                        order_items.product_id.id).product_id.id
                    if product_id:
                        move_id = self.env['stock.move'].search(
                            [('product_id', '=', product_id), ('picking_id', '=', stock_brw.id)])
                        if move_id:
                            self.env['stock.move'].write(
                                {'product_uom_qty': total_qty1, })

        self.write({'state': 'order'})
        return True


class res_partner(models.Model):
    _inherit = 'res.partner'
    _description = 'Partner'

    agent = fields.Boolean('Agent')
    commission = fields.Float('Commission Percentage')
    login_password = fields.Char('Login Password')
    reservation_warn = fields.Selection([
        ('no-message', 'No Message'),
        ('warning', 'Warning'),
        ('block', 'Blocking Message')
    ], 'Hotel Reservation', default='no-message', required=True)
    reservation_msg = fields.Text('Message for Hotel Reservation')

    @api.model
    def create(self, vals):
        if ('agent' in vals) and (vals['agent']):
            if not ('commission' in vals):
                raise ValidationError("Commission Percentage is not define.")
            if ('commission' in vals) and not vals['commission']:
                raise ValidationError("Commission Percentage is not define.")
        return super(res_partner, self).create(vals)

    # def write(self, vals):
    #     """
    #     Overriding the write method
    #     """
    #     if ('agent' in vals) and (vals['agent']):
    #         if not ('commission' in vals):
    #             raise Warning("Commission Percentage is not define.")
    #     return super(res_partner, self).sudo().write(vals)


class hotel_restaurant_order_list(models.Model):
    _inherit = "hotel.restaurant.order.list"
    _description = "Inherits Hotel Restaurant Order"

    # @api.one
    def _sub_total(self):
        cur = False
        for line in self:
            price = line.item_rate
            taxes = line.tax_id.compute_all(
                price, None, int(line.item_qty), line.product_id.product_id, False)
            # print "Taxessssssssss", taxes
            if line.o_list:
                cur = line.o_list.pricelist_id.currency_id
                # print cur, "---o_list"
            if line.order_l:
                cur = line.order_l.pricelist_id.currency_id
                # print cur, "---order_l"
            if line.o_l:
                cur = line.o_l.pricelist_id.currency_id
                # print cur, "---o_l"
            if line.kot_order_list:
                cur = line.kot_order_list.pricelist_id.currency_id

                # print cur, "---kot_order_list"

            if cur:
                line.price_subtotal += cur.round(taxes['total_excluded'])
            else:
                line.price_subtotal += taxes['total_excluded']

    name = fields.Char('Sequence')
    product_id = fields.Many2one('hotel.menucard', 'Item Name', required=True)
    product_qty = fields.Integer('quantity')
    states = fields.Boolean('States', default=False)
    previous_qty = fields.Integer('quantities')
    total = fields.Integer('total')
    tax_id = fields.Many2many(
        'account.tax', 'restaurant_order_tax', 'order_line_id', 'tax_id', 'Taxes', )
    price_subtotal = fields.Float(
        compute="_sub_total", string='Subtotal')

    @api.depends('order_l.pricelist_id', 'order_l.start_date', 'o_l.pricelist_id', 'o_l.date1', 'o_list.pricelist_id',
                 'o_list.o_date', 'product_id', 'item_qty')
    @api.onchange('product_id')
    def on_change_item_name(self):
        # if not self.order_l.pricelist_id:
        # raise Warning("Heloooo PriceList is not Selected !")
        if not self.product_id:
            return {'value': {}}
        temp = self.product_id
        taxx_id = self.product_id.taxes_id
        tax_id = self.env['account.fiscal.position'].map_tax(
            self.product_id.taxes_id)
        price_value = 0

        if self.o_l:
            if not self.o_l.pricelist_id:
                raise ValidationError("Orders PriceList is not Selected!")
            if self.o_l.date1:
                ol_date = self.o_l.date1
            else:
                ol_date = time.strftime('%Y-%m-%d')
        elif self.o_list:
            if not self.o_list.pricelist_id:
                raise ValidationError(
                    "Table Order PriceList is not Selected !")
            if self.o_list.o_date:
                olist_date = self.o_list.o_date
            else:
                olist_date = time.strftime('%Y-%m-%d')
        elif self.order_l:
            if not self.order_l.pricelist_id:
                raise ValidationError(
                    "Table Booking PriceList is not Selected !")
            if self.order_l.start_date:
                orderl_date = self.order_l.start_date
            else:
                orderl_date = time.strftime('%Y-%m-%d')

        if self.item_qty:
            if self.o_l:
                price_value = self.o_l.pricelist_id.price_get(
                    temp.product_id.id, self.item_qty, {
                        'uom': temp.uom_id.id,
                        'date': ol_date,
                    })[self.o_l.pricelist_id.id]
            elif self.o_list:
                price_value = self.o_list.pricelist_id.price_get(
                    temp.product_id.id, self.item_qty, {
                        'uom': temp.uom_id.id,
                        'date': olist_date,
                    })[self.o_list.pricelist_id.id]

            elif self.order_l:
                price_value = self.order_l.pricelist_id.price_get(
                    temp.product_id.id, self.item_qty, {
                        'uom': temp.uom_id.id,
                        'date': orderl_date,
                    })[self.order_l.pricelist_id.id]
            # else:
        #                 if price_value is False:
        #                     raise Warning(
        #                 "Couldn't find a pricelist line matching this product!")
        else:
            if self.o_l:
                price_value = self.o_l.pricelist_id.price_get(
                    temp.product_id.id, self.item_qty, {
                        'uom': temp.uom_id.id,
                        'date': ol_date,
                    })[self.o_l.pricelist_id.id]
            elif self.o_list:
                price_value = self.o_list.pricelist_id.price_get(
                    temp.product_id.id, self.item_qty, {
                        'uom': temp.uom_id.id,
                        'date': olist_date,
                    })[self.o_list.pricelist_id.id]
            elif self.order_l:
                price_value = self.order_l.pricelist_id.price_get(
                    temp.product_id.id,
                    temp.uom_id.id,
                )[self.order_l.pricelist_id.id]

            # else:
            #     print("No price values found in else")

        # if price_value == 0:
        #     raise Warning("Couldn't find a pricelist line matching this product!")
        self.item_rate = price_value
        self.tax_id = tax_id


class product_template(models.Model):
    _inherit = "product.template"

    shop_id = fields.Many2one('sale.shop', string='Hotel',
                              help="Will show list of shop that belongs to allowed companies of logged-in user. \n -Assigning a shop will make product exclusive for selected shop.")
    product_nature = fields.Selection(
        [('kot', 'KOT'), ('bot', 'BOT')], 'Product Nature')

    @api.onchange('shop_id')
    def on_change_shop_id(self):
        if not self.shop_id:
            return {'value': {}}
        temp = self.shop_id
        self.company_id = temp.company_id.id

    @api.model
    def _construct_tax_string(self, price):

        user_id = self.env['res.users'].search(
            [('id', '=', self._context.get('uid'))])
        if self.currency_id:
            currency = self.currency_id
        elif user_id.currency_id:
            currency = user_id.company_id.currency_id

        res = self.taxes_id.compute_all(
            price, product=self, partner=self.env['res.partner'])
        joined = []
        included = res['total_included']
        if currency.compare_amounts(included, price):
            joined.append(_('%s Incl. Taxes', format_amount(
                self.env, included, currency)))
        excluded = res['total_excluded']
        if currency.compare_amounts(excluded, price):
            joined.append(_('%s Excl. Taxes', format_amount(
                self.env, excluded, currency)))
        if joined:
            tax_string = f"(= {', '.join(joined)})"
        else:
            tax_string = " "
        return tax_string


class hotel_restaurant_kitchen_order_tickets(models.Model):
    _inherit = "hotel.restaurant.kitchen.order.tickets"
    _description = "Includes Hotel Restaurant Order"

    @api.model
    def create(self, vals):
        product_nature = vals['product_nature']
        if product_nature != 'kot':
            vals['ordernobot'] = self.env['ir.sequence'].next_by_code(
                'hotel.reservation.botorder')
        return super(hotel_restaurant_kitchen_order_tickets, self).create(vals)

    ordernobot = fields.Char('BOT Number', readonly=True)
    product_nature = fields.Selection(
        [('kot', 'KOT'), ('bot', 'BOT')], 'Product Nature')
    shop_id = fields.Many2one('sale.shop', 'Hotel', required=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', )

    company_id = fields.Many2one(
        'res.company', related='shop_id.company_id', string='Company', store=True)


class hotel_menucard(models.Model):
    _inherit = "hotel.menucard"
    _description = "Hotel menucard Inherit "

    #     company_id = fields.Many2one('res.company', related='shop_id.company_id', string='Company', default=lambda *a: False)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda *a: False)

    product_nature = fields.Selection(
        [('kot', 'KOT'), ('bot', 'BOT')], 'Product Nature', default='kot')

    @api.onchange('shop_id')
    def on_change_shop_id(self):
        if not self.shop_id:
            return {'value': {}}
        temp = self.shop_id
        self.company_id = temp.company_id.id

    @api.onchange('shop_id')
    def on_change_shop_id(self):
        if self.shop_id:
            temp = self.shop_id
            self.company_id = temp.company_id.id
        else:
            self.company_id = False


class database_configuration(models.Model):
    _name = 'database.configuration'
    _description = 'Database Configuration'

    name = fields.Char('Database Name', required=True)
    company_name = fields.Char('Company Name', required=True)
    user_name = fields.Char('User Name', required=True)
    password = fields.Char('Password', required=True)


class hotel_resv_id_details(models.Model):
    _name = 'hotel.resv.id.details'
    _description = 'Clients ID details during reservation'

    name = fields.Char('ID Card Number')
    client_id = fields.Many2one("id.master", "Document Type")
    partner_name = fields.Char('Guest Name')
    issuing_auth = fields.Char('Issuing Authority')
    gender = fields.Selection(
        [('M', 'Male'), ('F', 'Female')], 'Gender')
    country_id = fields.Many2one("res.country", "Country")
    date_birth = fields.Date('Date of Birth')
    valid_from = fields.Date('Valid From')
    valid_to = fields.Date('Valid To')
    reservation_id = fields.Many2one('hotel.reservation', 'Reservation Id')
    folio_id = fields.Many2one('hotel.folio', 'Folio Id')


# class for dashboard URL
class dashboard_url(models.Model):
    _name = "dashboard.url"
    _description = 'dashboard url'

    url = fields.Char("Dashboard URL")

    @api.model
    def create(self, vals):
        ids = self.env['dashboard.url'].search(self._ids, [])
        if ids:
            # self.env['dashboard.url'].unlink(self._ids)
            ids.unlink()
        return super(dashboard_url, self).create(vals)


class account_invoice(models.Model):
    _name = "account.move"
    _inherit = "account.move"
    _description = 'Invoice'

    exchange_rate = fields.Float('Exchange Rate', digits=(12, 6), )
    create_date = fields.Datetime('Creation Date', )

    @api.onchange('currency_id')
    @api.depends('journal_id')
    def onchange_currency_id(self):
        # on change of the journal, we need to set also the default value for
        # payment_rate and payment_rate_currency_id
        res = {}
        if self._context is None:
            self._context = {}
        currency_obj = self.env['res.currency']
        if not self.journal_id:
            raise ValidationError('Journal is not selected.')
        journal = self.env['account.journal'].browse(self.journal_id.id)
        # company_id = journal.company_id.id
        exchange_rate = 1.0
        payment_rate_currency_id = self.currency_id
        company_currency_id = journal.company_id.currency_id.id
        ctx = self._context and self._context.copy() or {}
        ctx.update({'date': str(time.strftime('%Y-%m-%d'))})
        if payment_rate_currency_id and payment_rate_currency_id.id != company_currency_id:
            tmp = currency_obj.browse(payment_rate_currency_id).rate
            exchange_rate = tmp / currency_obj.browse(company_currency_id).rate
        res['exchange_rate'] = exchange_rate
        res['currency_id'] = payment_rate_currency_id.id
        return {'value': res}


class hotel_folio_transport_line(models.Model):
    _name = 'hotel_folio_transport.line'
    _description = 'hotel folio transport line'
    _inherits = {'sale.order.line': 'transport_line_id'}

    transport_line_id = fields.Many2one(
        'sale.order.line', 'food_line_id', required=True, ondelete='cascade')
    folio_id = fields.Many2one('hotel.folio', 'Folio ref', ondelete='cascade')
    source_origin = fields.Char('Source Origin')

    @api.onchange('product_id')
    def product_id_change(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id
            self.price_unit = self.product_id.lst_price
            self.name = self.product_id.description_sale


class hotel_folio_laundry_line(models.Model):
    _name = 'hotel_folio_laundry.line'
    _description = 'hotel folio laundry line'
    _inherits = {'sale.order.line': 'laundry_line_id'}

    laundry_line_id = fields.Many2one(
        'sale.order.line', 'laundry ref', required=True, ondelete='cascade')
    folio_id = fields.Many2one('hotel.folio', 'Folio ref', ondelete='cascade')
    source_origin = fields.Char('Source Origin')

    @api.onchange('product_id')
    def product_id_change(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id
            self.price_unit = self.product_id.lst_price
            self.name = self.product_id.description_sale

# class StockChangeStandardPrice(models.TransientModel):
#     _inherit = "stock.change.standard.price"
#     _description = "Change Standard Price"
#
#     def change_price(self):
#         print("innnnnnnnnnnnnnnnnnnnnnn133", self._context)
#         """ Changes the Standard Price of Product and creates an account move accordingly. """
#         self.ensure_one()
#         if self._context['active_model'] == 'product.template':
#             products = self.env['product.template'].browse(self._context['active_id']).product_variant_ids
#         elif self._context['active_model'] == 'product.product':
#             products = self.env['product.product'].browse(self._context['active_id'])
#
#         elif self._context['active_model'] == 'hotel.room':
#             print("kkkkkkkkkkkkkkkkkkkk133")
#             products = self.env['hotel.room'].browse(self._context['active_id']).product_variant_ids
#
#         elif self._context['active_model'] == 'hotel.menucard':
#             products = self.env['hotel.menucard'].browse(self._context['active_id']).product_variant_ids
#
#         elif self._context['active_model'] == 'hotel.services':
#             products = self.env['hotel.services'].browse(self._context['active_id']).product_variant_ids
#
#         else:
#             pass
#
#         products._change_standard_price(self.new_price, counterpart_account_id=self.counterpart_account_id.id)
#         return {'type': 'ir.actions.act_window_close'}
