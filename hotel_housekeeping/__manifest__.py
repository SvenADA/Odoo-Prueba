# -*- encoding: utf-8 -*-
{
    "name": "Hotel Housekeeping Management",
    "version": "1.0.0.3",
    "author": "Pragmatic TechSoft Pvt Ltd",
    'website': 'http://pragtech.co.in/',
    "category": "Generic Modules/Hotel Housekeeping",
    "description": """
    Module for Hotel/Hotel Housekeeping. You can manage:
    * Housekeeping process
    * Housekeeping history room wise

      Different reports are also provided, mainly for hotel statistics.
    """,
    "depends": ["hotel"],
    "data": [
        # "hotel_housekeeping_workflow.xml",  # workflow does not exist in odoo11
        # "data/hotel_housekeeping_data.xml",
        "views/hotel_housekeeping_view.xml",
        "security/ir.model.access.csv",
    ],
    "active": False,
    "installable": True,
    'license': 'OPL-1',
}
