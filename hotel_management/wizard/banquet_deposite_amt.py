from odoo import fields, models, api
import time
import datetime
from odoo.exceptions import ValidationError, Warning


class deposit_journal_entry_wizard1(models.TransientModel):
    _name = 'deposit_journal_entry.wizard1'
    _description = 'Deposit_journal_entry Detail Wizard'

    name = fields.Char('Description', default=lambda *
                       a: 'Deposit amount Journal Entry', readonly=True)
    booking_id = fields.Many2one('hotel.reservation', "Booking Ref", default=lambda self: self._get_default_rec(), readonly=True)
    partner_id = fields.Many2one('res.partner', "Customer", default=lambda self: self._get_default_partner_val(), readonly=True)
    payment_date = fields.Date('Payment Date', required=True)
    journal_id = fields.Many2one('account.journal', "Journal", required=True)
    service_cost = fields.Float('Service Cost', default=lambda self: self._get_default_val(), readonly=True)
    
    
    # @api.one
    def allow_to_send(self):
        for obj in self:
            if not obj.booking_id.deposit_recv_acc:
                raise Warning("Account is not set for Deposit account.")
            if not obj.journal_id.default_credit_account_id:
                raise Warning("Account is not set for selected journal.")
            name = ''
            seq_obj = self.env['ir.sequence']
            if obj.journal_id.sequence_id:
                name = seq_obj.get_id(obj.journal_id.sequence_id.id)

            move_id = self.env['account.move'].create({
                'journal_id': obj.journal_id.id,
                'name': name or obj.name,
                'ref': obj.booking_id.name,
            })
            move_line1 = {

                'name': name or obj.name,
                'move_id': move_id,
                'account_id': obj.booking_id.deposit_recv_acc.id,
                'debit': 0.0,
                'credit': obj.service_cost,
                'ref': obj.booking_id.name,
                'journal_id': obj.journal_id.id,
                'partner_id': obj.partner_id.id,
                'date': obj.payment_date
            }
            move_line2 = {
                'name': name or obj.name,
                'move_id': move_id,
                'account_id': obj.journal_id.default_credit_account_id.id,
                'debit': obj.service_cost,
                'credit': 0.0,
                'ref': obj.booking_id.name,
                'journal_id': obj.journal_id.id,
                'partner_id': obj.partner_id.id,
                'date': obj.payment_date
            }
            move_id.write({'line_ids': [(0, 0, move_line1), (0, 0, move_line2)]})
            move_id.post()
            active_id = self._context.get('active_ids')
            active = self.env['hotel.reservation'].browse(active_id)
            # print(active,'=============so=============')
            active.create_folio()
            folio_obj = self.env['hotel.folio'].search([('reservation_id', '=', obj.booking_id.id)])
            # print(folio_obj,'===================folio obj========')
            if folio_obj:
                folio_id = folio_obj[0]
                # print(folio_id,'===================folio id========')
                self._cr.execute('insert into sale_account_move_rel(sale_id,move_id) values (%s,%s)', (folio_id.id, move_id.id))
        return {'type': 'ir.actions.act_window_close'}


    def _get_default_rec(self):
        # print("context", self._context)
        if self._context is None:
            self._context = {}
        if 'booking_id' in self._context:
            res = self._context['booking_id']
            # print(res, "res")
        return res


    def _get_default_val(self):
        if self._context is None:
            self._context = {}
        if 'booking_id' in self._context:
            coll_obj = self.env['hotel.reservation'].browse(self._context['booking_id'])
            # print(coll_obj.deposit_cost2, "coll_obj.deposit_cost1------------------------------------")
            # print(type(coll_obj.deposit_cost2))
        # print("--------------------float(coll_obj.deposit_cost2)", float(coll_obj.deposit_cost2))
        return float(coll_obj.deposit_cost2)


    def _get_default_partner_val(self):
        if self._context is None:
            self._context = {}
        if 'booking_id' in self._context:
            coll_obj = self.env['hotel.reservation'].browse(
                self._context['booking_id'])
            # print(coll_obj, "=============coll_obj====================")
        return coll_obj.partner_id.id

