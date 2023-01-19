# -*- encoding: utf-8 -*-
from odoo import api, fields, models
import time
import sys
import datetime
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
# from odoo.tools import amount_to_text_en
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import calendar
from dateutil import parser
from odoo.tools import config
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
# import mx.DateTime
import pytz
# import datetime
import time


class hotel_report_view(models.AbstractModel):
    _name = 'report.hotel_management.hotel_report_view'
    _description = 'hotel report view'


    @api.model
    def _get_report_values(self, docids, data=None):
        order = self.env['hotel.folio'].browse(docids)
        if order and not order.invoice_ids:
            raise ValidationError('Please Create invoice first ...!')
        # self.context =self._context
        # print('Fields : ', self._fields)
        # self.total = 0.00
        # self.service_total = 0.00
        # self.room_type = ''
        # self.taxe_amt = 0.00
        # self.net_amt = 0.00
        # cur_date = ''
        # bill_no = ''
        # self.no_of_invoices = ''
        # self.no_of_days = ''
        # self.net_amt = ''
        # self.count_line = 0

        return {
            'doc_ids': docids,
            'doc_model': 'hotel.folio',
            'data': data,
            'docs': order,
            'time': time,
            'get_total': self.get_total,
            'get_quantity': self.get_quantity,
            'get_service_total': self.get_service_total,
            'get_room_type': self.get_room_type,
            'get_alltaxes': self.get_alltaxes,
            'get_netamout': self.get_netamout,
            'get_netamout_comapny': self.get_netamout_comapny,
            'get_current_date': self.get_current_date,
            'get_invoice_reference': self.get_invoice_reference,
            'get_total_days': self.get_total_days,
            'get_net_amt': self.get_net_amt,
            'get_no_of_invoice': self.get_no_of_invoice,
            'get_lines': self.get_lines,
            'get_count': self.get_count,
            'get_user': self.get_user,
            'get_laundry_bill': self.get_laundry_bill,
            'get_total_restaurant': self.get_total_restaurant,
            'get_total_laundry': self.get_total_laundry,
            'get_total_transport': self.get_total_transport,
            'get_no_days': self.get_no_days,
            'get_rest_billl': self.get_rest_billl,
            'get_base_currency_amt': self.get_base_currency_amt,
            'get_base_currency_symbol': self.get_base_currency_symbol
        }
        

    def get_no_days(self, days):
        return int(days)

    def get_net_amt(self, total, tax):
        net_amt = total + tax
        return net_amt

    def get_total_days(self, check_in, check_out):

        day_count = (check_out - check_in).days
        timezone = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.timezone(self._context.get('tz') or 'UTC')
        time_in = datetime.strptime(str(check_in.astimezone(timezone))[11:16], '%H:%M')
        time_out = datetime.strptime(str(check_out.astimezone(timezone))[11:16], '%H:%M')
        time_count1 = (time_out - time_in)
        if time_count1 > timedelta(0):
            day_count += 1

        if not day_count:
            day_count = 1

        # s_date = check_in.date()
        # e_date = check_out.date()
        # no_of_days = e_date - s_date
        return day_count

    def get_base_currency_amt(self, obj):
        result = 0
        folio_browse = self.env['hotel.folio'].browse(obj.id)
        # print("folio_browse-------------------------------", folio_browse)
        rescur_search = self.env['res.currency.rate'].search([('currency_id', '=', folio_browse.pricelist_id.currency_id.id)])
        result = float(
            folio_browse.amount_total / folio_browse.pricelist_id.currency_id.rate)
        return "%0.2f" % result

    def get_base_currency_symbol(self, obj):
        folio_browse = self.env['hotel.folio'].browse(obj.id)
        # print("folio_browse---------11111111----------------------", folio_browse)
        cur_search1 = self.env['res.currency'].search([('active', '=', True)])[0]
        if cur_search1:
#             cur_brw = self.env['res.currency'].browse(cur_search1)[0]
            return cur_search1.symbol
        else:
            cur_search11 = self.env['res.currency'].search([('name', '=', 'EUR')])[0]
#             cur_brw = self.env['res.currency'].browse(cur_search11)
            return cur_search11.symbol

    def get_invoice_reference(self, obj):
        '''This method id used to show all the invoices related to curstomer in folio history '''
        folio_browse = self.env['hotel.folio'].browse(obj.id)
        # print("folio_browseeeeeeeeeeeeeeeee",folio_browse)
        if folio_browse.invoice_ids:
            for invoice_id in folio_browse.invoice_ids:
                if invoice_id.number:
                    no_of_invoices += ' ' + invoice_id.number + ','
        if folio_browse.laundry_invoice_ids:
            for invoice_id in folio_browse.laundry_invoice_ids:
                if invoice_id.reference == 'Laundry Customer Invoice' and invoice_id.number:
                    no_of_invoices += ' ' + invoice_id.number + ','
        if folio_browse.transport_invoice_ids:
            for invoice_id in folio_browse.transport_invoice_ids:
                if invoice_id.reference == 'Transport Invoice' and invoice_id.number:
                    no_of_invoices += ' ' + invoice_id.number + ','
        if folio_browse.order_reserve_invoice_ids:
            for invoice_id in folio_browse.order_reserve_invoice_ids:
                if invoice_id.reference == 'Order Invoice' and invoice_id.number:
                    no_of_invoices += ' ' + invoice_id.number + ','
        if folio_browse.table_order_invoice_ids:
            for invoice_id in folio_browse.table_order_invoice_ids:
                if invoice_id.number:
                    no_of_invoices += ' ' + invoice_id.number + ','
        no_of_invoices = no_of_invoices[:-1] + '.'
        return no_of_invoices

    def get_user(self):
        '''This is used to get the user name which are currently login, to show cashier'''
        user_id = self.env['res.users'].browse(self._uid)
        return user_id.name

    def get_total_laundry(self, obj):
        '''This will calculate total of all number of room's amount in the folio'''
        laundry_browse = self.env['hotel.folio'].browse(obj.id)
        subtotal = 0.00
        for laundry_line in laundry_browse.laundry_line_ids:
            subtotal = subtotal + laundry_line.price_subtotal
        total = subtotal
        return "%0.2f" % total

    def get_total_restaurant(self, obj):
        '''This will calculate total of all number of room's amount in the folio'''
        restaurant_browse = self.env['hotel.folio'].browse(obj.id)
        subtotal = 0.00
        for restaurant_line in restaurant_browse.food_lines:
            subtotal = subtotal + restaurant_line.price_subtotal
        total = subtotal
        return "%0.2f" % total

    def get_total_transport(self, obj):
        '''This will calculate total of all number of transport amount in the folio'''
        transport_browse = self.env['hotel.folio'].browse(obj.id)
        subtotal = 0.00
        for transport_line in transport_browse.transport_line_ids:
            subtotal = subtotal + transport_line.price_subtotal
        total = subtotal
        return "%0.2f" % total

    def get_count(self):
        # print("get_counttttttttttttttt",self)
        '''This method will be maintain the serial number in number of services'''
        count_line = 0
        count_line += 1
        # print(">>>>>>>>>>>>>.count line", count_line)
        return count_line

#     def convert(self):
#         '''We need to convert amount in words, so all translation will be calculate by this method'''
#         amount = self.net_amt
#         cur = "Rupee"
#         amt_en = amount_to_text_en.amount_to_text(amount, 'en', cur)
#         print(">>>>>>>>.amt in words", amount, amt_en)
#         return amt_en

    
    def get_data(self, data):
        folio_browse = self.env['hotel.folio'].browse(data.id)
        total_rows = 0
        if folio_browse.service_lines:
            for count in folio_browse.service_lines:
                total_rows += 1
        return total_rows

    
    def get_lines(self, data):
        '''We need to show the table with fixed number of rows, so all rows count maintain by this method'''
        result = []
        for line in range(1, self.put_lines(self.get_data(data))):
            result.append(line)
        return result

    
    def put_lines(self, len_data):
        val = 0
        if len_data < 8:
            val = 8 - len_data
        else:
            val = 0
        return val

    
    def get_no_of_invoice(self):
        return no_of_invoices

    
    def get_current_date(self):
        cur_date = time.strftime('%d-%b-%Y')
        # print(">>>>>date is ", cur_date)
        return cur_date

    
    def get_quantity(self, quantity):
        total = quantity
        return "%0.2f" %total

    
    def get_total(self, obj):
        '''This will calculate total of all number of room's amount in the folio'''
        folio_browse = self.env['hotel.folio'].browse(obj.id)
        subtotal = 0.00
        for folio_line in folio_browse.room_lines:
            subtotal = subtotal + folio_line.price_subtotal
        total = subtotal
        # print(">>>>>>>>>>.tarrif total", self.get_total)
        return "%0.2f" % total

    
    def get_room_type(self, room_name):
        p_obj = self.env['product.product'].search([('name', '=', room_name)])
        p_obj1 = self.pool.get('product.product').browse(
            self.cr, self.uid, p_obj[0])
        # print(">>>>>>room category", p_obj1.categ_id.name)
        room_type = p_obj1.categ_id.name
        return room_type

    
    def get_alltaxes(self, obj):
        folio_browse = self.env['hotel.folio'].browse(obj.id)
        days = folio_browse.duration
        tax_list = []  # final list
        temp_dict = {}  # dict
        room_tax_amt = 0.00
        service_tax_amt = 0.00
        rest_tax_amt = 0.00
        val = 0.00
        for line in folio_browse.room_lines:
            for c in self.env['account.tax'].compute_all(self._cr, self._uid, line.tax_id, line.price_unit * 1, line.product_uom_qty, line.product_id.id, folio_browse.partner_id.id)['taxes']:
                val += c.get('amount', 0.00)
                name = c.get('name')
                amount = c.get('amount', 0.00)
                flag = 0
                for record in tax_list:
                    if 'name' in record:
                        value = record['name']

                        if value == name:
                            record['amount'] += amount
                            flag = 1
                            break
                if (flag == 0):
                    temp_dict['name'] = name
                    temp_dict['amount'] = amount

                    tax_list.append(temp_dict)
            # print(tax_list, "tax_list")

            room_tax_amt = room_tax_amt + val
            # print(">>>>room tax", room_tax_amt)

        for service_line in folio_browse.service_lines:
            val = 0.00
            for c in self.env['account.tax'].compute_all(self._cr, self._uid, service_line.tax_id, service_line.price_unit * 1, service_line.product_uom_qty, service_line.product_id.id, folio_browse.partner_id.id)['taxes']:
                val += c.get('amount', 0.00)
                name = c.get('name')
                amount = c.get('amount', 0.00)
                flag = 0
                for record in tax_list:
                    if 'name' in record:
                        value = record['name']

                        if value == name:
                            record['amount'] += amount
                            flag = 1
                            break
                if (flag == 0):
                    temp_dict['name'] = name
                    temp_dict['amount'] = amount

                    tax_list.append(temp_dict)
            service_tax_amt = service_tax_amt + val
        for food_line in folio_browse.food_lines:
            val = 0.00
            for c in self.env['account.tax'].compute_all(self._cr, self._uid, food_line.tax_id, food_line.price_unit * 1, food_line.product_uom_qty, food_line.product_id.id, folio_browse.partner_id.id)['taxes']:
                val += c.get('amount', 0.00)
                name = c.get('name')
                amount = c.get('amount', 0.00)
                flag = 0
                for record in tax_list:
                    if 'name' in record:
                        value = record['name']

                        if value == name:
                            record['amount'] += amount
                            flag = 1
                            break
                if (flag == 0):
                    temp_dict['name'] = name
                    temp_dict['amount'] = amount

                    tax_list.append(temp_dict)
            rest_tax_amt = rest_tax_amt + val
        # print(">>>>>>>> tax list", tax_list)
        taxe_amt = room_tax_amt + service_tax_amt
        # print(">>>>>>>>>>>>>tax amt", taxe_amt)
        # print(tax_list, "tax_list-------------------------")
        return tax_list

    
    def get_tax_list(self):
        return list

    
    def get_netamout(self):
        '''count total of rooms with services'''
        net_amt = service_total + taxe_amt
        return net_amt

    
    def get_rest_billl(self, obj):
        folio_browse = self.env['hotel.folio'].browse(obj.id)
        origin_list = []
        for food_line in folio_browse.food_lines:
            if food_line.source_origin not in origin_list:
                origin_list.append(food_line.source_origin)
        res = []
        for origin in origin_list:
            subtotal = 0.00
            for food_line in folio_browse.food_lines:
                if origin == food_line.source_origin:
                    subtotal += food_line.price_subtotal
                dic = {
                    'origin': origin,
                    'amt': subtotal,
                }
            res.append(dic)
        # print(res, "ooooooooooonnnnnnnnnnnnnnnnnoooooooooooo")
        return res

    
    def get_laundry_bill(self, obj):
        folio_browse = self.env['hotel.folio'].browse(obj.id)
        origin_list = []
        for laundry_line in folio_browse.laundry_line_ids:
            if laundry_line.source_origin not in origin_list:
                origin_list.append(laundry_line.source_origin)
        res = []
        for origin in origin_list:
            subtotal = 0.00
            for laundry_line in folio_browse.laundry_line_ids:
                if origin == laundry_line.source_origin:
                    subtotal += laundry_line.price_subtotal
                dic = {
                    'origin': origin,
                    'amt': subtotal,
                }
            res.append(dic)

        return res

    
    def get_netamout_comapny(self, obj):
        '''count total of rooms with services'''
        net_amt = 0.00
        context = {}
        data_dic = {'net_amt': 0.00, 'exchange_rate': 1.00}
        net_amt = service_total + taxe_amt
        folio_browse = self.env['hotel.folio'].browse(obj.id)
        for folio_invoice in folio_browse.invoice_ids:
            payment_rate_currency_id = folio_browse.pricelist_id.currency_id.id
            company_currency_id = folio_browse.company_id.currency_id.id
            context.update({'date': folio_invoice.create_date[0:10]})
            if payment_rate_currency_id and payment_rate_currency_id != company_currency_id:
                tmp = self.env['res.currency'].browse(
                    self._cr, self._uid, payment_rate_currency_id, context=self._context).rate
                exchange_rate = tmp / self.env['res.currency'].browse(
                    self._cr, self._uid, company_currency_id, context=self._context).rate
                net_amt = net_amt * (1 / exchange_rate)
                data_dic['net_amt'] = net_amt
                data_dic['exchange_rate'] = (1 / exchange_rate)
        return data_dic

    
    def get_service_total(self, obj):
        '''This will calculate total of all number of service's amount and room's amount in the folio'''
        folio_browse = self.env['hotel.folio'].browse(obj.id)
        subtotal = 0.00
        for folio_service in folio_browse.service_lines:
            subtotal = subtotal + folio_service.price_subtotal
        service_total = subtotal + self.total
        # print(">>>>>>>.service total", service_total)
        return service_total



class res_currency(models.Model):
    _inherit = 'res.currency'
    
    @api.constrains('name')
    def _check_base(self):
        for wiz in self:
            # print("wiz--------------------------------------------", wiz)
            if wiz.base and wiz.company_id:
                cur_search1 = self.env['res.currency'].search([('company_id', '=', wiz.company_id.id), ('base', '=', True)])
                if cur_search1:
                    raise ValidationError('You Can not have more than 1 base currencies.')
            if not wiz.company_id:
                cur_search1 = self.env['res.currency'].search([('base', '=', True)])
                if cur_search1:
                    raise ValidationError('You Can not have more than 1 base currencies.')
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
