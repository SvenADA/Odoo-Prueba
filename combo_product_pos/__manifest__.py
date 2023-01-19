# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#    you can modify it under the terms of the GNU OPL (v1), Version 1.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU OPL (OPL v1) for more details.
#
##############################################################################
{
    'name': "POS Combo Product",
    'version': '15.0.1.0.0',
    'summary': """Pos Combo Products""",
    'description': """Pos Combo Products
    """,
    'author': 'Cybrosys Techno solutions',
    'company': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'maintainer': 'Cybrosys Techno Solutions',
    'live_test_url': 'https://www.youtube.com/watch?v=j8VdO7sXk0E',
    'category': 'Point of Sale',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'price': 49,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
    'application': False,
    'assets': {
        'point_of_sale.assets': [
            'combo_product_pos/static/src/css/pos_combo.css',
            'combo_product_pos/static/src/js/combo_popup.js',
            'combo_product_pos/static/src/js/combo_product.js',
            'combo_product_pos/static/src/js/combo_tag.js',
        ],
        'web.assets_qweb': [
            'combo_product_pos/static/src/xml/**/*',
        ],
    },
}
