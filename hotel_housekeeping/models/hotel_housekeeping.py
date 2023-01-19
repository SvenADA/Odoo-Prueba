# -*- encoding: utf-8 -*-


from odoo import api, fields, models
from odoo.exceptions import Warning
import datetime
import time
from datetime import datetime


class product_category(models.Model):
    _inherit = "product.category"
    isactivitytype = fields.Boolean('Is Activity Type')


class hotel_housekeeping_activity_type(models.Model):
    _name = 'hotel.housekeeping.activity.type'
    _description = 'Activity Type'
    _inherits = {'product.category': 'activity_id'}

    activity_id = fields.Many2one(
        'product.category', 'category', required=True, ondelete="cascade")
    isactivitytype = fields.Boolean('Is Activity Type', default=True)



class product_product(models.Model):
    _inherit = "product.product"
    isact = fields.Boolean('Is Activity')


class h_activity(models.Model):

    _name = 'h.activity'
    _inherits = {'product.product': 'h_id'}

    _description = 'Housekeeping Activity'

    h_id = fields.Many2one(
        'product.product', 'Product_id', required=True, ondelete="cascade")
    isact = fields.Boolean(
        'Is Activity', related='h_id.isact', inherited=True, default=True)


    @api.onchange('type')
    def onchange_type(self):
        res = {}
        if self.type in ('consu', 'service'):
            res = {'value': {'valuation': 'manual_periodic'}}
        return res


class hotel_housekeeping(models.Model):
    _name = "hotel.housekeeping"
    _description = "Reservation"

    current_date = fields.Date("Start Date", required=True, default=lambda *a: time.strftime('%Y-%m-%d'))
    end_date = fields.Date("Expected End Date", required=True)
    clean_type = fields.Selection([('daily', 'Daily'), ('checkin', 'Checkin'), ('checkout', 'Checkout')], 'Clean Type', required=True)
    room_no = fields.Many2one('hotel.room', 'Room No', required=True)
    activity_lines = fields.One2many('hotel.housekeeping.activities', 'a_list', 'Activities')
    room_no = fields.Many2one('product.product', 'Room No', required=True)
    inspector = fields.Many2one('res.users', 'Inspector', required=True)
    inspect_date_time = fields.Datetime('Inspect Date Time', required=True)
    quality = fields.Selection([('clean', 'Cleaning'), ('maintenance', 'Maintenance')], 'Housekeeping Type', required=True)
    state = fields.Selection([('dirty', 'Dirty'), ('clean', 'Clean'), ('inspect', 'Inspect'), ('done', 'Done'), (
        'cancel', 'Cancelled')], 'state', default="dirty", index=True, required=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)


    @api.onchange('current_date', 'end_date')
    def onchange_current_date(self):
        # print ("\n\n\nonchange current date\n\n")
        if self.end_date and self.current_date > self.end_date:
            # print("\n\n\n\n\n Raise warning\n\n\n\n")
            raise Warning('End date must be greater than Start Date')


    # @api.multi
    def action_set_to_dirty(self):
        self.write({'state': 'dirty'})
#         wf_service = netsvc.LocalService('workflow')

        return True


    # @api.multi
    def room_cancel(self):
        self.write({'state': 'cancel'})
        return True


    # @api.multi
    def room_done(self):
        self.write({'state': 'done'})
        return True


    # @api.multi
    def room_inspect(self):
        self.write({'state': 'inspect'})
        return True


    # @api.multi
    def room_clean(self):
        self.write({'state': 'clean'})
        return True


class hotel_housekeeping_activities(models.Model):
    _name = "hotel.housekeeping.activities"
    _description = "Housekeeping Activities "

    a_list = fields.Many2one('hotel.housekeeping')
    activity_name = fields.Many2one('h.activity', 'Housekeeping Activity')
    housekeeper = fields.Many2one('res.users', 'Housekeeper', required=True)
    clean_start_time = fields.Datetime('Clean Start Time', required=True)
    clean_end_time = fields.Datetime('Clean End Time', required=True)
    dirty = fields.Boolean('Dirty')
    clean = fields.Boolean('Clean')
    activity_id = fields.Many2one('activity.housekeeping', 'Housekeeping activity', required=True)


class activity_type(models.Model):
    _name = 'activity.type'
    _description = 'Activity Type'

    name = fields.Char('Name', required=True)
    parent_id = fields.Many2one('activity.type', 'Parent Category')


class activity_housekeeping(models.Model):
    _name = 'activity.housekeeping'
    _description = 'Activity'

    name = fields.Char('Name', required=True)
    categ_id = fields.Many2one('activity.type', 'Category', required=True)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
