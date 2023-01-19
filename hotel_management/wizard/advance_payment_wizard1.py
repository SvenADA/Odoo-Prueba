from odoo import fields, models, api
import time
import datetime
from odoo.exceptions import Warning


class advance_payment_wizard(models.TransientModel):
    _name = 'advance.payment.wizard'
    _description = 'Advance Payment Detail Wizard'

    amt = fields.Float('Amount')

    deposit_recv_acc = fields.Many2one('account.account', string="Deposit Account",  required=True)
    journal_id = fields.Many2one('account.journal', "Journal", required=True)
    reservation_id = fields.Many2one('hotel.reservation', 'Reservation Ref', default=lambda self: self._get_default_rec())
    payment_date = fields.Date('Payment Date', required=True)


    def _get_default_rec(self):
        res = {}
        # print("context", self._context)
        if self._context is None:
            self._context = {}
        if 'reservation_id' in self._context:
            res = self._context['reservation_id']
            # print(res, "res=====================")
        return res


    # @api.multi
    def payment_process(self):
        sum = 0
        remainder = 0
        # print(self._ids, "ids", self._context, "context-------------------------------------------", self.browse(self._ids))
        for obj in self:
            # print('==============obj===========',obj.reservation_id)
            folio_obj = self.env['hotel.folio'].search(
                [('reservation_id', '=', obj.reservation_id.id)])
            # print('===============folio obj=========',folio_obj)
            if folio_obj:
                folio_id = folio_obj[0]
                if folio_id.amount_total < folio_id.total_advance + obj.amt:
                    raise Warning("Advance Amount Should not be greater than Total Amount.")
            if not obj.deposit_recv_acc:
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
                'ref': obj.reservation_id.name,
            })

            move_line1 = {

                'name': name or obj.name,
                'move_id': move_id,
                'account_id': obj.deposit_recv_acc.id,
                'debit': 0.0,
                'credit': obj.amt,
                'ref': obj.reservation_id.name,
                'journal_id': obj.journal_id.id,
                'partner_id': obj.reservation_id.partner_id.id,
                'date': obj.payment_date
            }
            # print("move_line1====================================================", move_line1)
            move_line2 = {
                'name': name or obj.name,
                'move_id': move_id,
                'account_id': obj.journal_id.default_credit_account_id.id,
                'debit': obj.amt,
                'credit': 0.0,
                'ref': obj.reservation_id.name,
                'journal_id': obj.journal_id.id,
                'partner_id': obj.reservation_id.partner_id.id,
                'date': obj.payment_date
            }

            move_id.write(
                {'line_ids': [(0, 0, move_line1), (0, 0, move_line2)]})
            move_id.post()

            if folio_id:
                self._cr.execute('insert into sale_account_move_rel(sale_id,move_id) values (%s,%s)', (folio_id.id, move_id.id))
                result = folio_id
                # print("result====================================================", result)
                sum = result.total_advance + obj.amt
                remainder = folio_id.amount_total - sum
                # print("remainder========================================================", remainder)
                self.env['hotel.folio'].write({'total_advance': sum})
                sale = self.env['sale.order'].search([('id', '=', folio_id.order_id.id)])
                if sale:
                    rr = self.env['sale.order'].write({'remaining_amt': remainder})
                sum = 0
                remainder = 0
        return {'type': 'ir.actions.act_window_close'}

