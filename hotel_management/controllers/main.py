import logging
from odoo import http
from odoo.http import request
import json
from datetime import datetime, timedelta, timezone
import pytz
import math
from werkzeug import urls
from odoo.addons.payment import utils as payment_utils
utc_time = datetime.utcnow()

_logger = logging.getLogger(__name__)


class hotelManagementController(http.Controller):

    @http.route(['/hotel/payment/status'], type='http', auth='public')
    def payment_status(self):
        if request.httprequest.method == 'GET':
            order_name = request.httprequest.args.get('order_name')
            amount = request.httprequest.args.get('amount')
            payment_exists = request.env['payment.transaction'].sudo().search(
                [('reference', 'ilike', order_name), ('amount', '=', amount)], limit=1)
            if payment_exists:
                payment_status = payment_exists.state
                if payment_status == 'done':
                    return http.Response("Transaction confirmed", status=200)
                elif payment_status == 'pending':
                    return http.Response("Transaction pending", status=200)
                elif payment_status == 'cancel':
                    return http.Response("Transaction cancelled", status=200)
            else:
                return http.Response("Payment not yet registered", status=200)

    @http.route(['/hotel/payment/link'], type='http', auth='public')
    def payment_responce(self):
        """
        Takes arguments:
            order_name
            amount
            partner_id
            currency_id
            launch_id
        :return:
        """
        if request.httprequest.method == 'GET':
            order_name = request.httprequest.args.get('order_name')
            payment_amount = request.httprequest.args.get('amount')
            partner_id = request.httprequest.args.get('partner_id')
            currency_id = request.httprequest.args.get('currency_id')
            # print(lunch_model.currency_id.id)
            payment_link = None
            if 'lunch_id' in request.httprequest.args:
                lunch_id = request.httprequest.args.get('lunch_id')
                lunch_model = request.env['lunch.order'].sudo().search([('id', '=', lunch_id)])
                access_token = payment_utils.generate_access_token(
                    partner_id, payment_amount, lunch_model.currency_id.id
                )
                payment_link = f'{request.httprequest.url_root}payment/pay' \
                               f'?reference={urls.url_quote(order_name)}' \
                               f'&amount={payment_amount}' \
                               f'&currency_id={currency_id}' \
                               f'&partner_id={False}' \
                               f'&company_id={lunch_model.company_id.id}' \
                               f'&access_token={access_token}'

            elif 'company_id' in request.httprequest.args:
                company_id = request.httprequest.args.get('company_id')
                company = request.env['res.company'].sudo().search([('id', '=', company_id)])
                access_token = payment_utils.generate_access_token(
                    partner_id, payment_amount, company.currency_id.id
                )
                payment_link = f'{request.httprequest.url_root}payment/pay' \
                               f'?reference={urls.url_quote(order_name)}' \
                               f'&amount={payment_amount}' \
                               f'&currency_id={currency_id}' \
                               f'&partner_id={False}' \
                               f'&company_id={company_id}' \
                               f'&access_token={access_token}'

            return http.Response(str(payment_link), status=200)