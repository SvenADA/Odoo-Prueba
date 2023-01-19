from odoo import fields, models, api
from odoo.exceptions import ValidationError, Warning, UserError
from odoo.exceptions import UserError
from odoo.tools import config
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _
import datetime
import calendar
import time
# from mx.DateTime import RelativeDateTime, now, DateTime, localtime
from builtins import round
import logging

_logger = logging.getLogger(__name__)


class location_master(models.Model):
    _name = 'location.master'
    _description = 'Location details'

    name = fields.Char('Location Name', required=True)
    location_code = fields.Char('Location Code', required=True)


class transport_partner(models.Model):
    _name = 'transport.partner'
    _description = 'Transport details'

    # @api.multi
    def confirm_state(self):
        date1 = datetime.date
        date2 = date1.today()
        for transport in self:
            if transport.transport_info_ids == []:
                raise Warning(
                    "Warning! Please enter transport information details... !")
        return self.write({'state': 'confirm', 'date_of_authorization': date2})

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            obj = self.env['res.partner'].browse(self.partner_id).id
            self.name = obj.name

    name = fields.Char('Name')
    partner_id = fields.Many2one(
        'res.partner', 'Transporter Name', required=True)
    date_of_authorization = fields.Date(
        'Authorization Date', readonly=True)
    transport_info_ids = fields.One2many(
        'transport.information', 'tran_info_id', 'Transport Type Information')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed')],
                             'State', readonly=True, default='draft')


class transport_information(models.Model):
    _name = 'transport.information'
    _description = 'Transport Information'
    name = fields.Many2one(
        'transport.mode', 'Transport Mode', required=True)
    from_location = fields.Many2one('location.master', 'Source')
    to_location = fields.Many2one('location.master', 'Destination')
    cost_price = fields.Float('Cost Price')
    sale_price = fields.Float('Sale Price')
    tran_info_id = fields.Many2one(
        'transport.partner', 'Tranport Information ID')

    # _sql_constraints = [
    #     ('name_uniq', 'unique(name,from_location,to_location,tran_info_id)',
    #      'You have already created a record for same source and Destination.'),
    # ]


class transport_mode(models.Model):
    _name = 'transport.mode'
    _description = 'Transport Mode'

    name = fields.Char('Transport Mode', required=True)


class hotel_reservation(models.Model):
    _inherit = "hotel.reservation"
    _description = "Reservation"

    pick_up = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Is Pickup Required', readonly=True, states={
        'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, default=lambda *a: 'no')
    chargeable = fields.Boolean('Is Chargeable', readonly=True, states={
        'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    service_type = fields.Selection([('internal', 'Internal'), ('third_party', 'Third Party')], 'Service Type',
                                    readonly=True, states={
            'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, default=lambda *a: 'internal')
    trans_partner_id = fields.Many2one('transport.partner', 'Transporter Name', readonly=True, states={
        'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    pickup_time = fields.Datetime('Pickup Time', readonly=True, states={
        'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    source_id = fields.Many2one('location.master', 'Pickup Location', readonly=True, states={
        'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    destination_id = fields.Many2one('location.master', 'Destination', readonly=True, states={
        'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    trans_mode_id = fields.Many2one('transport.mode', 'Transport Mode', readonly=True, states={
        'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    trans_task_id = fields.Many2one('transport.task', 'Task ID')

    # @api.multi

    def cancel_reservation(self):
        for reservation in self:
            if reservation.pick_up == 'yes' and reservation.trans_task_id:
                reservation.trans_task_id.write({'state': 'cancelled'})
        so = super(hotel_reservation, self).cancel_reservation()
        return so

    # @api.multi

    def confirmed_reservation(self):
        so = super(hotel_reservation, self).confirmed_reservation()
        project_name = self.env['project.project'].search(
            [('name', '=', 'Tranportation')])
        for reservation in self:
            if reservation.pick_up == 'yes':
                task_id = self.env['transport.task'].create({
                    'trans_partner_id': reservation.trans_partner_id.id,
                    'pickup_time': reservation.pickup_time,
                    'source_id': reservation.source_id.id,
                    'destination_id': reservation.destination_id.id,
                    'trans_mode_id': reservation.trans_mode_id.id,
                    'guest_id': reservation.partner_id.id,
                    'reservation_id': reservation.id,
                    'service_type': reservation.service_type,
                    'name': 'Pickup and Drop for Customer',
                    'date_deadline': reservation.pickup_time or '',
                    'transport': 1,
                    'project_id': project_name.id or 1,
                    'is_chargeable': reservation.chargeable,
                    'is_pickup': True,
                })
                self.write({'trans_task_id': task_id.id})
        return True

    # @api.multi

    def update_history(self):
        so = super(hotel_reservation, self).update_history()
        for reservation in self:
            if reservation.pick_up == 'yes':
                trans_id = self.env['transport.task'].search(
                    [('reservation_id', '=', reservation.id)])
                if trans_id:
                    self.env['transport.task'].write({
                        'trans_partner_id': reservation.trans_partner_id.id,
                        'pickup_time': reservation.pickup_time,
                        'source_id': reservation.source_id.id,
                        'destination_id': reservation.destination_id.id,
                        'trans_mode_id': reservation.trans_mode_id.id,
                        'guest_id': reservation.partner_id.id,
                        'service_type': reservation.service_type,
                        'date_deadline': reservation.pickup_time[0:10] or '',
                        'transport': 1,
                        'project_id': 1,
                    })
                else:
                    task_id = self.env['transport.task'].create({
                        'trans_partner_id': reservation.trans_partner_id.id,
                        'pickup_time': reservation.pickup_time,
                        'source_id': reservation.source_id.id,
                        'destination_id': reservation.destination_id.id,
                        'trans_mode_id': reservation.trans_mode_id.id,
                        'guest_id': reservation.partner_id.id,
                        'reservation_id': reservation.id,
                        'service_type': reservation.service_type,
                        'name': 'Pickup and Drop for Customer',
                        'date_deadline': reservation.pickup_time[0:10] or '',
                        'transport': 1,
                        'project_id': 1,
                    })
                    self.write({'trans_task_id': task_id.id})
            if reservation.pick_up == 'no':
                trans_id = self.env['transport.task'].search(
                    [('reservation_id', '=', reservation.id)])
                if trans_id:
                    self.env['transport.task'].do_cancel(trans_id)
        return True


class TransportTask(models.Model):
    _name = 'transport.task'
    _inherits = {'project.task': 'task_id'}
    _description = 'Transport Task'

    def get_project_id(self):
        obj = self.env['project.project'].search(
            [('name', '=', 'Tranportation')])
        if not obj:
            raise Warning(
                "Warning! There is no project name as Tranportation !")
        return obj[0]

    # @api.onchange('user_id')
    # def _onchange_user(self):
    #     if self.user_id:
    #         self.date_start = fields.Datetime.now()

    task_id = fields.Many2one(
        'project.task', 'Task ID', required=True, ondelete="cascade")
    service_type = fields.Selection(
        [('internal', 'Internal'), ('third_party', 'Third Party')], 'Service Type', )
    trans_partner_id = fields.Many2one(
        'transport.partner', 'Transporter Name', )
    pickup_time = fields.Datetime('Pickup Time', )
    source_id = fields.Many2one('location.master', 'Pickup Location', )
    destination_id = fields.Many2one('location.master', 'Destination', )
    trans_mode_id = fields.Many2one('transport.mode', 'Transport Mode', )
    guest_id = fields.Many2one('res.partner', 'Guest Name', )
    reservation_id = fields.Many2one('hotel.reservation', 'Reservation Ref', )
    state = fields.Selection([('draft', 'New'), ('open', 'In Progress'), (
        'done', 'Done'), ('cancelled', 'Cancelled')], 'State', default='draft')
    project_id = fields.Many2one(
        'project.project', string='Project', ondelete='set null', default=get_project_id)
    date_start = fields.Datetime(string="Starting Date")
    is_chargeable = fields.Boolean(string="Is Chargeable")
    is_pickup = fields.Boolean(string="Is PickUp")

    def read_followers_data(self, follower_ids):
        result = []
        technical_group = self.env[
            'ir.model.data'].get_object('base', 'group_no_one')
        for follower in self.env['res.partner'].browse(follower_ids):
            is_editable = self._uid in [x.id for x in technical_group.users]
            is_uid = self._uid in [x.id for x in follower.user_ids]
            data = (follower.id,
                    follower.name,
                    {'is_editable': is_editable, 'is_uid': is_uid},
                    )
            result.append(data)
        return result

    def message_get_subscription_data(self, user_pid=None):
        """ Wrapper to get subtypes data. """
        return self.env['mail.thread']._get_subscription_data(None, None, user_pid=user_pid)

    def _read_group_user_id(self, domain, read_group_order=None, access_rights_uid=None, context=None):
        task_id = self.task_id
        res = task_id._read_group_user_id()
        return res

    def _hours_get(self, field_names):
        task_id = self.task_id
        res = task_id._hours_get()
        return res

    def onchange_remaining(self, remaining=0.0, planned=0.0):
        task_id = self.task_id
        res = task_id.onchange_remaining()
        return res

    @api.onchange('planned_hours')
    def onchange_planned(self, planned=0.0, effective=0.0):
        remaining_hours = planned - effective
        return {'value': remaining_hours}

    # @api.onchange('project_id')
    # def _onchange_project(self):
    #     task_id = self
    #     res = {}
    #     if not task_id:
    #         return res
    #     else:
    #         task_id = task_id[0].task_id
    #         if task_id:
    #             res = task_id._onchange_project()
    # return res

    def duplicate_task(self, map_ids):
        task_id = self.browse(map_ids)[0].task_id.id
        res = task_id.duplicate_task()
        return res

    def _is_template(self):
        task_id = self.task_id
        res = task_id._is_template()
        return res

    def _get_task(self):
        task_id = self.task_id
        res = task_id._get_task()
        return res

    def _check_child_task(self):
        task_id = self.task_id
        res = task_id._check_child_task()
        return res

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
            raise Warning(_('Warning !%s' % _(msg)))

        self._cr.execute(
            'SELECT i.* '
            'FROM product_pricelist_item AS i '
            'WHERE id = ' + str(plversion_ids[0].id) + '')

        res1 = self._cr.dictfetchall()
        if pricelist_obj:
            price = currency_obj.compute(
                price, pricelist_obj.currency_id, round=False)
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

    def action_close(self):
        task_id = self.task_id

        for obj in self:
            if obj.reservation_id:
                product_id = self.env['product.product'].search(
                    [('name', '=', 'Taxi')])
                if not product_id:
                    raise Warning(_("Warning! Product Taxi is not define."))
                product = product_id
                tax_ids = []
                for tax_line in product.taxes_id:
                    tax_ids.append(tax_line.id)
                if obj.reservation_id.state != 'done':
                    raise Warning(
                        _("Warning! Folio is not created for this reservation."))
                folio = self.env['hotel.folio'].search(
                    [('reservation_id', '=', obj.reservation_id.id)])
                folio_id = folio
                acc_id = obj.guest_id.property_account_receivable_id.id
                if not acc_id:
                    raise Warning(
                        _("Warning! Account Receivable is not defined for guest."))
                journal_obj = self.env['account.journal']
                journal_ids = journal_obj.search(
                    [('type', '=', 'sale')], limit=1)
                price_ids = self.env['transport.information'].search([('tran_info_id', '=', obj.trans_partner_id.id),
                                                                      ('from_location', '=',
                                                                       obj.source_id.id),
                                                                      ('to_location', '=',
                                                                       obj.destination_id.id),
                                                                      ('name', '=', obj.trans_mode_id.id)], limit=1)
                if not price_ids:
                    raise Warning(
                        _("Warning! Pricing is not defined for these location and transport mode."))
                price_id = price_ids
                sale_price = obj.get_price(
                    obj.reservation_id.pricelist_id.id, price_id.sale_price)

                if obj.service_type == 'internal' and obj.is_chargeable and obj.is_pickup:
                    so_line = {
                        'product_id': product.id,
                        'name': product.name,
                        'product_uom': product.uom_id.id,
                        'price_unit': sale_price,
                        'product_uom_qty': 1,
                        'tax_id': [(6, 0, tax_ids)],
                        'order_id': folio_id.order_id.id,
                    }
                    so_line_id = self.env['sale.order.line'].create(so_line)
                    service_line = {
                        'folio_id': folio_id.id,
                        'transport_line_id': so_line_id.id,
                        'source_origin': folio_id.reservation_id.name,
                    }
                    service_line_id = self.env['hotel_folio_transport.line'].create(
                        service_line)

                if obj.service_type != 'internal' and obj.is_chargeable and obj.is_pickup:
                    so_line = {
                        'product_id': product.id,
                        'name': product.name,
                        'product_uom': product.uom_id.id,
                        'price_unit': sale_price,
                        'product_uom_qty': 1,
                        'tax_id': [(6, 0, tax_ids)],
                        'order_id': folio_id.order_id.id,
                    }
                    so_line_id = self.env['sale.order.line'].create(so_line)
                    service_line = {
                        'folio_id': folio_id.id,
                        'transport_line_id': so_line_id.id
                    }
                    service_line_id = self.env['hotel_folio_transport.line'].create(
                        service_line)
                    cost_price = obj.get_price(
                        obj.trans_partner_id.partner_id.property_product_pricelist.id, price_id.cost_price)
                    if not obj.trans_partner_id.partner_id.property_account_payable_id:
                        raise Warning(
                            _("Warning! Accounting property is not define for Transport Supplier."))
                    pur_journal_ids = journal_obj.search(
                        [('type', '=', 'purchase')], limit=1)

                    _logger.info("Currency ID==>>>>{}".format(
                        obj.trans_partner_id.partner_id.property_product_pricelist.currency_id.id))
                    invoice_data1 = {
                        # 'name': obj.name,
                        'invoice_origin': obj.reservation_id.name + ' - ' + folio_id.order_id.name,
                        'move_type': 'in_invoice',
                        'ref': obj.name + '-' + obj.reservation_id.name,
                        # 'account_id': obj.trans_partner_id.partner_id.property_account_payable_id.id,
                        'partner_id': obj.trans_partner_id.partner_id.id,
                        'currency_id': obj.trans_partner_id.partner_id.property_product_pricelist.currency_id.id,
                        'journal_id': len(pur_journal_ids) and pur_journal_ids[0].id or False,
                    }
                    _logger.info("Invoice Data===>>>{}".format(invoice_data1))
                    invoice_data_id1 = self.env['account.move'].new(
                        invoice_data1)
                    invoice_data_id1._onchange_journal()
                    invoice_data_id1._onchange_currency()
                    invoice_data_id1._onchange_partner_id()
                    product_exp_acc_id = product.property_account_expense_id
                    if not product.property_account_expense_id:
                        product_exp_acc_id = product.categ_id.property_account_expense_categ_id
                        if not product.categ_id.property_account_expense_categ_id.id:
                            raise Warning(
                                _("Warning! Accounting property is not define for Taxi."))
                    tax_ids = []
                    for tax_line in product.taxes_id:
                        tax_ids.append(tax_line.id)

                    invoice_line = {
                        'name': product.name,
                        'product_id': product.id,
                        'account_id': product_exp_acc_id.id,
                        'price_unit': cost_price,
                        'quantity': 1,
                        'product_uom_id': product.uom_id.id,
                        'currency_id': obj.trans_partner_id.partner_id.property_product_pricelist.currency_id.id,
                        # 'uos_id': product.uom_id.id,
                        # 'origin': product.name,
                        'move_id': invoice_data_id1,
                        'tax_ids': [(6, 0, tax_ids)],
                    }
                    _logger.info("Invoice Line===>>>{}".format(invoice_line))
                    # self.env['account.move.line'].create(invoice_line)
                    product_context = dict(self.env.context, partner_id=obj.trans_partner_id.partner_id.id,
                                           date=time.strftime(
                                               '%Y-%m-%d'), uom=product.uom_id.id)
                    _logger.info('product_context========>>>>>{} '.format(product_context))
                    invoice_line_id = self.env['account.move.line'].new(invoice_line)
                    invoice_line_id._onchange_product_id()
                    invoice_line_id.price_unit = cost_price
                    invoice_line_id._onchange_mark_recompute_taxes()
                    invoice_line_id._onchange_price_subtotal()
                    invoice_line_id._get_fields_onchange_balance()

                    invoice_data_id1._onchange_invoice_line_ids()
                    account_move_vals = invoice_data_id1._convert_to_write(
                        {name: invoice_data_id1[name] for name in invoice_data_id1._cache})
                    account_move_rec = self.env['account.move'].create(account_move_vals)

                if obj.service_type != 'internal' and (not obj.is_chargeable) and obj.is_pickup:
                    cost_price = obj.get_price(
                        obj.trans_partner_id.partner_id.property_product_pricelist.id, price_id.cost_price)
                    if not obj.trans_partner_id.partner_id.property_account_payable_id:
                        raise Warning(
                            _("Warning! Accounting property is not define for Transport Supplier."))
                    pur_journal_ids = journal_obj.search(
                        [('type', '=', 'purchase')], limit=1)
                    invoice_data1 = {
                        # 'name': obj.name,
                        'invoice_origin': obj.reservation_id.name + ' - ' + folio_id.order_id.name,
                        'move_type': 'in_invoice',
                        'ref': obj.name + '-' + obj.reservation_id.name,
                        # 'account_id': obj.trans_partner_id.partner_id.property_account_payable_id.id,
                        'partner_id': obj.trans_partner_id.partner_id.id,
                        'currency_id': obj.trans_partner_id.partner_id.property_product_pricelist.currency_id.id,
                        'journal_id': len(pur_journal_ids) and pur_journal_ids[0] or False,
                    }
                    invoice_data_id1 = self.env['account.move'].new(
                        invoice_data1)
                    invoice_data_id1._onchange_journal()
                    invoice_data_id1._onchange_currency()
                    invoice_data_id1._onchange_partner_id()
                    product_exp_acc_id = product.property_account_expense_id

                    if not product.property_account_expense_id:
                        product_exp_acc_id = product.categ_id.property_account_expense_categ_id
                        if not product.categ_id.property_account_expense_categ_id.id:
                            raise Warning(
                                _("Warning! Accounting property is not define for Taxi."))
                    tax_ids = []
                    for tax_line in product.taxes_id:
                        tax_ids.append(tax_line.id)
                    invoice_line = {
                        'name': product.name,
                        'product_id': product.id,
                        'account_id': product_exp_acc_id.id,
                        'price_unit': cost_price,
                        'quantity': 1,
                        'product_uom_id': product.uom_id.id,
                        # 'uos_id': product.uom_id.id,
                        # 'origin': product.name,
                        'move_id': invoice_data_id1,
                        'tax_ids': [(6, 0, tax_ids)],
                    }
                    product_context = dict(self.env.context, partner_id=obj.trans_partner_id.partner_id.id,
                                           date=time.strftime(
                                               '%Y-%m-%d'), uom=product.uom_id.id)
                    _logger.info('product_context========>>>>>{} '.format(product_context))
                    invoice_line_id = self.env['account.move.line'].new(invoice_line)
                    invoice_line_id._onchange_product_id()
                    invoice_line_id.price_unit = cost_price
                    invoice_line_id._onchange_mark_recompute_taxes()
                    invoice_line_id._onchange_price_subtotal()
                    invoice_line_id._get_fields_onchange_balance()

                    invoice_data_id1._onchange_invoice_line_ids()
                    account_move_vals = invoice_data_id1._convert_to_write(
                        {name: invoice_data_id1[name] for name in invoice_data_id1._cache})
                    account_move_rec = self.env['account.move'].create(account_move_vals)

                    # self.env['account.move.line'].create(invoice_line)
            else:
                raise Warning(
                    _("Warning! Reservation Ref is missing  for this task"))
        self.write({'state': 'done'})
        return True

    def do_open(self):
        """ Compatibility when changing to case_open. """
        return self.case_open()

    def case_open(self):
        if not isinstance(self._ids, list):
            ids = [self._ids]
        return self.write({'state': 'open', 'date_start': fields.datetime.now()})

    def do_cancel(self):
        """ Compatibility when changing to case_cancel. """
        return self.case_cancel()

    def case_cancel(self):
        tasks = self
        for task in tasks:
            self.write({
                'state': 'cancelled', 'remaining_hours': 0.0})
        return True

    def do_close(self):
        """ This action closes the task
        """
        task_id = len(self._ids) and self._ids[0] or False
        self.check_child_task()
        if not task_id:
            return False
        return self.case_close()

    def case_close(self):
        """ Closes Task """
        if not isinstance(self._ids, list):
            ids = [self._ids]
        for task in self:
            vals = {}
            for parent_id in task.parent_ids:
                if parent_id.state in ('pending', 'draft'):
                    reopen = True
                    for child in parent_id.child_ids:
                        if child.id != task.id and child.state not in ('done', 'cancelled'):
                            reopen = False
                    if reopen:
                        self.do_reopen(parent_id.id)
            # close task
            vals['remaining_hours'] = 0.0
            vals['state'] = 'done'
            if not task.date_end:
                vals['date_end'] = fields.datetime.now()
            self.write([task.id], vals)
        return True

    def do_reopen(self):
        for task in self:
            self.write({'state': 'done'})
        return True

    def do_delegate(self):
        task_id = self.task_id
        res = task_id.do_delegate()
        return res

    def set_remaining_time(self, remaining_time=1.0):
        task_id = self.task_id
        res = task_id.set_remaining_time()
        return res

    def _store_history(self):
        task_id = self.task_id
        res = task_id._store_history()
        return res

    def _message_get_suggested_recipients(self):
        task_id = self.task_id
        res = task_id._message_get_suggested_recipients()
        return res


class Task(models.Model):
    _inherit = "project.task"
    _description = "Task"

    transport = fields.Boolean('Transport Task', default=lambda *a: 0)
