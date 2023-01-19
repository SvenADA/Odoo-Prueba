from odoo import fields, models, api
import time
from odoo import netsvc
import datetime
from odoo.tools import config
from odoo.tools.translate import _
# from mx.DateTime import RelativeDateTime, now, DateTime, localtime
import calendar
from odoo import exceptions, _
from odoo.exceptions import Warning
from odoo.exceptions import except_orm, UserError, AccessError, RedirectWarning


class DepositJournalEntryWizard(models.TransientModel):
    _name = 'deposit_journal_entry.wizard'
    _description = 'Deposit_journal_entry Detail Wizard'

    name = fields.Char('Description', readonly=True, default=lambda *a: 'Deposit amount Journal Entry')
    booking_id = fields.Many2one('hotel.reservation', "Booking Ref", readonly=True,
                                 default=lambda self: self._get_default_rec())
    partner_id = fields.Many2one('res.partner', "Customer", readonly=True,
                                 default=lambda self: self._get_default_partner_val())
    payment_date = fields.Date('Payment Date', required=True)
    journal_id = fields.Many2one('account.journal', "Journal", required=True)
    service_cost = fields.Float('Service Cost', readonly=True, default=lambda self: self._get_default_val())

    def allow_to_send(self):
        # print("\n\n\n allow_to_send ==========", self)
        for obj in self:
            if not obj.booking_id.deposit_recv_acc:
                raise exceptions.except_orm(_("Warning"), _("Account is not set for Deposit account."))
            if not obj.journal_id.default_credit_account_id:
                raise exceptions.except_orm(_("Warning"), _("Account is not set for selected journal."))
            name = ''
            seq_obj = self.env['ir.sequence']
            # print("\n\n\n seq_obj =======", seq_obj)
            if obj.journal_id.sequence_id:
                # print("\n\n\n obj.journal_id.sequence_id ========", obj.journal_id.sequence_id)
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

            self.env['account.move'].write({'line_ids': [(0, 0, move_line1), (0, 0, move_line2)]})

            self.env['account.move'].post()
            so = self.env['hotel.reservation'].create_folio()
            for reservation in self.env['hotel.reservation'].browse(self._context['active_ids']):
                folio_obj = self.env['hotel.folio'].search([('reservation_id', '=', reservation.id)])
                if folio_obj:
                    folio_browse = self.env['hotel.folio'].browse(folio_obj.id)
                    self._cr.execute('insert into sale_account_move_rel(sale_id,move_id) values (%s,%s)',
                                     (folio_browse[0].id, move_id))
                    for food in reservation.food_items_ids:
                        tax_ids = []
                        for tax_line in food.product_id.taxes_id:
                            tax_ids.append(tax_line.id)
                        vals = {
                            'folio_id': folio_browse[0].id,
                            'product_id': food.product_id.id,
                            'name': food.product_id.name,
                            'product_uom': food.product_uom.id,
                            'price_unit': food.price_unit,
                            'product_uom_qty': food.product_uom_qty,
                            'tax_id': [(6, 0, tax_ids)],
                        }
                        self.env["hotel_service.line"].create(vals)
                    for food in reservation.other_items_ids:
                        tax_ids = []
                        for tax_line in food.product_id.taxes_id:
                            tax_ids.append(tax_line.id)
                        vals = {
                            'folio_id': folio_browse[0].id,
                            'product_id': food.product_id.id,
                            'name': food.product_id.name,
                            'product_uom': food.product_uom.id,
                            'price_unit': food.price_unit,
                            'product_uom_qty': food.product_uom_qty,
                            'tax_id': [(6, 0, tax_ids)],
                        }
                        self.env["hotel_service.line"].create(vals)
                # print(reservation.deposit_cost1, "obj.reservation_id.deposit_cost1")
        return {'type': 'ir.actions.act_window_close'}

    def _get_default_rec(self):
        # print("context", self._context)
        res = None
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
            # print(coll_obj.deposit_cost1, "coll_obj.deposit_cost1")
            # print(type(coll_obj.deposit_cost1))
        return float(coll_obj.deposit_cost1)

    def _get_default_partner_val(self):
        if self._context is None:
            self._context = {}
        if 'booking_id' in self._context:
            coll_obj = self.env['hotel.reservation'].browse(self._context['booking_id'])
            # print(coll_obj, "coll_obj")
        return coll_obj.partner_id.id
