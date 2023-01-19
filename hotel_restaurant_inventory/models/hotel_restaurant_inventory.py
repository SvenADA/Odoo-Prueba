# -*- encoding: utf-8 -*-
import time
from odoo import api, fields, models, _
import odoo
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import float_compare, float_round
from odoo.exceptions import ValidationError, Warning, UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

from odoo import netsvc


class stock_picking(models.Model):
    _inherit = "stock.picking"

    def action_process(self):
        if self._context is None:
            self._context = {}
        """Open the partial picking wizard"""
        picking_context = dict(self.env.context)
        picking_context.update({
            'active_model': self._name,
            'active_ids': self._ids,
            'active_id': len(self._ids) and self._ids[0] or False
        })

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.partial.picking',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self._context,
            'nodestroy': True,
        }

    def draft_force_assign(self):
        """ Confirms picking directly from draft state.
        @return: True
        """
        # wf_service = odoo.netsvc.LocalService("workflow")
        for pick in self:
            if not pick.move_lines:
                raise UserError('You cannot process picking without stock moves.')
            # self.partner_id.trg_validate(self._uid, 'stock.picking', pick.id,'button_confirm', self._cr)
        return True

    def do_partial(self, partial_datas):
        """ Makes partial picking and moves done.
        @param partial_datas : Dictionary containing details of partial picking
                          like partner_id, partner_id, delivfery_date,
                          delivery moves with product_id, product_qty, uom
        @return: Dictionary of values
        """
        if self._context is None:
            self._context = {}
        else:
            context = dict(self._context)
        res = {}
        move_obj = self.env['stock.move']
        product_obj = self.env['product.product']
        currency_obj = self.env['res.currency']
        uom_obj = self.env['uom.uom']
        sequence_obj = self.env['ir.sequence']
        # wf_service = odoo.netsvc.LocalService("workflow")
        # self.signal_workflow('action_assign')
        for pick in self:
            new_picking = None
            complete, too_many, too_few = [], [], []
            move_product_qty, prodlot_ids, product_avail, partial_qty, product_uoms = {}, {}, {}, {}, {}
            for move in pick.move_lines:
                if move.state in ('done', 'cancel'):
                    continue
                partial_data = partial_datas.get('move%s' % (move.id), {})
                product_qty = partial_data.get('product_qty', 0.0)
                move_product_qty[move.id] = product_qty
                product_uom = partial_data.get('product_uom', False)
                product_price = partial_data.get('product_price', 0.0)
                product_currency = partial_data.get('product_currency', False)
                prodlot_id = partial_data.get('prodlot_id')
                prodlot_ids[move.id] = prodlot_id
                product_uoms[move.id] = product_uom
                partial_qty[move.id] = uom_obj._compute_qty(
                    product_uoms[move.id], product_qty, move.product_uom.id)
                if move.product_qty == partial_qty[move.id]:
                    complete.append(move)
                elif move.product_qty > partial_qty[move.id]:
                    too_few.append(move)
                else:
                    too_many.append(move)

                # Average price computation
                if (pick.picking_type_id.code == 'in') and (move.product_id.cost_method == 'average'):
                    product = product_obj.browse(move.product_id.id)
                    move_currency_id = move.company_id.currency_id.id
                    context['currency_id'] = move_currency_id
                    qty = uom_obj._compute_qty(product_uom, product_qty, product.uom_id.id)

                    if product.id in product_avail:
                        product_avail[product.id] += qty
                    else:
                        product_avail[product.id] = product.qty_available

                    if qty > 0:
                        new_price = currency_obj.compute(product_currency, move_currency_id, product_price)
                        new_price = uom_obj._compute_price(product_uom, new_price, product.uom_id)
                        if product.qty_available <= 0:
                            new_std_price = new_price
                        else:
                            # Get the standard price
                            amount_unit = product.price_get(
                                'standard_price')[product.id]
                            new_std_price = ((amount_unit * product_avail[product.id])
                                             + (new_price * qty)) / (product_avail[product.id] + qty)
                        # Write the field according to price type field
                        temp = product.write({'standard_price': new_std_price})

                        # Record the values that were chosen in the wizard, so they can be
                        # used for inventory valuation if real-time valuation
                        # is enabled.
                        move.write({'price_unit': product_price, 'price_currency_id': product_currency})

            for move in too_few:
                product_qty = move_product_qty[move.id]
                if not new_picking:
                    new_picking_name = pick.name
                    type = pick.picking_type_id.code[:2]
                    self.write(
                        {'name': sequence_obj.next_by_code(
                            'stock.picking.%s' % (type)),
                        })
                    new_picking = self.copy(
                        {
                            'name': new_picking_name,
                            'move_lines': [],
                            'state': 'draft',
                        })
                if product_qty != 0:
                    defaults = {
                        'product_qty': product_qty,
                        # TODO: put correct uos_qty
                        'product_uos_qty': product_qty,
                        'picking_id': new_picking,
                        'state': 'assigned',
                        'move_dest_id': False,
                        'price_unit': move.price_unit,
                        'product_uom': product_uoms[move.id]
                    }
                    prodlot_id = prodlot_ids[move.id]
                    if prodlot_id:
                        defaults.update(prodlot_id=prodlot_id)
                    move_obj.copy(defaults)
                move.write(
                    {
                        'product_uom_qty': move.product_qty - partial_qty[move.id],
                        # TODO: put correct uos_qty
                        'product_uos_qty': move.product_qty - partial_qty[move.id],
                        'prodlot_id': False,
                        'tracking_id': False,
                    })

            if new_picking:
                zzz1 = move_obj.write({'picking_id': new_picking})
            for move in complete:
                defaults = {'product_uom': product_uoms[
                    move.id], 'product_qty': move_product_qty[move.id]}
                if prodlot_ids.get(move.id):
                    defaults.update({'prodlot_id': prodlot_ids[move.id]})
                move.write(defaults)
            for move in too_many:
                product_qty = move_product_qty[move.id]
                defaults = {
                    'product_qty': product_qty,
                    # TODO: put correct uos_qty
                    'product_uos_qty': product_qty,
                    'product_uom': product_uoms[move.id]
                }
                prodlot_id = prodlot_ids.get(move.id)
                if prodlot_ids.get(move.id):
                    defaults.update(prodlot_id=prodlot_id)
                if new_picking:
                    defaults.update(picking_id=new_picking)
                pick.write(defaults)

            # At first we confirm the new picking (if necessary)
            if new_picking:
                self.trg_validate(
                    self._uid, 'stock.picking', new_picking, 'button_confirm', self._cr)
                # Then we finish the good picking
                self.write({'backorder_id': new_picking})
                self.action_move()
                self.trg_validate(self._uid, 'stock.picking', new_picking, 'button_done', self._cr)
                self.trg_write('stock.picking')
                delivered_pack_id = new_picking
                back_order_name = self.browse(delivered_pack_id).name
                self.message_post(body=_("Back order <em>%s</em> has been <b>created</b>.") % (back_order_name))
            else:
                self.action_move()
                self.trg_validate(self._uid, 'stock.picking', pick.id, 'button_done', self._cr)
                delivered_pack_id = pick.id

            delivered_pack = self.browse(delivered_pack_id)
            res[pick.id] = {'delivered_picking': delivered_pack.id or False}

        return res

    def action_move(self):
        """Process the Stock Moves of the Picking

        This method is called by the workflow by the activity "move".
        Normally that happens when the signal button_done is received (button 
        "Done" pressed on a Picking view). 
        @return: True
        """
        for pick in self:
            todo = []
            for move in pick.move_lines:
                if move.state == 'draft':
                    self.env['stock.move'].action_confirm()
                    todo.append(move.id)
                elif move.state in ('assigned', 'confirmed'):
                    todo.append(move.id)
            if len(todo):
                self.env['stock.move'].action_done()
        return True


stock_picking()


class stock_partial_picking_line(models.TransientModel):

    def _tracking(self):
        res = {}
        for tracklot in self.browse:
            tracking = False
            if (tracklot.move_id.picking_id.type == 'in' and tracklot.product_id.track_incoming == True) or \
                    (tracklot.move_id.picking_id.type == 'out' and tracklot.product_id.track_outgoing == True):
                tracking = True
            res[tracklot.id] = tracking
        return res

    _name = "stock.partial.picking.line"
    _description = 'stock partial picking line'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', 'Product', required=True)
    quantity = fields.Float("Quantity", required=True)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure', required=True, ondelete='cascade')
    prodlot_id = fields.Many2one('stock.production.lot', 'Serial Number', ondelete='cascade')
    location_id = fields.Many2one('stock.location', 'Location', required=True, ondelete='cascade',
                                  domain=[('usage', '<>', 'view')])
    location_dest_id = fields.Many2one('stock.location', 'Dest. Location', required=True, ondelete='cascade',
                                       domain=[('usage', '<>', 'view')])
    move_id = fields.Many2one('stock.move', "Move", ondelete='cascade')
    wizard_id = fields.Many2one('stock.partial.picking', string="Wizard", ondelete='cascade')
    update_cost = fields.Boolean('Need cost update')
    cost = fields.Float("Cost", help="Unit Cost for this product line")
    currency = fields.Many2one('res.currency', string="Currency",
                               help="Currency in which Unit cost is expressed", ondelete='cascade')
    tracking = fields.Boolean(compute="_tracking", string='Tracking')

    @api.onchange('product_id')
    def onchange_product_id(self):
        uom_id = False
        if self.product_id:
            product = self.env['product.product'].browse(self.product_id)
            uom_id = product.uom_id.id
        return {'value': {'product_uom': uom_id}}


class stock_partial_picking(models.TransientModel):
    _name = "stock.partial.picking"
    # _rec_name = 'picking_id'
    _description = "Partial Picking Processing Wizard"

    def _hide_tracking(self):
        res = {}
        for wizard in self:
            res[wizard.id] = any([not (x.tracking) for x in wizard.move_ids])
        return res

    #     _columns = {
    #         'date': fields.Datetime('Date', required=True),
    #         'move_ids' : fields.one2many('stock.partial.picking.line', 'wizard_id', 'Product Moves'),
    #         'picking_id': fields.many2one('stock.picking', 'Picking', required=True, ondelete='CASCADE'),
    #         'hide_tracking': fields.function(_hide_tracking, string='Tracking', type='boolean', help='This field is for internal purpose. It is used to decide if the column production lot has to be shown on the moves or not.'),
    #      }
    date = fields.Datetime('Date', required=True)
    move_ids = fields.One2many(
        'stock.partial.picking.line', 'wizard_id', 'Product Moves')
    picking_id = fields.Many2one(
        'stock.picking', 'Picking', required=True, ondelete='cascade')
    hide_tracking = fields.Boolean(compute="_hide_tracking", string='Tracking',
                                   help='This field is for internal purpose. It is used to decide if the column production lot has to be shown on the moves or not.')

    @api.model
    def default_get(self, fields):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        res = super(stock_partial_picking, self).default_get(fields)
        picking_ids = self._context.get('active_ids', [])
        active_model = self._context.get('active_model')
        if not picking_ids or len(picking_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a
            # time
            return res
        assert active_model in (
            'stock.picking', 'stock.picking.in', 'stock.picking.out'), 'Bad context propagation'
        picking_id, = picking_ids
        if 'picking_id' in fields:
            res.update(picking_id=picking_id)
        if 'move_ids' in fields:
            picking = self.env['stock.picking'].browse(picking_id)

            moves = [self._partial_move_for(
                m) for m in picking.move_lines if m.state not in ('done', 'cancel')]
            res.update(move_ids=moves)
        if 'date' in fields:
            res.update(date=time.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
        return res

    def _partial_move_for(self, move):
        partial_move = {
            'product_id': move.product_id.id,
            'quantity': move.product_qty if move.state == 'assigned' else 0,
            'product_uom': move.product_uom.id,
            # 'prodlot_id' : move.prodlot_id.id,
            'move_id': move.id,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
        }
        if move.picking_type_id.code == 'incoming' and move.product_id.cost_method == 'average':
            partial_move.update(
                update_cost=True, **self._product_cost_for_average_update(move))
        return partial_move

    def do_partial(self):
        assert len(
            self._ids) == 1, 'Partial picking processing may only be done one at a time.'
        stock_picking = self.env['stock.picking']
        stock_move = self.env['stock.move']
        uom_obj = self.env['uom.uom']
        # partial = self.browse(cr, uid, ids[0], context=context)
        partial_data = {
            'delivery_date': self.date
        }
        picking_type = self.picking_id.picking_type_id.code
        for wizard_line in self.move_ids:
            line_uom = wizard_line.product_uom

            # Quantiny must be Positive
            if wizard_line.quantity < 0:
                raise UserError('Please provide proper Quantity.')

            # Compute the quantity for respective wizard_line in the line uom
            # (this jsut do the rounding if necessary)
            qty_in_line_uom = uom_obj._compute_qty(
                line_uom.id, wizard_line.quantity, line_uom.id)
            # qty_in_line_uom = uom_obj._compute_qty(cr, uid, line_uom.id, wizard_line.quantity, line_uom.id)
            if line_uom.factor and line_uom.factor != 0:
                if float_compare(qty_in_line_uom, wizard_line.quantity, precision_rounding=line_uom.rounding) != 0:
                    raise UserError(
                        'The unit of measure rounding does not allow you to ship "%s %s", only rounding of "%s %s" is accepted by the Unit of Measure.') % (
                              wizard_line.quantity, line_uom.name, line_uom.rounding, line_uom.name)
            move_id = wizard_line.move_id.id

            if move_id:
                # Check rounding Quantity.ex.
                # picking: 1kg, uom kg rounding = 0.01 (rounding to 10g),
                # partial delivery: 253g
                # => result= refused, as the qty left on picking would be 0.747kg and only 0.75 is accepted by the uom.
                initial_uom = wizard_line.move_id.product_uom
                # Compute the quantity for respective wizard_line in the
                # initial uom
                qty_in_initial_uom = uom_obj._compute_qty(
                    line_uom.id, wizard_line.quantity, initial_uom.id)
                without_rounding_qty = (
                                               wizard_line.quantity / line_uom.factor) * initial_uom.factor
                if float_compare(qty_in_initial_uom, without_rounding_qty,
                                 precision_rounding=initial_uom.rounding) != 0:
                    raise UserError(
                        'The rounding of the initial uom does not allow you to ship "%s %s", as it would let a quantity of "%s %s" to ship and only rounding of "%s %s" is accepted by the uom.') % (
                              wizard_line.quantity, line_uom.name,
                              wizard_line.move_id.product_qty - without_rounding_qty, initial_uom.name,
                              initial_uom.rounding, initial_uom.name)
            else:
                seq_obj_name = 'stock.picking.' + picking_type[:2]
                move_id = stock_move.create({'name': self.env['ir.sequence'].nect_by_code(seq_obj_name),
                                             'product_id': wizard_line.product_id.id,
                                             'product_qty': wizard_line.quantity,
                                             'product_uom': wizard_line.product_uom.id,
                                             # 'prodlot_id': wizard_line.prodlot_id.id,
                                             'location_id': wizard_line.location_id.id,
                                             'location_dest_id': wizard_line.location_dest_id.id,
                                             'picking_id': self.picking_id.id
                                             })
                stock_move.action_confirm()
            partial_data['move%s' % (move_id)] = {
                'product_id': wizard_line.product_id.id,
                'product_uom_qty': wizard_line.quantity,
                'product_uom': wizard_line.product_uom.id,
                # 'prodlot_id': wizard_line.prodlot_id.id,
            }
            if (picking_type == 'in') and (wizard_line.product_id.cost_method == 'average'):
                partial_data['move%s' % (wizard_line.move_id.id)].update(product_price=wizard_line.cost,
                                                                         product_currency=wizard_line.currency.id)
        stock_picking.do_partial(partial_data)
        return {'type': 'ir.actions.act_window_close'}


stock_partial_picking()


class mrp_production(models.Model):
    _inherit = 'mrp.production'

    def test_if_product(self):
        """
        @return: True or False
        """
        res = True
        for production in self:
            if not production.product_lines:
                if not self.action_compute([production.id]):
                    res = False
        return res


class hotel_restaurant_inventory(models.Model):
    _inherit = "hotel.restaurant.kitchen.order.tickets"
    _description = "Add BOM to restaurant module"
    state = fields.Selection([('draft', 'Draft'), ('in_process', 'Process'), ('done', 'Done'),
                              ('canceled', 'Cancel')], 'State', default='draft')

    def process_kot1(self):
        route_obj = self.env["stock.location.route"]
        data_list = []
        for kot_obj in self:
            if kot_obj.kot_list == []:
                raise UserError("There is no item in order list ... !")
            else:
                for order_record in kot_obj.kot_list:
                    if order_record.state == 'draft':
                        menu_card_obj = self.env["hotel.menucard"].browse(order_record.product_id.id)
                        bom_id = self.env['mrp.bom'].search([('name', '=', menu_card_obj.product_id.name)])
                        shop_obj = self.env['sale.shop'].browse(kot_obj.shop_id.id)
                        warehouse_id = self.env['stock.warehouse'].browse(shop_obj.warehouse_id.id)
                        location_id = warehouse_id.lot_stock_id.id
                        self.env.cr.execute("select route_id from stock_route_product where product_id = %s" % (
                            menu_card_obj.product_id.id))
                        record = [i[0] for i in self.env.cr.fetchall()]
                        for data in route_obj.browse(record):
                            data_list.append(data.name)
                        if 'Manufacture' in data_list and 'Make To Order' in data_list and (bom_id and bom_id[0]):
                            mrp_data = {
                                'origin': kot_obj.orderno,
                                'product_id': menu_card_obj.product_id.id,
                                'product_qty': order_record.item_qty,
                                'product_uom': menu_card_obj.uom_id.id,
                                'location_src_id': location_id,
                                'location_dest_id': location_id,
                            }
                            mrp_id = self.env['mrp.production'].create(mrp_data)
                            if mrp_id:
                                m_order = self.env['mrp.production'].browse(mrp_id)
                                message = _("Manufacturing Order '%s' has been created.") % (m_order.name)
                                self.log(kot_obj.id, message)
                        order_record.write({'state': 'in_process'})
        self.write({'state': 'in_process'})

    def done_kot1(self):
        self_obj = self
        for order_list in self_obj.kot_list:
            if order_list.state == "in_process":
                bom_wizard_obj = self.env['mrp.product.produce']
                bom_obj = self.env['mrp.production']
                bom_record = bom_obj.search([('origin', '=', self_obj.orderno)])
                for b_id in bom_record:
                    bom_browse = bom_obj.browse(b_id)
                    if bom_browse.product_id.name == order_list.product_id.name:
                        # If values is True then call action_confirm or
                        # action_ready method
                        if bom_obj.test_if_product():
                            bom_obj.action_confirm()
                            bom_obj.force_production()
                        bom_obj.action_ready()
                        bom_obj.action_in_production()
                        context = {'lang': 'en_US', 'tz': False, 'uid': self._uid, 'active_model': 'mrp.production',
                                   'active_ids': [
                                       b_id], 'search_default_ready': 1, 'active_id': b_id}
                        product_qty = bom_wizard_obj._get_product_qty()
                        bom_obj.action_produce(product_qty, 'consume_produce')
                        bom_obj.action_production_end()
            order_list.write({'state': 'done'})
        self.write({'state': 'done'})
        return True

    def cancel_kot1(self):
        self.write({'state': 'canceled'})
        return True


class hotel_restaurant_order(models.Model):
    _inherit = "hotel.restaurant.order"
    _description = "Includes Hotel Restaurant Order"

    def confirm_order(self):
        for obj in self:
            if obj.order_list == []:
                raise Warning("There is no item in order ... !")
            else:
                for line in obj.order_list:
                    menu_card_obj = self.env["hotel.menucard"].browse(line.product_id.id)
                    for data in menu_card_obj.route_ids:
                        for info in data.rule_ids:  # pull_ids
                            if info.action == 'manufacture':
                                mrp_id = self.env["mrp.bom"].search([('product_id', '=', menu_card_obj.product_id.id)])

        return super(hotel_restaurant_order, self).confirm_order()

    def create_invoice(self):
        stock_obj = self.env['stock.picking']
        stock_wizard_obj = self.env['stock.partial.picking']
        for self_obj in self:
            stock_brw = self.env['stock.picking'].search(
                [('origin', '=', self_obj.order_no)])
            print('------------- {} '.format(stock_brw))
            if stock_brw:
                if stock_brw.state != 'done':
                    """Here we are manually calling stock picking method to create invoice"""
                    move_ids = stock_brw.move_ids_without_package
                    for move_id in move_ids:
                        move_id.write({'quantity_done': move_id.product_uom_qty})
                    response = stock_brw.button_validate()
                    # print('response1-------------- {}'.format(response))
                    ss = stock_brw.draft_force_assign()
                    # print('ss-------------- {}'.format(ss))
                    process = stock_brw.action_process()
                    # print('process-------------- {}'.format(process))

                """And in below call the wizard method to maintain product stock and confirm delivery order"""
                stock_brw_list = [each.id for each in stock_brw]
                context = {'active_model': 'stock.picking.in',
                           'active_ids': stock_brw_list, 'active_id': stock_brw[0].id}
                res = self.env['stock.partial.picking'].with_context(
                    context).default_get(['date', 'picking_id', 'move_ids'])

                move_ids = []
                for move in res['move_ids']:
                    move_ids.append((0, 0, move))
                res['move_ids'] = move_ids
                stock_partial_pick_id = self.env['stock.partial.picking'].create(res)
                stock_partial_pick_id.do_partial()
                stock_brw.write({'state': 'done'})
        return super(hotel_restaurant_order, self).create_invoice()

    def generate_kot(self):
        for self_obj in self:
            if self_obj.partner_id:
                addr = self_obj.partner_id.address_get(
                    ['delivery', 'invoice', 'contact'])
                if addr['invoice']:
                    partner_addr = addr['invoice']
                else:
                    res_add = self.env['res.partner.address'].search([('partner_id', '=', self_obj.partner_id.id)])
                    if res_add:
                        res_browse = self.env['res.partner.address'].browse(res_add)
                        partner_addr = res_add.id
            stock_brw = self.env['stock.picking'].search([('origin', '=', self_obj.order_no)])
            picking_id = None
            if stock_brw:
                for order_items in self_obj.order_list:

                    product_id = self.env["hotel.menucard"].browse(order_items.product_id.id).product_id.id
                    move_id = self.env['stock.move'].search(
                        [('product_id', '=', product_id), ('picking_id', '=', stock_brw.id)])
                    # print('move_id : {}'.format(move_id))
                    if move_id:
                        if not order_items.price_subtotal:
                            move_id.write({'product_uom_qty': float(order_items.item_qty)})
                        else:
                            total_qty = 0
                            order_list = self.env['hotel.restaurant.order.list'].search(
                                [('product_id', '=', self.env["hotel.menucard"].browse(order_items.product_id.id).id),
                                 ('o_list', '=', self_obj.id)])
                            # print('order_list : {}'.format(order_list))
                            for order_qty in order_list:
                                total_qty = total_qty + int(order_qty.item_qty)
                            brw = move_id.write({'product_uom_qty': total_qty, })

                    else:
                        customer_id = self_obj.partner_id.property_stock_customer.id
                        shop_obj = self.env['sale.shop'].browse(self_obj.shop_id.id)
                        warehouse_id = self.env['stock.warehouse'].browse(shop_obj.warehouse_id.id)
                        add = warehouse_id.lot_stock_id.id
                        product_id = self.env["hotel.menucard"].browse(order_items.product_id.id).product_id
                        # picking_type_ids = self.env["stock.picking.type"].search(
                        #     [('code', '=', 'outgoing'), ('name', '=', 'Delivery Orders')])
                        picking_type_ids = shop_obj.picking_type_id if shop_obj else None
                        move_line_data = {
                            'name': self_obj.order_no + ': ' + (order_items.product_id.name or ''),
                            'picking_id': stock_brw.id,
                            'picking_type_id': picking_type_ids.id,
                            'product_id': product_id.id,
                            'product_uom_qty': order_items.item_qty,
                            'product_uom': product_id.uom_id.id,
                            'location_id': warehouse_id.lot_stock_id.id,
                            'location_dest_id': customer_id,
                            # 'state': 'assigned',
                        }
                        pick_line = self.env['stock.move'].create(move_line_data)
                        pick_line._action_assign()

            else:
                # picking_type_ids = self.env["stock.picking.type"].search(
                #     [('code', '=', 'outgoing'), ('name', '=', 'Delivery Orders')])

                customer_id = self_obj.partner_id.property_stock_customer.id
                shop_obj = self.env['sale.shop'].browse(self_obj.shop_id.id)
                picking_type_id = shop_obj.picking_type_id if shop_obj else None
                warehouse_id = self.env['stock.warehouse'].browse(shop_obj.warehouse_id.id)
                # add = warehouse_id.lot_stock_id.id

                ############################# UPdated code to create stock.picking object @###############
                if picking_type_id:
                    picking = self.env['stock.picking'].create({
                        'location_id': warehouse_id.lot_stock_id.id,
                        'location_dest_id': customer_id,
                        # 'partner_id': self.test_partner.id,
                        'picking_type_id': picking_type_id.id,
                        'immediate_transfer': False,
                        'origin': self_obj.order_no,
                    })
                    for order_items in self_obj.order_list:
                        menu_card_obj1 = self.env["hotel.menucard"].browse(order_items.product_id.id)
                        move_receipt_1 = self.env['stock.move'].create({
                            'name': self_obj.order_no + ': ' + (order_items.product_id.name or ''),
                            'picking_id': picking.id,
                            'picking_type_id': picking_type_id.id,
                            'product_id': menu_card_obj1.product_id.id,
                            'product_uom_qty': order_items.item_qty,
                            'product_uom': menu_card_obj1.uom_id.id,
                            'location_id': warehouse_id.lot_stock_id.id,
                            'location_dest_id': customer_id,
                        })
                        move_receipt_1._action_assign()

                    # picking.action_confirm()
                #############################$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ @###############

        return super(hotel_restaurant_order, self).generate_kot()


# this code is updated by dayanand


class hotel_reservation_order(models.Model):
    _inherit = "hotel.reservation.order"
    _description = "Includes Hotel Reservation Order"

    def confirm_order(self):
        # print("\n\n\n\n****confirm in hotel_reservation_order****")
        for obj in self:
            if obj.order_list == []:
                # print("iffffff")
                raise Warning("There is no item in order ... !")
            else:
                # print("elseee")
                for line in obj.order_list:
                    menu_card_obj = self.env["hotel.menucard"].browse(line.product_id.id)
                    # print("menu_card_obj  ", menu_card_obj)
                    for data in menu_card_obj.route_ids:
                        # print("dataaaaaaaa", data)
                        for info in data.rule_ids:
                            # print("infooooo ", info)
                            # print("infooooo action ", info.action)
                            if info.action == 'manufacture':
                                mrp_id = self.env["mrp.bom"].search([('product_id', '=', menu_card_obj.product_id.id)])
                                # print("Mrp id ", mrp_id)

        return super(hotel_reservation_order, self).confirm_order()

    def create_invoice(self):
        stock_obj = self.env['stock.picking']
        stock_wizard_obj = self.env['stock.partial.picking']
        for self_obj in self:
            stock_brw = self.env['stock.picking'].search([('origin', '=', self_obj.order_number)])
            # print("stock_brw---", stock_brw)
            # print("stock_brw----------------", stock_brw.id)
            if stock_brw:
                """Here we are manually calling stock picking method to create invoice"""
                ss = stock_brw.draft_force_assign()
                # print("sssssssssssssssssss", ss)

                aa = stock_brw.action_process()
                # print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", aa)
                """And in below call the wizard method to maintain product stock and confirm delivery order"""
                stock_brw_list = [each.id for each in stock_brw]
                context = {'active_model': 'stock.picking.in',
                           'active_ids': stock_brw_list, 'active_id': stock_brw.id}
                # print('\n\nsending contextttt========', context)
                res = self.env['stock.partial.picking'].with_context(context).default_get(
                    ['date', 'picking_id', 'move_ids'])
                # print("resssssss", res)

                move_ids = []
                for move in res['move_ids']:
                    # print("\n\n mobbbbb", move)
                    move_ids.append((0, 0, move))

                res['move_ids'] = move_ids
                # print("res['move_idsssssssssss']  ", res['move_ids'])
                stock_partial_pick_id = self.env['stock.partial.picking'].create(res)
                # print("stock_partial_pick_idddddddddddd  ", stock_partial_pick_id)
                stock_partial_pick_id.do_partial()

                dd = stock_obj.write({'state': 'done'})
                # print('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
        return super(hotel_reservation_order, self).create_invoice()

    def reservation_generate_kot(self):
        for self_obj in self:
            if self_obj.partner_id:
                # print("\n\n\nself_obj.partner_idddd", self_obj.partner_id)
                addr = self_obj.partner_id.address_get(['delivery', 'invoice', 'contact'])
                # print("addressssssssssssssssssss :", addr)
                if addr['invoice']:
                    partner_addr = addr['invoice']
                    # print("partner invoice address", partner_addr)
                    # print("partner Id", self_obj.partner_id.id)
                else:
                    # print("partner Id", self_obj.partner_id.id)
                    res_add = self.env['res.partner.address'].search([('partner_id', '=', self_obj.partner_id.id)])
                    # print("resssssssssss_add", res_add)
                    if res_add:
                        res_browse = self.env['res.partner.address'].browse(res_add)
                        # print("res_browseeeeeeeeeeeee", res_browse, res_browse[0].id, res_browse[0], res_browse.id)
                        partner_addr = res_browse.id
                        # print("partner_addrrrrrrrrrr", partner_addr)
            # print("self_obj.order_noooooooooo", self_obj.order_number)
            stock_brw = self.env['stock.picking'].search([('origin', '=', self_obj.order_number)])
            if stock_brw:
                # print("\n\n\nstock brw", stock_brw)
                for order_items in self_obj.order_list:
                    product_obj = self.env['hotel.menucard'].browse(order_items.product_id.id)
                    product_id = product_obj.product_id.id
                    # print("brw product id", order_items.product_id[0].id)
                    # print("produuuct id", product_id)
                    # print("stock browseeeeee", stock_brw.id)
                    move_id = self.env['stock.move'].search(
                        [('product_id', '=', product_id), ('picking_id', '=', stock_brw.id)])
                    # print("Moveee id", move_id)

                    if move_id:
                        if not order_items.total:
                            # print("!!!!!!!!!!1order_items.item_qty:::::::::::", order_items.item_qty)
                            move_id.update({'product_uom_qty': order_items.item_qty})
                            # print("move_id:::::::::::::::::::---------------", move_id)
                        else:
                            total_qty = 0
                            # print("order_items.product_id.id", order_items.product_id.id, "self_obj.order_no",
                            #       self_obj.order_no)
                            order_list = self.env['hotel.restaurant.order.list'].search(
                                [('product_id', '=', order_items.product_id.id), ('resno', '=', self_obj.order_no)])
                            # print("orderrrrrrr_list order_no", order_list)
                            for order_qty in order_list:
                                # print("order_qty", order_qty)
                                p_qty = order_qty.item_qty
                                # print("p_qty", p_qty)
                                total_qty = total_qty + int(p_qty)
                                # print("total_qty", total_qty)
                            brw = move_id.write({'product_uom_qty': total_qty, })
                            order_list = self.env['hotel.restaurant.order.list'].search(
                                [('product_id', '=', order_items.product_id.id), ('resno', '=', self_obj.order_number)])
                            # print("Order Listtt order_number", order_list)
                            for order_qty in order_list:
                                p_qty = order_qty.item_qty

                                total_qty = total_qty + int(p_qty)
                            move_id.write({'product_uom_qty': total_qty, })
                    else:
                        customer_id = self_obj.partner_id.property_stock_customer.id
                        shop_obj = self.env['sale.shop'].browse(self_obj.shop_id.id)
                        # print("shop_obj", shop_obj)
                        # print("shop_obj.warehouse_id.id", shop_obj.warehouse_id.id)
                        warehouse_id = self.env['stock.warehouse'].browse(shop_obj.warehouse_id.id)
                        # print("warehouse_id.lot_stock_id.id", warehouse_id.lot_stock_id.id)
                        add = warehouse_id.lot_stock_id.id
                        # print("add", add)
                        move_line_data = {
                            'name': self_obj.order_number + ': ' + (order_items.product_id.name or ''),
                            'picking_id': stock_brw.id,
                            'product_id': product_id,
                            'product_uom_qty': order_items.item_qty,
                            'product_uom': order_items.product_id.uom_id.id,
                            'location_id': add,
                            'location_dest_id': customer_id,
                            'state': 'assigned',
                        }
                        # print("move_line_data", move_line_data)
                        pick_line = self.env['stock.move'].create(move_line_data)
                        # print("pick_line===", pick_line)
            else:
                customer_id = self_obj.partner_id.property_stock_customer.id
                # print("customer_id", customer_id)
                # picking_type_ids = self.env["stock.picking.type"].search(
                #     [('code', '=', 'outgoing'), ('name', '=', 'Delivery Orders')])
                # print("picking_type_idssssssssssssssss", picking_type_ids)
                # print("picking_type_idssssssss", picking_type_ids[0].id)
                # print("picking_type_idsssssssssssssssssss", picking_type_ids[0])
                shop_obj = self.env['sale.shop'].browse(self_obj.shop_id.id)
                picking_type_ids = shop_obj.picking_type_id if shop_obj else None
                # print("shop_obj", shop_obj)
                # print("shop_obj.warehouse_id.id", shop_obj.warehouse_id.id)
                warehouse_id = self.env['stock.warehouse'].browse(shop_obj.warehouse_id.id)
                # print("warehouse_id.lot_stock_id.id", warehouse_id.lot_stock_id.id)
                add = warehouse_id.lot_stock_id.id
                # print("add", add)
                if picking_type_ids:
                    picking_data = {
                        'name': self.env['ir.sequence'].next_by_code('stock.picking.out'),
                        'origin': self_obj.order_number,
                        'date': self_obj.date1,
                        'state': 'draft',
                        'picking_type_id': picking_type_ids.id,
                        'location_id': add,
                        'location_dest_id': customer_id,
                    }
                    # print("picking_dataddddd", picking_data)
                picking_id = self.env['stock.picking'].create(picking_data)
                # print("picking_idssssss", picking_id.id)
                pick_id = self.env['stock.picking'].browse(picking_id)
                # print("pick_id", pick_id)
                product_list = self.env['hotel.restaurant.order.list'].browse(picking_id)
                # print("product_list", product_list)
                for order_items in self_obj.order_list:
                    # print("\n\norder_items")
                    # print("order_items.product_id.id--", order_items.product_id.id)
                    menu_card_obj1 = self.env["hotel.menucard"].browse(order_items.product_id.id)
                    # print("menu_card_obj1-- ", menu_card_obj1)
                    move_data = {
                        'name': self_obj.order_number + ': ' + (order_items.product_id.name or ''),
                        'picking_id': picking_id.id,
                        'product_id': menu_card_obj1.product_id.id,
                        'product_uom_qty': order_items.item_qty,
                        'product_uom': menu_card_obj1.uom_id.id,
                        'location_id': add,
                        'location_dest_id': customer_id,
                        'state': 'assigned',
                    }
                    # print("move_dataaaaaaaa ", move_data)
                    picking_line = self.env['stock.move'].create(move_data)
                    # print("picking_lineeeeeeeeeee", picking_line)
                    pick_id = self.env['stock.picking'].browse(picking_id)
                    # print("pick_idddddd", pick_id)
        return super(hotel_reservation_order, self).reservation_generate_kot()


hotel_reservation_order()


class hotel_restaurant_inventory_orderlist(models.Model):
    _inherit = "hotel.restaurant.order.list"
    _description = "Add restaurant inventory"

    def _table_number(self):
        res = {}
        table_list = ' '
        for self_obj in self:
            if table_list:
                table_list = ' '
            if self_obj.kot_order_list:
                for table_nos in self_obj.kot_order_list.tableno:
                    table_list = table_list + "  " + table_nos.name + ","
            res[self_obj.id] = table_list[:-1]
            self_obj.tableno = res[self_obj.id]

    def _room_number(self):
        # print("\n\n***_room_number***")
        res = {}
        room_list = ' '
        for self_obj in self:
            if room_list:
                room_list = ' '
            if self_obj.kot_order_list:
                room = self_obj.kot_order_list.room_no
                if room:
                    room_list = room_list + "  " + str(room) + ","
            res[self_obj.id] = room_list[:-1]
            # print("res[self_obj.id]--------", res[self_obj.id])
            self_obj.room_no = res[self_obj.id]
        # return res

    #

    state = fields.Selection([('draft', 'Draft'), ('in_process', 'Process'), ('done', 'Done'),
                              ('canceled', 'Cancel')], 'State', default='draft', required=True,
                             ondelete='cascade')
    order_no = fields.Char(related='kot_order_list.orderno', string='KOT Number', store=True)
    ordernobot = fields.Char(related='kot_order_list.ordernobot', string='BOT Number', store=True)
    shop_id = fields.Many2one(related='kot_order_list.shop_id', string='Shop', store=True)
    resno = fields.Char(related='kot_order_list.resno', string='Order Number', store=True)
    date = fields.Date(related='kot_order_list.kot_date', string='Date', store=True)
    waiter_name = fields.Char(related='kot_order_list.w_name', string='Waiter Name', store=True)
    tableno = fields.Char(compute='_table_number', string='Table Number')
    room_no = fields.Char(compute='_room_number', string='Room Number')
    product_nature = fields.Selection([('kot', 'KOT'), ('bot', 'BOT')], 'Product Nature')
    picking_id = fields.Many2one('stock.picking', string='Picking', invisible=True)

    def process_kot(self):
        # print("\n\n\n\n***process_kot***")
        data_list = []
        route_obj = self.env["stock.location.route"]
        for self_obj in self:
            if self_obj.product_id:
                # print("self_obj.product_id", self_obj.product_id)
                menu_card_obj = self.env["hotel.menucard"].browse(self_obj.product_id.id)
                # print("menu_card_objjjjjjjjjjj------------", menu_card_obj.product_id.id)
                bom_id = self.env['mrp.bom'].search([('product_id', '=', menu_card_obj.product_id.id)])
                # print("bom_id", bom_id)
                shop_obj = self.env['sale.shop'].browse(self_obj.kot_order_list.shop_id.id)
                # print("shop_objjj", shop_obj)
                warehouse_id = self.env['stock.warehouse'].browse(shop_obj.warehouse_id.id)
                # print("warehouse_iddd", warehouse_id)
                # print("addresssssssss", warehouse_id)
                location_id = warehouse_id.lot_stock_id.id
                # print("location_id", location_id)

                self._cr.execute("select route_id from stock_route_product where product_id = %s" % (
                    menu_card_obj.product_id.id))
                record = [i[0] for i in self._cr.fetchall()]
                # print("recordddddddd", record)
                for data in self.env["stock.location.route"].browse(record):
                    data_list.append(data.name)

                if 'Manufacture' in data_list and 'Make To Order' in data_list and (bom_id and bom_id.id):
                    mrp_data = {
                        'origin': self_obj.kot_order_list.orderno,
                        'product_id': menu_card_obj.product_id.id,
                        'product_qty': self_obj.item_qty,
                        'product_uom': menu_card_obj.uom_id.id,
                        'location_src_id': location_id,
                        'location_dest_id': location_id,
                    }
                    # print("mrp_data", mrp_data)
                    mrp_id = self.env['mrp.production'].create(mrp_data)
                    # print("mrp_id", mrp_id)
                    if mrp_id:
                        m_order = self.env['mrp.production'].browse(mrp_id)
                        # print("m_orderrrrrrr", m_order)
                        message = _("Manufacturing Order '%s' has been created.") % (m_order.name)

                picking_type_id = self.env['stock.picking.type'].search(
                    [('code', '=', 'outgoing'), ('sequence_code', '=', 'OUT'),
                     ('warehouse_id', '=', warehouse_id.id),
                     ('company_id', '=', self.env.company.id)])

                dest_location_id = self.env['stock.location'].sudo().search([('name', '=', 'Customers')])

                picking_id = self.env['stock.picking'].create({
                    'location_id': location_id,
                    'location_dest_id': dest_location_id.id,
                    'picking_type_id': picking_type_id.id,
                    'move_lines': [(0, 0, {
                        'name': 'KOT Item',
                        'product_id': menu_card_obj.product_id.id,
                        'product_uom': menu_card_obj.product_id.uom_id.id,
                        'product_uom_qty': self_obj.item_qty,
                        'location_id': location_id,
                        'location_dest_id': dest_location_id.id,
                    })]
                })

                self.write({
                    'picking_id': picking_id.id,
                    'state': 'in_process',
                })
                self.picking_id.action_confirm()
            # print("self_obj.kot_order_list=======================", self_obj.kot_order_list)
            if self_obj.kot_order_list.state == 'draft':
                return self_obj.kot_order_list.write({'state': 'in_process'})

    def done_kot(self):
        # print("\n\n\n\n***done_kot***")
        self_obj = self
        # if self_obj.product_id:

        # bom_wizard_obj = self.env['mrp.product.produce']
        bom_obj = self.env['mrp.production']
        # print("iddddddddddddd", self_obj.kot_order_list.orderno)
        bom_record = bom_obj.search([('origin', '=', self_obj.kot_order_list.orderno)])
        # print("bom_recordddddddddd", bom_record)
        for b_id in bom_record:
            bom_browse = self.env['mrp.production'].browse(b_id.id)
            # print("bom_browse", bom_browse)
            # if bom_browse.product_id.name == self_obj.product_id.name:
            # print("bom_browse.product_id.name == self.product_id.name", bom_browse.product_id.name,
            #       self.product_id.name)
            if bom_browse.product_id.name == self.product_id.name:
                # If values is True then call action_confirm or action_ready
                # method
                if bom_obj.test_if_product():
                    bom_obj.action_confirm()
                    bom_obj.force_production()
                bom_obj.action_ready()
                bom_obj.action_in_production()
                context = {'lang': 'en_US', 'tz': False, 'uid': self.env.uid, 'active_model': 'mrp.production',
                           'active_ids': [
                               b_id], 'search_default_ready': 1, 'active_id': b_id}

                # print("contexttttt", context)
                bom_wizard_obj = self.env['mrp.product.produce']
                product_qty = bom_wizard_obj.with_context(
                    context)._get_product_qty()
                # print("product_qty---------", product_qty)
                bom_obj.action_produce(product_qty, 'consume_produce')
                bom_obj.action_production_end()

        kot_done = True
        if self_obj.kot_order_list:
            kot_obj = self.env['hotel.restaurant.kitchen.order.tickets'].browse(
                self_obj.kot_order_list.id)
            # print("kot_obj====", kot_obj)
            for kot_state_obj in kot_obj.kot_list:
                if kot_state_obj.id != self._ids[0]:
                    if kot_state_obj.state != 'done':
                        kot_done = False
            # print("self_obj.kot_order_list===========", self_obj.kot_order_list)
            if kot_done:
                self_obj.kot_order_list.write({'state': 'done'})

        # if self.picking_id:
        #     if self.picking_id.state != 'done':
        #         self.picking_id.action_assign()
        #         for rec in self.picking_id.move_ids_without_package:
        #             if rec.forecast_availability != rec.product_uom_qty:
        #                 raise UserError(_("You are trying to order %s quantity, but the current quantity is %s for %s "
        #                                   "product. Please Update the Quantity or Validate the picking from Delivery",
        #                                   self.item_qty, rec.forecast_availability, rec.product_id.name))
        #             rec.quantity_done = rec.forecast_availability
        #         self.picking_id.with_context(skip_immediate=True).button_validate()

        self.write({'state': 'done'})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_view_kot_delivery(self):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        if self.picking_id:
            action['domain'] = [('id', '=', self.picking_id.id)]
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['views'] = form_view
            action['res_id'] = self.picking_id.id
        return action


class ProductUoM(models.Model):
    _inherit = 'uom.uom'
    _description = 'Product Unit of Measure'
    _order = "name"

    def _compute_qty(self, from_uom_id, qty, to_uom_id=False, round=True, rounding_method='UP'):
        # print("from_uom_idiiiiiiiiiiiiiiiiiiiiii", from_uom_id, qty, to_uom_id)
        if not from_uom_id or not qty or not to_uom_id:
            return qty
        uoms = self.browse([from_uom_id, to_uom_id])
        if uoms[0].id == from_uom_id:
            from_unit, to_unit = uoms[0], uoms[-1]
        else:
            from_unit, to_unit = uoms[-1], uoms[0]
        # print("from_unitttttttttttttttttttttttttttttttttt", from_unit, to_unit)
        return self._compute_qty_obj(from_unit, qty, to_unit, round=round, rounding_method=rounding_method)

    def _compute_qty_obj(self, from_unit, qty, to_unit, round=True, rounding_method='UP'):
        if self._context is None:
            self._context = {}
        if from_unit.category_id.id != to_unit.category_id.id:
            if self._context.get('raise-exception', True):
                raise UserError(_(
                    'Conversion from Product UoM %s to Default UoM %s is not possible as they both belong to different Category!.') % (
                                    from_unit.name, to_unit.name))
            else:
                return qty
        amount = qty / from_unit.factor
        if to_unit:
            amount = amount * to_unit.factor
            if round:
                amount = float_round(
                    amount, precision_rounding=to_unit.rounding, rounding_method=rounding_method)
        return amount
