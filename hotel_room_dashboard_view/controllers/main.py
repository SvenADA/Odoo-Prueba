# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request
import json
from datetime import datetime, timedelta, timezone
import pytz
import math
utc_time = datetime.utcnow()

_logger = logging.getLogger(__name__)


class RoomDashboardController(http.Controller):

    @http.route('/hotel_room_dashboard/web', type='http', auth='user')
    def a(self, debug=False, **k):
        # print ("request.session.uid-----------",request.session.uid)
        if not request.session.uid:
            return http.local_redirect('/web/login?redirect=/hotel_room_dashboard/web')
        context = {
            'session_info': json.dumps(request.env['ir.http'].session_info())
        }
        return request.render('hotel_room_dashboard_view.room_dashboard', qcontext=context)

    @http.route('/get/checkout/configuration', type='http', auth='public')
    def get_checkout_conf(self,**kwargs):
        _logger.info("CHECK OUT CONF===>>>>>>>>>>>>>>{}".format(kwargs))
        shop_id = kwargs.get('shop_id')
        if shop_id:
            shop_id = request.env['sale.shop'].sudo().search([('id','=',int(shop_id))])

        _logger.info("SHOP ID====>>>>>>>>>>>>>>{}".format(shop_id))
        checkout_conf_id = request.env['checkout.configuration'].sudo().search([('shop_id','=',shop_id.id)])
        _logger.info("ihbfkwjbckjwebfjnlk==>>>{}".format(checkout_conf_id))

        user_id = request.env['res.users'].sudo().search([('id','=',2)])
        tz = pytz.timezone(user_id.tz)
        time_difference=tz.utcoffset(utc_time).total_seconds()
        res = {
            "checkout_time": int(checkout_conf_id.time),
            "time_difference": time_difference,
            "checkout_policy_name":checkout_conf_id.name,
        }
        if checkout_conf_id:
            return json.dumps(res)

        