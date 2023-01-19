from odoo import fields, models, api
import pytz
from odoo.exceptions import ValidationError, Warning
import datetime


class folio_invoice_transfer_wizard(models.TransientModel):
    _name = 'folio.invoice.transfer.wizard'
    _description = 'Folio invoice transfer Wizard'

    folio_id = fields.Many2one(
        'hotel.folio', 'Folio Ref', default=lambda self: self._get_default_rec())
    trans_folio_id = fields.Many2one(
        'hotel.folio', 'Transfer Folio Ref', domain="[('state', 'not in', ['check_out','done','cancel'])]",)

    def _get_default_rec(self):
        res = {}
        if 'by_dashbord' in self._context and self._context.get('by_dashbord'):
            hotel_folio_id = self.env['hotel.folio'].search(
                [('reservation_id', '=', self._context['active_id'])])
            if hotel_folio_id:
                res = hotel_folio_id.id
                return res
        if self._context is None:
            self._context = {}
        if 'active_id' in self._context:
            # print(self._context, '=================context=======')
            res = self._context['active_id']
            # print(res, "res=====================")
        return res

    def transfer_process(self):
        for obj in self.browse(self._ids):
            if obj.trans_folio_id:
                if obj.trans_folio_id.partner_id.id == obj.folio_id.partner_id.id:
                    raise ValidationError(
                        "Error !, Invoice can't be transfer as both folio partner is same !")
            folio = self.env['hotel.folio'].browse(obj.folio_id.id)
            so = self.env['sale.order'].browse(folio.order_id.id)
            # for record in so.order_line:
            #     print("\n\n\nSale order Line==>>>", record.product_id,
            #           "\n\n\nLine name", record.name)
            data = so._create_invoices()
            for acc_id in data:
                acc_obj = self.env["account.move"].browse(acc_id)
                if folio.shop_id.project_id.id:
                    acc_id.invoice_line_ids.write(
                        {
                            'analytic_account_id': folio.shop_id.project_id.id,
                        })

                obj.folio_id.write({'state': 'progress'})
                if obj.trans_folio_id:
                    # print(obj.trans_folio_id.partner_id,
                    #       "obj.trans_folio_id.partner_id.id")
                    # print(obj.folio_id.partner_id, "obj.folio_id.partner_id")
                    if obj.trans_folio_id.partner_id.id != obj.folio_id.partner_id.id:
                        acc_obj.write(
                            {'partner_id': obj.trans_folio_id.partner_id.id})

                    self._cr.execute('insert into sale_transfer_account_invoice_rel (sale_id,invoice_id) values (%s,%s)', (
                        obj.trans_folio_id.order_id.id, data[0]))

        return {'type': 'ir.actions.act_window_close'}


class FolioSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _description = 'Preparing Sale order Line'

    def _prepare_invoice_line(self, sequence):
        res = super(FolioSaleOrderLine, self)._prepare_invoice_line()
        hotel_folio_line_id = self._format_desc()
        if hotel_folio_line_id:
            # print('-------------- {} {}'.format(hotel_folio_line_id, hotel_folio_line_id.checkin_date))
            timezone = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.timezone(
                self._context.get('tz') or 'UTC')
            checkin_date = hotel_folio_line_id.checkin_date.astimezone(timezone)
            if checkin_date:
                checkin_date = datetime.datetime.strftime(
                    checkin_date, "%m/%d/%Y, %H:%M:%S")

                checkout_date = hotel_folio_line_id.checkout_date.astimezone(timezone)
                if checkout_date:
                    checkout_date = datetime.datetime.strftime(
                        checkout_date, "%m/%d/%Y, %H:%M:%S")
                res.update({'name': "Room: {}  From: {} To: {}".format(res.get('name'), checkin_date, checkout_date)})

        return res

    def _format_desc(self):
        hotel_folio_line = self.env['hotel_folio.line'].search(
            [('order_line_id', '=', self.id)])
        return hotel_folio_line