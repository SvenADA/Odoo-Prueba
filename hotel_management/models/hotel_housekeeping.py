# -*- encoding: utf-8 -*-

from odoo import fields, models, api
import time
# from mx import DateTime
import datetime
from odoo.tools.translate import _
from odoo.exceptions import Warning


class rr_housekeeping(models.Model):

    _name = 'rr.housekeeping'
    _description = 'test'

    name = fields.Char(
        'Req No', readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Datetime('Date Ordered', required=True, readonly=True, default=lambda *
                           a: time.strftime('%Y-%m-%d %H:%M:%S'), states={'draft': [('readonly', False)]})
    activity = fields.Selection([('repair', 'Repair'), ('replaced', 'Replace')], 'Activity',
                                index=True, required=True, readonly=True, states={'draft': [('readonly', False)]})
    requested_by = fields.Many2one('res.users', 'Requested By User', readonly=True, states={'draft': [('readonly', False)]})
    requested_by_partner = fields.Many2one('res.partner', 'Requested By ', readonly=True, states={'draft': [('readonly', False)]})
    source = fields.Selection([('intern', 'Internal Observation'), ('guest', 'Guest')], 'Source',
                              default='intern', required=True, readonly=True, states={'draft': [('readonly', False)]})
    assign_to = fields.Selection([('intern', 'Internal'), ('third_party', 'Third Party')], 'Assign Method', default='intern',
                                 required=True, readonly=True, states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]})
    assigned_third_party = fields.Many2one('res.partner', 'Assigned To Thirt Party', readonly=True, states={
                                           'draft': [('readonly', False)], 'confirmed': [('readonly', False)]})
    assigned_internal = fields.Many2one('res.users', 'Assigned To', readonly=True, states={
                                        'draft': [('readonly', False)], 'confirmed': [('readonly', False)]})
    room_no = fields.Many2one('hotel.room', 'Room No', required=True, readonly=True, states={
                              'draft': [('readonly', False)]})
    approved_by = fields.Char('Approved By')
    rr_line_ids = fields.One2many('rr.housekeeping.line', 'rr_line_id', 'Repair / Replacement Info',
                                  required=True, readonly=True, states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]})
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('assign', 'Assigned'), (
        'done', 'Done'), ('cancel', 'Cancel')], 'State', default="draft", readonly=True, index=True)
    complaint = fields.Char('Complaint', readonly=True, states={'draft': [('readonly', False)]})
    shop_id = fields.Many2one('sale.shop', 'Hotel', required=True, readonly=True, states={
                              'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', related='shop_id.company_id', string='Company', store=True)


    @api.model
    def create(self, vals):
        now = datetime.datetime.now()
        if 'rr_line_ids' in vals:
            # print(vals['rr_line_ids'])
            if not vals['rr_line_ids']:
                raise Warning('There are no product in requirement  line.')
        ir_obj = self.env['ir.sequence']
        if vals['activity'] == 'repair':
            temp = ir_obj.next_by_code('rr.housekeeping.repair')
            # print(temp, '=================================temp')
            temp1 = temp[0:3]
            temp2 = temp[3:]
            vals['name'] = str(temp1) + '/' + str(now.year) + '/' + str(temp2)
        else:
            temp = ir_obj.next_by_code('rr.housekeeping.replace')
            temp1 = temp[0:3]
            temp2 = temp[3:]
            vals['name'] = str(temp1) + '/' + str(now.year) + '/' + str(temp2)
        res = super(rr_housekeeping, self).create(vals)
        # print(res, '=====================res')
        return res


    def confirm_request(self):
        p = self.env['res.users'].browse(self._uid)
        # print("--------------------------", p.id)
        self.write({
            'approved_by': p.name,
            'state': 'confirmed'
        })
        return True


    def assign_request(self):
        obj = self.env['rr.housekeeping'].browse(self._ids[0])
        if obj.assign_to == 'intern':
            if not obj.assigned_internal:
                raise Warning('There is no  user selected')
        elif obj.assign_to == 'third_party':
            if not obj.assigned_third_party:
                raise Warning('There is no Third party selected')
        else:
            pass
        self.write({
            'state': 'assign'
        })
        return True



    def onchange_date_source(self):
        res = {}
        if self.date and self.source and self.shop_id:
            if self.source == 'guest':
                history_obj = self.env[
                    'hotel.room.booking.history']
                main_obj_ids = history_obj.search(
                    [('check_in', '<=', self.date), ('check_out', '>=', self.date)])
                # print(main_obj_ids, "main_obj_ids")
                main_obj = history_obj.browse(main_obj_ids)
                new_ids = []
                for dest_line in main_obj:
                    if dest_line.history_id.product_id.shop_id.id == self.shop_id.id:

                        new_ids.append(dest_line.history_id.id)
                return {
                    'domain': {
                        'room_no': [('id', 'in', new_ids)],
                    }}
            else:
                hotel_room_obj = self.env["hotel.room"]
                new_ids = hotel_room_obj.search(
                    [('product_id.shop_id.id', '=', self.shop_id.id)])
                # print("\n\n after---", new_ids)
                return {
                    'domain': {
                        'room_no': [('id', 'in', [x.id for x in new_ids])],
                    }}
        return {'value': res}


    @api.onchange('date', 'room_no')
    def onchange_room(self):
        res = {}
        today = self.date
        booking_id = 0
        history_obj = self.env["hotel.room.booking.history"]
        folio_obj = self.env["hotel.folio"]
        if not self.room_no:
            return {'value': {'requested_by_partner': False}}
        # print(".>>>>>>>>>>>>>room", self.room_no)
        # print(".>>>>>>>>>>>>>", self.room_no.product_id.name)
        for folio_hsry_id in history_obj.search([('name', '=', self.room_no.product_id.name)]):
            hstry_line_id = history_obj.browse(folio_hsry_id).id
            # print(hstry_line_id,'=hstry_line_id===========')
            start_dt = hstry_line_id.check_in
            end_dt = hstry_line_id.check_out
            if (start_dt <= today) and (end_dt >= today):
                booking_id = hstry_line_id.booking_id.id
                folio_obj_id = folio_obj.search(
                    [('reservation_id', '=', booking_id)])
                res['requested_by_partner'] = hstry_line_id.partner_id.id
            # print(">>>>>>>>>>>>>>>>>>res : ", res)
        return {'value': res}


    def cancel_request(self):
        self.write({
            'state': 'cancel'
        })
        return True


    def done_task(self):
        self.write({
            'state': 'done'
        })
        return True


class rr_housekeeping_line(models.Model):
    _name = 'rr.housekeeping.line'
    _description = 'rr housekeeping line'

    rr_line_id = fields.Many2one('rr.housekeeping', 'Housekeeping line id')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_line_ids = fields.One2many(
        'product.product.line', 'product_line_id', 'Product Details')
    qty = fields.Float('Qty', default=1)
    uom = fields.Many2one('uom.uom', 'UOM')
    source_locatiion = fields.Many2one('stock.location', 'Source Location')
    dest_locatiion = fields.Many2one('stock.location', 'Destination Location')
    info_id = fields.Many2one('issue.material.details', 'Material Id')

    @api.onchange('product_id')
    def onchange_product(self):
        # print('=====================================================')
        if self.product_id:
            # print(self.product_id, '==============product')
            uom = self.product_id.uom_id.id
            self.uom = uom


    @api.model
    def create(self, vals):
        if 'qty' in vals:
            # print("---------------------------------", vals['qty'])
            if vals['qty'] <= 0.0:
                raise Warning('Product Quantity should not be 0 ')

        return super(rr_housekeeping_line, self).create(vals)



class product_product_line(models.Model):
    """Product of product"""
    _name = "product.product.line"
    _description = 'product product line'

    product_line_id = fields.Many2one(
        'rr.housekeeping.line', 'Product line id')
    product_product_id = fields.Many2one(
        'product.product', 'Product', required=True)
    qty = fields.Float('Qty')
    uom = fields.Many2one('uom.uom', 'UOM')

    api.onchange('product_product_id')

    @api.onchange('product_product_id')
    def onchange_product(self):
        if self.product_product_id:
            # print('product_product_id==============', self.product_product_id)
            uom = self.product_product_id.uom_id.id
            self.uom = uom


    @api.model
    def create(self, vals):
        if 'qty' in vals:
            # print("---------------------------------", vals['qty'])
            if vals['qty'] <= 0.0:
                raise Warning('Product Quntity should not be 0 ')
        return super(product_product_line, self).create(vals)


class issue_material_details(models.Model):
    _name = "issue.material.details"
    _description = 'Issue Material Details'

    name = fields.Char('Issue Slip')
    request_id = fields.Many2one('rr.housekeeping', 'Request Number',
                                 required=True, readonly=True, states={'draft': [('readonly', False)]})
    repair_ids = fields.One2many('rr.housekeeping.line', 'info_id', 'Product Replacement info', readonly=True, states={
                                 'draft': [('readonly', False)]})
    complaint = fields.Char(
        'Complaint', readonly=True, states={'draft': [('readonly', False)]})
    shop_id = fields.Many2one('sale.shop', 'Hotel', required=True, readonly=True, states={
                              'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), (
        'done', 'Done')], 'State', default='draft', readonly=True, index=True)
#     company_id = fields.related('shop_id','company_id',type='many2one',relation='res.company',string='Company',store=True)
    company_id = fields.Many2one(
        'res.company', related='shop_id.company_id', string='Company', store=True)

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code(
            'issue.material.details')
        return super(issue_material_details, self).create(vals)


    def done_task(self):
        self.write({'state': 'done'})
        return True

#
    def confirm_task(self):
        for obj in self.browse(self.id):
            internal_move_id = None
            for line in obj.repair_ids:
                if not line.product_line_ids:
                    raise Warning('Product details is missing.')
                if not (line.source_locatiion and line.dest_locatiion):
                    raise Warning('Location is missing.')
                if not internal_move_id:
                    internal_move_id = self.env['stock.picking'].create({'picking_type_id': obj.shop_id.warehouse_id.int_type_id.id, 'company_id': obj.company_id.id, 'origin': obj.name,
                                                                         'location_id': line.source_locatiion.id, 'location_dest_id': line.dest_locatiion.id, })


                for product in line.product_line_ids:
                    # print(product)
                    move_id = self.env['stock.move'].create({
                        'product_id': product.product_product_id.id,
                        'product_uom': product.uom.id,
                        'origin': obj.name,
                        'name': obj.name,
                        'product_uom_qty': product.qty,
                        'location_id': line.source_locatiion.id,
                        'location_dest_id': line.dest_locatiion.id,
                        'picking_id': internal_move_id.id,

                    })

        self.write({'state': 'confirm'})
        return True


    @api.onchange('request_id')
    def on_change_request_id(self):
        result = {}
        # print(self.request_id, "request_id")
        housekeeping_id = self.request_id
        # print(housekeeping_id, "housekeeping_id")
        result['complaint'] = housekeeping_id.complaint
        result['shop_id'] = housekeeping_id.shop_id.id
        source_location = housekeeping_id.shop_id.warehouse_id.lot_stock_id.id
        product_list = []
        for product in housekeeping_id.rr_line_ids:
            product_list.append(product.id)
        # print(product_list, "product_list")
        housekeeping_obj = self.env['rr.housekeeping.line']
        line_ids = housekeeping_obj.browse(product_list)
        for line in line_ids:
            line.write({'source_locatiion': source_location})
        result['repair_ids'] = product_list
        return {'value': result}

