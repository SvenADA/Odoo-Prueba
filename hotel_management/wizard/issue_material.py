# -*- encoding: utf-8 -*-

from odoo import fields,models, api
from odoo.tools.translate import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time


class rr_housekeeping_wizard(models.TransientModel):
    _name = 'rr.housekeeping.wizard'
    _description = 'rr_housekeeping_wizard'
    
    rr_line_ids = fields.One2many('rr.housekeeping.line.wizard','rr_line_id','Repair / Replacement Info',required=True)
    



class rr_housekeeping_line_wizard(models.TransientModel):
    _name = 'rr.housekeeping.line.wizard'
    _description = 'rr_housekeeping_line_wizard'
    
    rr_line_id = fields.Many2one('rr.housekeeping.wizard','Housekeeping line id')



class issue_material(models.Model):
    _name = 'issue.material'
    _description = 'Issue Material'
    
    location_id = fields.Many2one('stock.location', 'Source Location', required=True)
    location_dest_id = fields.Many2one('stock.location', 'Destination Location',required=True)
    rr_line_ids = fields.One2many('rr.housekeeping.line.wizard','rr_line_id','Repair / Replacement Info',required=True)


    def check_stock(self,context=None):
        wizard_obj = self.browse()
        field_names=['stock_real']
        res = self.browse()
        line_obj = self.env['rr.housekeeping.line'].search([('rr_line_id','=',context['active_id'])])
        list1=[]
        list2=[]
        for obj in line_obj:
            line_line_obj = self.env['product.product.line'].search([('product_line_id','=',obj)])
            if line_line_obj:
                for obj1 in line_line_obj:
                    p1 = self.env['product.product.line'].browse(obj1)
                    list1.append(p1.product_product_id.id)
                    list2.append(p1.id)
                    p=self.env['product.product'].browse(p1.product_product_id.id)
            else:
                print()
        new_list = list(set(list1))
        for i in new_list:
            sum=0
            for j in list2:
                get_ids=self.env['product.product.line'].search([('product_product_id','=',i),('id','=',j)])
                for k in get_ids:
                    p=self.env['product.product.line'].browse(k)
                    sum=sum+p.qty
            product_obj=self.env['product.product'].browse(i)
            stock_obj1=self.env['stock.location']
            if context is None:
                context = {}
            ctx = context.copy()
            ctx.update({'product_id':product_obj.id})
            arg = None
            total_sum = self.env['stock.location']._product_value([wizard_obj.location_id.id], ['stock_real'], arg, ctx)
            for item in total_sum.values():
                # print("--------------------------------------",item)
                item1=item
                for value in item1.values():
                    test_sum=value
            if test_sum <= sum:
                raise Warning('There is only  %s qty for product %s products.')% (product_obj.qty_available,product_obj.name)
        
        return {'type': 'ir.actions.act_window_close'}


