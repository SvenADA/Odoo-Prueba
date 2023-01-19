from odoo import fields, models, api
import time
# from mx import DateTime
import datetime


class cancel_foilo_wizard(models.TransientModel):
    _name = 'cancel.foilo.wizard'

    _description = 'Cancel Wizard'

    desc = fields.Text('Description', readonly=True)

    def default_get(self, fields):
        # print("default_get=================")
        if self._context is None:
            self._context = {}
        # no call to super!
        res = {}
        move_ids = self._context.get('active_ids')
        # print(move_ids, "move_ids")
        # print(fields, "fields")
        if not move_ids or not self._context.get('active_model') == 'hotel.folio':
            return res
        move_ids = self.env['hotel.folio'].browse(move_ids)
        # print(move_ids, "move_ids=============")
        today = time.strftime('%Y-%m-%d %H:%M:%S')
        if today > move_ids[0].checkin_date:
            desc = "Checkin time is Passed still want to cancel this folio."
        else:
            desc = "Do You want to continue ?"
        if 'desc' in fields:
            res.update(desc=desc)
        # print("desc", desc)
        return res


    def cancel_wizard(self):
        # print(self._context, "context", data)
        # folio_object = self.browse(data['active_id'])
        # cancel_data = self.env['hotel.folio'].action_cancel(data['active_ids'])
        # print(cancel_data, "cancel_data===============")
        return {'type': 'ir.actions.act_window_close'}

