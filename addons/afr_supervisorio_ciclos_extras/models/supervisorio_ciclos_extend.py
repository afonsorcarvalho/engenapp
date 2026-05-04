"""Extensão do modelo de ciclos para incluir materiais"""
from odoo import models, fields, api
import hashlib
import hmac


class SupervisorioCiclosExtend(models.Model):
    """Extensão do modelo de ciclos para incluir relação com materiais"""
    
    _inherit = 'afr.supervisorio.ciclos'
    
    # Relação One2many com as linhas de materiais
    material_lines_ids = fields.One2many(
        'afr.supervisorio.cycle.materials.lines',
        'ciclo_id',
        string='Materiais Esterilizados',
        help='Lista de materiais que foram esterilizados neste ciclo'
    )
    
    # Campo computed para contar materiais
    material_count = fields.Integer(
        string='Total de Materiais',
        compute='_compute_material_count',
        store=True
    )
    
    @api.depends('material_lines_ids')
    def _compute_material_count(self):
        """Calcula o total de linhas de materiais"""
        for record in self:
            record.material_count = len(record.material_lines_ids)
    
    def action_view_materials(self):
        """Abre a visão de materiais do ciclo"""
        self.ensure_one()
        return {
            'name': 'Materiais do Ciclo',
            'type': 'ir.actions.act_window',
            'res_model': 'afr.supervisorio.cycle.materials.lines',
            'view_mode': 'tree,form',
            'domain': [('ciclo_id', '=', self.id)],
            'context': {
                'default_ciclo_id': self.id,
                'search_default_active': 1,
            },
        }
    
    def action_print_laudo_wizard(self):
        """Abre o wizard de impressão do laudo"""
        self.ensure_one()
        return {
            'name': 'Gerar Laudo de Liberação',
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.print.laudo',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ciclo_id': self.id,
                'active_id': self.id,
                'active_model': 'afr.supervisorio.ciclos',
            },
        }
    
    def _get_laudo_public_token(self, material_line_ids=None):
        """
        Gera um token único para acesso público ao laudo

        O token é assinado (HMAC-SHA256) e inclui, além do ciclo, a lista de materiais
        autorizados para o laudo. Isso impede que alguém altere a URL (ex.: adicionar IDs)
        e consiga visualizar materiais que não foram selecionados no wizard.
        
        Returns:
            str: Token único para acesso público
        """
        self.ensure_one()
        # Normaliza a lista de materiais para uma representação estável
        # (ordenação e remoção de duplicados) para que o token seja determinístico.
        material_line_ids = material_line_ids or []
        material_line_ids = tuple(sorted({int(x) for x in material_line_ids}))

        secret = self.env["ir.config_parameter"].sudo().get_param("database.secret", "default_secret")
        token_data = (self.env.cr.dbname, int(self.id), 'laudo_liberacao', material_line_ids)
        token = hmac.new(
            secret.encode('utf-8'),
            repr(token_data).encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return token
    
    def get_laudo_public_url(self, material_line_ids=None):
        """
        Retorna a URL pública para download do laudo
        
        Returns:
            str: URL completa para download público do laudo
        """
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        material_line_ids = material_line_ids or []
        material_line_ids = [str(int(x)) for x in sorted({int(x) for x in material_line_ids})]

        # Assina o token com o conjunto de materiais
        token = self._get_laudo_public_token(material_line_ids=[int(x) for x in material_line_ids])

        # Inclui os materiais na URL para o controller público aplicar o mesmo filtro do laudo.
        # Usamos string CSV para evitar query params repetidos e manter a leitura simples.
        materials_param = ",".join(material_line_ids)
        url = f"{base_url}/laudo/liberacao/public/{self.id}?token={token}&materials={materials_param}"
        return url

