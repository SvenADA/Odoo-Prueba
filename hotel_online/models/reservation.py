# -*- coding: utf-8 -*-
import uuid
from odoo import fields, models, api, _

import logging
_logger = logging.getLogger(__name__)
from odoo.tools import float_compare



class hotel_reservation(models.Model):
    _inherit = "hotel.reservation"

    
    def _get_default_access_token(self):
        return str(uuid.uuid4())

    # def get_portal_last_transaction(self):
    #     self.ensure_one()
    #     return self.transaction_ids._get_last()

    payment_acquirer_id = fields.Many2one('payment.acquirer', 'Payment Acquirer', copy=False)
    payment_tx_id = fields.Many2one('payment.transaction', 'Transaction', copy=False)
    
    access_token = fields.Char('Security Token', copy=False,default=_get_default_access_token)
    
    
    # @api.multi
    def action_quotation_send(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('sale', 'email_template_edi_sale')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'sale.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "sale.mail_template_data_notification_email_sale_order",
            'proforma': self.env.context.get('proforma', False),
            'force_email': True
        }
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
    
    
    # @api.multi
    def force_quotation_send(self):
        for order in self:
            email_act = order.action_quotation_send()
            if email_act and email_act.get('context'):
                email_ctx = email_act['context']
                email_ctx.update(default_email_from=order.company_id.email)
                order.with_context(email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
        return True
    
