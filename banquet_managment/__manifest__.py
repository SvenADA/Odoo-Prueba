{
    "name" : "Banquet Management ",
    "version" : "1.0.1.13",
    "author" : "Pragmatic",
    "category" : "Generic Modules/Banquet Management",

    "description": """
    Module for Banquet/Resort/Property management. You can manage:
    * Configure Property
    * Banquet Configuration
    * Check In, Check out
    * Manage Folio
    * Payment

    Different reports are also provided, mainly for Banquet statistics.
    """,
    "depends": ["base", 'hotel', 'crm', 'hotel_management'],
    "init_xml": [],
    "demo_xml": [
    ],
    "data": [
        'security/banquet_security.xml',
        'security/ir.model.access.csv',
        'wizard/banquet_deposite_amt_view.xml',
        "views/banquet_managment_view.xml",
        'views/banquet_sequence_view.xml'

    ],
    "active": False,
    "installable": True,
    'license': 'OPL-1',
}
