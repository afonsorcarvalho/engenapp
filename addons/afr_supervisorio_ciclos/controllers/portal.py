from odoo import http
from odoo.http import request
import base64

class AuthenticityPortal(http.Controller):
    @http.route(['/authenticity/check'], type='http', auth='public', website=True)
    def authenticity_check_form(self, **kw):
        if request.httprequest.method == 'POST':
            # Criar registro de verificação
            values = {
                'name': kw.get('name'),
                'digital_tape_file': base64.b64encode(kw.get('digital_tape_file').read()),
                'digital_tape_filename': kw.get('digital_tape_file').filename,
            }
            
            check = request.env['afr.public.authenticity.check'].sudo().create(values)
            check.sudo().action_verify_authenticity()
            
            return request.render('afr_supervisorio_ciclos.portal_authenticity_check_result', {
                'check': check
            })
        
        return request.render('afr_supervisorio_ciclos.portal_authenticity_check_form') 