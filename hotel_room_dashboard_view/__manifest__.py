# -*- coding: utf-8 -*-


{
    'name': 'Hotel Room Dashboard View',
    'version': '1.0.0.13',
    'category': 'General',
    'sequence': 6,
    'description': """
    """,
    'license': 'OPL-1',
    'author': 'Pragmatic Techsoft Pvt. Ltd.',
    'depends': ['hotel_management', 'base'],
    'data': [
        'views/hotel_room_dashboard_view.xml',
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/dashboard.xml',
        'views/hotel_reservation_view.xml',
    ],
    'installable': True,
    'application': True,
    'qweb': ['static/src/xml/base.xml',
             'static/src/xml/template.xml'
             ],
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            '/hotel_room_dashboard_view/static/src/js/widgets.js',
            '/hotel_room_dashboard_view/static/src/js/dashboard_hotel.js',
            '/hotel_room_dashboard_view/static/src/js/fullcalender.js',
            '/hotel_room_dashboard_view/static/src/js/schedular.js',
            '/hotel_room_dashboard_view/static/src/css/base.css',
            '/hotel_room_dashboard_view/static/src/css/dashboard.css',
            '/web/static/lib/fullcalendar/core/main.css',
            '/hotel_room_dashboard_view/static/src/css/schedular-min-js.css',
            '/hotel_room_dashboard_view/static/src/css/scheduler.css'
        ],
        'web.assets_qweb': [
            'hotel_room_dashboard_view/static/src/xml/base.xml',
            'hotel_room_dashboard_view/static/src/xml/template.xml'
        ],
    },
}
