import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from PIL import Image

from odoo import fields,models,api
from odoo.tools.translate import _
import odoo.addons.decimal_precision as dp
from decimal import Decimal
from odoo import netsvc, tools
from odoo.exceptions import UserError



class HotelRestaurantPos(models.Model):
    _name = "hotel.restaurant.pos"
    _description = "Restaurant POS related Back end"
    
    kot_prev_quantity=0;
    def update_table_book(self,vals):
#        print "table_value int--->>>",int(tbl_id)
       
#        table_id=self.pool.get('hotel.restaurant.tables').search(cr,uid,[('name','=',tbl_value)]) 
#        print "table id in restaurant pos=======>",tbl_id
        for t_id in vals['tableid']:
            # print("idsdd",int(t_id))
            self.env['hotel.restaurant.tables'].write({ 'avl_state': 'book', })
               
    
    def update_table_available(self,vals):
        # print("vals in update_table_book",vals)
#        table_id=self.pool.get('hotel.restaurant.tables').search(cr,uid,[('name','=',table_value)]) 
#        print "table id=======>",table_id
        for ts_id in vals['tab_id']:
                # print("table id in update table available",int(ts_id))
                self.env['hotel.restaurant.tables'].write({'avl_state':'available'})
                
    def create_kot(self,vals):
        # print("In Here KOT GENERATION FOR TABLE")
        # print(vals)
        # print("ORDER LINE",vals['kot'])
        # print(vals['resno'])
        # print(vals['kot_date'])
#        print vals['tableno']
#         print(vals['w_name'])
        if vals['kot']: 
            if 'tableno' in vals:
                # print("I am in if")
                          
                shop_name=vals['shop_name']    
                # print("shop_name is",shop_name)
                order_no = vals['orderno']       
                reservation_no = vals['resno']    
                table=vals['tableno']
                waiter=vals['w_name']
                # print("waiter name-----------",waiter)
                date=vals['kot_date']
                kot_data=False
                # global shop_id
                    
                shop_id=self.env['sale.shop'].search([('name','=',shop_name)])[0]
                # print("HEYYYYYYYYY2",shop_id)
                product_nature=None
                create_kot = False
                for k in vals['kot'] : 
    #                print "product id is as follows",k[2]['product_id']
                    old_product_id=k[2]['product_id'];
                    product_obj=self.env['product.product'].browse(k[2]['product_id'])
                    product_name=product_obj.name
                    product_nature=product_obj.product_nature
    #                print "product nature xxxxxxxxxxxxx updated code",product_nature
                    max_qty=0
                    kot_quantity=k[2]['qty']
    #                print "k[2]['kot_quantity']",kot_quantity
                
                #get product id from menucard according to order line product id
                    product_obj=self.env['product.product'].browse(k[2]['product_id'])
                    menu_card_id = self.env['hotel.menucard'].search([('name','=',product_obj.name)])
                    old_kot_id = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno','=',reservation_no)])
                    #this condition will used when  order no is not created 
                    if not old_kot_id:
                        create_kot = True
                    for test in self.env['hotel.restaurant.order.list'].search([('product_id','=',menu_card_id[0]), ('resno','=',reservation_no)]):
    #                            print "testttttttttttt",test
                                prod_name=self.env['hotel.restaurant.order.list'].browse(test)
                                # print("product qty",prod_name.product_qty,"product id ",prod_name.product_id)
                                if max_qty <= prod_name.product_qty:
                                    max_qty = prod_name.product_qty
                                    
                    #when max qty and current order kot qty is differ then new kot will create after check out 
                    if max_qty!=kot_quantity:
                        # print("yeeeeeeeeeeees")
                        create_kot = True
    #            print "k[2]['kot_quantity'] in product nature kot---dayanand--->>>",k[2]['qty']
                old_kot_id = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno','=',reservation_no)])
                old_kot_length = len(old_kot_id) 
    #            print "old_kot_id---------->",old_kot_id
    #            print "old_kot_id length",old_kot_length
                
                if create_kot:
                    kot_data=self.env['hotel.restaurant.kitchen.order.tickets'].create({
                                                                                            'orderno':order_no,
                                                                                            'resno':reservation_no,
                                                                                            'kot_date':date,                                                                                                                                                
                                                                                            'w_name':waiter,  
                                                                                            'shop_id':shop_id, 
                                                                                            'product_nature':product_nature,         
                                                                                            })
                    # print("max qty======in kot_quantity---------->",kot_quantity)
                    table_id=self.env['hotel.restaurant.tables'].search([('name','=',table)])
                    for tab_id in table_id:
                                self._cr.execute('insert into temp_table3 (name,table_no) values (%s,%s)',(tab_id,kot_data))
                for x in vals['kot']: 
                    kot_quantities=x[2]['qty']
                    sum_qty = 0                
                    i=0
                    for i in range(0,old_kot_length) :                  
                       kot_no_id = old_kot_id[i]
                       # print("kot_no_id----->",kot_no_id)
                       old_kot_object = self.env['hotel.restaurant.kitchen.order.tickets'].browse(kot_no_id)
                       # print("kot object----->",old_kot_object)
                       # print("kot list----->",old_kot_object.kot_list)
                       for y in old_kot_object.kot_list :                                            
                            product_id = self.env['product.product'].search([('name','=',y['product_id'].name)])
                            #print "x p_id++---->",x[2]['product_id']
                            #print "y p_id++---->",product_id[0]
                            if x[2]['product_id'] == product_id[0] :
                                #print "PRODUCT ID MATCH IN KOT"
                                #print "1 qty ",x[2]['qty']
                                #print "2 qty",y['item_qty']                                          
                                sum_qty = sum_qty + int (y['item_qty']) 
                    
                    # print("x[2]['qty']--->",x[2]['qty'])
                    # print("sum_qty --->",sum_qty)
                    x[2]['qty'] = x[2]['qty'] - sum_qty                                     
#                    print "ID",kot_data    
#                     print("PRODUCT ID",x[2]['product_id'])
#                     print("QTY ",x[2]['qty'])
#                     print("RATE---",x[2]['price_unit'])
                    product_obj = self.env['product.product'].browse(x[2]['product_id'])
                    # print(product_obj)
                    name=product_obj.name
                    # print(name)
                    product_nature=product_obj.product_nature
                    menu_card_id = self.env['hotel.menucard'].search([('name','=',name)])
                    # print("menu_card_id ",menu_card_id)
#                    print "KOT DATA",kot_data
                    
                    if(x[2]['qty']!=0):            
                        o_line={   
                             'product_id':menu_card_id[0],
                             'kot_order_list':kot_data,
                             'name':name,
                             'item_qty':x[2]['qty'],
                             'item_rate':x[2]['price_unit'],   
                             'product_qty':kot_quantities, 
                             'product_nature':product_nature,                     
                            }
                    
                        self.env['hotel.restaurant.order.list'].create(o_line)
            
            else:
                # print("I am in else")
                shop_name=vals['shop_name']    
                # print("shop_name is",shop_name)
                order_no = vals['orderno']       
                reservation_no = vals['resno']    
                rooms=vals['room_no'][0]
                # print("room no is",rooms)
                waiter=vals['w_name']
                date=vals['kot_date']
                kot_data=False
                # global shop_id
                    
                shop_id=self.env['sale.shop'].search([('name','=',shop_name)])[0]
                   
                # print("HEYYYYYYYYY2",shop_id)
                product_nature=None
                create_kot = False
                for k in vals['kot'] : 
    #                print "product id is as follows",k[2]['product_id']
                    old_product_id=k[2]['product_id'];
                    product_obj=self.env['product.product'].browse(k[2]['product_id'])
                    product_name=product_obj.name
                    product_nature=product_obj.product_nature
    #                print "product nature xxxxxxxxxxxxx updated code",product_nature
                    max_qty=0
                    kot_quantity=k[2]['qty']
    #                print "k[2]['kot_quantity']",kot_quantity
                
                #get product id from menucard according to order line product id
                    product_obj=self.env['product.product'].browse(k[2]['product_id'])
                    menu_card_id = self.env['hotel.menucard'].search([('name','=',product_obj.name)])
                    old_kot_id = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno','=',reservation_no)])
                    #this condition will used when  order no is not created 
                    if not old_kot_id:
                        create_kot = True
                    for test in self.env['hotel.restaurant.order.list'].search([('product_id','=',menu_card_id[0]), ('resno','=',reservation_no)]):
    #                            print "testttttttttttt",test
                                prod_name = self.env['hotel.restaurant.order.list'].browse(test)
                                # print("product qty",prod_name.product_qty,"product id ",prod_name.product_id)
                                if max_qty <= prod_name.product_qty:
                                    max_qty = prod_name.product_qty
                                    
                    #when max qty and current order kot qty is differ then new kot will create after check out 
                    if max_qty!=kot_quantity:
                        # print("yeeeeeeeeeeees")
                        create_kot = True
    #            print "k[2]['kot_quantity'] in product nature kot---dayanand--->>>",k[2]['qty']
                old_kot_id = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno','=',reservation_no)])
                old_kot_length = len(old_kot_id) 
    #            print "old_kot_id---------->",old_kot_id
    #            print "old_kot_id length",old_kot_length
                
                if create_kot:
                    kot_data=self.env['hotel.restaurant.kitchen.order.tickets'].create({
                                                                                            'orderno':order_no,
                                                                                            'resno':reservation_no,
                                                                                            'kot_date':date,                                                                                                                                                
                                                                                            'w_name':waiter,  
                                                                                            'shop_id':shop_id, 
                                                                                            'product_nature':product_nature,         
                                                                                            'room_no':rooms,
                                                                                            })
                    # print("max qty======in kot_quantity---------->",kot_quantity)
                for x in vals['kot']: 
                    kot_quantities=x[2]['qty']
                    sum_qty = 0                
                    i=0
                    for i in range(0,old_kot_length) :                  
                       kot_no_id = old_kot_id[i]
                       # print("kot_no_id----->",kot_no_id)
                       old_kot_object = self.env['hotel.restaurant.kitchen.order.tickets'].browse(kot_no_id)
                       # print("kot object----->",old_kot_object)
                       # print("kot list----->",old_kot_object.kot_list)
                       for y in old_kot_object.kot_list :                                            
                            product_id = self.env['product.product'].search([('name','=',y['product_id'].name)])
                            #print "x p_id++---->",x[2]['product_id']
                            #print "y p_id++---->",product_id[0]
                            if x[2]['product_id'] == product_id[0] :
                                #print "PRODUCT ID MATCH IN KOT"
                                #print "1 qty ",x[2]['qty']
                                #print "2 qty",y['item_qty']                                          
                                sum_qty = sum_qty + int (y['item_qty']) 
                    
                    # print("x[2]['qty']--->",x[2]['qty'])
                    # print("sum_qty --->",sum_qty)
                    x[2]['qty'] = x[2]['qty'] - sum_qty                                     
#                    print "ID",kot_data    
#                     print("PRODUCT ID",x[2]['product_id'])
#                     print("QTY ",x[2]['qty'])
#                     print("RATE---",x[2]['price_unit'])
                    product_obj = self.env['product.product'].browse(x[2]['product_id'])
                    # print(product_obj)
                    name = product_obj.name
                    # print(name)
                    product_nature = product_obj.product_nature
                    menu_card_id = self.env['hotel.menucard'].search([('name','=',name)])
                    # print("menu_card_id ",menu_card_id)
#                    print "KOT DATA",kot_data
                    
                    if(x[2]['qty']!=0):            
                        o_line={   
                             'product_id':menu_card_id[0],
                             'kot_order_list':kot_data,
                             'name':name,
                             'item_qty':x[2]['qty'],
                             'item_rate':x[2]['price_unit'],   
                             'product_qty':kot_quantities, 
                             'product_nature':product_nature,                     
                            }
                    
                        self.env['hotel.restaurant.order.list'].create(o_line)
        
        
        
        
        
        if vals['bot']:
            if 'tableno' in vals:
                shop_name=vals['shop_name']    
                # print("shop_name is",shop_name)
                ordernobot = vals['ordernobot']       
                reservation_no = vals['resno']    
                table=vals['tableno']
                waiter=vals['w_name']
                date=vals['kot_date']
                # global shop_id
                bot_data=False;
                create_bot = False;
                    
                shop_id = self.env['sale.shop'].search([('name','=',shop_name)])[0]
                # print("HEYYYYYYYYY2 in bot---------------->>>",shop_id)
                for k in vals['bot'] : 
                    # print("product id is as follows",k[2]['product_id'])
                    old_product_id = k[2]['product_id'];
                    product_obj = self.env['product.product'].browse(k[2]['product_id'])
                    product_name = product_obj.name
                    product_nature = product_obj.product_nature
                    # print("product nature xxxxxxxxxxxxx updated code",product_nature)
                    kot_quantity = k[2]['qty']
                    # print("k[2]['kot_quantity']",k[2]['qty'])
                    max_qty = 0
                    
                
                #get product id from menucard according to order line product id
                    product_obj=self.env['product.product'].browse(k[2]['product_id'])
                    menu_card_id = self.env['hotel.menucard'].search([('name','=',product_obj.name)])
                    old_kot_id = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno','=',reservation_no)])
                    if not old_kot_id:
                        create_bot = True
                    for test in self.env['hotel.restaurant.order.list'].search([('product_id','=',menu_card_id[0]), ('resno','=',reservation_no)]):
    #                            print "testttttttttttt",test
                                prod_name = self.env['hotel.restaurant.order.list'].browse(test)
                                # print("product qty",prod_name.product_qty,"product id ",prod_name.product_id)
                                if max_qty <= prod_name.product_qty:
                                    max_qty = prod_name.product_qty
                                    
                    #when max qty and current order kot qty is differ then new kot will create after check out 
                    if max_qty!=kot_quantity:
                        # print("yeeeeeeeeeeees")
                        create_bot = True
    #            print "k[2]['kot_quantity'] in product nature kot---dayanand--->>>",k[2]['qty']
                old_kot_id = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno','=',reservation_no)])
                old_kot_length = len(old_kot_id) 
    #            print "old_kot_id---------->",old_kot_id
    #            print "old_kot_id length",old_kot_length
                if create_bot:
                    bot_data=self.env['hotel.restaurant.kitchen.order.tickets'].create({
    #                                                                                    'orderno':ordernobot,
                                                                                        'resno':reservation_no,
                                                                                        'kot_date':date,                                                                                                                                                
                                                                                        'w_name':waiter,  
                                                                                        'shop_id':shop_id,
                                                                                        'product_nature':product_nature,                                                                          
                                                                                         })
                    # print("KOT DATA ID-----------> ",bot_data)
                   
                            
                    table_id = self.env['hotel.restaurant.tables'].search([('name','=',table)])
                    # print("table id in generate kot", table_id)
                    for tab_id in table_id:
                        self._cr.execute('insert into temp_table3 (name,table_no) values (%s,%s)',(tab_id,bot_data))
               
                for x in vals['bot']: 
                        kot_quantities=x[2]['qty']
                        sum_qty = 0                
                        i=0
                        for i in range(0,old_kot_length) :                  
                           kot_no_id = old_kot_id[i]
                           # print("kot_no_id----->",kot_no_id)
                           old_kot_object = self.env['hotel.restaurant.kitchen.order.tickets'].browse(kot_no_id)
                           # print("kot object----->",old_kot_object)
                           # print("kot list----->",old_kot_object.kot_list)
                           for y in old_kot_object.kot_list :                                            
                                product_id = self.env['product.product'].search([('name','=',y['product_id'].name)])
                                #print "x p_id++---->",x[2]['product_id']
                                #print "y p_id++---->",product_id[0]
                                if x[2]['product_id'] == product_id[0] :
                                    #print "PRODUCT ID MATCH IN KOT"
                                    #print "1 qty ",x[2]['qty']
                                    #print "2 qty",y['item_qty']                                          
                                    sum_qty = sum_qty + int (y['item_qty']) 
                        
                        # print("x[2]['qty']--->",x[2]['qty'])
                        # print("sum_qty --->",sum_qty)
                        x[2]['qty'] = x[2]['qty'] - sum_qty                                     
#                        print "ID",kot_data    
#                         print("PRODUCT ID",x[2]['product_id'])
#                         print("QTY ",x[2]['qty'])
#                         print("RATE---",x[2]['price_unit'])
                        product_obj=self.env['product.product'].browse(x[2]['product_id'])
                        # print(product_obj)
                        name=product_obj.name
                        # print(name)
                        product_nature = product_obj.product_nature
                        menu_card_id = self.env['hotel.menucard'].search([('name','=',name)])
                        # print("menu_card_id ",menu_card_id)
#                        print "KOT DATA",kot_data
                        
                        if(x[2]['qty']!=0):            
                            o_line={   
                                 'product_id':menu_card_id[0],
                                 'kot_order_list':bot_data,
                                 'name':name,
                                 'item_qty':x[2]['qty'],
                                 'item_rate':x[2]['price_unit'], 
                                 'product_qty':kot_quantities,                     
                                 'product_nature':product_nature,    
                                }
                        
                            self.env['hotel.restaurant.order.list'].create(o_line)                    
            
            else:
                shop_name=vals['shop_name']    
                # print("shop_name is",shop_name)
                ordernobot = vals['ordernobot']       
                reservation_no = vals['resno']    
                rooms=vals['room_no'][0]
                waiter=vals['w_name']
                date=vals['kot_date']
                # global shop_id
                bot_data=False;
                create_bot = False;
                    
                shop_id = self.env['sale.shop'].search([('name','=',shop_name)])[0]
                # print("HEYYYYYYYYY2 in bot---------------->>>",shop_id)
                for k in vals['bot'] : 
                    # print("product id is as follows",k[2]['product_id'])
                    old_product_id=k[2]['product_id'];
                    product_obj=self.env['product.product'].browse(k[2]['product_id'])
                    product_name=product_obj.name
                    product_nature=product_obj.product_nature
                    # print("product nature xxxxxxxxxxxxx updated code",product_nature)
                    kot_quantity=k[2]['qty']
                    # print("k[2]['kot_quantity']",k[2]['qty'])
                    max_qty= 0
                    
                
                #get product id from menucard according to order line product id
                    product_obj = self.env['product.product'].browse(k[2]['product_id'])
                    menu_card_id = self.env['hotel.menucard'].search([('name','=',product_obj.name)])
                    old_kot_id = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno','=',reservation_no)])
                    if not old_kot_id:
                        create_bot = True
                    for test in self.env['hotel.restaurant.order.list'].search([('product_id','=',menu_card_id[0]), ('resno','=',reservation_no)]):
    #                            print "testttttttttttt",test
                                prod_name = self.env['hotel.restaurant.order.list'].browse(test)
                                # print("product qty",prod_name.product_qty,"product id ",prod_name.product_id)
                                if max_qty <= prod_name.product_qty:
                                    max_qty = prod_name.product_qty
                                    
                    #when max qty and current order kot qty is differ then new kot will create after check out 
                    if max_qty!=kot_quantity:
                        # print("yeeeeeeeeeeees")
                        create_bot = True
    #            print "k[2]['kot_quantity'] in product nature kot---dayanand--->>>",k[2]['qty']
                old_kot_id = self.env['hotel.restaurant.kitchen.order.tickets'].search([('resno','=',reservation_no)])
                old_kot_length = len(old_kot_id) 
    #            print "old_kot_id---------->",old_kot_id
    #            print "old_kot_id length",old_kot_length
                if create_bot:
                    bot_data=self.env['hotel.restaurant.kitchen.order.tickets'].create({
    #                                                                                    'orderno':ordernobot,
                                                                                        'resno':reservation_no,
                                                                                        'kot_date':date,                                                                                                                                                
                                                                                        'w_name':waiter,  
                                                                                        'shop_id':shop_id,
                                                                                        'product_nature':product_nature,
                                                                                        'room_no':rooms,                                                                          
                                                                                         })
                    # print("KOT DATA ID-----------> ",bot_data)
                for x in vals['bot']: 
                        kot_quantities=x[2]['qty']
                        sum_qty = 0                
                        i=0
                        for i in range(0,old_kot_length) :                  
                           kot_no_id = old_kot_id[i]
                           # print("kot_no_id----->",kot_no_id)
                           old_kot_object = self.env['hotel.restaurant.kitchen.order.tickets'].browse(kot_no_id)
                           # print("kot object----->",old_kot_object)
                           # print("kot list----->",old_kot_object.kot_list)
                           for y in old_kot_object.kot_list :                                            
                                product_id = self.env['product.product'].search([('name','=',y['product_id'].name)])
                                #print "x p_id++---->",x[2]['product_id']
                                #print "y p_id++---->",product_id[0]
                                if x[2]['product_id'] == product_id[0] :
                                    #print "PRODUCT ID MATCH IN KOT"
                                    #print "1 qty ",x[2]['qty']
                                    #print "2 qty",y['item_qty']                                          
                                    sum_qty = sum_qty + int (y['item_qty']) 
                        
                        # print("x[2]['qty']--->",x[2]['qty'])
                        # print("sum_qty --->",sum_qty)
                        x[2]['qty'] = x[2]['qty'] - sum_qty                                     
#                        print "ID",kot_data    
#                         print("PRODUCT ID",x[2]['product_id'])
#                         print("QTY ",x[2]['qty'])
#                         print("RATE---",x[2]['price_unit'])
                        product_obj = self.env['product.product'].browse(x[2]['product_id'])
                        # print(product_obj)
                        name=product_obj.name
                        # print(name)
                        product_nature=product_obj.product_nature
                        menu_card_id = self.env['hotel.menucard'].search([('name','=',name)])
                        # print("menu_card_id ",menu_card_id)
#                        print "KOT DATA",kot_data
                        
                        if(x[2]['qty']!=0):            
                            o_line={   
                                 'product_id':menu_card_id[0],
                                 'kot_order_list':bot_data,
                                 'name':name,
                                 'item_qty':x[2]['qty'],
                                 'item_rate':x[2]['price_unit'], 
                                 'product_qty':kot_quantities,                     
                                 'product_nature':product_nature,    
                                }
                        
                            self.env['hotel.restaurant.order.list'].create(o_line)                    

class PosOrder(models.Model):
    _inherit="pos.order"
    
    
    
    @api.model    
    def _order_fields(self, ui_order):
        # print("\n\n\n _order_fields =====ui_order===",ui_order)
        # print("\n\n\n ui_order.get('folio_line_id') ======",ui_order.get('folio_line_id'))
        pos_order_obj = super(PosOrder,self)._order_fields(ui_order)
        pos_order_obj.update({
                              'folio_line_id':ui_order.get('folio_line_id'),
                              'folio_ids':ui_order.get('folio_ids'),
                              });
#         self.env['hotel.folio'].write({'pos_order_ids':ui_order.get('folio_id')})
        
        return pos_order_obj
    
    
#    START  ========= COMMENTED BY RADHIKA =============
  
#     @api.model
#     def create_from_ui(self, orders):
#         print "\n\n\n self =========",self
#     #_logger.info("orders: %r", orders)
#         print "orders are",orders
# #            print "orders in create from ui",orders[0]['data']['room_id']
#         list = []
#         order_ids=[]
#         print "orders in create from ui",orders
#         for ord in orders:
#           
# #                print "old customer id",ord['data']['old_cust_id']
#             print "new customer name is as follows",ord['data']['get_new_cust_name']
#             print "new customer mobile number",ord['data']['get_new_cust_mobile']
#             
#             if ord['data']['get_new_cust_name']:
#                 cust_rec = {
#                             'name' :  ord['data']['get_new_cust_name'],
#                             'mobile' : ord['data']['get_new_cust_mobile'],
#                             }
#                 cust_id = self.env['res.partner'].create(cust_rec)
#             else:
#                 if ord['data']['old_cust_id']:
#                     cust_id = int(ord['data']['old_cust_id'])
#                 else:
#                     cust_id = False
#                 
#             credit_sales=False
#             ids=ord['id']
#             print "ids is---------------=================++++++++++++>>",ids
#             if ord['data']['credit_sale']:
#                 credit_sales=ord['data']['credit_sale']
#                 print "on credit sale is"
#                
# #                    credit_sales={
# #                                    'credit_sales':ord['data']['credit_sale'],
# #                                  }
# #                    credit_sales_id = self.pool.get('pos.order').create(cr, uid,  credit_sales, context=context)
# #            
#         
#          
#         for tmp_order in orders:
#             order= tmp_order['data']
#             tab_in_order = [int(t) for t in order['table_id']]
#             order_id = self.create({
#                 'name': order['name'],
#                 'user_id': order['user_id'] or False,
#                 'session_id': order['pos_session_id'],
#                 'lines': order['lines'],
#                 'pos_reference':order['name'],
#                 'waiter_name':order['waiter_name'],
#                 'credit_sales':credit_sales,
#                 'partner_id' : cust_id,
#                 'table_ids' :  [(6,0,tab_in_order)],
#             })
#             
# #                print "order 1 is-------------------------->>",order1
#             for payments in order['statement_ids']:
#                 payment = payments[2]
#                 if credit_sales is False:
#                     self.add_payment(order_id, {
#                         'amount': payment['amount'] or 0.0,
#                         'payment_date': payment['name'],
#                         'statement_id': payment['statement_id'],
#                         'payment_name': payment.get('note', False),
#                         'journal': payment['journal_id']
#                     })
#                 
#             if order['amount_return']:
#                 session = self.env['pos.session'].browse(order['pos_session_id'])
#                 cash_journal = session.cash_journal_id
#                 cash_statement = False
#                 if not cash_journal:
#                     cash_journal_ids = filter(lambda st: st.journal_id.type=='cash', session.statement_ids)
#                     if not len(cash_journal_ids):
#                         raise UserError(_("No cash statement found for this session. Unable to record returned cash."))
# #                             raise osv.except_osv( _('error!'),
# #                                 _("No cash statement found for this session. Unable to record returned cash."))
#                     cash_journal = cash_journal_ids[0].journal_id
#                 self.add_payment(order_id, {
#                     'amount': -order['amount_return'],
#                     'payment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
#                     'payment_name': _('return'),
#                     'journal': cash_journal.id,
#                 })
#             order_ids.append(order_id)
#             wf_service = netsvc.LocalService("workflow")
#             print "credit sales is trueeeeeeeeeeeeeeeeee",credit_sales
#             if credit_sales:
#                 print "credit sale in true"
#                 wf_service.trg_validate('pos.order', order_id, 'credit')
#                 product_name=ord['data']['name']
#                 print "product_name-------------pppppppppppppppppp-----------",product_name
#                 ids = self.env["pos.order"].search([('pos_reference','=',product_name)])
#                 print "ids are---------------------------------ccccccccccccccc----------",ids
#                 self.create_picking()
#                 print "\n************************************************"
#             else:
#                 wf_service.trg_validate('pos.order', order_id, 'paid')
#         
#         ####################### If Order is booked against reservation #####################################
#          
#         if order.has_key('reservation_no') and order['reservation_no']:
#             order_list_lines = []
#             for line in order['lines']:
#                 line_vals = line[2]
#                 vals_dict = {
#                                     'product_id' : self.env['hotel.menucard'].search([('product_id','=',line_vals['product_id'])])[0],
#                                     'item_qty' : line_vals['qty'],
#                                     'item_rate' : line_vals['price_unit'],
#                              }
#                 order_list_lines.append([0,0,vals_dict])
#             
#             res_obj = self.env['hotel.restaurant.reservation']
#             res_id = res_obj.search([('name','=',order['reservation_no'][0])])
#             
#             
#             #Adding Tables if new tables are booked
#             tables_in_order = [int(t) for t in order['table_id']]                 
#             res_brw = res_obj.browse(res_id[0])
#             reserved_tables_list  = [x.id for x in res_brw.tableno]
#             tbl_list_to_update = []
#             
# #                 for tbl in tables_in_order:
# #                     if tbl not in reserved_tables_list:
# #                         tbl_list_to_update.append(tbl)
#             
# #                 for t in reserved_tables_list:
# #                     tbl_list_to_update.append(t)
#             for tbl in tables_in_order:
#                 tbl_list_to_update.append(tbl)
#             
#             res_obj.write({'order_list_ids' : order_list_lines,'tableno' : [(6,0,tbl_list_to_update)]})
#             
#             #Change state of reservation to Done
#             res_obj.table_done(res_id)
#             res_obj.create_order(res_id)
#             
#             #Change state of order to done
#             res_order_obj = self.env['hotel.reservation.order']
#             res_order_obj.write(res_order_obj.search([('reservation_id','=',res_id[0])]),{ 'state' : 'order', 'pos_ref' : order['name']})
# 
#             list.append(order_id)
#             
#         for order in orders:
#             if 'room_id' in order['data']:
#                 current_room_id=''
#                 current_room_id= order['data']['room_id']
#                 type1=type(current_room_id)
#                 
#                 if  type1 is int:
#                     current_room_id=order['data']['room_id']
#                 else:
#                     current_room_id = order['data']['room_id'][0]
#                 room_history_objects = self.env["hotel.room.booking.history"].browse(int(current_room_id))
#                 room_no = room_history_objects.history_id.id
#                 room_no = room_history_objects.history_id.id
#                 res={}
#                 today=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#                 booking_id=0
#                 history_obj=self.env["hotel.room.booking.history"]
#                 folio_obj = self.env["hotel.folio"]
#                 obj = self.env["hotel.room"].browse(room_no)
# 
#                 for folio_hsry_id in history_obj.search([('name','=',obj.product_id.name)]):
#                     hstry_line_id = history_obj.browse(folio_hsry_id)
#                     start_dt = hstry_line_id.check_in
#                     end_dt = hstry_line_id.check_out
#                     booking_id = hstry_line_id.booking_id.id
#                     if (start_dt<=today) and (end_dt>=today):                     
#                         folio_obj_id = folio_obj.search([('reservation_id','=',booking_id)])
#                         res['folio_id'] = folio_obj_id[0]
# #                             res['partner_id'] = hstry_line_id.partner_id.id
#                         res['partner_id'] = order['data']['partner_id'][0]
#                         
#                                                                                                                                                                         
#                 self.write({'partner_id':res['partner_id']})
#                 cr.execute('insert into pos_order_ids_rel_new(folio_id,order_id) values (%s,%s)',(res['folio_id'],order_id))
#                  
#                  
#         list.append(order_id)
#         return list    

#   END    ========= COMMENTED BY RADHIKA ============= 
    
    table_ids = fields.Many2many('hotel.restaurant.tables','pos_book_tables','table_no','name','Table number')
    state = fields.Selection(selection_add=[('draft', 'Draft'),
                ('credit', 'Credit Sale'),
               ('cancel', 'Cancelled'),
               ('paid', 'Paid'),
               ('done', 'Posted'),
               ('invoiced', 'Invoiced') ,],
              string='Status', readonly=True)
    folio_line_id = fields.Many2one('hotel_folio.line','Link to Room')
    folio_ids = fields.Many2one('hotel.folio','Link to Folio')
    credit_sales = fields.Char('creditsales')
    waiter_name = fields.Char('Waiter Name')
        
    def action_paid(self):

        for order in self.env['pos.order'].browse():
            # print("order stae is--------------kkkkkkkkkkkkkkkkkk------------>>>>>",order.state)
            if order.credit_sales=='True':
                # print("order stae is--------------yyyyyyyyyyyyy------------>>>>>",order.state)
                self.write({'state': 'paid'})
            else:
                self.create_picking()
                self.write({'state': 'paid'})
        
        return True
    
#     START   ========= COMMENTED BY RADHIKA =============
#     def add_payment(self,order_id, data):
#         print "I am in add payment"
#     
#         """Create a new payment for the order"""
#         statement_obj = self.env['account.bank.statement']
#         statement_line_obj = self.env['account.bank.statement.line']
#         prod_obj = self.env['product.product']
#         property_obj = self.env['ir.property']
#         curr_c = self.env['res.users'].browse().company_id
#         curr_company = curr_c.id
#         order = self.browse(order_id)
#         ids_new = []
#         args = {
#             'amount': data['amount'],
#         }
#         
#         if 'payment_date' in data.keys():
#             args['date'] = data['payment_date']
#         args['name'] = order.name
#         
#         if data.get('payment_name', False):
#             args['name'] = args['name'] + ': ' + data['payment_name']
#         account_def = property_obj.get('property_account_receivable', 'res.partner')
#         args['account_id'] = (order.partner_id and order.partner_id.property_account_receivable \
#                              and order.partner_id.property_account_receivable.id) or (account_def and account_def.id) or False
#         args['partner_id'] = order.partner_id and order.partner_id.id or None
#         
#         if not args['account_id']:
#             if not args['partner_id']:
#                 msg = _('There is no receivable account defined to make payment')
#             else:
#                 msg = _('There is no receivable account defined to make payment for the partner: "%s" (id:%d)') % (order.partner_id.name, order.partner_id.id,)
#             raise exceptions.except_orm(_('Configuration Error !'), msg)
#         
#         statement_id = statement_obj.search([
#                                                      ('journal_id', '=', int(data['journal'])),
#                                                      ('company_id', '=', curr_company),
#                                                      ('user_id', '=', uid),
#                                                      ('state', '=', 'open')], context=context)
#         
#         if len(statement_id) == 0:
#             raise exceptions.except_orm(_('Error !'), _('You have to open at least one cashbox'))
#         if statement_id:
#             statement_id = statement_id[0]
#         
#         args['statement_id'] = statement_id
#         args['pos_statement_id'] = order_id
#         args['journal_id'] = int(data['journal'])
#         args['type'] = 'customer'
#         args['ref'] = order.name
#         
#                
#         print args['statement_id']
#         print args['pos_statement_id']
#         print args['journal_id'] 
#         print args['type']
#         print args['ref']
#                 
#         statement_line_obj.create(args)
#         ids_new.append(statement_id)
#         wf_service = netsvc.LocalService("workflow")       
#         wf_service.trg_validate('pos.order', order_id, 'paid')
#         wf_service.trg_write('pos.order', order_id)
# 
#         return statement_id
    
#   END    ========= COMMENTED BY RADHIKA =============
    
    def action_credit(self):
        return self.write({'state': 'credit'})
    
    def create_picking(self):
        """Create a picking for each order and validate it."""
        picking_obj = self.env['stock.picking.out']
        partner_obj = self.env['res.partner']
        move_obj = self.env['stock.move']

        for order in self.browse():
            if not order.state in ['draft','credit']:
                continue
            addr = order.partner_id and partner_obj.address_get([order.partner_id.id], ['delivery']) or {}
            picking_id = picking_obj.create({
                'origin': order.name,
                'partner_id': addr.get('delivery',False),
                'type': 'out',
                'company_id': order.company_id.id,
                'move_type': 'direct',
#                 'note': order.note or "",
                'invoice_state': 'none',
                'auto_picking': True,
            })
            # print("\n\nOrder Info=",order.name,"\nPicking id=",picking_id)
            self.write({'picking_id': picking_id})
            location_id = order.shop_id.warehouse_id.lot_stock_id.id
            output_id = order.shop_id.warehouse_id.lot_output_id.id

            for line in order.lines:
                if line.product_id and line.product_id.type == 'service':
                    continue
                if line.qty < 0:
                    location_id, output_id = output_id, location_id

                move_obj.create({
                    'name': line.name,
                    'product_uom': line.product_id.uom_id.id,
                    'product_uos': line.product_id.uom_id.id,
                    'picking_id': picking_id,
                    'product_id': line.product_id.id,
                    'product_uos_qty': abs(line.qty),
                    'product_qty': abs(line.qty),
                    'tracking_id': False,
                    'state': 'draft',
                    'location_id': location_id,
                    'location_dest_id': output_id,
                })
                if line.qty < 0:
                    location_id, output_id = output_id, location_id

            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate('stock.picking', picking_id, 'button_confirm')
            picking_obj.force_assign([picking_id])
        return True


class PosSession(models.Model):
        _inherit="pos.session"
        _description="inherited pos.session class"
        
        def _confirm_orders(self):
#                  wf_service = netsvc.LocalService("workflow")
        
                
                for session in self:
                    # print("session.config_id.journal_id.id",session.config_id.journal_id.name)
                    
#                    order_id = [order.id for order in session.order_ids if order.state == 'paid']
                    order_ids = [order.id for order in session.order_ids 
                                 if order.state == 'paid']
                    move_id = self.env['account.move'].create({'ref' : session.name, 'journal_id' : session.config_id.journal_id.id, })
                    if order_ids:
                        for order in order_ids:
                            order._create_account_move_line(session, move_id)
                    for order in session.order_ids:
                        if order.state not in ('paid', 'invoiced','draft'):
#                             raise exceptions.except_orm(
#                                 _('Error!'),
#                                 _("You cannot confirm all orders of this session, because they have not the 'paid' status"))
                            raise UserError(_("You cannot confirm all orders of this session, because they have not the 'paid' status."))
                        else:
#                             wf_service.trg_validate('pos.order', order.id, 'done')
                            
                            order.action_pos_order_done(session, move_id)
        
                return True
             
             
class HotelFolio(models.Model):
    
    _inherit = "hotel.folio"
    _description = "Hotel Folio Inherit Adding POS ORDER TABS"
    
#     pos_order_ids = fields.Many2many('pos.order','pos_order_ids_rel_new','folio_id','order_id','POS Order IDS',readonly=True)   
    pos_order_ids = fields.One2many('pos.order','folio_ids','POS Orders',readonly=True)     
    
class HotelMenucard(models.Model):
    
    def _get_image(self, name, args):
        result = dict.fromkeys(self._ids, False)
        for obj in self.browse():
            result[obj.id] = tools.image_get_resized_images(obj.image)
        return result
    
    def _set_image(self, name, value, args):
        return self.write({'image1': tools.image_resize_image_big(value)})

    _inherit = "hotel.menucard"
    _description = "Hotel Menucard Inherit Adding Point_of_sale category"
    pos_category = fields.Many2one('pos.category','Point Of Sale Category ',
                                        help="The Point of Sale Category this products belongs to. Those categories are used to group similar products and are specific to the Point of Sale.") 


class HotelReservationOrder(models.Model):
    
    _inherit = 'hotel.reservation.order'
    
    pos_ref = fields.Char('POS Ref.')


class PosConfig(models.Model):
    _inherit = 'pos.config'

    shop_id = fields.Many2one('sale.shop', string='Hotel')

    def open_ui(self):

        # print('--------------------', self.shop_id)
        if not self.shop_id:
            raise UserError("Shop must be define before starting your shopping. (Under Shop Setting--> Click on checkbox Barcode Scanner -->Hotel Name)")
        else :
            return super(PosConfig, self).open_ui()

    def _open_session(self, session_id):
        if not self.shop_id:
            raise UserError("Shop must be define before starting your shopping. (Under Setting--> Click on Checkbox Barcode Scanner -->Hotel Name)")
        else :
            return super(PosConfig, self)._open_session(session_id)


