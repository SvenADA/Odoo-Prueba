# -*- encoding: utf-8 -*-

{
    "name": "Hotel Management",
    "version": "1.0.0.1.6",
    "author": "Pragmatic TechSoft Pvt Ltd",
    'website': 'http://pragtech.co.in/',
    "category": "Generic Modules/Hotel Management",
    "description": """
                Module for Hotel/Resort/Property management. You can manage:
                * Configure Property
                * Hotel Configuration
                * Check In, Check out
                * Manage Folio
                * Payment
            
                Different reports are also provided, mainly for hotel statistics.
            """,
    #     "depends" : ["base","product","sale",'sale_enhancement','account_accountant'],
    # removed account_accountant module dependency, doesnt exist in odoo11
    "depends": ["base", "product", "sale"],
    "init_xml": [],
    "demo_xml": [

    ],
    "data": [
        "security/hotel_security.xml",
        # "data/hotel_data.xml",
        "security/ir.model.access.csv",
        "views/hotel_view.xml",
        # "data/hotel_folio_workflow.xml",
    ],
    "active": False,
    "installable": True,
    'application': True,
    'license': 'LGPL-3',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
