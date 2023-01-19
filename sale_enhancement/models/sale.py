# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from odoo.addons import decimal_precision as dp
from odoo import netsvc
from odoo.exceptions import ValidationError

class sale_order(models.Model):
    _name = "sale.order"
    _inherit = "sale.order"
    _description = "Sales Order"

    @api.onchange('shop_id')
    def onchange_shop_id(self):
        # print("\n\n\n onchange shop id===========", self, self.shop_id)
        v = {}
        if self.shop_id:
            shop = self.env['sale.shop'].browse(self.shop_id.id)
            # print("\n\n\n Shop==========", shop)
            if shop.project_id.id:
                v['project_id'] = shop.project_id.id
            if shop.pricelist_id.id:
                v['pricelist_id'] = shop.pricelist_id.id
        # print("\n\n\n\n v : ", v)
        return {'value': v}

    @api.model
    def _get_default_shop(self):
        company_id = self.env['res.users'].browse(self._uid).company_id.id
        shop_ids = self.env['sale.shop'].search(
            [('company_id', '=', company_id)], limit=1)
        # if not shop_ids:
        #     raise  ValidationError(('Error! There is no default shop for the current user\'s company!'))
        return shop_ids

    shop_id = fields.Many2one('sale.shop', 'Hotel', required=True, readonly=True, states={
                              'draft': [('readonly', False)], 'sent': [('readonly', False)]}, default=_get_default_shop)

    # @api.multi
    def _prepare_order_line_procurement(self, line, group_id=False):
        # print("\n\n\n _prepare_order_line_procurement=========",
        #       self, "\nline=====", line)
        for order in self:
            date_planned = self._get_date_planned(line, order.date_order)
            routes = line.route_id and [(4, line.route_id.id)] or []
            # print('_prepare_order_line_procurement in sale_enhancement issssss',
            #       line.route_id, '\n\nbbbbbb', line.route_id.id)
            return {
                'name': line.name,
                'origin': order.name,
                'date_planned': date_planned,
                'product_id': line.product_id.id,
                'product_qty': line.product_uom_qty,
                'product_uom': line.product_uom.id,
                'product_uos_qty': (line.product_uos and line.product_uos_qty)
                or line.product_uom_qty,
                'product_uos': (line.product_uos and line.product_uos.id)
                or line.product_uom.id,
                'location_id': order.shop_id.warehouse_id.lot_stock_id.id,
                'procure_method': line.route_id,
                'route_ids': routes,
                'group_id': group_id,
                'company_id': order.company_id.id,
                'note': line.name,
            }

    # @api.multi
    def _prepare_order_line_move(self, line, picking_id, date_planned):
        # print("\n\n\n in _prepare_order_line_move()")
        for order in self:
            location_id = order.shop_id.warehouse_id.lot_stock_id.id
            output_id = order.shop_id.warehouse_id.lot_output_id.id
            # print("\n\n location_id : ", location_id,
            #       "\n\nouput_id : ", output_id)
            return {
                'name': line.name,
                'picking_id': picking_id,
                'product_id': line.product_id.id,
                'date': date_planned,
                'date_expected': date_planned,
                'product_qty': line.product_uom_qty,
                'product_uom': line.product_uom.id,
                'product_uos_qty': (line.product_uos and line.product_uos_qty) or line.product_uom_qty,
                'product_uos': (line.product_uos and line.product_uos.id)
                or line.product_uom.id,
                'product_packaging': line.product_packaging.id,
                'partner_id':  order.partner_shipping_id.id,
                'location_id': location_id,
                'location_dest_id': output_id,
                'sale_line_id': line.id,
                'tracking_id': False,
                'state': 'draft',
                #'state': 'waiting',
                'company_id': order.company_id.id,
                'price_unit': line.product_id.standard_price or 0.0
            }


class product_product(models.Model):
    _inherit = "product.product"

    # @api.multi
    def get_product_available(self):
        """ Finds whether product is available or not in particular warehouse.
        @return: Dictionary of values
        """

        # print("\n\n\n\n in get_product_available")
        if self._context is None:
            self._context = {}

        location_obj = self.env['stock.location']
        warehouse_obj = self.env['stock.warehouse']
        shop_obj = self.env['sale.shop']

        states = self._context.get('states', [])
        what = self._context.get('what', ())
        if not self._ids:
            ids = self.search([])
        res = {}.fromkeys(ids, 0.0)
        if not self._ids:
            return res

        if self._context.get('shop', False):
            warehouse_id = shop_obj.read(['warehouse_id'])['warehouse_id'][0]
            if warehouse_id:
                self._context['warehouse'] = warehouse_id

        if self._context.get('warehouse', False):
            lot_id = warehouse_obj.read(['lot_stock_id'])['lot_stock_id'][0]
            if lot_id:
                self._context['location'] = lot_id

        if self._context.get('location', False):
            if type(self._context['location']) == type(1):
                location_ids = [self._context['location']]
            elif type(self._context['location']) in (type(''), type(u'')):
                location_ids = location_obj.search(
                    [('name', 'ilike', self._context['location'])])
            else:
                location_ids = self._context['location']
        else:
            location_ids = []
            wids = warehouse_obj.search([])
            if not wids:
                return res
            for w in warehouse_obj.browse(wids):
                location_ids.append(w.lot_stock_id.id)

        # build the list of ids of children of the location given by id
        if self._context.get('compute_child', True):
            child_location_ids = location_obj.search(
                [('location_id', 'child_of', location_ids)])
            location_ids = child_location_ids or location_ids

        # this will be a dictionary of the product UoM by product id
        product2uom = {}
        uom_ids = []
        for product in self.read(['uom_id']):
            product2uom[product['id']] = product['uom_id'][0]
            uom_ids.append(product['uom_id'][0])
        # this will be a dictionary of the UoM resources we need for conversion
        # purposes, by UoM id
        uoms_o = {}
        for uom in self.env['uom.uom'].browse(uom_ids):
            uoms_o[uom.id] = uom

        results = []
        results2 = []

        from_date = self._context.get('from_date', False)
        to_date = self._context.get('to_date', False)
        date_str = False
        date_values = False
        where = [tuple(location_ids), tuple(
            location_ids), tuple(ids), tuple(states)]
        if from_date and to_date:
            date_str = "date>=%s and date<=%s"
            where.append(tuple([from_date]))
            where.append(tuple([to_date]))
        elif from_date:
            date_str = "date>=%s"
            date_values = [from_date]
        elif to_date:
            date_str = "date<=%s"
            date_values = [to_date]
        if date_values:
            where.append(tuple(date_values))

        prodlot_id = self._context.get('prodlot_id', False)
        prodlot_clause = ''
        if prodlot_id:
            prodlot_clause = ' and prodlot_id = %s '
            where += [prodlot_id]

        # TODO: perhaps merge in one query.
        if 'in' in what:
            # all moves from a location out of the set to a location in the set
            self._cr.execute(
                'select sum(product_qty), product_id, product_uom '
                'from stock_move '
                'where location_id NOT IN %s '
                'and location_dest_id IN %s '
                'and product_id IN %s '
                'and state IN %s ' +
                (date_str and 'and ' + date_str + ' ' or '') + ' '
                + prodlot_clause +
                'group by product_id,product_uom', tuple(where))
            results = self._cr.fetchall()
        if 'out' in what:
            # all moves from a location in the set to a location out of the set
            self._cr.execute(
                'select sum(product_qty), product_id, product_uom '
                'from stock_move '
                'where location_id IN %s '
                'and location_dest_id NOT IN %s '
                'and product_id  IN %s '
                'and state in %s ' +
                (date_str and 'and ' + date_str + ' ' or '') + ' '
                + prodlot_clause +
                'group by product_id,product_uom', tuple(where))
            results2 = self._cr.fetchall()

        # Get the missing UoM resources
        uom_obj = self.env['uom.uom']
        uoms = map(lambda x: x[2], results) + map(lambda x: x[2], results2)
        if self._context.get('uom', False):
            uoms += [self._context['uom']]
        uoms = filter(lambda x: x not in uoms_o.keys(), uoms)
        if uoms:
            uoms = uom_obj.browse(list(set(uoms)))
            for o in uoms:
                uoms_o[o.id] = o

        # TOCHECK: before change uom of product, stock move line are in old
        # uom.
        self._context.update({'raise-exception': False})
        # Count the incoming quantities
        for amount, prod_id, prod_uom in results:
            amount = uom_obj._compute_qty_obj(uoms_o[prod_uom], amount,
                                              uoms_o[self._context.get('uom', False) or product2uom[prod_id]])
            res[prod_id] += amount
        # Count the outgoing quantities
        for amount, prod_id, prod_uom in results2:
            amount = uom_obj._compute_qty_obj(uoms_o[prod_uom], amount,
                                              uoms_o[self._context.get('uom', False) or product2uom[prod_id]])
            res[prod_id] -= amount
        return res
