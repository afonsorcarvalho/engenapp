from odoo import models, fields, api
import base64
import os
import subprocess
import tempfile
import logging
import stat

_logger = logging.getLogger(__name__)

class PublicAuthenticityCheck(models.Model):
    _name = 'afr.public.authenticity.check'
    _description = 'Verificação Pública de Autenticidade'
    _inherit = ['portal.mixin']

    name = fields.Char(string='Nome', required=True, default='Nova Verificação')
    digital_tape_file = fields.Char(string='Arquivo da Fita Digital', required=True)
    digital_tape_filename = fields.Char(string='Nome do Arquivo')
    verification_result = fields.Text(string='Resultado da Verificação', readonly=True)
    state = fields.Selection([
        ('draft', 'Rascunho'),
        ('verified', 'Verificado'),
        ('error', 'Erro')
    ], string='Status', default='draft', readonly=True)
    date = fields.Datetime(string='Data da Verificação', default=fields.Datetime.now)

    def action_verify_authenticity(self):
        self.ensure_one()
        pub_key_path = None
        tape_path = None
        try:
            # Obter a chave pública das configurações
            public_key = self.env['ir.config_parameter'].sudo().get_param('afr_supervisorio_ciclos.public_key')
            if not public_key:
                raise ValueError("Chave pública não configurada no sistema")

            # Criar arquivo temporário para a chave pública
            with tempfile.NamedTemporaryFile(mode='w', suffix='.pub', delete=False) as pub_key_file:
                pub_key_file.write(base64.b64decode(public_key).decode())
                pub_key_path = pub_key_file.name

            # Criar arquivo temporário para a fita digital
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as tape_file:
                if isinstance(self.digital_tape_file, bytes):
                    tape_file.write(self.digital_tape_file)
                else:
                    tape_file.write(base64.b64decode(self.digital_tape_file))
                tape_path = tape_file.name

            # Caminho do script verify_sign.sh
            module_path = os.path.dirname(os.path.dirname(__file__))
            script_path = os.path.join(module_path, 'tools', 'verify_sign.sh')
            
            # Garantir que o script tem permissão de execução
            #st = os.stat(script_path)
            #os.chmod(script_path, st.st_mode | stat.S_IEXEC | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

            # Executar verificação
            process = subprocess.Popen(
                [script_path, tape_path, pub_key_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.dirname(script_path)  # Executar no diretório do script
            )
            stdout, stderr = process.communicate()

            # Processar resultado
            if process.returncode == 0:
                self.verification_result = "✅ Arquivo verificado com sucesso!\nAssinatura digital válida."
                self.state = 'verified'
            else:
                error_msg = stderr.decode() if stderr else stdout.decode()
                self.verification_result = f"❌ Erro na verificação:\n{error_msg}"
                self.state = 'error'

        except Exception as e:
            self.verification_result = f"❌ Erro durante a verificação: {str(e)}"
            self.state = 'error'
            _logger.error("Erro na verificação de autenticidade: %s", str(e))

        finally:
            # Limpar arquivos temporários
            if pub_key_path:
                try:
                    os.unlink(pub_key_path)
                except Exception:
                    pass
            if tape_path:
                try:
                    os.unlink(tape_path)
                except Exception:
                    pass

        return True 