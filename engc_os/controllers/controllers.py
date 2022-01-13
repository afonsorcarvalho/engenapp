# -*- coding: utf-8 -*-
# from odoo import http


# class EngcOs(http.Controller):
#     @http.route('/engc_os/engc_os/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/engc_os/engc_os/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('engc_os.listing', {
#             'root': '/engc_os/engc_os',
#             'objects': http.request.env['engc_os.engc_os'].search([]),
#         })

#     @http.route('/engc_os/engc_os/objects/<model("engc_os.engc_os"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('engc_os.object', {
#             'object': obj
#         })
