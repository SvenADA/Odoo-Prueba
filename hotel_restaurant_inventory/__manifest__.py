# -*- encoding: utf-8 -*-

{
    "name": "Hotel Restaurant Inventory ",
    "version": "1.0.0.8",
    "author": "Pragmatic TechSoft Pvt Ltd",
    "category": "Generic Modules/Hotel Restaurant Inventory",
    "description": """
    Module for Add Concept of BOM to restaurant Module:
    * Configure Property
    * Hotel Configuration
    * Product Quantity maintainance
    """,
    "depends": ["hotel_management", "mrp"],
    "data": [
        "security/ir.model.access.csv",
        "views/hotel_restaurant_inventory_view.xml",
        "views/sale_shop.xml",
    ],
    "active": False,
    "installable": True,
    'license': 'OPL-1',
}
