from odoo import fields, models, api
import time
# from mx import DateTime
import datetime
from odoo.exceptions import ValidationError, Warning


class hotel_laundry_picking(models.TransientModel):
    """Hotel laundry picking is use to show all the product according to service in picking generation"""
    _name = 'hotel.laundry.picking'
    _description = 'Return Picking'
    product_return_moves = fields.One2many('hotel.laundry.picking.memory', 'wizard_id', 'Moves')
    invoice_state = fields.Selection([('2binvoiced', 'To be refunded/invoiced'), ('none', 'No invoicing')], 'Invoicing',required=True)

    
    def default_get(self):

        result1 = []
        context = self._context or {}
        res = super(hotel_laundry_picking, self).default_get(fields)
        laundry_record_id = context and context.get('active_id', False) or False
        laundry_obj=self.pool.get('laundry.management')
        pick_obj = self.pool.get('stock.picking')
        laudnry_id=laundry_obj.browse(laundry_record_id)
        record_ids=pick_obj.search([('origin','=',laudnry_id.name)])
        # print("records",record_ids)
        for rec in record_ids:
            # print("rec",rec)
            records=pick_obj.browse(rec)
            record_id = False
            if records.type=='out':
                record_id=records.id
            if record_id:
                # print("out type records",record_id)
                pick = pick_obj.browse(record_id, context=context)
                if pick:
                    return_history = self.get_return_history(record_id, context)
                    for line in pick.move_lines:
                        qty = line.product_qty - return_history[line.id]
                        if qty > 0:
                            result1.append({'product_id': line.product_id.id, 'quantity': qty,'move_id':line.id})
                    
                    if 'invoice_state' in fields:
                        if pick.invoice_state=='invoiced':
                            res.update({'invoice_state': '2binvoiced'})
                        else:
                            res.update({'invoice_state': 'none'})        
                    if 'product_return_moves' in fields:
                        res.update({'product_return_moves': result1})
        return res
    
    
    def get_return_history(self,pick_id):
        """ 
         Get  return_history.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param pick_id: Picking id
         @param context: A standard dictionary
         @return: A dictionary which of values.
        """
        pick_obj = self.pool.get('stock.picking')
        pick = pick_obj.browse(pick_id,)
        return_history = {}
        for m  in pick.move_lines:
            if m.state == 'done':
                return_history[m.id] = 0
                for rec in m.move_history_ids2:
                    return_history[m.id] += (rec.product_qty * rec.product_uom.factor)
            else:
                raise Warning(('Warning !'), ("Please process the delivery order shipment-%s first!")%(pick.name)) 
        return return_history
    
    
    def do_method(self):
        context = self._context or {}
        laundry_record_id = context and context.get('active_id', False) or False
        laundry_obj=self.pool.get('laundry.management')
        laundry_obj.write(laundry_record_id,{'state':'laundry_returned'})
        return {'type': 'ir.actions.act_window_close'}
    
    
    def create_returns(self):
        """ 
         Creates return picking.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: List of ids selected
         @param context: A standard dictionary
         @return: A dictionary which of fields with values.
        """
        count=0
        pick = ""
        context = self._context or {}
        laundry_record_id = context and context.get('active_id', False) or False
        laundry_obj=self.pool.get('laundry.management')
        pick_obj = self.pool.get('stock.picking')
        laundry_id=laundry_obj.browse(laundry_record_id)
        
        if laundry_id.request_type=='from_room':
            count=-1
        
        record_ids=pick_obj.search([('origin','=',laundry_id.name)])
        for rec in record_ids:
            records=pick_obj.browse(rec)
            count=count+1
            if records.type=='out':
                record_id=records.id
                if record_id:
                    pick = pick_obj.browse(record_id, context=context)
        move_obj = self.pool.get('stock.move')
        pick_obj = self.pool.get('stock.picking')
        uom_obj = self.pool.get('uom.uom')
        data_obj = self.pool.get('hotel.laundry.picking.memory')
        wf_service = netsvc.LocalService("workflow")
        
        data = self.read( context=context)
        new_picking = None
        date_cur = time.strftime('%Y-%m-%d %H:%M:%S')
        set_invoice_state_to_none = True
        returned_lines = 0
        
#        Create new picking for returned products
        if pick:
            if pick.type=='out':
                new_type = 'in'
            elif pick.type=='in':
                new_type = 'out'
            else:
                new_type = 'internal'
                # print("internal==========================new_type=====================",new_type)
            new_picking = pick_obj.copy( pick.id, {'name':'%s-return/%s' % (pick.name,count),
            'move_lines':[], 'state':'draft', 'type':new_type,
            'date':date_cur, 'invoice_state':data['invoice_state'],})
            # print("new_picking===========================================================",new_picking)
        
        val_id = data['product_return_moves']
        for v in val_id:
            data_get = data_obj.browse(v, context=context)
            mov_id = data_get.move_id.id
            new_qty = data_get.quantity
            move = move_obj.browse(mov_id, context=context)
            # print("move===================================================",move)
            if move.location_dest_id:
                new_location = move.location_dest_id.id
            # print("move=================================111111111111==================",move)
            if move.product_qty:   
                returned_qty = move.product_qty
            # print("move==================================2222222222222=================",move)
            if move.move_history_ids2:
                for rec in move.move_history_ids2:
                    returned_qty -= rec.product_qty
            # print("move====================================33333333333===============",move)
            if returned_qty != new_qty:
                set_invoice_state_to_none = False
            if new_qty:
                returned_lines += 1
                new_move=move_obj.copy(move.id, {
                    'product_qty': new_qty,
                    'product_uos_qty': uom_obj._compute_qty(move.product_uom.id,
                        new_qty, move.product_uos.id),
                    'picking_id':new_picking, 'state':'draft',
                    'location_id':new_location, 'location_dest_id':move.location_id.id,
                    'date':date_cur,})
                move_obj.write([move.id], {'move_history_ids2':[(4,new_move)]})
        if not returned_lines:
            laundry_obj.write(laundry_record_id,{'state':'laundry_returned'})
            raise Warning(('Warning !'), ("Please specify at least one non-zero quantity!"))

        if set_invoice_state_to_none:
            pick_obj.write([pick.id], {'invoice_state':'none'})
        wf_service.trg_validate( 'stock.picking', new_picking, 'button_confirm', cr)
        pick_obj.force_assign([new_picking], context)
        # Update view id in context, lp:702939
        view_list = {
                'out': 'view_picking_out_tree',
                'in': 'view_picking_in_tree',
                'internal': 'vpicktree',
            }
        data_obj = self.pool.get('ir.model.data')
        res = data_obj.get_object_reference('stock', view_list.get(new_type, 'vpicktree'))
        context.update({'view_id': res and res[1] or False})
        
        
        self._cr.execute('insert into laundry_order_picking_rel (laundry_order_id,picking_id) values (%s,%s)', (laundry_id.id, new_picking))
        return {
            'domain': "[('id', 'in', ["+str(new_picking)+"])]",
            'name': 'Picking List',
            'view_type':'form',
            'view_mode':'tree,form',
            'res_model':'stock.picking',
            'type':'ir.actions.act_window',
            'context':context,
        }


class hotel_laundry_picking_memory(models.TransientModel):
    _name = 'hotel.laundry.picking.memory'
    _description ='Hotel Laundry Picking Memory'
    
    product_id = fields.Many2one('product.product', string="Product", required=True)
    quantity = fields.Float("Quantity", required=True)
    wizard_id = fields.Many2one('hotel.laundry.picking', string="Wizard")
    move_id = fields.Many2one('stock.move', "Move")
