# -*- encoding: utf-8 -*-
{
    "name": "Hotel Laundry ",
    "version": "1.0.0.7",
    "author": "Pragmatic TechSoft Pvt Ltd",
    'website': 'http://pragtech.co.in/',
    "category": "Generic Modules/Hotel Laundry",
    "description": """
    Module for laundry management. You can manage:
    * Configure Property
    * Hotel Configuration
    * laundry services
    * Payment

    Different reports are also provided, mainly for hotel statistics.
    """,
    "depends": ["base", "hotel", "hotel_management"],
    "data": [
        'security/hotel_laundry_security.xml',
        "security/ir.model.access.csv",
        "wizard/hotel_laundry_picking_view.xml",
        "views/hotel_laundry_view.xml",
        "views/laundry_sequence_view.xml",
        "laundry_data.xml",
    ],
    "active": False,
    "installable": True,
    'license': 'OPL-1',
}
