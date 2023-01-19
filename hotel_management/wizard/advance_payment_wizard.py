from odoo import fields, models, api
import time
import datetime
from odoo.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)

class advance_payment_wizard(models.TransientModel):
    _name = 'advance.payment.wizard'
    _description = 'Advance Payment Detail Wizard'

    amt = fields.Float('Amount')

    deposit_recv_acc = fields.Many2one(
        'account.account', string="Deposit Account", required=True)
    journal_id = fields.Many2one(
        'account.journal', "Journal", required=True, domain="[('type','=',('cash','bank'))]")
    reservation_id = fields.Many2one(
        'hotel.reservation', 'Reservation Ref', default=lambda self: self._get_default_rec())
    payment_date = fields.Date(
        'Payment Date', required=True, default=fields.Date.context_today)

    @api.model
    def default_get(self, fields):
        res = super(advance_payment_wizard, self).default_get(fields)
        active_model_id = self.env[self._context.get(
            'active_model')].browse(self._context.get('active_id'))
        if active_model_id:
            if active_model_id.partner_id.property_account_receivable_id:
                res['deposit_recv_acc'] = active_model_id.partner_id.property_account_receivable_id.id
        return res

    def _get_default_rec(self):
        res = {}
        # print("context", self._context)
        if self._context is None:
            self._context = {}
        if 'reservation_id' in self._context:
            res = self._context['reservation_id']
        return res

    # @api.multi

    def payment_process(self):
        sum = 0
        remainder = 0
        # print(self._ids, "ids", self._context,
        #   "context-------------------------------------------", self.browse(self._ids))
        if self._context.get('active_model') == 'hotel.folio' :#or self._context.get('active_model') == 'hotel.reservation':
            for obj in self:
                # print('==============obj===========', obj.reservation_id)
                folio_obj = self.env['hotel.folio'].search(
                    [('reservation_id', '=', obj.reservation_id.id)])
                # print('===============folio obj=========', folio_obj)
                if folio_obj:
                    folio_id = folio_obj[0]
#                     if folio_id.amount_total < folio_id.total_advance + obj.amt:
#                         raise Warning("Advance Amount Should not be greater than Total Amount.")
                if not obj.deposit_recv_acc:
                    raise Warning("Account is not set for Deposit account.")
                if not obj.journal_id.default_account_id:
                    raise Warning("Account is not set for selected journal.")
                name = ''
                seq_obj = self.env['ir.sequence']
                if obj.journal_id.secure_sequence_id:
                    name = seq_obj.get_id(obj.journal_id.secure_sequence_id.id)
                
                payment_id = self.env['account.payment'].create({
                    'journal_id': obj.journal_id.id,
                    'partner_id': obj.reservation_id.partner_id.id,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'amount': obj.amt,
                })
                payment_id.move_id.ref = obj.reservation_id.name
                payment_id.action_post()
                # print('===========order_id=========== {}'.format(folio_id.order_id.id))
                if folio_obj and folio_id.id:
                    self._cr.execute('insert into sale_account_move_rel(sale_id, move_id) values (%s,%s)', (
                        folio_id.id, payment_id.move_id.id))
                    result = folio_id
                    # print("result====================================================", result)
                    sum = result.total_advance + obj.amt
                    remainder = folio_id.amount_total - sum
                    # print("remainder========================================================", remainder)
                    self.env['hotel.folio'].write({'total_advance': sum})
                    sale = self.env['sale.order'].search(
                        [('id', '=', folio_id.order_id.id)])
                    if sale:
                        rr = self.env['sale.order'].write(
                            {'remaining_amt': remainder})
                    sum = 0
                    remainder = 0
        else:
            for obj in self:
                if not obj.deposit_recv_acc:
                    raise Warning("Account is not set for Deposit account.")
                if not obj.journal_id.default_account_id:
                    raise Warning("Account is not set for selected journal.")
                name = ''
                seq_obj = self.env['ir.sequence']
                _logger.info("SEQUENCE======>>>>>%s",obj.journal_id.secure_sequence_id)
                # name = seq_obj.next_by_code(obj.journal_id.secure_sequence_id.id)
                # _logger.info("SEQUENCE======>>>>>%s  %s",name,obj.id)
                # wlkenljwnjwvljwenvlwenlkeng

                if obj.journal_id.secure_sequence_id:
                    name = seq_obj.get_id(obj.journal_id.secure_sequence_id.id)
                    _logger.info("SEQUENCE======>>>>>%s",name)

                vals = {
                    'journal_id': obj.journal_id.id,
                    'partner_id': obj.reservation_id.partner_id.id,
                    'destination_account_id': obj.reservation_id.partner_id.property_account_receivable_id.id,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'amount': obj.amt,
                    
                }
                _logger.info("VALS_======>>>>>>%s",vals)
                
                payment_id = self.env['account.payment'].create(vals)
                payment_id.move_id.ref = obj.reservation_id.name
                payment_id.action_post()
                self._cr.execute(
                    'insert into reservation_account_move_rel(reservation_id,move_id) values (%s,%s)', (obj.reservation_id.id, payment_id.move_id.id))
                result = obj.reservation_id
                sum = result.total_advance + obj.amt
                remainder = result.total_cost1 - sum
                result.total_advance = sum
                sum = 0
                remainder = 0
        return {'type': 'ir.actions.act_window_close'}