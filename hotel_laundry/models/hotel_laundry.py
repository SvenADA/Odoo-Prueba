# -*- encoding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError, Warning
import datetime
from datetime import timedelta
from datetime import date
import time
from odoo.tools.translate import _


class hotel_laundry(models.Model):
    """Hotel laundry is show in configuration and it will create supplier with service and items prices"""
    _name = 'hotel.laundry'
    _description = 'Hotel Laundry'
    _rec_name = 'partner_id'

    #     @api.onchange('partner_id')
    #     @api.depends('partner_id')
    #     def onchange_partner(self):
    #         if self.partner_id:
    #             self.name = self.partner_id.name

    def confirm(self):
        for service in self:
            if service.laundry_service_ids == []:
                raise Warning(
                    'Warning!', "There is no services regarding to supplier ... !")
            else:
                for record in service.laundry_service_ids:
                    record.write({'supplier_id': service.partner_id.id})
        self.write({'state': 'confirmed'})
        return True

    def cancel_supplier(self):
        self.write({'state': 'draft'})
        return True

    def update_record(self):
        self.write({'state': 'edit'})
        return True

    #     name = fields.Char('Name')
    partner_id = fields.Many2one('res.partner', 'Supplier Name', required=True, states={
        'confirmed': [('readonly', True)], 'edit': [('readonly', True)]}, index=True)
    laundry_service_ids = fields.One2many(
        'hotel.laundry.services', 'hotel_laundry_service_id', 'Laundry Services',
        states={'confirmed': [('readonly', True)]})
    state = fields.Selection([('draft', 'Draft'), ('edit', 'Edit'), ('confirmed', 'Confirmed'), (
        'canceled', 'Cancel')], 'State', default='draft', required=True, readonly=True)


class hotel_laundry_service(models.Model):
    """This class is used to create all the services which will be provide by the hotel management"""
    _name = 'hotel.laundry.services'
    _description = 'Laundry services in hotel'

    @api.depends('service_id')
    # @api.onchange('service_id')
    def onchange_services_id(self):
        res1 = {}
        if self.service_id:
            service_ids = self.env['product.product'].browse(self.service_id)
            self.name = service_ids.name

    def get_category_id(self):
        obj = self.env['product.category'].search(
            [('name', '=', 'Laundry Services')], limit=1)
        return obj

    name = fields.Char(related='laundry_services_id.name')
    hotel_laundry_service_id = fields.Many2one('hotel.laundry')
    supplier_id = fields.Integer('Supplier Id')
    laundry_services_id = fields.Many2one('product.product', 'Service Name', required=True)
    laundry_services_items_ids = fields.One2many('hotel.laundry.services.items', 'laundry_items_id',
                                                 'laundry service items')
    category_id = fields.Integer('Category', default=get_category_id)

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        # print("valssssssssssssssssssss", vals)
        if 'hotel_laundry_service_id' not in vals:
            if vals['supplier_id']:
                # print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                obj = self.env['hotel.laundry'].search(
                    [('partner_id', '=', vals['supplier_id'])])
                vals['hotel_laundry_service_id'] = obj
        # print("vals===================================================", vals)
        return super(hotel_laundry_service, self).create(vals)

    @api.onchange('laundry_services_id')
    @api.depends('laundry_services_id')
    def onchange_laundry_services_id(self):
        res1 = {}
        if self.laundry_services_id:
            # print("self.laundry_services_idddddddddddddddd", self.laundry_services_id.name)
            self.name = self.laundry_services_id.name


class hotel_laundry_service_items(models.Model):
    """This class is used to create all the items which are related to hotel services"""
    _name = 'hotel.laundry.services.items'
    _description = 'Laundry services Items Details'

    @api.onchange('item_id')
    @api.depends('item_id')
    def onchange_item_id(self):
        if self.item_id:
            item_ids = self.env['product.product'].browse(self.item_id.id)
            self.name = item_ids.name
            self.cost_price = item_ids.standard_price
            self.sale_price = item_ids.lst_price

    def get_category_id(self):
        obj = self.env['product.category'].search([('name', '=', 'Clothes')])
        # print(">>>>>>>>..category id ", obj[0])
        return obj[0]

    name = fields.Char('Name')
    laundry_items_id = fields.Many2one('hotel.laundry.services')
    item_id = fields.Many2one(
        'product.product', 'Items', required=True)
    cost_price = fields.Float('Cost Price')
    sale_price = fields.Float('Sale Price')
    category_id1 = fields.Integer('Category', default=get_category_id)


class laundry_management(models.Model):
    """This class is use to show all task related laundry management like washing, cleaning, iron and so on"""
    _name = 'laundry.management'
    _description = 'Laundry Management'

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        # print("valssssssssssssssss", vals)
        vals['name'] = self.env['ir.sequence'].get('laundry.management')
        if vals.get('request_type') == 'internal':
            pass
        elif "room_number" in vals:
            # print("i am in else=======================================")
            room_no = vals.get('room_number')
            today = vals.get('date_order')
            # print("today::::::::::",type(today))
            today = datetime.datetime.strptime(str(today), '%Y-%m-%d %H:%M:%S')
            # print("today::::::::::::::::::::",today)
            history_obj = self.env["hotel.room.booking.history"]
            # print("history_obj=========================================")
            if not room_no:
                # print("room_no================================================ ", room_no)
                return super(laundry_management, self).create(vals)
            obj = self.env['hotel.room'].browse(room_no)
            for folio_hsry_id in history_obj.search([('name', '=', obj.product_id.name)]):
                # hstry_line_id = history_obj.browse(folio_hsry_id)
                start_dt = folio_hsry_id.check_in
                end_dt = folio_hsry_id.check_out

                if (start_dt <= today) and (end_dt >= today):
                    vals['partner_id'] = folio_hsry_id.partner_id.id
        return super(laundry_management, self).create(vals)

    def write(self, vals):
        if vals.get('request_type') == 'internal':
            pass
        elif "room_number" in vals:
            room_no = vals.get('room_number')
            today = vals.get('date_order')
            if not today:
                for self_obj in self:
                    today = self_obj.date_order
            history_obj = self.env["hotel.room.booking.history"]
            if not room_no:
                return {'value': {'partner_id': False}}
            obj = self.env["hotel.room"].browse(room_no)
            for folio_hsry_id in history_obj.search([('name', '=', obj.product_id.name)]):
                # hstry_line_id = history_obj.browse(cr, uid, folio_hsry_id)
                start_dt = folio_hsry_id.check_in
                end_dt = folio_hsry_id.check_out
                if (start_dt <= today) and (end_dt >= today):
                    vals['partner_id'] = folio_hsry_id.partner_id.id

        return super(laundry_management, self).write(vals)

    @api.onchange('pricelist_id')
    @api.depends('laundry_service_product_ids')
    def onchange_pricelist_id(self):
        if not self.pricelist_id:
            return {}
        if not self.laundry_service_product_ids or self.laundry_service_product_ids == [(6, 0, [])]:
            return {}
        if len(self.laundry_service_product_ids) != 1:
            warning = {
                'title': _('Pricelist Warning!'),
                'message': _(
                    'If you change the pricelist of this order (and eventually the currency), prices of existing order lines will not be updated.')
            }
            return {'warning': warning}

    @api.onchange('shop_id')
    @api.depends('shop_id')
    def on_change_shop_id(self):
        v = {}
        if self.shop_id:
            shop = self.env['sale.shop'].browse(self.shop_id.id)
            if shop.pricelist_id:
                self.pricelist_id = shop.pricelist_id.id
                self.company_id = shop.company_id.id

    @api.onchange('supplier_id')
    @api.depends('supplier_id')
    def onchange_partner_id(self):
        res1 = {}
        if self.supplier_id:
            p_ids = self.env['hotel.laundry'].browse(self.supplier_id)
            for p_id in p_ids:
                self.supplier_id_temp = p_id.id

    def get_folio_id(self, date_order, room_number, partner_id):
        id_val = 0
        today = date_order
        booking_id = 0
        history_obj = self.env["hotel.room.booking.history"]
        folio_obj = self.env["hotel.folio"]
        for folio_hsry_id in history_obj.search([('history_id', '=', room_number), ('state', '=', 'done')]):
            start_dt = folio_hsry_id.check_in
            end_dt = folio_hsry_id.check_out
            if (start_dt <= today) and (end_dt >= today):
                booking_id = folio_hsry_id.booking_id.id
                folio_obj_id = folio_obj.search(
                    [('reservation_id', '=', booking_id)])
                if folio_obj_id:
                    # print("fffffffffff",folio_obj_id.order_id)
                    # folio_id = folio_obj.browse(folio_obj_id)[0]
                    id_val = folio_obj_id.order_id.id
        return id_val

    def confirm(self):
        journal_obj = self.env['account.journal']
        so_line = None
        for service in self:
            if service.laundry_service_product_ids == []:
                raise Warning(
                    "Warning! There is no services regarding to supplier ... !")
            if not service.shop_id:
                raise Warning("Warning! Shop is not selected!")
            if service.request_type == 'from_room':
                # >>>>>>>>>>>>>>>#Calculation for getting folio id/ sale order i
                sale_id = self.get_folio_id(
                    service.date_order, service.room_number.id, service.partner_id.id)
                folio_id = self.env["hotel.folio"].search(
                    [('order_id', '=', sale_id)])
                if not folio_id:
                    raise UserError(
                        _("Warning! Folio is not created for this room Order."))

                # >>>>>>>>>>>>>>>#**********************************************
                #### The working on creation of customer invoice#####
                partner_id = service.partner_id.id
                # print(">>>>>>>>>>>>>>>>>>>>>>", partner_id)
                if service.is_chargable:
                    account = self.env[
                        'res.partner'].browse(partner_id)
                    account_id = account.property_account_receivable_id.id
                    journal_ids = journal_obj.search(
                        [('type', '=', 'sale')], limit=1)
                    pricelist_obj = self.env['product.pricelist'].browse(
                        service.pricelist_id.id)
                    cur_id = pricelist_obj.currency_id.id

                    for service_line in service.laundry_service_product_ids:
                        # print("service Lineeeeeeeeeeeeeeee", service_line)
                        for service_line_item in service_line.laundry_service_product_line_ids:
                            # print("000000000000000000000000000000")
                            tax_ids = []
                            for tax_line in service_line.tax_id:
                                tax_ids.append(tax_line.id)
                            sup_id = self.env['hotel.laundry.services'].browse(
                                service_line.laundry_services_id.id)
                            laundry_service_id = sup_id.laundry_services_id.id
                            laundry_service_name = sup_id.laundry_services_id.name
                            so_line = {
                                #                                'product_id':service_line.laundry_services_id.id,
                                #                                'name':service_line.laundry_services_id.name,
                                'name': laundry_service_name,
                                'product_id': laundry_service_id,
                                'product_uom': service_line_item.qty_uom.id,
                                'price_unit': service_line.sales_rate,
                                # 'price_unit':service_line.sale_subtotal,
                                'product_uom_qty': 1,
                                'order_id': folio_id.order_id.id,
                                'tax_id': [(6, 0, tax_ids)],
                            }
                        # print("fffffffffffffff",so_line)
                        if so_line:
                            so_line_id = self.env[
                                'sale.order.line'].create(so_line)
                            service_line = {
                                'folio_id': folio_id.id,
                                'laundry_line_id': so_line_id.id,
                                'source_origin': service.name,
                            }
                            service_line_id = self.env[
                                'hotel_folio_laundry.line'].create(service_line)

        self.write({'state': 'confirmed'})
        return True

    def cancel_service(self):
        self.write({'state': 'canceled'})
        return True

    def send_to_laundry(self):
        journal_obj = self.env['account.journal']
        for service in self:
            sale_id = self.get_folio_id(
                service.date_order, service.room_number.id, service.partner_id.id)
            if (service.request_type == 'from_room' and service.service_type == 'third_party') or (
                    service.request_type == 'internal' and service.service_type == 'third_party' and service.is_chargable):
                supplier_id = service.supplier_id.id
                sup_id = self.env['hotel.laundry'].browse(supplier_id)
                sup_pid = sup_id.partner_id.id

                part_obj = self.env[
                    'res.partner'].browse(sup_pid)
                account_id = part_obj.property_account_payable_id.id
                sup_pricelist = part_obj.property_product_pricelist.id
                pur_journal_ids = journal_obj.search(
                    [('type', '=', 'purchase')], limit=1)
                pricelist_obj = self.env[
                    'product.pricelist'].browse(sup_pricelist)
                cur_id = pricelist_obj.currency_id.id

                invoice_data = {
                    # 'name': service.name,
                    'invoice_origin': service.name,
                    'ref': service.name,
                    'move_type': 'in_invoice',
                    'currency_id': cur_id,
                    'partner_id': sup_pid,
                    #                        'address_invoice_id':supplier_add,
                    #         'account_id': account_id,
                    'journal_id': len(pur_journal_ids) and pur_journal_ids[0].id or False,
                }
                # print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> invoice_data", invoice_data)
                invoice_id = self.env['account.move'].create(invoice_data)

                # print("fffffffffff",invoice_id,service)
                # print("fffffffffff",service.laundry_service_product_ids)

                for service_lines in service.laundry_service_product_ids:
                    # print("44444444444444444")
                    for service_line_item in service_lines.laundry_service_product_line_ids:
                        # print("555555555555555555",service_lines.tax_id)
                        tax_ids = []
                        for tax_line in service_lines.tax_id:
                            # print("kkkkkkkkkkkkkkkkkkkkkkkkk")
                            tax_ids.append(tax_line.id)
                        sup_id = self.env['hotel.laundry.services'].browse(
                            service_lines.laundry_services_id.id)
                        laundry_service_id = sup_id.laundry_services_id.id
                        laundry_service_name = sup_id.laundry_services_id.name
                        cost_subtotal = 0.00

                        # for service in service_lines.laundry_service_product_line_ids:
                        #     print('_______________', service.qty, service.item_id_ref.cost_price,)
                        #     cost_subtotal += service.item_id_ref.cost_price * \
                        #         service.qty

                        line_account_id = service_line_item.item_id.property_account_expense_id.id
                        if not line_account_id:
                            line_account_id = service_line_item.item_id.categ_id.property_account_expense_categ_id.id
                        if not line_account_id:
                            raise Warning(_('Error !'),
                                          _('There is no Expense account defined '
                                            'for this product: "%s" (id:%d)') %
                                          (service_line_item.item_id.name, service_line_item.item_id.id,))


                        invoice_id.write({
                            'invoice_line_ids': [(0, 0, {
                                'name': '{}-{}'.format(laundry_service_name, service_line_item.item_id_ref.name),
                                'account_id': line_account_id,
                                'price_unit': service_line_item.item_id_ref.cost_price,
                                'quantity': service_line_item.qty,
                                'product_id': laundry_service_id,
                                'tax_ids': [(6, 0, tax_ids)],
                            })]
                        })
                    # print("invoice_id::::::::::::::::",invoice_id)
                    # print("invoice_id::::::::::::::::",invoice_id.invoice_line_ids)
                    # print(">>>>>>>>>>>>>>>>>>>>>>>>>invoice_line_data", invoice_line_data)
                    # self.env['account.move.line'].create(invoice_line_data)

                    # print("This is internal request type so no need to create picking or return")

        self.write({'state': 'sent_to_laundry'})
        return True

    def customer_return(self):
        self.write({'state': 'customer_returned'})
        return True

    def done_from_room(self):
        self.write({'state': 'done'})
        return True

    def done_internal(self):
        self.write({'state': 'done'})
        return True

    def laundry_returned(self):
        self.write({'state': 'laundry_returned'})
        return True

    @api.onchange('room_number')
    @api.depends('date_order')
    def onchange_room_no(self):
        # res = {}
        today = self.date_order
        history_obj = self.env["hotel.room.booking.history"]
        # if not self.room_number:
        #
        self.partner_id = False
        for folio_hsry_id in history_obj.search([('history_id', '=', self.room_number.id), ('state', '=', 'done')]):
            hstry_line_id = history_obj.browse(folio_hsry_id).id
            start_dt = hstry_line_id.check_in
            end_dt = hstry_line_id.check_out
            if (start_dt <= today) and (end_dt >= today):
                # res['partner_id'] = hstry_line_id.partner_id.id
                self.partner_id = hstry_line_id.partner_id.id

    @api.onchange('date_order', 'request_type')
    @api.depends('date_order', 'request_type')
    def get_rooms(self):
        # res = []
        # val = {}
        # today = (self.date_order).date()
        # if self.request_type == 'from_room':
        #     main_obj_ids = self.env['hotel.room.booking.history'].search([
        #         ('check_in_date', '<=', today), ('check_out_date', '>=', today), ('state', '=', 'done')])
        #
        #     for obj in main_obj_ids:
        #         # print(obj, "main_obj1:::::::::::::::::::::::::::")
        #         for dest_line in obj:
        #             res.append(dest_line.history_id.id)

        # New Logic
        new_ids = []

        room_lines = self.env['hotel.folio'].search([('state', '=', 'draft')]).mapped('room_lines')
        for rec in room_lines:
            if rec.product_id:
                room_id = self.env['hotel.room'].search([('product_id', '=', rec.product_id.id)])
                if room_id:
                    new_ids.append(room_id.id)
        return {
            'domain': {
                'room_number': [('id', 'in', new_ids)],
            }}

    @api.model
    def _get_default_shop(self):
        user = self.env['res.users'].browse(self._uid)
        company_id = user.company_id.id
        shop_ids = self.env['sale.shop'].search(
            [('company_id', '=', company_id)])
        if not shop_ids:
            raise Warning(
                _('Error!'), _('There is no default shop for the current user\'s company!'))
        return shop_ids[0]

    def _amount_line_tax(self, line):
        val = 0.0
        taxes = line.tax_id.compute_all(
            line.sales_rate, None, 1, line.laundry_services_id.laundry_services_id)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    def _sub_total(self):
        val = 0.00
        for line in self.laundry_service_product_ids:
            val += line.sale_subtotal
        self.amount_subtotal = self.pricelist_id.currency_id.round(val)

    def _amount_tax(self):
        val = 0.00
        for sale in self:
            for line in sale.laundry_service_product_ids:
                val += self._amount_line_tax(line)
            self.amount_tax = self.pricelist_id.currency_id.round(val)

    def _total(self):
        val = val1 = 0.0
        for line in self.laundry_service_product_ids:
            val1 += line.sale_subtotal
            # print("SubTotal -------", val1)
            val += self._amount_line_tax(line)
            # print("Tax ------", val)
        self.amount_tax = self.pricelist_id.currency_id.round(val)
        # print("amount Tax  ------ ", self.amount_tax)
        amount_untaxed = self.pricelist_id.currency_id.round(val1)
        # print("subtotal  ------ ", amount_untaxed)
        self.amount_total = amount_untaxed + self.amount_tax

    name = fields.Char('Order Reference', readonly=True)
    user_id = fields.Many2one('res.users', 'Responsible',
                              states={'confirmed': [('readonly', True)], 'laundry_returned': [
                                  ('readonly', True)], 'sent_to_laundry': [('readonly', True)],
                                      'customer_returned': [('readonly', True)], 'done': [('readonly', True)]},
                              default=lambda self: self._uid)
    date_order = fields.Datetime('Request Date', required=True,
                                 states={'confirmed': [('readonly', True)], 'laundry_returned': [('readonly', True)],
                                         'sent_to_laundry': [
                                             ('readonly', True)], 'customer_returned': [('readonly', True)],
                                         'done': [('readonly', True)]}, index=True,
                                 default=lambda self: datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    deadline_date = fields.Datetime('Request Deadline',
                                    states={'confirmed': [('readonly', True)], 'laundry_returned': [(
                                        'readonly', True)], 'sent_to_laundry': [('readonly', True)],
                                            'customer_returned': [('readonly', True)], 'done': [('readonly', True)]})
    shop_id = fields.Many2one('sale.shop', 'Hotel Name',
                              states={'confirmed': [('readonly', True)], 'laundry_returned': [('readonly', True)],
                                      'sent_to_laundry': [('readonly', True)], 'customer_returned': [
                                      ('readonly', True)], 'done': [('readonly', True)]}, index=True,
                              help="Will show list of shop that belongs to allowed companies of logged-in user.",
                              default=_get_default_shop)
    #        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', states={'confirmed':[('readonly',True)], 'laundry_returned':[('readonly',True)],'sent_to_laundry':[('readonly',True)],'customer_returned':[('readonly',True)],'done':[('readonly',True)]}, select=True),
    company_id = fields.Many2one('res.company', 'Company',
                                 states={'confirmed': [('readonly', True)], 'laundry_returned': [('readonly', True)],
                                         'sent_to_laundry': [
                                             ('readonly', True)], 'customer_returned': [('readonly', True)],
                                         'done': [('readonly', True)]}, required=True, index=True,
                                 default=lambda self: self.env['res.company']._company_default_get('purchase.order'))
    request_type = fields.Selection([('internal', 'Internal'), ('from_room', 'From Room')], 'Request Type',
                                    states={'confirmed': [('readonly', True)], 'laundry_returned': [
                                        ('readonly', True)], 'sent_to_laundry': [('readonly', True)],
                                            'customer_returned': [('readonly', True)], 'done': [('readonly', True)]},
                                    required=True, )
    room_number = fields.Many2one('hotel.room', 'Room No',
                                  states={'confirmed': [('readonly', True)], 'laundry_returned': [('readonly', True)],
                                          'sent_to_laundry': [(
                                              'readonly', True)], 'customer_returned': [('readonly', True)],
                                          'done': [('readonly', True)]},
                                  help="Will show list of currently occupied room no that belongs to selected shop.")
    partner_id = fields.Many2one('res.partner', 'Guest Name',
                                 states={'confirmed': [('readonly', True)], 'laundry_returned': [
                                     ('readonly', True)], 'sent_to_laundry': [('readonly', True)],
                                         'customer_returned': [('readonly', True)], 'done': [('readonly', True)]})
    supplier_id = fields.Many2one('hotel.laundry', 'Supplier',
                                  states={'confirmed': [('readonly', True)], 'laundry_returned': [
                                      ('readonly', True)], 'sent_to_laundry': [('readonly', True)],
                                          'customer_returned': [('readonly', True)], 'done': [('readonly', True)]})
    #        'supplier_address_id':fields.many2one('res.partner.address','Address',states={'confirmed':[('readonly',True)], 'laundry_returned':[('readonly',True)],'sent_to_laundry':[('readonly',True)],'customer_returned':[('readonly',True)],'done':[('readonly',True)]}),
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('canceled', 'Canceled'),
                              ('sent_to_laundry', 'Sent to Laundry'), (
                                  'laundry_returned', 'Laundry Returned'), ('customer_returned', 'Customer Returned'),
                              ('done', 'Done')], 'State', readonly=True, default='draft')
    laundry_service_product_ids = fields.One2many('laundry.service.product', 'laundry_service_id',
                                                  'Laundry Service Product', states={'confirmed': [(
            'readonly', True)], 'laundry_returned': [('readonly', True)], 'sent_to_laundry': [('readonly', True)],
            'customer_returned': [('readonly', True)], 'done': [('readonly', True)]})
    supplier_id_temp = fields.Integer('Supplier Temp Id')
    pricelist_id = fields.Many2one(
        'product.pricelist', 'Pricelist', required=True, readonly=True, states={'draft': [('readonly', False)]})
    invoice_ids = fields.Many2many(
        'stock.picking', 'laundry_order_picking_rel', 'laundry_order_id', 'picking_id', 'Invoice Lines', readonly=True)
    #        'room_number_selection':fields.selection(get_room_numbers, 'room number'),
    service_type = fields.Selection(
        [('internal', 'Internal'), ('third_party', 'Third Party')], 'Service Type', required=True, )
    is_chargable = fields.Boolean('Is Chargable')
    amount_subtotal = fields.Float(
        compute='_sub_total', string='Subtotal')
    amount_tax = fields.Float(compute='_amount_tax', string='Tax')
    amount_total = fields.Float(compute='_total', string='Total')


class laundry_service_product(models.Model):
    """This class is used to show all the services according to supplier means all services of the supplier will be show here"""
    _name = 'laundry.service.product'
    _description = 'Laundry Service Product'

    def get_cost_subtotal_value(self):
        if self._context is None:
            self._context = {}
        cost_subtotal = 0.00
        for line in self:
            for records1 in line.laundry_service_product_line_ids:
                # print(records1.cost_subtotal, "records1.cost_subtotal0000000000000000")
                cost_subtotal += records1.cost_subtotal
                taxes = line.cost_tax_id.compute_all(
                    cost_subtotal, None, 1, line.laundry_services_id.laundry_services_id,
                    line.laundry_services_id.supplier_id)
            val = taxes['total_excluded']
            # print(line, "line==============")
            cur = line.laundry_service_id.pricelist_id.currency_id
            self.cost_subtotal = cur.round(val)

    def get_sales_subtotal_values(self):
        if self._context is None:
            self._context = {}
        sale_subtotal = 0.00
        for line in self:
            for records1 in line.laundry_service_product_line_ids:
                sale_subtotal += records1.sale_subtotal
            taxes = line.tax_id.compute_all(
                sale_subtotal, None, 1, line.laundry_services_id.laundry_services_id)
            val = taxes['total_excluded']
            # print(line, "line==============")
            cur = line.laundry_service_id.pricelist_id.currency_id
            self.sale_subtotal = cur.round(val)

    def get_cost_value(self):
        cost_subtotal = 0.0
        # print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>.get cost values")
        for records in self.browse:
            for records1 in records.laundry_service_product_line_ids:
                # print(records1.cost_subtotal, "records1------------")
                cost_subtotal += records1.cost_subtotal
            self.cost_rate = cost_subtotal

    def get_sales_value(self):
        sale_subtotal = 0.0
        # print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>.get sale values")
        for records in self:
            for records1 in records.laundry_service_product_line_ids:
                sale_subtotal += records1.sale_subtotal
            # print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>555555555555555555555", sale_subtotal)
            self.sales_rate = sale_subtotal

    @api.onchange('laundry_service_id')
    @api.depends('laundry_service_id.pricelist_id', 'laundry_service_id.supplier_id_temp', 'laundry_service_id')
    def on_change_service_ids(self):
        res = {}
        if self.laundry_service_id.pricelist_id:
            self.pricelist_id = self.laundry_service_id.pricelist_id
            self.supplier_id = self.laundry_service_id.supplier_id_temp
            # print("--------------------------------------", self.laundry_service_id.pricelist_id, self.laundry_service_id.supplier_id_temp)
        if self.laundry_services_id:
            service_id = self.env['hotel.laundry.services'].browse(
                self.laundry_services_id)
            cost_tax_id = []
            tax_id = []
            for tax_line in service_id.laundry_services_id.taxes_id:
                tax_id.append(tax_line.id)
            for cost_tax_line in service_id.laundry_services_id.supplier_taxes_id:
                cost_tax_id.append(cost_tax_line.id)
            self.tax_id = tax_id
            self.cost_tax_id = cost_tax_id

    def _get_currency(self):
        comp = self.pool.get('res.users').browse().company_id
        if not comp:
            comp_id = self.env['res.company'].search([], limit=1)
            comp = self.env['res.company'].browse(comp_id)
        return comp.currency_id.id

    @api.model
    def default_get(self, fields):
        res = {}
        if 'default_supplier_id' in self._context:
            supp_id = self._context.get('default_supplier_id')
            partner = self.env['hotel.laundry'].browse(supp_id)
            res.update({'supplier_id': partner.partner_id.id})
        return res

    laundry_service_id = fields.Many2one('laundry.management')
    laundry_services_id = fields.Many2one('hotel.laundry.services', 'Service Name', required=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist')
    supplier_id = fields.Many2one('res.partner', 'Supplier')
    #     supp_id=fields.Integer("suuuu")

    #            'currency_id' : fields.many2one('res.currency','Currency'),
    #            'product_uom_qty':fields.float('Quantity'),
    #            'qty_uom':fields.many2one('product.uom','UOM'),

    cost_rate = fields.Float(compute='get_cost_value', string='Cost Rate', type="float",
                             store=True,
                             help="This column will compute cost price based on the pricelist linked to selected supplier")
    sales_rate = fields.Float(compute='get_sales_value', string='Sales Rate', type="float",
                              help="This column will compute cost price based on the pricelist selected at header part")
    cost_subtotal = fields.Float(compute='get_cost_subtotal_value', string='Cost Sub Total', type="float", store=True)
    sale_subtotal = fields.Float(compute='get_sales_subtotal_values', string='Sales Sub Total', type="float")
    laundry_service_product_line_ids = fields.One2many('laundry.service.product.line', 'laundry_service_line_id',
                                                       'Laundry Product Service Line')
    tax_id = fields.Many2many('account.tax', 'laundry_order_tax', 'order_line_id', 'tax_id', 'Customer Taxes', )
    cost_tax_id = fields.Many2many('account.tax', 'laundry_cost_order_tax', 'order_line_id', 'tax_id',
                                   'Supplier Taxes', )


class laundry_service_product_line(models.Model):
    """This class will show all the items according to service selection by the hotel manager"""
    _name = 'laundry.service.product.line'
    _description = 'Product Line show all items details'

    def get_price(self, pricelist_ids, price):
        # print("-----------------------------------", pricelist_ids)
        # print("priceeeeeeeeeeeeeeeeeeeeee", price,type(price))
        price_amt = 0.0
        pricelist_item_ids = []
        if self._context is None:
            self._context = {}

        date = time.strftime('%Y-%m-%d')
        # print("dateeeeeeeeeeeeeeeeeee", date)
        if 'date' in self._context:
            date = self._context['date']

        currency_obj = self.env['res.currency']
        product_pricelist_version_obj = self.env['product.pricelist.item']
        user_browse = self.env['res.users'].browse(self._uid)
        company_obj = self.env['res.company']
        company_id = company_obj.browse(user_browse.company_id.id)
        # print(company_id, "company_id")
        # print(company_id.currency_id.id ,"company_idcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc")
        pricelist_obj = self.env['product.pricelist'].browse(pricelist_ids)
        # print("\n\n\n pricelist_ids=====")
        if pricelist_ids:
            pricelist_item_ids.append(pricelist_ids)
            pricelist_obj = self.env['product.pricelist'].browse(pricelist_ids)
        # print("pricelist_obj2:::::::::::::::::;",pricelist_obj)

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

        # print("plversions_search_args::::::::::;",plversions_search_args)

        plversion_ids = product_pricelist_version_obj.search(
            plversions_search_args)

        # print("herrrrrrrrrrrrrrrrrrrr1",plversion_ids)
        # if not plversion_ids:
        #     raise Warning(
        #         'Warning! At least one pricelist item has not declared !\nPlease create pricelist item')
        #
        # self._cr.execute(
        #     'SELECT i.* '
        #     'FROM product_pricelist_item AS i '
        #     'WHERE id = ' + str(plversion_ids[0].id) + '')
        #
        # res1 = self._cr.dictfetchall()
        if pricelist_obj:
            # print("pricelist_obj.currency_id.idddddddddddd", pricelist_obj.currency_id.id)
            # print("priceeeeeeeeeeeeeee", price,type(price))
            price = currency_obj.compute(price, pricelist_obj.currency_id, round)
            # print(price,type(price), "price333333333333333333333333333333333333")
        # for res in res1:
        #     if res:
        #         price_limit = price
        #         x = (1.0 + (res['price_discount'] or 0.0))
        #         price = price * (1.0 + (res['price_discount'] or 0.0))
        #         price += (res['price_surcharge'] or 0.0)
        #         if res['price_min_margin']:
        #             price = max(price, price_limit + res['price_min_margin'])
        #         if res['price_max_margin']:
        #             price = min(price, price_limit + res['price_max_margin'])
        #         break

        price_amt = price
        return price_amt

    def _get_uom_id(self):
        try:
            proxy = self.env['ir.model.data']
            result = proxy.get_object_reference('product', 'product_uom_unit')
            # print("result : ",result)
            return result[1]
        except Exception as ex:
            return False

    def get_cost_subtotal_value(self):
        if self._context is None:
            self._context = {}
        for records in self:
            # print(records.laundry_service_line_id.laundry_service_id.supplier_id, "kkkkkkkkkkkkkkkkkkkkkkkkkk")
            sup_pricelist = records.laundry_service_line_id.laundry_service_id.supplier_id.partner_id.property_product_pricelist.id
            cost_price = records.item_id_ref.cost_price
            cost = records.qty * \
                   self.get_price(sup_pricelist, cost_price)
            # print(records.cost_price, "----------------------------------------", cost)
        self.cost_subtotal = cost

    def get_cost_value(self):
        cost_subtotal = 0.0
        for records in self:
            # print(records.laundry_service_line_id.laundry_service_id.supplier_id, "kkkk")
            sup_pricelist = records.laundry_service_line_id.laundry_service_id.supplier_id.partner_id.property_product_pricelist.id
            cost_price = records.item_id_ref.cost_price
            cost = self.get_price(sup_pricelist, cost_price)
            self.cost_price = cost
            # print("fdhfhsdfjdhfhjsdfd",self.cost_price)

    @api.onchange('item_id_ref')
    @api.depends('item_id_ref', 'laundry_service_line_id.pricelist_id', 'laundry_service_line_id.supplier_id')
    def onchange_itemid(self):
        partner_obj = self.laundry_service_line_id.supplier_id
        sup_pricelist = partner_obj.property_product_pricelist.id
        cost = 0.0
        sale = 0
        if self.item_id_ref:
            record_id = self.item_id_ref
            # record_id=self.env['hotel.laundry.services.items'].browse(self.item_id_ref)
            cost = self.get_price(sup_pricelist, record_id.cost_price)
            sale = self.get_price(
                self.laundry_service_line_id.pricelist_id.id, record_id.sale_price)
            self.item_id = record_id.item_id.id
            self.cost_price = cost
            self.sales_price = sale
            self.cost_subtotal = cost
            self.sale_subtotal = sale

    @api.onchange('qty')
    @api.depends('qty', 'sales_price')
    def onchange_quantity(self):
        if self.qty:
            self.sale_subtotal = self.qty * self.sales_price

    @api.depends("item_id")
    def _get_product_uom(self):
        if self.item_id:
            self.qty_uom = self.item_id.uom_id

    laundry_service_line_id = fields.Many2one('laundry.service.product')
    item_id = fields.Many2one('product.product', 'Item')
    item_id_ref = fields.Many2one('hotel.laundry.services.items', 'Items', required=True)
    qty_uom = fields.Many2one('uom.uom', 'UOM2', compute="_get_product_uom", store=True)  # default=_get_uom_id
    qty = fields.Float('Quantity', default=1)
    cost_price = fields.Float(compute='get_cost_value', string='Cost Price', store=True)
    #             'cost_price':fields.float('Cost Price', help="This column will compute cost price based on the pricelist linked to selected supplier"),
    sales_price = fields.Float('Sales Price',
                               help="This column will compute cost price based on the pricelist selected at header part")
    #             'cost_subtotal':fields.float('Cost Sub Total'),
    cost_subtotal = fields.Float(compute='get_cost_subtotal_value', string='Cost Sub Total', store=True)
    sale_subtotal = fields.Float('Sale Sub Total')
