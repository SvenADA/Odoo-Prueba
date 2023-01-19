# -*- encoding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
# from mx import DateTime
from odoo import netsvc
# from odoo.tools import config
from datetime import datetime


class product_category(models.Model):
    _inherit = "product.category"

    ismenutype = fields.Boolean('Is Menu Type')


class product_product(models.Model):
    _inherit = "product.product"

    ismenucard = fields.Boolean('Is room ')


class hotel_menucard_type(models.Model):
    _name = 'hotel.menucard.type'
    _description = 'amenities Type'
    _inherits = {'product.category': 'menu_id'}

    menu_id = fields.Many2one('product.category', string='Category', required=True, ondelete='cascade')
    ismenutype = fields.Boolean('Is Menu Type', related='menu_id.ismenutype', inherited=True, default=True)

    # @api.multi
    def unlink(self):
        for categ in self:
            categ.menu_id.unlink()
        return super(hotel_menucard_type, self).unlink()


class Hotel_menucard(models.Model):
    _name = 'hotel.menucard'
    _description = 'Hotel Menucard'
    _inherits = {'product.product': 'product_id'}
    _inherit = ['mail.thread']

    product_id = fields.Many2one('product.product', string='Product_id', required=True, ondelete='cascade')
    ismenucard = fields.Boolean('Is Hotel Room', related='product_id.ismenucard', inherited=True, default=True)
    currency_id = fields.Many2one('res.currency', 'Currency')

    def action_open_label_layout(self):
        action = self.env['ir.actions.act_window']._for_xml_id('product.action_open_label_layout')
        action['context'] = {'default_product_tmpl_ids': self.ids}
        return action
        
    def open_pricelist_rules(self):
        # print("eeeeeeeeeeeeeeeeeeeeee")
        self.ensure_one()
        domain = ['|',
                  ('product_tmpl_id', '=', self.id),
                  ('product_id', 'in', self.product_variant_ids.ids)]
        return {
            'name': ('Price Rules'),
            'view_mode': 'tree,form',
            'views': [(self.env.ref('product.product_pricelist_item_tree_view_from_product').id, 'tree'),
                      (False, 'form')],
            'res_model': 'product.pricelist.item',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain,
            'context': {
                'default_product_tmpl_id': self.id,
                'default_applied_on': '1_product',
                'product_without_variants': self.product_variant_count == 1,
            },
        }

    @api.onchange('type')
    def onchange_type(self):
        res = {}
        if self.type in ('consu', 'service'):
            res = {'value': {'valuation': 'manual_periodic'}}
        return res

    @api.onchange('tracking')
    def onchange_tracking(self):
        # print("kkkkkkkkkkkkk")
        if not self.tracking:
            return {}
        product_product = self.env['product.product']
        variant_ids = product_product.search(
            [('product_tmpl_id', 'in', self._ids)])
        for variant_id in variant_ids:
            variant_id.onchange_tracking()

    # @api.multi
    def read_followers_data(self):
        # print("kkkkkkkkkkkkk1")
        result = []
        technical_group = self.env['ir.model.data'].get_object('base', 'group_no_one')
        for follower in self.env['res.partner'].browse(self._ids):
            is_editable = self._uid in map(lambda x: x.id, technical_group.users)
            is_uid = self._uid in map(lambda x: x.id, follower.user_ids)
            data = (follower.id,
                    follower.name,
                    {'is_editable': is_editable,
                     'is_uid': is_uid
                     },
                    )
            result.append(data)
        return result

    # @api.multi
    def unlink(self):
        # print("\n\n\n\nunliliiiiiiiiiiiiiiiiiiiiiiiiix\n\n\n\n", self)

        return super(Hotel_menucard, self).unlink()

    @api.onchange('uom_id', 'uom_po_id')
    def onchange_uom(self):
        # print("kkkkkkkkkkkkk3")
        if self.uom_id:
            return {'value': {'uom_po_id': self.uom_id}}
        return {}

    def message_get_subscription_data(self, user_pid=None):

        """ Wrapper to get subtypes data. """
        return self.env['mail.thread']._get_subscription_data(None, None, user_pid=user_pid)
    
    def action_open_label_layout(self):
        action = self.env['ir.actions.act_window']._for_xml_id('product.action_open_label_layout')
        action['context'] = {'default_product_tmpl_ids': self.ids}
        return action  

class hotel_restaurant_tables(models.Model):
    _name = "hotel.restaurant.tables"
    _description = "Includes Hotel Restaurant Table"

    name = fields.Char(string='Table number', required=True)
    capacity = fields.Integer(string='Capacity')
    state = fields.Selection([('available', 'Available'), ('book', 'Booked')],
                             string='State', default='available', index=True, required=True, readonly=True)


class hotel_restaurant_reservation(models.Model):

    @api.model
    def create(self, vals):
        # function overwrites create method and auto generate request no.
        # print(vals,"________________________________")
        vals['name'] = self.env['ir.sequence'].next_by_code(
            'hotel.restaurant.reservation')
        self.write({'name': vals['name']})
        # vals.update({'partner_id':vals['cname']})

        return super(hotel_restaurant_reservation, self).create(vals)

    # @api.multi
    def create_order(self):
        # print("\n\n\n create order method called")
        for i in self:
            # print("i:::::::::::::::::", i)
            # print("i:::::::::::::::::", i.order_list_ids)
            table_ids = [x.id for x in i.tableno]
            kot_data = self.env['hotel.reservation.order'].create({
                'reservation_id': i.id,
                'date1': i.start_date,
                'partner_id': i.cname.id,
                'room_no': i.room_no.id,
                'folio_id': i.folio_id.id,
                'table_no': [(6, 0, table_ids)],
            })
            # print("i::::::::::::::", i)

            for line in i.order_list_ids:
                line.write({'o_l': kot_data.id})
        self.write({'state': 'order'})
        return True

    # @api.multi
    def action_set_to_draft(self, *args):
        # print("\n\n\n\n action set to draft method called")
        self.write({'state': 'draft'})
        wf_service = netsvc.LocalService('workflow')
        for record in self._ids:
            wf_service.trg_create(self._uid, self._name, record, self._cr)
        return True

    #     def action_set_to_draft(self, cr, uid, ids, *args):
    #         self.write(cr, uid, ids, {'state': 'draft'})
    #         wf_service = netsvc.LocalService('workflow')
    #         for id in ids:
    #             wf_service.trg_create(uid, self._name, id, cr)
    #         return True

    # @api.multi
    def table_reserved(self):
        # print("\n\n\n\n table_reserved method called")
        for reservation in self:
            # print("Table reservation method", reservation)
            if reservation.room_no:
                if reservation.start_date <= reservation.folio_id.checkin_date and reservation.start_date >= reservation.folio_id.checkout_date:
                    raise Warning('Please Check Start Date which is not between check in and check out date')
                if reservation.end_date <= reservation.folio_id.checkin_date and reservation.end_date >= reservation.folio_id.checkout_date:
                    raise Warning('Please Check End Date which is not between check in and check out date')
            self._cr.execute("select count(*) from hotel_restaurant_reservation as hrr "
                             "inner join reservation_table as rt on rt.reservation_table_id = hrr.id "
                             "where (start_date,end_date)overlaps( timestamp %s , timestamp %s ) "
                             "and hrr.id<> %s "
                             "and rt.name in (select rt.name from hotel_restaurant_reservation as hrr "
                             "inner join reservation_table as rt on rt.reservation_table_id = hrr.id "
                             "where hrr.id= %s) and hrr.state not in ('order','cancel')",
                             (reservation.start_date, reservation.end_date, reservation.id, reservation.id))

            res = self._cr.fetchone()
            # print("ressss", res)
            roomcount = res and res[0] or 0.0
            # print("roomcount", roomcount)
            if roomcount:
                raise Warning(
                    'You tried to confirm reservation with table those already reserved in this reservation period')
            else:
                self.write({'state': 'confirm'})
            return True

    # @api.multi
    def table_cancel(self, *args):
        # print("\n\n\n table_cancel method called")
        return self.write({'state': 'cancel'})

    # @api.multi
    def table_done(self, *args):
        # print("\n\n\n table_done method called")
        return self.write({'state': 'done'})

    _name = "hotel.restaurant.reservation"
    _description = "Includes Hotel Restaurant Reservation"

    # _inherits = {'sale.order': 'order_id'}
    # order_id = fields.Many2one('sale.order', required=True, string='Order Id', ondelete='cascade')

    name = fields.Char('Reservation No', readonly=True)
    room_no = fields.Many2one('hotel.room', 'Room No')
    start_date = fields.Datetime('Start Date', required=True)
    end_date = fields.Datetime('End Date', required=True)
    cname = fields.Many2one('res.partner', 'Customer Name', required=True)
    folio_id = fields.Many2one('hotel.folio', 'Hotel Folio', ondelete='cascade')
    tableno = fields.Many2many('hotel.restaurant.tables', 'reservation_table', 'reservation_table_id', 'name',
                               'Table number')
    order_list_ids = fields.One2many('hotel.restaurant.order.list', 'order_l', 'Order List')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done'), ('order', 'Order Done'), (
        'cancel', 'Cancelled')], 'State', default='draft', index=True, required=True, readonly=True)

    # @api.onchange('partner_id')
    def onchange_partner_id(self):
        # print("\n\n\n onchange_partner_id , self=====", self, self.partner_id)
        if not self.partner_id:
            return {'value': {'partner_address_id': False}}
        addr = self.partner_id.address_get(['default'])
        return {'value': {'partner_address_id': addr['default']}}


class hotel_restaurant_kitchen_order_tickets(models.Model):
    _name = "hotel.restaurant.kitchen.order.tickets"
    _description = "Includes Hotel Restaurant Order"

    @api.model
    def create(self, vals):
        # print("\n\n\n vals123======", vals)
        # function overwrites create method and auto generate request no.
        vals['orderno'] = self.env['ir.sequence'].next_by_code('hotel.reservation.order12')
        # print("\n\nvals['orderno']=====", vals['orderno'])
        return super(hotel_restaurant_kitchen_order_tickets, self).create(vals)

    orderno = fields.Char('KOT Number', readonly=True)
    resno = fields.Char('Order Number')
    kot_date = fields.Date('Date')
    room_no = fields.Char('Room No', readonly=True)
    w_name = fields.Char('Waiter Name', readonly=True)
    tableno = fields.Many2many('hotel.restaurant.tables', 'temp_table3', 'table_no', 'name', 'Table number')
    kot_list = fields.One2many('hotel.restaurant.order.list', 'kot_order_list', 'Order List')


class hotel_restaurant_order(models.Model):

    @api.model
    def create(self, vals):
        # print("\n\n\n in create vals========", vals)
        # function overwrites create method and auto generate request no.
        vals['order_no'] = self.env['ir.sequence'].next_by_code('hotel.restaurant.order')
        vals['name'] = vals['order_no']
        # print("\n\n\nvals['order_no']=====", vals['order_no'])
        return super(hotel_restaurant_order, self).create(vals)

    # @api.multi
    def _sub_total(self):
        # print("killlllllllllllllllll")
        res = {}
        for sale in self:
            res[sale.id] = 0.00
            for line in sale.order_list:
                res[sale.id] += line.price_subtotal
        return res

    # @api.multi
    def _total(self):
        res = {}
        for line in self:
            res[line.id] = line.amount_subtotal + (line.amount_subtotal * line.tax) / 100
        return res

    # @api.multi
    def generate_kot(self):

        for order in self:
            table_ids = [x.id for x in order.table_no]

            kot_data = self.env['hotel.restaurant.kitchen.order.tickets'].create({
                'resno': order.order_no,
                'kot_date': order.o_date,
                'room_no': order.room_no.name,
                'w_name': order.waiter_name.name,
                'tableno': [(6, 0, table_ids)],
            })

            for order_line in order.order_list:
                o_line = {
                    'kot_order_list': kot_data.id,
                    'name': order_line.name.id,
                    'item_qty': order_line.item_qty,
                }
                self.env['hotel.restaurant.order.list'].create(o_line)
        self.write({'state': 'order'})
        return True

    _name = "hotel.restaurant.order"
    _description = "Includes Hotel Restaurant Order"

    order_no = fields.Char('Order Number', readonly=True)
    name = fields.Char('Name')
    partner_id = fields.Many2one('res.partner', 'Customer', required=True)
    guest_name = fields.Char('Guest Name')
    o_date = fields.Datetime('Date', required=True, default=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    room_no = fields.Many2one('hotel.room', 'Room No')
    folio_id = fields.Many2one('hotel.folio', 'Hotel Folio Ref')
    waiter_name = fields.Many2one('res.partner', 'Waiter Name')
    table_no = fields.Many2many('hotel.restaurant.tables', 'temp_table2', 'table_no', 'name', 'Table number')
    order_list = fields.One2many('hotel.restaurant.order.list', 'o_list', 'Order List')
    tax = fields.Float('Tax (%) ')
    amount_subtotal = fields.Float(compute='_sub_total', string='Subtotal')
    amount_total = fields.Float(compute='_total', string='Total')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done'), (
        'order', 'Order Done'), ('cancel', 'Cancelled')], string='State', default='draft', index=True, required=True)

    invoice_count = fields.Integer(compute="_compute_invoice", string='Invoice Count', copy=False, default=0,
                                   readonly=True)
    invoice_ids = fields.Many2many('account.move', compute="_compute_invoice", string='Invoices', copy=False,
                                   readonly=True)
    picking_count = fields.Integer(compute="_compute_pickings", string='Invoice Count', copy=False, default=0,
                                   readonly=True)
    picking_ids = fields.Many2many('stock.picking', compute="_compute_pickings", string='Invoices', copy=False,
                                   readonly=True)

    @api.depends('picking_count')
    def _compute_pickings(self):
        for order in self:
            if self.order_no:
                pickings = self.env['stock.picking'].search([('origin', "=", self.order_no)])
                order.picking_ids = pickings
                order.picking_count = len(pickings)
            else:
                order.picking_count = 0

    def action_picking_order_view(self):
        pickings = self.mapped('picking_ids')
        action = self.env.ref('stock.stock_picking_action_picking_type').sudo().read()[0]
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif len(pickings) == 1:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.depends('order_no', 'order_list', 'invoice_count')
    def _compute_invoice(self):
        for order in self:
            if self.order_no:
                invoices = self.env['account.move'].search([('invoice_origin', "=", self.order_no)])
                order.invoice_ids = invoices
                order.invoice_count = len(invoices)
            else:
                order.invoice_count = 0

    def action_invoice_view(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        # context = {
        #     'default_type': 'out_invoice'
        # }
        # action['context'] = context
        # print("action : ", action)
        return action





    #     @api.onchange('room_no')
    #     def onchange_room_no(self):
    #         print "\n\n\n onchange_room_no",self.room_no
    #         if not self.room_no:
    #             return {'value':{'cname': False}}
    # return {'value':{'cname': self.room_no.id,'folio_id': self.room_no.id}}

    #     def onchange_room_no(self, cr, uid, ids, room_no):
    #         if not room_no:
    #             return {'value':{'cname': False}}
    #         obj = self.pool.get("hotel.room").browse(cr,uid,room_no)
    # return {'value':{'cname': obj.ref_partner_id.id,'folio_id':
    # obj.ref_folio_id.id}}


    # @api.multi
    def confirm_order(self, *args):
        for obj in self:
            for line in obj.table_no:
                line.write({'state': 'book'})
        self.write({'state': 'confirm'})
        return True

    # @api.multi
    def cancel_order(self, *args):
        self.write({'state': 'cancel'})

    # @api.multi
    def create_invoice(self, *args):
        for obj in self:
            for line in obj.table_no:
                line.write({'state': 'available'})

            acc_id = obj.partner_id.property_account_receivable_id.id
            journal_obj = self.env['account.journal']
            journal_ids = journal_obj.search([('type', '=', 'sale')], limit=1)

            journal_id = None
            if journal_ids[0]:
                journal_id = journal_ids[0].id

            if not obj.room_no:
                inv = {
                    'invoice_origin': obj.order_no,
                    'type': 'out_invoice',
                    'ref': "Order Invoice ({})".format(obj.order_no),
                    'account_id': acc_id,
                    'partner_id': obj.partner_id.id,
                    'currency_id': self.env['res.currency'].search([('name', '=', 'EUR')])[0].id,
                    'journal_id': journal_id,
                    'amount_tax': 0,
                    'amount_untaxed': obj.amount_total,
                    'amount_total': obj.amount_total,
                }
                inv_id = self.env['account.move'].create(inv)
                todo = []
                for ol in obj.order_list:
                    todo.append(ol.id)
                    if ol.name.categ_id:
                        a = ol.name.categ_id.property_account_income_categ_id.id
                        if not a:
                            raise ValidationError(
                                _('There is no expense account defined for this product: "%s" (id:%d)') % (
                                    ol.product_id.name, ol.product_id.id,))
                    else:
                        a = self.env['ir.property'].get(
                            'property_account_income_categ_id', 'product.category').id
                    il = {
                        'name': ol.name.name,
                        'account_id': a,
                        'price_unit': ol.item_rate,
                        'quantity': ol.item_qty,
                        'uos_id': False,
                        'origin': obj.order_no,
                        'invoice_id': inv_id.id,
                        'price_subtotal': ol.price_subtotal,
                    }
                    self.env['account.move.line'].create(il)
        self.write({'state': 'done'})
        return True


class hotel_reservation_order(models.Model):

    @api.model
    def create(self, vals):
        # function overwrites create method and auto generate request no.
        # print("\n\n\n\n Vals : ", vals)
        vals['order_number'] = self.env['ir.sequence'].next_by_code('hotel.reservation.order')
        # print("\n\n\n req_no : ", vals['order_number'])
        return super(hotel_reservation_order, self).create(vals)

    # @api.multi
    def _sub_total(self):
        res = {}
        for sale in self:
            res[sale.id] = 0.00
            for line in sale.order_list:
                res[sale.id] += line.price_subtotal
        return res

    # @api.multi
    def _total(self):
        res = {}
        for line in self:
            res[line.id] = line.amount_subtotal + \
                           (line.amount_subtotal * line.tax) / 100
        return res

    # @api.multi
    def reservation_generate_kot(self):
        # print("\n\n\n in reservation_generate_kot self========", self)
        for order in self:
            # print("\n\n\n order=======", order)

            table_ids = [x.id for x in order.table_no]

            # print("\norder.order_number=====", order.order_number)
            # print("\norder.room_no.name====", order.room_no.name)
            # print("\norder.date1=========", order.date1)
            # print("\norder.waitername.name=====", order.waitername.name)
            # print("\ntable_ids=====", table_ids)

            kot_data = self.env['hotel.restaurant.kitchen.order.tickets'].create({
                'resno': order.order_number,
                'room_no': order.room_no.name,
                'kot_date': order.date1,
                'w_name': order.waitername.name,
                'tableno': [(6, 0, table_ids)],
            })

            # print("\n\n\nkot_data=====", kot_data)
            for order_line in order.order_list:
                o_line = {
                    'kot_order_list': kot_data.id,
                    'name': order_line.name.id,
                    'item_qty': order_line.item_qty,
                }
                self.env['hotel.restaurant.order.list'].create(o_line)
        self.write({'state': 'order'})
        return True

    _name = "hotel.reservation.order"
    _description = "Reservation Order"

    order_number = fields.Char('Order No', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', required=True)
    guest_name = fields.Char('Guest Name')
    room_no = fields.Many2one('hotel.room', 'Room No')
    folio_id = fields.Many2one('hotel.folio', 'Hotel Folio Ref')
    reservation_id = fields.Many2one('hotel.restaurant.reservation', 'Reservation No')
    date1 = fields.Datetime('Date', required=True)
    waitername = fields.Many2one('res.partner', 'Waiter Name')
    table_no = fields.Many2many('hotel.restaurant.tables', 'temp_table4', 'table_no', 'name', 'Table number')
    order_list = fields.One2many('hotel.restaurant.order.list', 'o_l', 'Order List')
    tax = fields.Float('Tax (%) ')
    amount_subtotal = fields.Float(compute='_sub_total', string='Subtotal')
    amount_total = fields.Float(compute='_total', string='Total')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done'), ('order', 'Order Done'), (
        'cancel', 'Cancelled')], 'State', default='draft', index=True, required=True, readonly=True)

    invoice_count = fields.Integer(compute="_compute_invoice", string='Invoice Count', copy=False, default=0, readonly=True)
    invoice_ids = fields.Many2many('account.move', compute="_compute_invoice", string='Invoices', copy=False, readonly=True )

    @api.depends('order_number', 'order_list', 'invoice_count')
    def _compute_invoice(self):
        for order in self:
            invoices = self.env['account.move'].search([('name', "=", self.order_number)])
            order.invoice_ids = invoices
            order.invoice_count = len(invoices)

    def action_invoice_view(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        # context = {
        #     'default_type': 'out_invoice'
        # }
        # action['context'] = context
        # print("action : ", action)
        return action

    # @api.multi
    def confirm_order(self, *args):
        for obj in self:
            for line in obj.table_no:
                line.write({'state': 'book'})
        self.write({'state': 'confirm'})
        return True

    # @api.multi
    def create_invoice(self, *args):

        for obj in self:
            for line in obj.table_no:
                line.write({'state': 'available'})

            acc_id = obj.partner_id.property_account_receivable_id.id
            journal_obj = self.env['account.journal']
            journal_ids = journal_obj.search([('type', '=', 'sale')], limit=1)

            journal_id = None
            if journal_ids[0]:
                journal_id = journal_ids[0].id

            inv = {
                'name': obj.order_number,
                'origin': obj.order_number,
                'type': 'out_invoice',
                'reference': "Order Invoice",
                'account_id': acc_id,
                'partner_id': obj.partner_id.id,
                'currency_id': self.env['res.currency'].search([('name', '=', 'EUR')])[0].id,
                'journal_id': journal_id,
                'amount_tax': 0,
                'amount_untaxed': obj.amount_total,
                'amount_total': obj.amount_total,
            }
            # print("inv", inv)
            inv_id = self.env['account.move'].create(inv)

            todo = []
            for ol in obj.order_list:
                todo.append(ol.id)
                if ol.name.categ_id:
                    a = ol.name.categ_id.property_account_income_categ_id.id
                    if not a:
                        raise ValidationError(
                            _('There is no expense account defined for this product: "%s" (id:%d)') % (
                                ol.product_id.name, ol.product_id.id,))
                else:
                    a = self.env['ir.property'].get(
                        'property_account_income_categ_id', 'product.category').id

                il = {
                    'name': ol.name.name,
                    'account_id': a,
                    'price_unit': ol.item_rate,
                    'quantity': ol.item_qty,
                    'uos_id': False,
                    'origin': obj.order_number,
                    'invoice_id': inv_id.id,
                    'price_subtotal': ol.price_subtotal,
                }
                # print("il", il)
                cres = self.env['account.move.line'].create(il)
                # print("\n\n\n cres=====", cres)
            if obj.room_no:
                self._cr.execute('insert into order_reserve_invoice_rel(folio_id,invoice_id) values (%s,%s)',
                                 (obj.folio_id.id, inv_id.id))
        self.write({'state': 'done'})
        return True


class hotel_restaurant_order_list(models.Model):

    # @api.multi
    def _sub_total(self):
        res = {}
        for line in self:
            res[line.id] = line.item_rate * int(line.item_qty)
        return res

    @api.onchange('name')
    def on_change_item_name(self):
        if not self.name:
            return {'value': {}}
        return {'value': {'item_rate': self.name.list_price}}

    _name = "hotel.restaurant.order.list"
    _description = "Includes Hotel Restaurant Order"

    o_list = fields.Many2one('hotel.restaurant.order')
    order_l = fields.Many2one('hotel.restaurant.reservation')
    o_l = fields.Many2one('hotel.reservation.order')
    kot_order_list = fields.Many2one('hotel.restaurant.kitchen.order.tickets')
    name = fields.Many2one('hotel.menucard', 'Item Name')
    item_qty = fields.Char('Qty', required=True)
    item_rate = fields.Float('Rate')
    price_subtotal = fields.Float(compute='_sub_total', string='Subtotal')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
