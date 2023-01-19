# -*- encoding: utf-8 -*-
{
    "name" : "Hotel Management GDS",
    "version" : "1.0.0.4",
    "author" : "Pragmatic TechSoft Pvt Ltd",
    'website' : 'http://pragtech.co.in/',
    "category" : "Generic Modules/Hotel Management GDS",

    "description": """
    Module for Hotel/Resort/Property management. You can manage:
    * GDS Property

    Different reports are also provided, mainly for hotel statistics.
    """,
    "depends": ["hotel_management", 'banquet_managment'],
    "data": [
        "view/hotel_gds_view.xml",
        'security/ir.model.access.csv',
    ],
    "active": False,
    "installable": True,
    'license': 'OPL-1',
}
