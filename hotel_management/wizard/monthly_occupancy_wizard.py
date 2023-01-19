# -*- coding: utf-8 -*-

import time
from odoo import models, fields, api


class monthly_occupancy_wizard(models.TransientModel):
    _name = 'monthly.occupancy.wizard'
    _description = 'monthly occupancy wizard'

    start_date = fields.Date('From Date', required=True)
    end_date = fields.Date('To Date', required=True)

    @api.model
    def default_get(self, fields):
        res = super(monthly_occupancy_wizard, self).default_get(fields)
        today = time.strftime("%Y-%m-01")
        if int(time.strftime('%m') == 1 or time.strftime('%m') == 3 or time.strftime('%m') == 5 or time.strftime(
                '%m') == 7 or time.strftime('%m') == 8 or time.strftime('%m') == 10 or time.strftime('%m') == 12):
            lastday = time.strftime("%Y-%m-31")
        else:
            lastday = time.strftime("%Y-%m-30")
        res.update({'start_date': today, 'end_date': lastday})
        return res

    def print_report(self):
        datas = {}
        return self.env.ref('hotel_management.monthly_occupency_qweb').report_action(self, data=datas, config=False)

    def _get_report_base_filename(self):
        return "Monthly-Occupancy-Report"
