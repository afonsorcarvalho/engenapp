import base64
import os
import subprocess
import tempfile
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AuthenticityCheck(models.TransientModel):
    _name = 'afr.supervisorio.ciclos.authenticity.check'
    _description = 'Verificação de Autenticidade de Fita Digital'

    file = fields.Binary(string='Arquivo de Fita Digital', required=True)
    file_name = fields.Char(string='Nome do Arquivo')
    result = fields.Text(string='Resultado da Verificação', readonly=True)
    state = fields.Selection([
        ('draft', 'Rascunho'),
        ('checked', 'Verificado')
    ], default='draft', string='Status')

    def action_check_authenticity(self):
        self.ensure_one()
        
        # Verifica se existe uma chave pública configurada
        public_key = self.env['ir.config_parameter'].sudo().get_param('afr_supervisorio_ciclos.public_key')
        if not public_key:
            raise UserError(_('Chave pública não configurada. Por favor, configure a chave pública nas configurações do Supervisório.'))

        # Cria arquivos temporários para o arquivo e para a chave pública
        try:
            # Arquivo temporário para a fita digital
            file_content = base64.b64decode(self.file)
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.write(file_content)
            temp_file.close()

            # Arquivo temporário para a chave pública
            public_key_content = base64.b64decode(public_key)
            temp_key = tempfile.NamedTemporaryFile(delete=False)
            temp_key.write(public_key_content)
            temp_key.close()

            # Caminho do script de verificação
            script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools', 'verify_sign.sh')

            # Executa o script de verificação
            try:
                result = subprocess.run(
                    ['bash', script_path, temp_file.name, temp_key.name],
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.result = result.stdout
                self.state = 'checked'
            except subprocess.CalledProcessError as e:
                self.result = f"Erro na verificação:\n{e.stdout}\n{e.stderr}"
                self.state = 'checked'

        except Exception as e:
            raise UserError(_(f'Erro ao verificar autenticidade: {str(e)}'))
        finally:
            # Limpa os arquivos temporários
            if 'temp_file' in locals():
                os.unlink(temp_file.name)
            if 'temp_key' in locals():
                os.unlink(temp_key.name)

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        } 