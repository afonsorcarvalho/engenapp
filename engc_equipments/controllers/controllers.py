# -*- coding: utf-8 -*-
# from odoo import http


# class EngcEquipments(http.Controller):
#     @http.route('/engc_equipments/engc_equipments/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/engc_equipments/engc_equipments/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('engc_equipments.listing', {
#             'root': '/engc_equipments/engc_equipments',
#             'objects': http.request.env['engc_equipments.engc_equipments'].search([]),
#         })

#     @http.route('/engc_equipments/engc_equipments/objects/<model("engc_equipments.engc_equipments"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('engc_equipments.object', {
#             'object': obj
#         })
