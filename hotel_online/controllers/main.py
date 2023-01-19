from odoo import http
from werkzeug.exceptions import Forbidden
from odoo.http import request
from datetime import datetime, timedelta
import logging
from odoo import tools
import time
import werkzeug.urls
from werkzeug.exceptions import NotFound
from dateutil.relativedelta import relativedelta
from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.osv import expression
from odoo.tools.translate import _
from odoo import fields, models, api
import hashlib
import json
import ast
from odoo import SUPERUSER_ID
from odoo.exceptions import AccessError, MissingError, ValidationError, Warning, UserError
from builtins import int
from odoo.fields import Command
from odoo.addons.payment.controllers import portal as payment_portal
import pytz
import math

utc_time = datetime.utcnow()
_logger = logging.getLogger(__name__)


class PaymentPortal(payment_portal.PaymentPortal):

    @http.route(
        '/shop/payment/transaction/<int:order_id>', type='json', auth='public', website=True
    )
    def shop_payment_transaction(self, order_id, access_token, **kwargs):
        """ Create a draft transaction and return its processing values.

        :param int order_id: The sales order to pay, as a `sale.order` id
        :param str access_token: The access token used to authenticate the request
        :param dict kwargs: Locally unused data passed to `_create_transaction`
        :return: The mandatory values for the processing of the transaction
        :rtype: dict
        :raise: ValidationError if the invoice id or the access token is invalid
        """
        try:
            self._document_check_access('hotel.reservation', order_id, access_token)
        except MissingError as error:
            raise error
        except AccessError:
            raise ValidationError("The access token is invalid.")
        if order_id:
            order = request.env['hotel.reservation'].sudo().search(
                [('id', '=', int(order_id))])
            request.session['sale_last_order_id'] = order.id
        kwargs.update({
            'reference_prefix': None,  # Allow the reference to be computed based on the order
            'sale_order_id': order_id,  # Include the SO to allow Subscriptions to tokenize the tx
        })
        kwargs.pop('custom_create_values', None)  # Don't allow passing arbitrary create values
        tx_sudo = self._create_transaction(
            custom_create_values={'sale_order_ids': [Command.set([order_id])]}, **kwargs,
        )
        # print("TRANSACTION ID===>>>>>",tx_sudo)

        # Store the new transaction into the transaction list and if there's an old one, we remove
        # it until the day the ecommerce supports multiple orders at the same time.
        last_tx_id = request.session.get('__website_sale_last_tx_id')
        last_tx = request.env['payment.transaction'].browse(last_tx_id).sudo().exists()
        if last_tx:
            PaymentPostProcessing.remove_transactions(last_tx)
        request.session['__website_sale_last_tx_id'] = tx_sudo.id

        return tx_sudo._get_processing_values()


class check(http.Controller):

    @http.route(['/page/hotel_online.product_show', '/page/product_show'], auth="public", website=True)
    def contact(self, **kwargs):
        #print "*********** contact ***********",self
        values = {}
        portal_id = request.env['hotel.room'].sudo().search([])
        for port in portal_id:
            port.sudo().write({'state': 'draft'})
        request.website.sale_reset()
        lang_id = request.env['res.lang'].search([('code', '=', request.env.user.lang)])
        if lang_id and lang_id.date_format == '%m/%d/%Y':
            date_format = 'mm/dd/yyyy'
        if lang_id and lang_id.date_format == '%d/%m/%Y':
            date_format = 'dd/mm/yyyy'
        values.update({
            'home':True,
            'date_format':date_format
        })
        # print(values,'=====================================')
        return request.render("hotel_online.product_show", values)

    @http.route('/product_screen/', type='http', auth='public', website=True)
    def get_products(self):
        #         print "*********** get_product ***********",self
        result = {}
        values = {'product': False}
        #         print "values",values
        return request.redirect_query("/page/hotel_online.product_show", values)

    @http.route('/product_search/', auth='public', website=True)
    def search_products(self, **kwargs):
        # print("*********** Search Product ***********", self, kwargs)
        lst = []
        res1 = []
        res = []
        room_ids1 = []
        room_res = {}
        cnt = 0
        result_list11 = []
        count = []
        result = {}
        rm_brw = []
        date_values = list(kwargs.values())
        lang_id = request.env['res.lang'].search([('code', '=', request.env.user.lang)])
        date_format = lang_id.date_format
        if not (kwargs['from_date'] and kwargs['to_date']):
            raise Warning("Please Enter Checkin Date And Checkout Date")
        self._uid = SUPERUSER_ID
        product_id = request.env['product.product'].sudo().search([]).ids
        room_idsss = request.env['hotel.room_type'].sudo().search([]).ids

        if room_idsss:
            room_res11 = {}
            room_brw = request.env['hotel.room_type'].sudo().browse(room_idsss)
            for rbrw in room_brw:
                room_res11 = {}
                res = []
                res1 = []
                img_lst = []
                img_lst_ids = []
                room_res11['type'] = rbrw.name,
                room_res11['description'] = rbrw.description
                img_lst = rbrw.img_ids
                user = request.env['res.users'].sudo().browse(request.uid)
                company = request.env.user.sudo().company_id
                if kwargs['from_date'] and kwargs['to_date']:
                    room_res11['chkin'] = kwargs['from_date']
                    room_res11['chkout'] = kwargs['to_date']
                for i in img_lst:
                    img_lst_ids.append(i.id)
                if rbrw.img_ids:
                    room_res11['image'] = img_lst_ids

                else:
                    room_res11['image'] = ''
                room_ids111 = request.env['hotel.room'].sudo().search([]).ids

                if room_ids111:
                    room_br11 = request.env['hotel.room'].sudo().browse(
                        room_ids111)
                    room_ids1 = []
                    room_res11['room_type_id'] = rbrw.id
                    shop_ids = request.env['sale.shop'].sudo().search(
                        [('company_id', '=', request.env.user.sudo().company_id.id)]).ids
                    shop_brw = request.env['sale.shop'].sudo().browse(
                        shop_ids[0])
                    room_res11['currency'] = shop_brw.pricelist_id.currency_id.symbol
                    for r in room_br11:
                        if r.product_id.product_tmpl_id.categ_id == rbrw.cat_id:
                            room_ids1.append(r.id)
                            # print("room_ids1--", room_ids1)
                for rm in room_ids1:
                    rm1 = request.env['hotel.room'].sudo().browse(rm)
                    # print("rmmmmmmmmmmm111111", rm1)
                    price1 = shop_brw.sudo().pricelist_id.price_get(
                        rm1.product_id.id, False, {
                            'uom': rm1.product_id.uom_id.id,
                            'date': kwargs['from_date'],
                        })[shop_brw.pricelist_id.id]
                    # print("priceee1", price1)
                    room_res11['price'] = round(price1, 2)
                    book_his = request.env['hotel.room.booking.history'].sudo().search(
                        [('history_id', '=', rm)]).ids
                    _logger.info("BOOKING HISTORY===>>>>>%s", book_his)
                    if book_his:
                        room_book = ''
                        book_brw = request.env['hotel.room.booking.history'].sudo().browse(
                            book_his)
                        # print("booooooking browsee", book_brw)
                        for bk_his in book_brw:
                            start_date = datetime.strptime(kwargs['from_date'], '%Y-%m-%d').date()
                            end_date = datetime.strptime(kwargs['to_date'], '%Y-%m-%d').date()
                            try:
                                chkin_date = datetime.strptime(
                                    str(bk_his.check_in), '%Y-%m-%d %H:%M:%S').date()
                            except Exception as e:
                                chkin_date = datetime.strptime(
                                    str(bk_his.check_in), '%Y-%m-%d %H:%M:%S.%f').date()

                            try:
                                chkout_date = datetime.strptime(
                                    str(bk_his.check_out), '%Y-%m-%d %H:%M:%S').date()
                            except Exception as e:
                                chkout_date = datetime.strptime(
                                    str(bk_his.check_out), '%Y-%m-%d %H:%M:%S.%f').date()

                            #                                 if((start_date <= chkin_date and chkout_date <= end_date)or(start_date <= chkin_date and chkout_date >= end_date>chkin_date) or (start_date >= chkin_date and chkout_date >= end_date)or (start_date >= chkin_date and chkout_date >= end_date)):
                            # print("start_date--", start_date, "--end_date--", end_date, "--chkin_date--", chkin_date,
                            #       "--chkout_date--", chkout_date)
                            _logger.info("Booking History ===>>>>>%s", bk_his)
                            
                            primera = type(start_date)
                            segunda = type(chkin_date)
                            
                            _logger.info(primera)
                            _logger.info(segunda)
                            
                            if ((start_date <= chkin_date and (
                                    chkout_date <= end_date or chkout_date >= end_date >= chkin_date)) or (
                                    start_date >= chkin_date and chkout_date >= end_date) or (
                                    start_date <= chkout_date <= end_date)):
                                room_book = bk_his.history_id
                                # print("room_book = ", room_book)
                                break
                            else:
                                if not bk_his.history_id in lst:
                                    lst.append(bk_his.history_id)
                                    # print("------------lst-------", lst)
                        if room_book in lst:
                            lst.remove(room_book)
                            # print("----lst---", lst)
                        for l in lst:
                            rm_brw = l
                            housek = request.env['hotel.housekeeping'].sudo().search(
                                [('room_no', '=', rm_brw.product_id.id), ('state', '=', 'dirty')])
                            # print("hoooouuuuuuuusssssseeeeeeelllkk", housek)
                            if not housek:
                                if rm_brw.product_id.product_tmpl_id.categ_id == rbrw.cat_id:
                                    if not rm_brw in res1:
                                        res1.append(rm_brw)
                                        # print("-----res1------", res1)
                    else:
                        rm_brw = request.env['hotel.room'].sudo().browse(rm)
                        # print("room_____broooseeeee----", rm_brw)
                        if rm_brw.product_id.product_tmpl_id.categ_id == rbrw.cat_id:
                            housek = request.env['hotel.housekeeping'].sudo().search(
                                [('room_no', '=', rm_brw.product_id.id), ('state', '=', 'dirty')])
                            # print("======housek===", housek)
                            if not housek:
                                res1.append(rm_brw)
                                # print("===res1==", res1)
                cnt = 0
                count = []
                adult = []
                child = []

                if rm_brw:
                    # print("rm_brw : ",rm_brw);
                    for i in range(1, (int(rm_brw[0].max_adult) + 1)):
                        adult.append(i)
                    for i in range(1, (int(rm_brw[0].max_child) + 1)):
                        child.append(i)
                    for r in res1:
                        cnt = cnt + 1
                        count.append(cnt)
                        # print("\n\n\ncnt---", cnt, "-------count")
                    #                     print "aduultt--",adult,"--child--",child
                    room_res11['count'] = count,
                    room_res11['adult'] = adult,
                    room_res11['child'] = child,
                    result_list11.append(room_res11)

        values = {
            'length': len(room_idsss),
            'count': count,
            'room_res': result_list11
            # 'room_res': None
        }
        _logger.info("VALUES====>>>>>>>>>%s", values)
        return request.render("hotel_online.product_show", values)

    @http.route(['/page/hotel_online.booking_show', '/page/booking_show'], type='http', auth="public", website=True)
    def contact11(self, **kwargs):
        # print("*********** contact11 ***********")
        values = {}
        return request.render("hotel_online.booking_show", values)

    @http.route('/booking_screen/', type='http', auth='pubilc', website=True)
    def get_productsss(self):
        # print("*********** get_productsss ***********")
        values = {'product': False}
        return http.local_redirect("/page/hotel_online.booking_show", values)

    @http.route(['/product/reserv/'], type='http', auth="public", website=True)
    def reserv_products(self, **kwargs):
        # print("*********** reserv_products ***********", kwargs)
        # cr,  context , pool= request.cr, request.context, request.registry
        values = {}
        rm_types = []
        room_id123 = []
        room_data = []
        lsttt = []
        cnt = 0
        tot = 0
        tax = 0
        dayss = 0
        res1, lst = [], []
        room_id = ''
        self._uid = SUPERUSER_ID
        lang_id = request.env['res.lang'].search([('code', '=', request.env.user.lang)])
        date_format = lang_id.date_format
        date_time_format = lang_id.date_format + ' ' +lang_id.time_format
        user = request.env['res.users'].sudo().browse(request.uid)
        company = request.env.user.sudo().company_id
        if request.uid != 4:
            user_id = request.env['res.users'].sudo().search(
                [('id', '=', request.uid)])
            part_id = user_id.partner_id
        else:
            part_id = request.env['res.partner'].sudo().search(
                [('name', '=', 'Public user'), ('active', '=', False)])

        shop_ids = request.env['sale.shop'].sudo().search(
            [('company_id', '=', company.id)]).ids
        shop_brw = request.env['sale.shop'].sudo().browse(shop_ids[0])
        if 'chkin_id' in kwargs:
            newdate = kwargs['chkin_id'] + " 14:00:00"
        if 'chkout_id' in kwargs:
            newdate1 = kwargs['chkout_id'] + " 12:00:00"
        dt = datetime.strptime(time.strftime(
            '%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S').date()
        no = int(kwargs['len']) + 1
        total_no_adults = 0
        total_no_childs = 0
        for ll in range(1, int(no)):
            lsttt.append(ll)
        # print(kwargs,'============================', lsttt)
        for l1 in lsttt:
            no_of_childs = 0
            no_of_adults = 0
            record = {}
            str1 = 'type_' + str(l1)
            str2 = 'child_' + str(l1)
            str3 = 'adult_' + str(l1)
            str4 = 'sel_' + str(l1)
            str5 = 'no_room_' + str(l1)
            if str1 in kwargs:
                record.update({'room_type': int(kwargs[str1])})

            if str2 in kwargs:
                record.update({'child': int(kwargs[str2])})
                no_of_childs = int(kwargs[str2])

            if str3 in kwargs:
                record.update({'adult': int(kwargs[str3])})
                no_of_adults += int(kwargs[str3])

            if str4 in kwargs:
                record.update({'chk': kwargs[str4]})

            if str5 in kwargs:
                record.update({'no_room': int(kwargs[str5])})
                if int(kwargs[str5]):
                    if no_of_adults:
                        total_no_adults += no_of_adults * int(kwargs[str5])
                    if no_of_childs:
                        total_no_childs += no_of_childs * int(kwargs[str5])

            if record:
                rm_types.append(record)
        room_id = request.session.get('reservation_order_id')

        _logger.info("RESERVATION ID====>>>>>>>>>%s", room_id)

        if not room_id:
            room_id = request.env['hotel.reservation'].sudo().create({
                'partner_id': part_id.id,
                'shop_id': shop_ids[0],
                'adults': total_no_adults,
                'childs': total_no_childs,
                'pricelist_id': shop_brw.pricelist_id.id,
                'source': 'through_web',
                'date_order': time.strftime('%Y-%m-%d %H:%M:%S'),
            })
            _logger.info("RESERVATION ID2====>>>>>>>>>%s", room_id)

            request.session['reservation_order_id'] = room_id.id
        else:
            room_id = request.env['hotel.reservation'].sudo().search(
                [('id', '=', room_id)])
        tot_lines = 0
        # print("priceeeeeeeeeeeeeeee, cin  ,no_of_days", price, cin, no_of_days)
        # print("rmtypes>>>>>>>>>>", rm_types)
        for rtype in rm_types:
            # print("roooOOOOOOOOOOOOOOOOOOOOOOOOoom ", room_id.id)
            room_brwww = request.env['hotel.room_type'].sudo().browse(
                rtype['room_type'])
            #########################################################################################
            room_ids111 = request.env['hotel.room'].sudo().search([]).ids
            if room_ids111:
                room_br11 = request.env['hotel.room'].sudo().browse(
                    room_ids111)
                room_ids1 = []
                for r in room_br11:
                    housek = request.env['hotel.housekeeping'].sudo().search(
                        [('room_no', '=', r.product_id.id), ('state', '=', 'dirty')]).ids
                    if not housek:
                        if r.product_id.product_tmpl_id.categ_id.id == room_brwww.cat_id.id:
                            room_ids1.append(r.id)
                            # print("room_ids1 >>>>>>>>>>>>>>>>>>>>", room_ids1)
            res1 = []
            for rm in room_ids1:
                book_his = request.env['hotel.room.booking.history'].sudo().search(
                    [('history_id', '=', rm)]).ids
                if book_his:
                    room_book = ''
                    book_brw = request.env['hotel.room.booking.history'].sudo().browse(
                        book_his)

                    for bk_his in book_brw:
                        if kwargs['chkin_id'] and kwargs['chkout_id']:
                            start_date = datetime.strptime(
                                kwargs['chkin_id'], '%Y-%m-%d').date()
                            # print('________________')
                            end_date = datetime.strptime(
                                kwargs['chkout_id'], '%Y-%m-%d').date()
                            try:
                                chkin_date = datetime.strptime(
                                    str(bk_his.check_in), '%Y-%m-%d %H:%M:%S').date()
                            except Exception as e:
                                chkin_date = datetime.strptime(
                                    str(bk_his.check_in), '%Y-%m-%d %H:%M:%S.%f').date()

                            try:
                                chkout_date = datetime.strptime(
                                    str(bk_his.check_out), '%Y-%m-%d %H:%M:%S').date()
                            except Exception as e:
                                chkout_date = datetime.strptime(
                                    str(bk_his.check_out), '%Y-%m-%d %H:%M:%S.%f').date()

                            #                             if not ((start_date <= chkin_date and chkout_date <= end_date)or(start_date <= chkin_date and chkout_date >= end_date) or (start_date >= chkin_date and chkout_date >= end_date)or (start_date >= chkin_date and chkout_date >= end_date)):
                            #                                 lst.append(bk_his.history_id)

                            if ((start_date <= chkin_date and (
                                    chkout_date <= end_date or chkout_date >= end_date >= chkin_date)) or (
                                    start_date >= chkin_date and chkout_date >= end_date) or (
                                    start_date <= chkout_date <= end_date)):
                                room_book = bk_his.history_id
                                break
                            else:
                                if not bk_his.history_id in lst:
                                    lst.append(bk_his.history_id)
                    if room_book in lst:
                        lst.remove(room_book)
                    for l in lst:
                        rm_brw = l
                        if rm_brw.product_id.product_tmpl_id.categ_id == room_brwww.cat_id:
                            if not rm in res1:
                                res1.append(rm_brw)
                else:
                    rm_brw = request.env['hotel.room'].sudo().browse(rm)
                    if rm_brw.product_id.product_tmpl_id.categ_id == room_brwww.cat_id:
                        res1.append(rm_brw)
            # print("rtypes>>>>>>>>>>>>>>", rtype)
            if 'no_room' in rtype and 'chk' in rtype:
                if rtype['chk'] == 'on':
                    for lno in range(0, (int(rtype['no_room']))):
                        
                        no_of_days = (datetime.strptime(newdate1, '%Y-%m-%d %H:%M:%S') - datetime.strptime(newdate, '%Y-%m-%d %H:%M:%S')).total_seconds()
                        # print("No Of Dayssss=====>>>>>>>",no_of_days)
                        
                        no_of_days = no_of_days / 86400

                        
                        no_of_days = "{:.2f}".format(no_of_days)
                        _logger.info("DIFFERENCE==>>>>>>>>>{}".format(no_of_days))
                        no_of_days = math.ceil(float(no_of_days))

                        _logger.info("NO OF DAYS====>>>>>%s", no_of_days)
                        cin = str(datetime.strptime(
                            newdate, '%Y-%m-%d %H:%M:%S').date())
                        price = shop_brw.sudo().pricelist_id.price_get(
                            res1[lno].product_id.id, no_of_days, {
                                'uom': res1[lno].product_id.uom_id.id,
                                'date': cin,
                            })[shop_brw.pricelist_id.id]
                        # print("priceeeeeeeeeeeeeeee, cin  ,no_of_days", price, cin, no_of_days)
                        # print("roooOOOOOOOOOOOOOOOOOOOOOOOOoom ", room_id.id)
                        vals = {
                            'checkin': datetime.strptime(newdate, '%Y-%m-%d %H:%M:%S'),
                            'checkout': datetime.strptime(newdate1, '%Y-%m-%d %H:%M:%S'),
                            'categ_id': room_brwww.cat_id.id,
                            'room_number': res1[lno].product_id.id,
                            # 'taxes_id': [(6, 0, [res1[lno].taxes_id.id])],
                            'line_id': room_id.id,
                            'price': price,
                            'number_of_days': no_of_days,
                        }
                        vals = self.set_checkin_checkout(vals)
                        _logger.info("VALSSS===>>>>>>%s", vals)
                        room_line_id = request.env['hotel.reservation.line'].sudo().create(
                            vals)

                        if res1[lno].taxes_id.id:
                            room_line_id.update(
                                {'taxes_id': [(6, 0, [res1[lno].taxes_id.id])]})
                        for rec in room_line_id:
                            room_line_id = request.env['hotel.room'].sudo().search(
                                [('product_id', '=', rec.room_number.id)])
                            _logger.info(
                                "ROOM LINE ID=====>>>%s", room_line_id)
                            vals = {
                                'partner_id': part_id.id,
                                'check_in': rec.checkin,
                                'check_out': rec.checkout,
                                'history_id': room_line_id.id,
                                'product_id': rec.room_number.id,
                                'booking_id': room_id.id,
                                'state': 'draft',
                                'category_id': room_line_id.categ_id.id,
                                'name': rec.room_number.name,
                                'check_in_date': (rec.checkin).date(),
                                'check_out_date': (rec.checkout).date(),
                            }
                            _logger.info(
                                "VALS Booking History=======>>>>>>>>>>>%s", vals)
                            room_his_id = request.env['hotel.room.booking.history'].sudo().create(
                                vals)

            dict = {}
            if 'no_room' in rtype and 'chk' in rtype:
                tot_lines = tot_lines + rtype['no_room']
                # print("tot_linesss", tot_lines)
                room_brw = request.env['hotel.room_type'].sudo().browse(
                    rtype['room_type'])
                for lll in range(1, (int(rtype['no_room'] + 1))):
                    dict = {'rm_name': room_brw.name}
                    # print("dictionaaaaaaaaaaaaaaary", dict)
                    if room_brw.img_ids:
                        dict.update({'image': room_brw.img_ids[0].id})
                    if 'child' in rtype:
                        dict.update({'child': int(rtype['child'])})
                    if 'adult' in rtype:
                        dict.update({'adult': int(rtype['adult'])})
                    if 'chkin_id' in kwargs:
                        dict.update({'chkin': kwargs['chkin_id']})
                    if 'chkout_id' in kwargs:
                        dict.update({'chkout': kwargs['chkout_id']})
                    delta = (datetime.strptime(newdate1, '%Y-%m-%d %H:%M:%S')) - (
                        datetime.strptime(newdate, '%Y-%m-%d %H:%M:%S'))

                    dayss = delta.total_seconds()
                    dayss = dayss / 86400
                    dayss = "{:.2f}".format(dayss)
                    _logger.info("DIFFERENCE==>>>>>>>>>{}".format(dayss))
                    dayss = math.ceil(float(dayss))
                    # if delta.days == 0:
                    #     nights = 1
                    #     dayss = 1
                    # else:
                    #     nights = delta.days
                    nights = dayss
                    if delta:
                        dict.update({'nights': nights})
                    dict.update({'img': company.currency_id.symbol})
                    room_search = request.env['hotel.room'].sudo().search(
                        []).ids
                    if room_search:
                        for rm_sear in room_search:
                            rm_brw = request.env['hotel.room'].sudo().browse(
                                rm_sear)
                            if rm_brw.product_id.product_tmpl_id.categ_id.id == room_brw.cat_id.id:
                                price = rm_brw.lst_price * dayss
                                tot = tot + rm_brw.lst_price
                                # print("tot tot tot tot ", tot)
                                tax = tax + price * \
                                      (rm_brw.taxes_id.amount / 100)
                                # tax = tax + 0.00
                                break
                    dict.update({'price': "%.2f" % price, })
                    room_data.append(dict)
        values = {
            'room_data': room_data,
            'length': tot_lines,
            'tot': "%.2f" % (tot * dayss),
            'tax': "%.2f" % tax,
            'tot_tax': "%.2f" % ((tot * dayss) + tax),
            'room_id': room_id.id,
        }
        # print("vaaaaalues", values)
        return request.render("hotel_online.booking_show", values)

    def set_checkin_checkout(self, vals):
        user_id = request.env['res.users'].sudo().search([('id', '=', 2)])
        tz = pytz.timezone(user_id.tz)
        time_difference = tz.utcoffset(utc_time).total_seconds()

        _logger.info("TIME DIFFERENCE===>>>>>>>>>>>>>>>>>>{}".format(time_difference))
        _logger.info("VALS SHOP ID===>>>>{}".format(vals.get('line_id')))
        reservation_id = request.env['hotel.reservation'].sudo().search([('id', '=', vals.get('line_id'))])
        _logger.info("RESERVATION ID===>>>>>>{}".format(reservation_id))
        sale_shop_id = request.env['sale.shop'].sudo().search([('id', '=', reservation_id.shop_id.id)])
        _logger.info("SALE SHOP ID ===>>>>>>>>>>>>>{}".format(sale_shop_id))

        checkout_policy_id = request.env['checkout.configuration'].sudo().search([('shop_id', '=', sale_shop_id.id)])
        if checkout_policy_id.name == 'custom':
            time = int(checkout_policy_id.time)

            checkin = vals.get('checkin')
            checkin = datetime(checkin.year, checkin.month, checkin.day)
            checkin = checkin + timedelta(hours=14)

            checkout = vals.get('checkout')
            checkout = datetime(checkout.year, checkout.month, checkout.day)
            checkout = checkout + timedelta(hours=12)

            checkout = checkout - timedelta(seconds=time_difference)
            checkin = checkin - timedelta(seconds=time_difference)

            _logger.info("\n\n\n\n\nVALS=====>>>>>>>>>>>>>>>>>>{}".format(checkout))
            vals.update({'checkout': checkout, 'checkin': checkin})
        else:
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            _logger.info("CURRENT TIME ===>>>>>>>>{}".format(current_time))
            checkin = vals.get('checkin')
            _logger.info("CHECKIN TIME===>>>>>>>>>>>{}".format(type(checkin)))
            from_string = datetime.strptime(current_time, "%H:%M:%S")
            _logger.info("CHECKIN TIME===>>>>>>>>>>>{}".format(type(from_string)))

            checkin = checkin + timedelta(hours=from_string.hour, minutes=from_string.minute,
                                          seconds=from_string.second)

            _logger.info("CHECKIN TIME===>>>>>>>>>>>{}".format(checkin))

            checkout = vals.get('checkout')
            checkout = checkout + timedelta(hours=from_string.hour, minutes=from_string.minute,
                                            seconds=from_string.second)

            vals.update({'checkout': checkout, 'checkin': checkin})
        return vals

    @http.route(['/product_remove/'], type='http', auth="public", website=True)
    def remove_products(self, **kwargs):
        # print("*********** remove_products ***********", kwargs)
        values = {}
        i = 0
        tot = 0
        room_data = []
        if 'len' in kwargs:
            data = ast.literal_eval(kwargs['len'])['data']
            for l in data:
                if 'room_type' in kwargs and 'rm_name' in l and str(l['rm_name']) == str(kwargs['room_type']):
                    if 'adult' in kwargs and 'adult' in l and str(l['adult']) == str(kwargs['adult']):
                        if 'child' in kwargs and 'child' in l and str(l['child']) == str(kwargs['child']):
                            data.pop(i)
                            i = i + 1
                            part_id = request.env['res.partner'].sudo().search(
                                [('name', '=', 'Public user'), ('active', '=', False)], limit=1)
                            reserv_se = request.env['hotel.reservation'].sudo().search(
                                [('partner_id', '=', part_id)])
                            if reserv_se:
                                for r_sear in reserv_se:
                                    reserv_br = request.env['hotel.reservation'].sudo().browse(
                                        r_sear)
                                    if datetime.strptime(reserv_br.date_order,
                                                         '%Y-%m-%d %H:%M:%S').date() == datetime.strptime(
                                        time.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S').date():
                                        if reserv_br.reservation_line:
                                            for rl in reserv_br.reservation_line:
                                                if 'chkin' in kwargs and 'chkout' in kwargs:
                                                    rtse = request.env['hotel.room_type'].sudo().search(
                                                        [('name', '=', kwargs['room_type'])])
                                                    rtypr_br = request.env['hotel.room_type'].sudo().browse(
                                                        rtse)
                                                    chin = datetime.strptime(
                                                        rl.checkin, '%Y-%m-%d %H:%M:%S').date()
                                                    kchin = datetime.strptime(
                                                        kwargs['chkin'], '%Y-%m-%d').date()
                                                    chout = datetime.strptime(
                                                        rl.checkout, '%Y-%m-%d %H:%M:%S').date()
                                                    kcout = datetime.strptime(
                                                        kwargs['chkout'], '%Y-%m-%d').date()
                                                    if (chin == kchin and (chout == kcout) and (
                                                            rl.categ_id.id == rtypr_br.cat_id.id)):
                                                        request.env['hotel.reservation.line'].unlink(
                                                            rl.id)
                                                        break
        for d1 in data:
            tot = tot + d1['price']
        values = {
            'room_data': data,
            'tot': tot}
        return request.render("hotel_online.booking_show", values)

    def checkout_values(self, data=None):
        countries = request.env['res.country'].sudo().search([])
        states_ids = request.env['res.country.state'].sudo().search([])
        # request.env['res.country.state'].sudo().browse([states_ids])
        states = states_ids
        # partner = request.env['res.partner'].sudo().search(
        #     [("user_id", "=", request.uid)])
        user_id = request.env['res.users'].sudo().search([('id', '=', request._uid)])
        partner = user_id.partner_id
        order = None

        shipping_id = data and data.get('shipping_id') or None
        shipping_ids = []
        checkout = {}
        if not data:
            if request.uid != request.website.user_id.id:
                checkout.update(self.checkout_parse("billing", partner))
            else:
                order1 = request.website.get_reservation()
                order = request.env['hotel.reservation'].sudo().browse(order1)
                # print("order***********", order)
                if order.partner_id:
                    domain = [("partner_id", "=", order.partner_id.id)]
                    # print("domainnnnnnnn ", domain)
                    user_ids = request.env['res.users'].sudo().search(
                        domain)
                    # print("user_idssssssssssss", user_ids)
                    if not user_ids or request.website.user_id.id not in user_ids:
                        checkout.update(self.checkout_parse(
                            "billing", order.partner_id))
        else:
            checkout = self.checkout_parse('billing', data)
            # print("checkouttttttttt ", checkout)

        # Default search by user country
        if not checkout.get('country_id'):
            country_code = request.session['geoip'].get('country_code')
            # print("cooooountryy cooode", country_code)
            if country_code:
                country_ids = request.env['res.country'].search(
                    [('code', '=', country_code)], limit=1)
                # print("country_ids", country_ids)
                if country_ids:
                    checkout['country_id'] = country_ids[0]

        values = {
            'countries': countries,
            'states': states,
            'checkout': checkout,
            'error': {},
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
            'only_services': order or False
        }
        #         print "valuuuuuuuesssss of checkout_values",values
        return values

    mandatory_billing_fields = ["name", "phone",
                                "email", "street", "city", "country_id"]
    optional_billing_fields = ["street", "state_id", "zip"]
    mandatory_shipping_fields = [
        "name", "phone", "street", "city", "country_id"]
    optional_shipping_fields = ["state_id", "zip"]

    def checkout_parse(self, address_type, data, remove_prefix=False):
        """ data is a dict OR a partner browse record
        """
        # set mandatory and optional fields
        assert address_type in ('billing', 'shipping')
        if address_type == 'billing':
            all_fields = self.mandatory_billing_fields + self.optional_billing_fields
            prefix = ''
        else:
            all_fields = self.mandatory_shipping_fields + self.optional_shipping_fields
            prefix = 'shipping_'
        # set data
        if isinstance(data, dict):
            query = dict((prefix + field_name, data[prefix + field_name])
                         for field_name in all_fields if prefix + field_name in data)
        else:
            query = dict((prefix + field_name, getattr(data, field_name))
                         for field_name in all_fields if getattr(data, field_name))
            if address_type == 'billing' and data.parent_id:
                query[prefix + 'street'] = data.parent_id.name

        if query.get(prefix + 'state_id'):
            query[prefix + 'state_id'] = int(query[prefix + 'state_id'])
        if query.get(prefix + 'country_id'):
            query[prefix + 'country_id'] = int(query[prefix + 'country_id'])

        if not remove_prefix:
            return query
        return dict((field_name, data[prefix + field_name]) for field_name in all_fields if prefix + field_name in data)

    #    Validation for billing information
    def checkout_form_validate(self, data):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        error = dict()
        error_message = []

        # Validation
        for field_name in self.mandatory_billing_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'

        # email validation
        if data.get('email') and not tools.single_email_re.match(data.get('email')):
            error["email"] = 'error'
            error_message.append(
                _('Invalid Email! Please enter a valid email address.'))

        # vat validation
        if data.get("vat") and hasattr(registry["res.partner"], "check_vat"):
            if request.website.company_id.vat_check_vies:
                # force full VIES online check
                check_func = registry["res.partner"].vies_vat_check
            else:
                # quick and partial off-line checksum validation
                check_func = registry["res.partner"].simple_vat_check
                # print(data.get('vat'))
            # vat_country, vat_number = registry["res.partner"]._split_vat(data.get("vat"))
            # print('error : ', vat_country, vat_number)
            # if not check_func(cr, uid, vat_country, vat_number, context=None):  # simple_vat_check
            #     error["vat"] = 'error'

        if data.get("shipping_id") == -1:
            for field_name in self.mandatory_shipping_fields:
                field_name = 'shipping_' + field_name
                if not data.get(field_name):
                    error[field_name] = 'missing'
        # error message for empty required fields
        if [err for err in list(error.values()) if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))
        return error, error_message

    def checkout_form_save(self, checkout):
        #         cr, uid, context, registry = request.cr, request.uid, request.context, request.registry
        order1 = request.website.get_reservation()
        order = request.env['hotel.reservation'].sudo().browse(order1)
        #         order = request.website.get_reservation()
        orm_partner = request.env['res.partner']
        orm_user = request.env['res.users']
        order_obj = request.env['hotel.reservation']

        #         partner_lang = request.lang if request.lang in [lang.code for lang in request.website.language_ids] else None
        #         print "partner_lang", partner_lang
        partner_lang = request.lang if request.lang in request.website.mapped(
            'language_ids.code') else None
        billing_info = {}
        if partner_lang:
            billing_info['lang'] = partner_lang
        billing_info.update(self.checkout_parse('billing', checkout, True))

        # set partner_id
        partner_id = None
        if request.uid != request.website.user_id.id:
            #             partner_id = orm_user.browse(cr, SUPERUSER_ID, uid, context=context).partner_id.id
            partner_id = orm_user.sudo().browse(request.uid).id
        elif order.partner_id:
            user_ids = request.env['res.users'].sudo().search(
                [("partner_id", "=", order.partner_id.id)])
            # print("\nUuuuuserrrr id", user_ids)
            if not user_ids or request.website.user_id.id not in user_ids:
                partner_id = order.partner_id.id
                # print("Paaaaaaaaaartneeeeeeeeeer Id", partner_id)

        # save partner informations
        if billing_info.get('country_id'):
            billing_info['property_account_position_id'] = request.env[
                'account.fiscal.position'].sudo()._get_fpos_by_region(
                billing_info['country_id'], billing_info.get(
                    'state_id') or False, billing_info.get('zip'),
                                            billing_info.get('vat') and True or False)
        if partner_id and request.website.partner_id.id != partner_id:
            partner_id1 = orm_partner.browse(partner_id)
            if not billing_info.get('state_id'):
                billing_info.pop('state_id')
            valiee = partner_id1.sudo().write(billing_info)
        else:
            # create partner
            partner_id = request.env['res.partner'].sudo().create(billing_info)
        order.write({'partner_id': partner_id})
        order_info = {
            'message_partner_ids': [(4, partner_id), (3, request.website.partner_id.id)],
        }
        zz = order_obj.sudo().write(order_info)


    @http.route(['/page/hotel_online.booking_show', '/partner/checkout'], type='http', auth="public", website=True)
    def checkout(self, **post):
        _logger.info("@@@@@@@@@@@@@@@%s", request.session)
        if request.session.get('reservation_order_id'):
            # print(self, " ^^^^^^^^ checkout ^^^^^^ ", post)
            cr, context = request.cr, request.context

            reservation = request.website.get_reservation()
            # print("reservationnnnnnnnnn", reservation)
            redirection = self.checkout_redirection(reservation)
            # print("=====redirection ", redirection)
            if redirection:
                return redirection

            values = self.checkout_values()
            # print("valueeeessss", values)

            return request.render("hotel_online.res_partner_show", values)
        else:
            return request.redirect("/product_screen/")

    @http.route(['/custom/search/read'], type='json', auth="public", website=True)
    def custom_search_read(self, **post):
        # print("self ----------------",post)
        reservation_obj = request.env['hotel.reservation'].sudo().search(
            [('id', '=', int(post['room_id']))])
        if reservation_obj and len(reservation_obj) > 0:
            if reservation_obj.state == 'cancel':
                return False
            else:
                return True
        return False

    @http.route(['/partner_add/'], type='http', auth="public", website=True, csrf=False)
    def confirm_order(self, **post):
        _logger.info("POST====>>>>>%s", post)
        vals = {
            'name': post.get('name'),
            'email': post.get('email'),
            'phone': post.get('phone'),
            'street': post.get('street'),
            'city': post.get('city'),
            'zip': post.get('zip'),
            'country_id': int(post.get('country_id')),

        }
        _logger.info("STATE ID===>>>>>%s", post.get('state_id'))
        if post.get('state_id'):
            vals.update({'state_id': int(post.get('state_id')), })
        else:
            vals.update({'state_id': None})
        _logger.info("VALS===>>>>%s", vals)
        user_id = request.env['res.users'].sudo().search(
            [('id', '=', request._uid)])
        if user_id:
            partner_id = user_id.partner_id
            if partner_id:
                _logger.info("PARTNER ID===>>>>%s", partner_id)
                partner_id.sudo().write(vals)
        order = request.website.get_reservation()
        if not order:
            return request.redirect("/shop")
        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        values = self.checkout_values(post)
        values["error"], values["error_message"] = self.checkout_form_validate(
            values["checkout"])
        if values["error"]:
            return request.render("hotel_online.res_partner_show", values)

        self.checkout_form_save(values["checkout"])
        _logger.info("PARTNER ID===>>>>%s", values)
        return request.redirect("/shop/payment")

    @http.route(['/shop/payment'], type='http', auth="public", website=True)
    def payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.acquirer. State at this point :

         - a draft sales order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.acquirer website but closed the tab without
           paying / canceling
        """
        order = request.website.get_reservation()
        # print("@@@@@@@@@@@@@@@222order::::::::::::::::::::::::::::::::::::::", order)
        order_browse = request.env['hotel.reservation'].sudo().browse(order)
        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        render_values = self._get_shop_payment_values(order_browse, **post)

        if render_values['errors']:
            render_values.pop('acquirers', '')
            render_values.pop('tokens', '')
        # print("\n\n\n\n renderrrrrrrrr_valuesss===", render_values)
        _logger.info("RENDER VALUES====>>>>%s", render_values)
        return request.render("hotel_online.payment123", render_values)

    def _get_shop_payment_values(self, order, **kwargs):
        logged_in = not request.env.user._is_public()
        acquirers_sudo = request.env['payment.acquirer'].sudo()._get_compatible_acquirers(
            order.company_id.id,
            order.partner_id.id,
            currency_id=order.currency_id.id,
            sale_order_id=order.id,
            website_id=request.website.id,
        )  # In sudo mode to read the fields of acquirers, order and partner (if not logged in)
        tokens = request.env['payment.token'].search(
            [('acquirer_id', 'in', acquirers_sudo.ids), ('partner_id', '=', order.partner_id.id)]
        ) if logged_in else request.env['payment.token']
        fees_by_acquirer = {
            acq_sudo: acq_sudo._compute_fees(
                order.total_cost1, order.currency_id, order.partner_id.country_id
            ) for acq_sudo in acquirers_sudo.filtered('fees_active')
        }
        # Prevent public partner from saving payment methods but force it for logged in partners
        # buying subscription products
        show_tokenize_input = logged_in \
                              and not request.env['payment.acquirer'].sudo()._is_tokenization_required(
            sale_order_id=order.id
        )
        return {
            'website_sale_order': order,
            'errors': [],
            'partner': order.partner_id,
            'order': order,
            'payment_action_id': request.env.ref('payment.action_payment_acquirer').id,
            # Payment form common (checkout and manage) values
            'acquirers': acquirers_sudo,
            'tokens': tokens,
            'fees_by_acquirer': fees_by_acquirer,
            'show_tokenize_input': show_tokenize_input,
            'amount': order.total_cost1,
            'currency': order.currency_id,
            'partner_id': order.partner_id.id,
            'access_token': order.access_token,
            'transaction_route': f'/shop/payment/transaction/{order.id}',
            'landing_route': '/shop/payment/validate',
        }

    @http.route('/shop/payment/validate', type='http', auth="public", website=True, sitemap=False)
    def shop_payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :

         - UDPATE ME
        """

        transaction_id = request.session.get('__website_sale_last_tx_id')
        if sale_order_id is None:
            order = request.website.get_reservation()
        else:
            order = request.env['hotel.reservation'].sudo().browse(sale_order_id)
            assert order.id == request.session.get('sale_last_order_id')
        order = request.env['hotel.reservation'].sudo().browse(order)

        if transaction_id:
            tx = request.env['payment.transaction'].sudo().browse(transaction_id)

        else:
            tx = None

        if not order or (order.total_cost1 and not tx):
            return request.redirect('/shop')

        if order and not order.total_cost1 and not tx:
            # order.with_context(send_email=True).action_confirm()
            return request.redirect(order.get_portal_url())

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset()
        if tx and tx.state == 'draft':
            return request.redirect('/shop')

        PaymentPostProcessing.remove_transactions(tx)

        return request.redirect('/shop/confirmation1')

    # @http.route('/shop/payment/validate', type='http', auth="public", website=True)
    # def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
    #     """ Method that should be called by the server when receiving an update
    #     for a transaction. State at this point :

    #      - UDPATE ME
    #     """
    #     _logger.info("@@@@@@@@@@@@@@@@@@@@@@@@%s",transaction_id)

    #     if not order or (order.total_cost1 and not tx):

    #         return request.redirect('/shop')

    #     elif tx and tx.state == 'cancel':
    #         order.action_cancel()

    #     # clean context and session, then redirect to the confirmation page
    #     request.website.sale_reset()
    #     if tx and tx.state == 'draft':
    #         return request.redirect('/shop')
    #     return request.redirect('/shop/confirmation1')

    @http.route(['/shop/confirmation1'], type='http', auth="public", website=True)
    def payment_confirmation(self, **post):
        # print("======payment_confirmation========")
        """ End of checkout process controller. Confirmation is basically seing
         the status of a sale.order. State at this point :
          - should not have any context / session info: clean them
          - take a sale.order id, because we request a sale.order and are not
            session dependant anymore
         """
        sale_order_id = request.session.get('reservation_order_id')
        _logger.info("SALE ORDER IDDDDD========>>>>>>>%s", sale_order_id)
        if sale_order_id:
            order = request.env['hotel.reservation'].sudo().browse(
                sale_order_id)
            return request.render("hotel_online.confirmation1", {'order': order})
        else:
            return request.redirect('/shop')

    @http.route(['/payment/status'], type="http", auth="public", website=True, sitemap=False)
    def payment_status_page(self, **kwargs):
        tx = request.website.sale_get_transaction()
        order_id = request.website.get_reservation()
        order_id = request.env['hotel.reservation'].sudo().search([('id', '=', order_id)])
        order = None
        # order_obj = request.env['payment.transaction'].browse(order_id)
        if tx and tx.state == 'done':
            # print("TRANSACTION==>>>>>>>>>>>>",tx)
            order = tx.sale_order_id

            if order_id:
                order_id.confirmed_reservation()
                payment_vals = {
                    'amt': tx.amount,
                    'reservation_id': order_id.id,
                    'payment_date': datetime.now().date(),
                    'deposit_recv_acc': order_id.partner_id.property_account_receivable_id.id,
                    'journal_id': tx.acquirer_id.journal_id.id,
                }
                _logger.info("@@@@@@@@@@@@@@@@@@@%s", payment_vals)
                wiz_obj = request.env['advance.payment.wizard'].sudo().with_context(active_model='hotel.reservation',
                                                                                    active_id=order_id.id).create(
                    payment_vals)
                # print("WIZARD OBJECT==>>>>>>>>>>",wiz_obj)
                wiz_obj.with_context(active_model='hotel.reservation').payment_process()
                _logger.info("WIZARD======>>>>>>>>>>%s", wiz_obj)
                order = order_id
        elif order_id:
            # print("ORDER IDDDDDDDDDDDDDDDDDDD==>>",order_id)
            order_obj = request.env['hotel.reservation'].sudo().browse(
                order_id)
            # print("order_obj --------",order_obj.id.id)
            tx = request.env['payment.transaction'].sudo().search(
                [('sale_order_id', '=', order_obj.id.id), ('state', '=', 'draft')], limit=1)
            # print("****",tx,tx.state)
            tx.write({'state': 'done'})
            order = tx.sale_order_id
            # print("ORDER=====>>>>>",order)
            if order:
                order.confirmed_reservation()
                payment_vals = {
                    'amt': tx.amount,
                    'reservation_id': order.id,
                    'payment_date': datetime.now().date(),
                    'deposit_recv_acc': order.partner_id.property_account_receivable_id.id,
                    'journal_id': tx.acquirer_id.journal_id.id,
                }
                wiz_obj = request.env['advance.payment.wizard'].sudo().create(payment_vals)
                # print("WIZARD OBJECT===>>>>>>>>>>>>>",wiz_obj)
                wiz_obj.with_context(active_model='hotel.reservation', active_id=order_id.id).payment_process()
            else:
                order = order_id
            # print("ORDER============>>>>>>>>>>>>",order)
        # _logger.info("ORDER====>>>>>>>>>>>>>>>>>>>{}".format(order))
        return request.render("hotel_online.confirmation1", {'order': order})

    @http.route('/shop/payment/token', type='http', auth='public', website=True, sitemap=False)
    def payment_token(self, pm_id=None, **kwargs):
        """ Method that handles payment using saved tokens

        :param int pm_id: id of the payment.token that we want to use to pay.
        """
        # print("inheritted !!!", pm_id,)
        # tx = request.website.sale_get_transaction()
        tx = request.website.sale_get_transaction(
        ) or request.env['payment.transaction'].sudo()
        order_id = request.website.get_reservation()
        order = request.env['hotel.reservation'].sudo().browse(order_id)
        # print("\n \n token method --------***--------", tx, order)
        if not request.env['payment.token'].sudo().search_count([('id', '=', pm_id)]):
            return request.redirect('/shop/?error=token_not_found')

        payment_token = request.env['payment.token'].sudo().search([
            ('id', '=', pm_id)])
        acquirer = payment_token.acquirer_id
        tx_type = 'form'
        if not acquirer.payment_flow == 's2s':
            tx_type = 'form_save'
        # print("\n details -----------:,",payment_token,acquirer,tx_type)
        x = tx._check_or_create_sale_tx(
            order, acquirer, payment_token=payment_token, tx_type=tx_type)
        # print("********--------",x)

        # vals = {'payment_token_id': pm_id, 'return_url': '/shop/payment/validate'}
        # tx = order._create_payment_transaction(vals)
        # PaymentProcessing.add_payment_transaction(x)
        # print(ahmed)
        return request.redirect('/payment/process')

    @http.route('/shop/payment/get_status123/<int:sale_order_id>', type='json', auth="public", website=True)
    def payment_get_status(self, sale_order_id, **post):
        # print("********payment_get_status**********")
        order = request.env['hotel.reservation'].sudo().browse(sale_order_id)
        assert order.id == request.session.get('reservation_order_id')
        if not order:
            return {
                'state': 'error',
                'message': '<p>%s</p>' % _('There seems to be an error with your request.'),
            }
        tx_ids = request.env['payment.transaction'].sudo().search([
            '|', ('sale_order_id', '=', order.id), ('reference', '=', order.name)
        ])
        if not tx_ids:
            if order.total_cost1:
                return {
                    'state': 'error',
                    'message': '<p>%s</p>' % _('There seems to be an error with your request.'),
                }
            else:
                state = 'done'
                message = ""
                validation = None
        else:
            # print("TRansactionsssss   ============    ", tx_ids)
            #             tx = request.env['payment.transaction'].sudo().browse(tx_ids)
            tx = tx_ids
            state = tx.state
            if state == 'done':
                message = '<p>%s</p>' % _('Your payment has been received.')
            elif state == 'cancel':
                message = '<p>%s</p>' % _(
                    'The payment seems to have been canceled.')
            elif state == 'pending' and tx.acquirer_id.validation == 'manual':
                message = '<p>%s</p>' % _(
                    'Your transaction is waiting confirmation.')
                if tx.acquirer_id.post_msg:
                    message += tx.acquirer_id.post_msg
            else:
                message = '<p>%s</p>' % _(
                    'Your transaction is waiting confirmation.')
            # print("Acquirereeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee   ", tx.acquirer_id)
        #             validation = tx.acquirer_id.validation
        return {
            'state': state,
            'message': message,
            'validation': None
        }

    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        product_id = request.env['product.template'].sudo().search(
            [('id', '=', product_id)])
        vals = {
            'product_id': product_id.id,
            'name': product_id.name,
            'product_uom': product_id.uom_id.id,
            'product_uom_qty': add_qty,
            'price_unit': product_id.list_price,
            'tax_id': [(6, 0, [product_id.taxes_id.id])],
        }
        _logger.info("RESERVATION ID====>>>>%s",
                     request.session.get('reservation_order_id'))
        if request.session.get('reservation_order_id'):
            order = request.env['hotel.reservation'].sudo().search(
                [('id', '=', request.session.get('reservation_order_id'))])
            vals.update({'other_items_id': order.id, })
        else:
            user = request.env['res.users'].sudo().browse(request.uid)
            company = request.env.user.sudo().company_id
            _logger.info("REQUEST UID====>>>>%s", request.uid)
            if request.uid != 4:
                user_id = request.env['res.users'].sudo().search(
                    [('id', '=', request.uid)])
                part_id = user_id.partner_id
            else:
                part_id = request.env['res.partner'].sudo().search(
                    [('name', '=', 'Public user'), ('active', '=', False)])

            _logger.info("USER ID====>>>>>%s", part_id)

            shop_ids = request.env['sale.shop'].sudo().search(
                [('company_id', '=', company.id)]).ids
            shop_brw = request.env['sale.shop'].sudo().browse(shop_ids[0])
            order = request.env['hotel.reservation'].sudo().create({
                'partner_id': part_id.id,
                'shop_id': shop_ids[0],
                'pricelist_id': shop_brw.pricelist_id.id,
                'source': 'through_web',
                'date_order': time.strftime('%Y-%m-%d %H:%M:%S'),
            })
            vals.update({'other_items_id': order.id})
            request.session['reservation_order_id'] = order.id
        other_items_id = request.env['other.items'].sudo().create(vals)
        _logger.info("OTHER ITEMS ID===>>>>%s", other_items_id)
        _logger.info("UID====>>>>>..%s", request.uid)
        if request.uid != 4:
            return request.redirect('/shop/payment')
        else:
            return request.redirect('/partner/checkout')

    @http.route(['/other/items/unlink'], type='json', auth="public", website=True)
    def other_items_unlink(self, **post):
        # print("self ----------------",post)
        _logger.info("POST========>>>>>>%s", post)
        other_items_id = request.env['other.items'].sudo().search(
            [('id', '=', int(post.get('other_items_id')))])
        _logger.info("POST========>>>>>>%s", other_items_id)
        other_items_id.unlink()
        return True

    def checkout_redirection(self, order):
        # print(" ^^^^^^^^ chechout redirect ^^^^^^ ", order)
        if type(order) == int:
            order = request.env['hotel.reservation'].sudo().browse(order)
            # print("Browseeeee Order  ", order.state)
        if not order or order.state != 'draft':
            request.session['sale_order_id'] = None
            request.session['sale_transaction_id'] = None

        # print(request.env.context.get('website_sale_transaction'))
        tx = request.env.context.get('website_sale_transaction')
        # print("tttttttxxxxx", tx)
        if tx and tx.state != 'draft':
            return request.redirect('/shop/payment/confirmation/%s' % order)


check()
reserv_list = []


class website(models.Model):
    _inherit = 'website'
    _columns = {}

    def get_image(self, a):
        # print("****** get_image *******")
        if 'image' in list(a.keys()):
            return True
        else:
            # print('no img')
            return False

    def get_type(self, record1):
        # print("*****get tyoe*****", self, record1)
        categ_type = record1['type']
        #         print "\n\ncateg_type",categ_type
        categ_ids = self.env['product.category'].sudo().search(
            [('name', '=', categ_type[0])])
        #         print "categ_idsssssss",categ_ids
        categ_records = categ_ids[0]
        #         print "categ_records",categ_records
        #         if categ_records.type == 'view':
        #             return False
        return True

    def check_next_image(self, main_record, sub_record):
        if len(main_record['image']) > sub_record:
            return 1
        else:
            return 0

    def image_url_new(self, record1, field, size=None):
        #         print "====----image_url_new----===",self,record1,field
        """Returns a local url that points to the image field of a given browse record."""
        lst = []
        record = self.env['hotel.room.images'].sudo().browse(record1)
        cnt = 0
        for r in record:
            cnt = cnt + 1
            model = r._name
            sudo_record = r.sudo()
            id = '%s_%s' % (r.id, hashlib.sha1(
                (str(sudo_record.write_date) or str(sudo_record.create_date) or '').encode('utf-8')).hexdigest()[0:7])

            if cnt == 1:
                size = '' if size is None else '/%s' % size
            else:
                size = '' if size is None else '%s' % size
            lst.append('/website/image/%s/%s/%s%s' % (model, id, field, size))
        return lst

    def get_reservation(self):
        # print("------------get_reservation-------------")
        reservation_order_id = request.session.get('reservation_order_id')
        if not reservation_order_id:
            part_id1 = request.env['res.partner'].sudo().search(
                [('name', '=', 'Public user'), ('active', '=', False)])
            # print("part_id1-----", part_id1)
            reservation = request.env['hotel.reservation'].sudo().search(
                [('partner_id', '=', part_id1[0].id)])
            # print("reservation", reservation)
            reserv_list = reservation
            if reservation:
                reservation1 = request.env['hotel.reservation'].sudo().browse(
                    reservation[0])
                # print("reservation1", reservation1)
                request.session['reservation_order_id'] = reservation1.id
                return reservation1.id
        return reservation_order_id

    def sale_get_transaction(self):
        # print("------------sale_get_transaction-------------")
        transaction_obj = self.env['payment.transaction']
        tx_id = request.session.get('__website_sale_last_tx_id')
        # print("------------tx_id-------------", tx_id)
        if tx_id:
            tx_ids = transaction_obj.sudo().search(
                [('id', '=', tx_id), ('state', 'not in', ['cancel'])])
            # print("transactionnnnnnnnnnnn of sale_get_transaction", tx_ids)

            if tx_ids:
                return tx_ids
            #                 return transaction_obj.browse(tx_ids)
            else:
                request.session['sale_transaction_id'] = False
        return False

    #

    def sale_reset(self):
        request.session.update({
            'sale_order_id': False,
            'sale_transaction_id': False,
            'sale_order_code_pricelist_id': False,
            'reservation_order_id': False,
        })


website()


class ResCountry(models.Model):
    _inherit = 'res.country'

    def get_website_sale_countries(self, mode='billing'):
        return self.sudo().search([])

    def get_website_sale_states(self, mode='billing'):
        return self.sudo().state_ids


class CustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'reservation_count' in counters:
            values['reservation_count'] = request.env['hotel.reservation'].sudo().search_count([
            ])
        return values

    @http.route(['/my/reservations/', '/my/reservations/<int:reservation_id>'], type='http', auth='public',
                website=True)
    def template_reservation_render(self, **kwargs):
        values = self._prepare_portal_layout_values()
        reservation_id = kwargs.get('reservation_id')
        if reservation_id:
            order = request.env['hotel.reservation'].sudo().browse(reservation_id)
            values.update({
                'order': order,
                'page_name': 'reservation',
                'default_url': '/my/reservations',
            })
            return request.render('hotel_online.portal_my_reservations_detailed', values)
        reservations = request.env['hotel.reservation'].sudo().search([])
        values.update({'reservations': reservations,
                       'default_url': '/my/reservations',
                       'page_name': 'page'
                       })
        return request.render('hotel_online.portal_my_reservations', values)
