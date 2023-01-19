{
    "name": "Hotel Transport Management",
    "version": "1.0.0.5",
    "author": "Pragmatic TechSoft Pvt Ltd",
    'website': 'http://pragtech.co.in/',
    "category": "Generic Modules/Hotel Transport",
    "description": """
    Module for Hotel/Transport management. You can manage:
    * Task Creation For Transport
    """,
    "depends": ["base", "hotel_management", 'banquet_managment', 'project'],
    "init_xml": [],
    "demo_xml": [],
    "data": [
        'security/transport_security.xml',
        "security/ir.model.access.csv",
        "views/hotel_transport_management_view.xml",
        "hotel_transport_data.xml",
    ],
    "active": False,
    "installable": True,
    'license': 'OPL-1',
}
