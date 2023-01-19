from datetime import datetime

from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare
import logging
import pprint
from . import reservation as res
from odoo import api, fields, models, _, SUPERUSER_ID
_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    # sale_order_id = fields.Many2one('hotel.reservation', 'Sale Order')
    # sale_order_ids = fields.Many2many('hotel.reservation', 'hotel_reservation_transaction_rel','transaction_id','sale_order_id',
    #                                 string='Sales Orders', copy=False, readonly=True)

    reservation_id = fields.Many2one('hotel.reservation', string='Reservation')
    reservation_ids = fields.Many2many('hotel.reservation', 'hotel_reservation_transactions_rel','transaction_id','reservation_id',
                                    string='Reservation Orders', copy=False, readonly=True)


############# COMMENTED THE FUNCTIONALITY TO RUN THE SALE ORDER FUNCTIONALITY OF WEBSITE  ##################

#     def _set_pending(self, state_message=None):
#         """ Override of payment to send the quotations automatically. """
#         super(PaymentTransaction, self)._set_pending(state_message=state_message)

#         for record in self:
#             sales_orders = record.sale_order_ids.filtered(lambda so: so.state in ['draft'])
#             sales_orders.filtered(lambda so: so.state == 'draft').with_context(tracking_disable=True).write({'state': 'confirm'})

    
#     def _set_authorized(self, state_message=None):
#         """ Override of payment to confirm the quotations automatically. """
#         super()._set_authorized(state_message=state_message)
#         sales_orders = self.mapped('sale_order_ids').filtered(lambda so: so.state in ('draft', 'sent'))
#         for tx in self:
#             tx._check_amount_and_confirm_order()

#         # send order confirmation mail
#         # sales_orders._send_order_confirmation_mail()

    
#     @api.model
#     def _reconcile_after_done(self):
#         """ Override of payment to automatically confirm quotations and generate invoices. """
#         sales_orders = self.mapped('sale_order_ids').filtered(lambda so: so.state in ('draft', 'sent'))
#         for tx in self:
#             tx._check_amount_and_confirm_order()
#         # send order confirmation mail
#         # sales_orders._send_order_confirmation_mail()
#         # invoice the sale orders if needed
#         self._invoice_sale_orders()
#         # res = super()._reconcile_after_done()
#         if self.env['ir.config_parameter'].sudo().get_param('sale.automatic_invoice') and any(so.state in ('sale', 'done') for so in self.sale_order_ids):
#             default_template = self.env['ir.config_parameter'].sudo().get_param('sale.default_invoice_email_template')
#             if default_template:
#                 for trans in self.filtered(lambda t: t.sale_order_ids.filtered(lambda so: so.state in ('sale', 'done'))):
#                     trans = trans.with_company(trans.acquirer_id.company_id).with_context(
#                         mark_invoice_as_sent=True,
#                         company_id=trans.acquirer_id.company_id.id,
#                     )
#                     for invoice in trans.invoice_ids.with_user(SUPERUSER_ID):
#                         invoice.message_post_with_template(int(default_template), email_layout_xmlid="mail.mail_notification_paynow")
#         return res
    
    
#     def _check_or_create_sale_tx(self, order, acquirer, payment_token=None, tx_type='form', add_tx_values=None, reset_draft=True):
#         tx = self
#         if not tx:
#             tx = self.search([('reference', '=', order.name)], limit=1)

#         if tx.state in ['error', 'cancel']:  # filter incorrect states
#             tx = False
#         if (tx and tx.acquirer_id != acquirer) or (tx and tx.sale_order_id != order):  # filter unmatching
#             tx = False
#         if tx and payment_token and tx.payment_token_id and payment_token != tx.payment_token_id:  # new or distinct token
#             tx = False

#         # still draft tx, no more info -> rewrite on tx or create a new one depending on parameter
#         if tx and tx.state == 'draft':
#             if reset_draft:
#                 tx.write(dict(
#                     # self.on_change_partner_id(order.partner_id.id).get('value', {}),
#                     amount=order.total_cost1 if isinstance(
#                         order, res.hotel_reservation) else order.amount_total,
#                     type=tx_type)
#                 )
#             else:
#                 tx = False

#         reference = "VALIDATION-%s-%s" % (self.id,
#                                           datetime.now().strftime('%y%m%d_%H%M%S'))
#         if not tx:
#             tx_values = {
#                 'acquirer_id': acquirer.id,
#                 'type': tx_type,
#                 'amount': order.total_cost1 if isinstance(order, res.hotel_reservation) else order.amount_total,
#                 'currency_id': order.pricelist_id.currency_id.id,
#                 'partner_id': order.partner_id.id,
#                 'partner_country_id': order.partner_id.country_id.id,
#                 'reference': reference,
#                 'sale_order_id': order.id,
#             }
#             if add_tx_values:
#                 tx_values.update(add_tx_values)
#             if payment_token and payment_token.sudo().partner_id == order.partner_id:
#                 tx_values['payment_token_id'] = payment_token.id

#             tx = self.create(tx_values)

#         # update quotation
#         order.write({
#             'payment_tx_id': tx.id,
#         })

#         return tx

#     def render_sale_button(self, invoice, return_url, submit_txt=None, render_values=None):
#         values = {
#             'return_url': return_url,
#             'partner_id': invoice.partner_id.id,
#         }
#         if render_values:
#             values.update(render_values)

#         return self.acquirer_id.with_context(submit_class='btn btn-primary', submit_txt=submit_txt or _('Pay Now')).sudo().render(
#             self.reference,
#             invoice.total_cost1,
#             invoice.currency_id.id,
#             values=values,
#         )

#     def _confirm_so(self):
#         """ Check tx state, confirm the potential SO """
#         self.ensure_one()
#         if self.sale_order_id.state not in ['draft', 'sent', 'sale']:
#             _logger.warning('<%s> transaction STATE INCORRECT for order %s (ID %s, state %s)',
#                             self.acquirer_id.provider, self.sale_order_id.name, self.sale_order_id.id, self.sale_order_id.state)
#             return 'pay_sale_invalid_doc_state'
#         if not float_compare(self.amount, self.sale_order_id.total_cost1, 2) == 0:
#             _logger.warning('<%s> transaction AMOUNT MISMATCH for order %s (ID %s)',
#                             self.acquirer_id.provider, self.sale_order_id.name, self.sale_order_id.id)
#             return 'pay_sale_tx_amount'

#         if self.state == 'authorized' and self.acquirer_id.capture_manually:
#             _logger.info('<%s> transaction authorized, auto-confirming order %s (ID %s)',
#                          self.acquirer_id.provider, self.sale_order_id.name, self.sale_order_id.id)
#             if self.sale_order_id.state in ('draft', 'sent'):
#                 self.sale_order_id.with_context(
#                     send_email=True).action_confirm()

#         if self.state == 'done':
#             _logger.info('<%s> transaction completed, auto-confirming order %s (ID %s) and generating invoice',
#                          self.acquirer_id.provider, self.sale_order_id.name, self.sale_order_id.id)
#             if self.sale_order_id.state in ('draft', 'sent'):
#                 self.sale_order_id.with_context(
#                     send_email=True).action_confirm()
#             self._generate_and_pay_invoice()
#         elif self.state not in ['cancel', 'error'] and self.sale_order_id.state == 'draft':
#             _logger.info('<%s> transaction pending/to confirm manually, sending quote email for order %s (ID %s)',
#                          self.acquirer_id.provider, self.sale_order_id.name, self.sale_order_id.id)
# #             self.sale_order_id.force_quotation_send()
#         else:
#             _logger.warning('<%s> transaction MISMATCH for order %s (ID %s)',
#                             self.acquirer_id.provider, self.sale_order_id.name, self.sale_order_id.id)
#             return 'pay_sale_tx_state'
#         return True
