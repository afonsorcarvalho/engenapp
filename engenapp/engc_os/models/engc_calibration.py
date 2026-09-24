

import json
from math import sqrt
from statistics import mean, stdev

from datetime import date
from dateutil.relativedelta import relativedelta



from odoo import models, fields, api, _
#from odoo.addons import decimal_precision as dp
from odoo import netsvc

from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
from babel.dates import  format_date
from odoo.tools.misc import  get_lang

import logging
_logger = logging.getLogger(__name__)

#TODO Não deixar excluir instrumento padrao caso ele esteja sendo utilizado nas medidas adquiridas

class EngcCalibration(models.Model):
    _name = 'engc.calibration'
    _inherit = ['mail.thread']
    _description = 'Calibração de Equipamentos'
    _check_company_auto = True

    name = fields.Char( readonly=True, default=lambda self: _('New'))

    STATES = [
        ('draft', 'Rascunho'),
        ('confirmed', 'Em andamento'),
        ('done', 'Concluída'),
    ]
    state = fields.Selection(string='State', selection=STATES, default="draft", 
    required=True, tracking=True
    )
    
    company_id = fields.Many2one(
        string='Instituição',
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.user.company_id
    )
    os_id = fields.Many2one("engc.os", "Ordem de Serviço")
    client_id = fields.Many2one("res.partner", "Cliente", required=True)
    equipment_id = fields.Many2one("engc.equipment",'Equipamento', 
    required=True
    )

    technician_id = fields.Many2one(
        'hr.employee', 'Técnico', check_company=True, required=True)
    date_calibration = fields.Date(
        'Data Cal.', help="Data da realização da calibração", required=True)
    date_next_calibration = fields.Date('Próxima Calibração')
    
    @api.constrains("date_next_calibration", "date_calibration", )
    def _check_date_calibration(self):
        for rec in self:
            if not rec.date_calibration or not rec.date_next_calibration:
                continue
            if rec.date_calibration > rec.date_next_calibration:
                raise ValidationError(_("A data de calibração não pode ser maior que a data da próxima calibração"))
    
    instruments_ids = fields.Many2many(string='Instrumentos padrão', comodel_name='engc.calibration.instruments', required=True)
    
    issue_date = fields.Date('Data de Emissão', help="Data de emissão do certificado de calibração")
    duration = fields.Float('Duração')
    note = fields.Text("Observações")
    measurement_procedure = fields.Many2one(string='Norma/Procedimento', comodel_name='engc.calibration.measurement.procedure', ondelete='restrict', required=True)
    measurement_ids = fields.One2many(string='Cod. Medidas', comodel_name='engc.calibration.measurement',inverse_name='calibration_id')
    
    environmental_conditions = fields.Char('Condições ambientais', 
    required=True, 
    default='25 ºC, 60% UR',
    
    
    ) 
    @api.onchange('date_calibration')
    def onchange_date_calibration(self):
        if self.date_calibration:
            self.date_next_calibration = self.date_calibration + relativedelta(years=1)
    # @api.ondelete(at_uninstall=False)
    # def _unlink_except_instruments_ids(self):
        
    #     if any(instrument.id in self.instruments_ids.mapped(lambda r: r.id) for instrument in self.measurement_ids.mapped(lambda r: r.instrument_id)):
    #         raise UserError("Não pode deletar um instrumento que está em um medida adquirida ")
        
    @api.model_create_multi
    def create(self, vals_list):
        """Gera a sequência e já confirma as calibrações criadas."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                sequencia = self.env['ir.sequence']
                if vals.get('company_id'):
                    sequencia = sequencia.with_company(vals['company_id'])
                vals['name'] = sequencia.next_by_code('engc.calibration_sequence') or _('New')

        registros = super(EngcCalibration, self).create(vals_list)
        registros.action_confirmed()
        return registros
    
    def get_sign_date(self):
        '''
            Função que retorna uma string da data para impressão 
            no formato: ex. São Luis-MA, 02 de agosto de 2022
        '''
        locale = get_lang(self.env).code

        _logger.info(str(self.company_id.city )+ '-' + str(self.company_id.state_id.code))
        date_str = str(self.company_id.city) + '-' + str(self.company_id.state_id.code) + ', ' + format_date(self.issue_date,format="long",locale=locale)
        return   date_str


    def action_confirmed(self):
        for rec in self:
            resp = rec.write({
                'state': 'confirmed',
            })
            if resp:
                if rec.os_id:
                    rec.os_id.calibration_created = True
                    rec.os_id.calibration_id = rec.id

    def action_done(self):
        for rec in self:
            if not rec.date_calibration:
                raise ValidationError(_("Verifique a Data de Calibração"))
            if not rec.date_next_calibration:
                raise ValidationError(_("Verifique a Data da proxima Calibração"))
            if not rec.technician_id:
                raise ValidationError(_("Verifique o Calibrado por"))

            pendentes = rec.measurement_ids.measurement_lines.filtered(
                lambda l: l.standard_status != 'ok')
            if pendentes:
                detalhe = "\n".join(
                    "- %s (%s): %s" % (
                        l.measurement_id.title or l.measurement_id.name,
                        l.true_quantity_value,
                        l.standard_message or l.standard_status)
                    for l in pendentes)
                raise ValidationError(_(
                    "Não é possível concluir: %(quantas)s linha(s) de medição "
                    "não resolvem os valores do padrão.\n\n%(detalhe)s\n\n"
                    "Se o certificado do padrão foi corrigido (ex.: um ponto "
                    "que faltava foi cadastrado), use o botão \"Recalcular "
                    "Padrão\" no cabeçalho e tente concluir de novo.",
                    quantas=len(pendentes), detalhe=detalhe))

            rec.write({
                    'state': 'done',
                    'issue_date': date.today(),


                })
    def action_draft(self):
        for rec in self:
            rec.write({

                'state': 'draft'
            })

    def action_recalcular_padrao(self):
        """Recalcula os standard_* das linhas ainda não resolvidas.

        _compute_standard_contribution deliberadamente NÃO depende das
        uncertainty_lines do certificado (decisão D5): editar o certificado
        depois de emitido não pode reescrever retroativamente uma
        calibração já registrada. Isso cria uma armadilha comum: o técnico
        mede fora da faixa do certificado, cadastra o ponto que faltava no
        instrumento padrão, e a linha CONTINUA 'fora_faixa' — nada dispara
        o compute de novo, porque nada que está no @api.depends mudou.

        Este botão dispara o recompute explicitamente, só nas linhas ainda
        pendentes, para o técnico ter um caminho depois de corrigir o
        certificado sem precisar tocar em true_quantity_value só para
        forçar o compute."""
        for rec in self:
            pendentes = rec.measurement_ids.measurement_lines.filtered(
                lambda l: l.standard_status != 'ok')
            if pendentes:
                pendentes._compute_standard_contribution()


class CalibrationInstrument(models.Model):
    _name = 'engc.calibration.instruments'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Instrumentos de calibração'

    name = fields.Char("Nome", tracking=True)
    id_number = fields.Char("Nº Idenficação")
    
    tag = fields.Char("Tag")    
    marca = fields.Char("Marca")
    modelo = fields.Char("Modelo")
   

    certificate_ids = fields.One2many(
        string='Certificado',
        comodel_name='engc.calibration.instruments.certificates',
        inverse_name='instrument_id',)
    
   

    def get_valid_certificates(self):
        """Todos os certificados válidos e não substituídos, do mais recente
        para o mais antigo."""
        self.ensure_one()
        validos = self.certificate_ids.filtered(
            lambda rec: rec.is_valid and not rec.superseded_by_id)
        return validos.sorted(
            key=lambda rec: (rec.date_calibration or date.min, rec.id),
            reverse=True,
        )

    def get_certificate_valid(self):
        """Certificado válido a usar — no máximo UM registro.

        Devolvia o recordset inteiro, o que quebrava o `t-field` do template
        do certificado em qualquer instrumento com mais de um válido (caso
        real: QPT-014, com três). Assinatura mantida por causa do QWeb.
        """
        self.ensure_one()
        return self.get_valid_certificates()[:1]


class CalibrationInstrumentCertificates(models.Model):
    _name = 'engc.calibration.instruments.certificates'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Certificados dos Instrumentos de calibração'

    
    instrument_id = fields.Many2one(
        string='Instrumento',
        comodel_name='engc.calibration.instruments',
        ondelete='restrict',
        required=True
        
    )
    certificate_calibration = fields.Binary(
        "Certificado de Calibração", tracking=True)
    certificate_number = fields.Char(
        string='Nº Certificado', tracking=True)
    certificate_partner = fields.Many2one(
        string='Certificadora', comodel_name='res.partner', ondelete='restrict', tracking=True)
    date_calibration = fields.Date(
        'Data da Calibração', tracking=True)
    date_next_calibration = fields.Date(
        'Data Prox. Cal.', tracking=True)
    validate_calibration = fields.Date(
        'Data de Validade', tracking=True)
    environmental_conditions = fields.Char('Condições ambientais') 

    uncertainty_lines = fields.One2many(
        string='Incertezas e erros',
        comodel_name='engc.calibration.instruments.uncertainty.lines',
        inverse_name='certificate',
    )
    is_valid = fields.Boolean(
        string="É válido",
        compute="_compute_is_valid",
        help="Certificado dentro do prazo de validade na data de hoje.",
    )
    certificate_file_ids = fields.One2many(
        string='Arquivos / idiomas',
        comodel_name='engc.calibration.instruments.certificates.file',
        inverse_name='certificate_id',
        help="Versões do MESMO certificado em outros idiomas. Não cadastre "
             "aqui um certificado diferente — crie outro registro.")
    superseded_by_id = fields.Many2one(
        string='Substituído por',
        comodel_name='engc.calibration.instruments.certificates',
        ondelete='set null',
        help="Preenchido quando este registro é duplicata de outro (ex.: a "
             "mesma calibração cadastrada duas vezes, em idiomas diferentes). "
             "Certificados substituídos são ignorados na escolha do válido.")

    @api.depends('validate_calibration')
    def _compute_is_valid(self):
        hoje = date.today()
        for rec in self:
            rec.is_valid = bool(rec.validate_calibration) and rec.validate_calibration >= hoje

    def name_get(self):
        """Sem isto, o fallback do Odoo é "model,id" — foi exatamente o
        que apareceu no painel de certificado da medição (Fase 2): em vez
        de "R1236/2026", o campo mostrava
        "engc.calibration.instruments.certificates,1284".

        Usa name_get (não _rec_name) de propósito: _rec_name mudaria o
        display_name em TODO lugar, inclusive no widget de
        superseded_by_id; e certificate_number não é obrigatório, então um
        certificado salvo sem número precisa de um rótulo não-vazio mesmo
        assim.
        """
        result = []
        for rec in self:
            if rec.certificate_number:
                name = rec.certificate_number
            elif rec.date_calibration:
                name = _("Certificado de %s") % rec.date_calibration
            else:
                name = "%s,%s" % (rec._name, rec.id)
            result.append((rec.id, name))
        return result


    @api.onchange('date_calibration')
    def onchange_date_calibration(self):
        if self.date_calibration:
            self.date_next_calibration = self.date_calibration + relativedelta(years=1)
            self.validate_calibration = self.date_calibration + relativedelta(years=1)

    def verify_is_valid(self):
        self.ensure_one()
        return bool(self.validate_calibration) and self.validate_calibration >= date.today()

    def _uncertainty_from_line(self, linha):
        """Monta o dict de contribuições a partir de uma linha do certificado."""
        return {
            'status': 'ok',
            'message': '',
            'erro_value': linha.erro_value,
            'uncertainty': linha.uncertainty,
            'coverage_factor': linha.coverage_factor,
            'veff': linha.veff,
            'veff_infinito': linha.veff_infinito,
            'resolution': linha.resolution,
            'source_line_id': linha.id,
        }

    def _incerteza_padrao(self, linha):
        """u = U / k.

        Devolve 0.0 quando k é zero: cadastro incompleto não pode derrubar
        um compute store=True, e um k ausente torna a linha incomparável,
        não infinita.
        """
        if not linha.coverage_factor:
            return 0.0
        return linha.uncertainty / linha.coverage_factor

    def _pior_ponto(self, a, b):
        """O ponto de maior incerteza padrão entre dois.

        Empate resolve pelo menor id, para o resultado não depender da
        ordem de iteração do recordset (Review Focus 4).
        """
        casas = self.env['decimal.precision'].precision_get('Calibration')
        ua = self._incerteza_padrao(a)
        ub = self._incerteza_padrao(b)
        comparacao = float_compare(ua, ub, precision_digits=casas)
        if comparacao > 0:
            return a
        if comparacao < 0:
            return b
        return a if a.id <= b.id else b

    def _select_uncertainty_at(self, unit, value):
        """Contribuições do padrão na grandeza `unit`, no ponto `value`.

        NUNCA levanta exceção — devolve sempre um dict com 'status'. Um
        compute store=True chama isto, e um compute que estoura derruba
        todo `-u` do módulo sobre dado histórico já gravado.
        """
        vazio = {
            'status': 'sem_unidade',
            'message': '',
            'erro_value': 0.0,
            'uncertainty': 0.0,
            'coverage_factor': 0.0,
            'veff': 0.0,
            'veff_infinito': False,
            'resolution': 0.0,
            'source_line_id': False,
        }
        if not self:
            return dict(vazio, status='sem_certificado', message=_(
                "Nenhum certificado válido para o padrão desta medição."))
        self.ensure_one()
        if not unit:
            return dict(vazio, message=_("Unidade de medida não informada."))

        linhas = self.uncertainty_lines.filtered(
            lambda r: r.unit_of_measurement == unit)
        if not linhas:
            return dict(vazio, message=_(
                "O certificado %(cert)s não tem linha de incerteza para a "
                "unidade %(unidade)s.",
                cert=self.certificate_number or '',
                unidade=unit.display_name))

        genericas = linhas.filtered('is_generic')
        if genericas:
            return self._uncertainty_from_line(genericas[0])

        casas = self.env['decimal.precision'].precision_get('Calibration')
        pontos = linhas.sorted(key=lambda r: r.nominal_value)
        minimo = pontos[0].nominal_value
        maximo = pontos[-1].nominal_value

        if (float_compare(value, minimo, precision_digits=casas) < 0
                or float_compare(value, maximo, precision_digits=casas) > 0):
            return dict(vazio, status='fora_faixa', message=_(
                "Valor %(valor)s fora da faixa calibrada do certificado "
                "%(cert)s (%(minimo)s a %(maximo)s).",
                valor=value, cert=self.certificate_number or '',
                minimo=minimo, maximo=maximo))

        exatos = pontos.filtered(
            lambda r: float_compare(
                r.nominal_value, value, precision_digits=casas) == 0)
        if exatos:
            return self._uncertainty_from_line(exatos[0])

        inferior = pontos.filtered(
            lambda r: float_compare(
                r.nominal_value, value, precision_digits=casas) < 0)[-1]
        superior = pontos.filtered(
            lambda r: float_compare(
                r.nominal_value, value, precision_digits=casas) > 0)[0]

        resultado = self._uncertainty_from_line(
            self._pior_ponto(inferior, superior))

        intervalo = superior.nominal_value - inferior.nominal_value
        fracao = (value - inferior.nominal_value) / intervalo
        resultado['erro_value'] = (
            inferior.erro_value
            + fracao * (superior.erro_value - inferior.erro_value))
        return resultado


class CalibrationInstrumentCertificateFile(models.Model):
    _name = 'engc.calibration.instruments.certificates.file'
    _description = 'Arquivos do certificado (variantes de idioma)'
    _order = 'id'

    certificate_id = fields.Many2one(
        string='Certificado',
        comodel_name='engc.calibration.instruments.certificates',
        ondelete='cascade',
        required=True,
        index=True,
    )
    lang_id = fields.Many2one(
        string='Idioma', comodel_name='res.lang', ondelete='restrict')
    name = fields.Char(
        string='Identificação',
        help="Como este arquivo é identificado. Ex.: o número do certificado "
             "na versão em inglês.")
    file = fields.Binary(string='Arquivo')
    filename = fields.Char(string='Nome do arquivo')


class CalibrationIntrumentUncertaintyLines(models.Model):
    _name = 'engc.calibration.instruments.uncertainty.lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Incertezas dos Instrumentos de calibração'
    
    
    certificate = fields.Many2one(
        string='Instrumento',
        comodel_name='engc.calibration.instruments.certificates',
        ondelete='restrict',
        required=True
    )

    
    erro_value= fields.Float(string="Erro fiducial", digits='Calibration')
    uncertainty = fields.Float('Incerteza',
    required=True, digits='Calibration'
    )
    coverage_factor= fields.Float(string="Fator K",
        required=True, default=2.0
     )
    veff = fields.Float(string = "Veff", help="Graus de liberdade efetiva. Para valores infinitos preencha com qualquer número maior que 100")
    resolution = fields.Float(string = "Resolução", help="Resolução do padrão",
        required=True, digits='Calibration'
    )
    unit_of_measurement = fields.Many2one(string='Unidade de medida', comodel_name='engc.calibration.measurement.unit', ondelete='restrict',
    required=True
    )

    is_generic = fields.Boolean(
        string="Vale para toda a faixa",
        default=True,
        help="Marcado: a linha vale para qualquer valor medido — é o cadastro "
             "antigo, um conjunto de valores por unidade. Desmarcado: a linha "
             "vale para o ponto nominal indicado.",
    )
    nominal_value = fields.Float(
        string="Valor nominal",
        digits='Calibration',
        help="O ponto calibrado a que esta linha se refere. Só tem efeito "
             "com 'Vale para toda a faixa' desmarcado.",
    )
    veff_infinito = fields.Boolean(
        string="Veff infinito",
        default=True,
        help="Marcado: graus de liberdade efetivos infinitos, o caso usual "
             "em certificado de padrão. Desmarcado: usar o valor de Veff.",
    )

    @api.constrains('is_generic', 'nominal_value', 'certificate',
                    'unit_of_measurement')
    def _check_pontos_coerentes(self):
        """Impede os três arranjos ambíguos dentro de um mesmo
        (certificado, unidade).

        A terceira checagem é a que fecha o bug que originou esta fase: sem
        ela, duas linhas na mesma unidade fazem _search_statistics devolver
        um recordset e qualquer leitura de campo levanta Expected singleton.
        """
        casas = self.env['decimal.precision'].precision_get('Calibration')
        for rec in self:
            irmas = rec.certificate.uncertainty_lines.filtered(
                lambda r: r.unit_of_measurement == rec.unit_of_measurement
                and r.id != rec.id
            )
            genericas = irmas.filtered('is_generic')
            if rec.is_generic:
                if genericas:
                    raise ValidationError(_(
                        "Já existe uma linha 'vale para toda a faixa' para a "
                        "unidade %s neste certificado."
                    ) % rec.unit_of_measurement.display_name)
                if irmas - genericas:
                    raise ValidationError(_(
                        "Não é possível misturar uma linha 'vale para toda a "
                        "faixa' com linhas de ponto na unidade %s. Ou a "
                        "unidade tem um conjunto único de valores, ou tem "
                        "pontos nominais."
                    ) % rec.unit_of_measurement.display_name)
            else:
                if genericas:
                    raise ValidationError(_(
                        "A unidade %s já tem uma linha 'vale para toda a "
                        "faixa' neste certificado. Desmarque-a antes de "
                        "cadastrar pontos."
                    ) % rec.unit_of_measurement.display_name)
                repetido = (irmas - genericas).filtered(
                    lambda r: float_compare(
                        r.nominal_value, rec.nominal_value,
                        precision_digits=casas) == 0
                )
                if repetido:
                    raise ValidationError(_(
                        "Já existe uma linha para o valor nominal %s na "
                        "unidade %s deste certificado."
                    ) % (rec.nominal_value,
                         rec.unit_of_measurement.display_name))


class CalibrationTypes(models.Model):
    _name = 'engc.calibration.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Tipos de calibração'

    name = fields.Char("Nome", tracking=True)


class CalibrationMeasurement (models.Model):
    _name = 'engc.calibration.measurement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Medições da Calibração'

    name = fields.Char( readonly=True, default=lambda self: _('New'))
    title = fields.Char("Título",help="O título que aparecerá no certificado acima das medidas adquiridas")
    calibration_id = fields.Many2one(string='Cod. Calibração', comodel_name='engc.calibration', ondelete='restrict')
    date_measurement= fields.Date("Data de aquisição")
    measurement_lines = fields.One2many('engc.calibration.measurement.lines', 'measurement_id')
    coverage_factor= fields.Float(string="Fator K padrão",
    required=True, default=2.0, help="Fator de abrangência padrão que será utilizado no cálculo da incerteza das medições"
     )
    environmental_conditions = fields.Char('Condições ambientais', default="25 graus Celsius, Umidade Relativa 60%")
    instrument_id = fields.Many2one(
        'engc.calibration.instruments',
        string='Padrão utilizado',
        required=True
        )
    instrument_id_domain = fields.Char(
        compute="_compute_instrument_id_domain",
        readonly=True,
        store=False,
    )
    unit_of_measurement = fields.Many2one(string='Unidade de medida', comodel_name='engc.calibration.measurement.unit', ondelete='restrict')
    unit_of_measurement_domain = fields.Char(
        compute="_compute_unit_of_measurement_domain",
        readonly=True,
        store=False,
    )
    @api.depends('calibration_id')
    def _compute_instrument_id_domain(self):
        for rec in self:
            ids_permitidos = rec.calibration_id.instruments_ids.ids
            rec.instrument_id_domain = json.dumps([('id', 'in', ids_permitidos)])


    @api.depends('instrument_id')
    def _compute_unit_of_measurement_domain(self):
        for rec in self:
            # get_certificate_valid() faz ensure_one() no instrumento (Task 3);
            # sem essa guarda, uma linha de medição sem padrão escolhido ainda
            # (instrument_id vazio) levantaria "Expected singleton" aqui — o
            # mesmo tipo de erro que a Task 3 corrigiu no PDF. Também trocado
            # `self.instrument_id` (bug pré-existente) por `rec.instrument_id`.
            certificates = (
                rec.instrument_id.get_certificate_valid()
                if rec.instrument_id
                else self.env['engc.calibration.instruments.certificates']
            )
            uncertainty_lines = certificates.mapped(lambda r: r.uncertainty_lines)
            unit_of_measurement_lines = uncertainty_lines.mapped(lambda r: r.unit_of_measurement)
            rec.unit_of_measurement_domain = json.dumps(
                [('id', 'in', unit_of_measurement_lines.mapped(lambda r: r.id))]
            )
    
    certificate_id = fields.Many2one(
        string="Certificado do padrão",
        comodel_name='engc.calibration.instruments.certificates',
        compute='_compute_certificate_id',
        help="O certificado válido mais recente do padrão escolhido — o mesmo "
             "que o PDF do certificado de calibração cita.")
    certificate_validate = fields.Date(
        string="Validade do certificado",
        related='certificate_id.validate_calibration', readonly=True)

    @api.depends('instrument_id')
    def _compute_certificate_id(self):
        for rec in self:
            rec.certificate_id = (
                rec.instrument_id.get_certificate_valid()
                if rec.instrument_id else False)

    @api.onchange('instrument_id')
    def onchange_instrument_id(self):
        self.unit_of_measurement = None

    @api.model
    def create(self, vals_list):
        """Salva ou atualiza os dados no banco de dados"""
        if 'company_id' in vals_list:
            vals_list['name'] = self.env['ir.sequence'].with_context(force_company=self.env.user.company_id.id).next_by_code(
                'engc.calibration_measurement_sequence') or _('New')
        else:
            vals_list['name'] = self.env['ir.sequence'].next_by_code('engc.calibration_measurement_sequence') or _('New')
        
        
        result = super(CalibrationMeasurement, self).create(vals_list)
        return result
   
class CalibrationMeasurementLines (models.Model):
    _name = 'engc.calibration.measurement.lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Medições da Calibração'

   
    measurement_id = fields.Many2one(string='Cod. Medidas', comodel_name='engc.calibration.measurement', ondelete='restrict')

    unit_of_measurement = fields.Many2one(string='Unidade de medida', comodel_name='engc.calibration.measurement.unit', related='measurement_id.unit_of_measurement' )
    true_quantity_value = fields.Float(string="Valor Real", digits='Calibration' )
    measurement_quantity_value_1= fields.Float(string="Leitura 01", digits='Calibration' )
    measurement_quantity_value_2= fields.Float(string="Leitura 02", digits='Calibration' )
    measurement_quantity_value_3= fields.Float(string="Leitura 03", digits='Calibration' )
    measurement_quantity_value_mean= fields.Float(string="Média", compute="_compute_statistics", store=True, digits='Calibration')
    erro_value= fields.Float(string="Valor Erro", compute="_compute_statistics", store=True, digits='Calibration' )
    uncertainty= fields.Float(string="Incerteza",compute="_compute_statistics", store=True, digits='Calibration' )
    coverage_factor= fields.Float(string="Fator K", default=2.0 )
    veff = fields.Float(string = "Veff",compute="_compute_statistics", store=True)
    resolutino_instrument = fields.Float(string = "Resolução do instrumento", compute="_compute_statistics", store=True, digits='Calibration')

    STANDARD_STATUS = [
        ('ok', 'OK'),
        ('sem_certificado', 'Sem certificado válido'),
        ('sem_unidade', 'Unidade não consta do certificado'),
        ('fora_faixa', 'Fora da faixa calibrada'),
    ]

    standard_status = fields.Selection(
        string="Situação do padrão", selection=STANDARD_STATUS,
        compute="_compute_standard_contribution", store=True)
    standard_message = fields.Char(
        string="Detalhe do padrão",
        compute="_compute_standard_contribution", store=True)
    standard_line_id = fields.Many2one(
        string="Ponto do certificado",
        comodel_name='engc.calibration.instruments.uncertainty.lines',
        ondelete='set null',
        compute="_compute_standard_contribution", store=True,
        help="Qual linha do certificado do padrão sustentou esta medição.")
    standard_uncertainty = fields.Float(
        string="Incerteza do padrão", digits='Calibration',
        compute="_compute_standard_contribution", store=True)
    standard_erro = fields.Float(
        string="Erro do padrão", digits='Calibration',
        compute="_compute_standard_contribution", store=True)
    standard_resolution = fields.Float(
        string="Resolução do padrão", digits='Calibration',
        compute="_compute_standard_contribution", store=True)
    standard_coverage_factor = fields.Float(
        string="Fator K do padrão",
        compute="_compute_standard_contribution", store=True)
    standard_veff = fields.Float(
        string="Veff do padrão",
        compute="_compute_standard_contribution", store=True)
    standard_veff_infinito = fields.Boolean(
        string="Veff do padrão infinito",
        compute="_compute_standard_contribution", store=True)

    @api.onchange('true_quantity_value')
    def onchange_true_quantity_value(self):
        """Avisa na hora quando o ponto não resolve. Não bloqueia: quem
        bloqueia é action_done()."""
        self.ensure_one()
        if self.standard_status and self.standard_status != 'ok':
            return {'warning': {
                'title': _("Padrão não resolvido neste ponto"),
                'message': self.standard_message or '',
            }}

    @api.depends('true_quantity_value',
                 'measurement_id.instrument_id',
                 'measurement_id.unit_of_measurement')
    def _compute_standard_contribution(self):
        """Resolve as contribuições do padrão no ponto desta linha.

        NUNCA levanta. Este compute é store=True, e um compute que estoura
        derruba todo `-u` do módulo: o upgrade recomputa os campos de todas
        as linhas já gravadas, e basta uma com certificado vencido ou ponto
        fora de faixa para impedir qualquer atualização futura.

        O bloqueio do técnico mora no onchange e em action_done().
        """
        sem_padrao = {
            'status': 'sem_certificado',
            'message': _("Nenhum certificado válido para o padrão desta medição."),
            'erro_value': 0.0, 'uncertainty': 0.0, 'coverage_factor': 0.0,
            'veff': 0.0, 'veff_infinito': False, 'resolution': 0.0,
            'source_line_id': False,
        }
        for rec in self:
            padrao = rec.measurement_id.instrument_id
            certificado = padrao.get_certificate_valid() if padrao else padrao
            if not certificado:
                dados = sem_padrao
            else:
                dados = certificado._select_uncertainty_at(
                    rec.measurement_id.unit_of_measurement,
                    rec.true_quantity_value,
                )
            rec.standard_status = dados['status']
            rec.standard_message = dados['message']
            rec.standard_line_id = dados['source_line_id']
            rec.standard_uncertainty = dados['uncertainty']
            rec.standard_erro = dados['erro_value']
            rec.standard_resolution = dados['resolution']
            rec.standard_coverage_factor = dados['coverage_factor']
            rec.standard_veff = dados['veff']
            rec.standard_veff_infinito = dados['veff_infinito']

    @api.depends('standard_uncertainty','standard_coverage_factor','standard_erro','standard_resolution','true_quantity_value','coverage_factor','measurement_quantity_value_1','measurement_quantity_value_2','measurement_quantity_value_3')
    def _compute_statistics(self):
        for rec in self:
            # Fase 2: os valores do padrão passaram a ser resolvidos por
            # linha, no ponto dela. A ARITMÉTICA ABAIXO NÃO MUDOU — só a
            # origem destes quatro números.
            uncertainty_instrument = rec.standard_uncertainty
            k_instrument = 2.0
            if rec.standard_coverage_factor != 0:
                k_instrument = rec.standard_coverage_factor

            erro_instrument = rec.standard_erro
            resolution_instrument = rec.standard_resolution

            for record in rec:
                values = [
                    record.measurement_quantity_value_1,
                    record.measurement_quantity_value_2,
                    record.measurement_quantity_value_3,
                    ]
            
                record.measurement_quantity_value_mean = mean(values)
                record.erro_value = record.measurement_quantity_value_mean - record.true_quantity_value
                # incerteza combinada é igual a raiz quadrada da soma de:
                #    - incerteza das medidas
                #    - incerteza do instrumento
                #    - incerteza do erro do instrumento
                #    - incerteza da resolução do instrumento
            
                combined_uncertainty = sqrt((stdev(values)/2)**2
                        + (uncertainty_instrument/k_instrument)**2
                        + (erro_instrument/sqrt(3))**2
                        + (resolution_instrument/sqrt(12))**2
                        )
                
                # incerteza =  incerteza combinada*k
                record.uncertainty = record.coverage_factor * combined_uncertainty
                record.resolutino_instrument = resolution_instrument

                #grau de liberdade efetivo
                # Fórmula vigente (NÃO é Welch-Satterthwaite — ver seção 5.2 do
                # relatório; a correção é da Fase 3). Aqui só se troca o except
                # nu por um específico: leituras idênticas zeram o desvio padrão.
                try:
                    record.veff = 3*(combined_uncertainty/(stdev(values)/2))**4
                except ZeroDivisionError:
                    record.veff = 0





   
    
class CalibrationMeasurementProcedure (models.Model):
    _name = 'engc.calibration.measurement.procedure'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Procedimentos de Medições da Calibração'

    STATES = [
        ('review', 'Em Revisão'),
        ('emited', 'Emitido'),
        ('confered', 'Conferido'),
        ('aproved', 'Aprovado'),
        ('cancel', 'Cancelado'),
    ]
    state = fields.Selection(string='State', selection=STATES, default="review", 
    required=True
    )

    name = fields.Char( readonly=True, default=lambda self: _('New'))
    codigo = fields.Char("Código", tracking=True)
    description = fields.Char("Descrição")
    
    environmental_conditions = fields.Char("Condições ambientais")
    revision = fields.Integer(string='Revisão',tracking=True)
    emission = fields.Many2one(string= "Emitido por",
        comodel_name='hr.employee',tracking=True
    )
    checked = fields.Many2one( string="Conferido por",comodel_name='hr.employee',tracking=True)
    aproved = fields.Many2one( string="Aprovado por",comodel_name='hr.employee',tracking=True)

    
    objective = fields.Html("Objetivo")
    application = fields.Html("Aplicação")
    reference_documents = fields.Html("Documentos de Referência")
    terminology = fields.Html("Terminologia")
    materials_used = fields.Html("Materiais utilizados")
    ambiental_conditions = fields.Html("Condições ambientais")
    precaution_and_preparation = fields.Html("Precauções e Preparação")
    method = fields.Html("Método")
    analysis = fields.Html("Determinação e análise dos resultados")
    measurement_uncertainty = fields.Html("Incerteza da medição")
    presentation_of_results = fields.Html("Apresentação dos resultados")
    
    anexos_ids = fields.One2many(string='Anexos',comodel_name='engc.calibration.measurement.procedure.anexos',inverse_name='measurements_procedure_ids' )
    changes = fields.Html("Alterações")
    document = fields.Binary(
        "Documento do PM", tracking=True)

    @api.model
    def create(self, vals_list):
        """Salva ou atualiza os dados no banco de dados"""
        if 'company_id' in vals_list:
            vals_list['name'] = self.env['ir.sequence'].with_context(force_company=self.env.user.company_id.id).next_by_code(
                'engc.calibration_procedure_sequence') or _('New')
        else:
            vals_list['name'] = self.env['ir.sequence'].next_by_code('engc.calibration_procedure_sequence') or _('New')
        

        result = super(CalibrationMeasurementProcedure, self).create(vals_list)
        return result

    #******************************************
    #  ACTIONS
    #
    #******************************************
    
    def action_emited(self):
        self.write({
            'state':'emited'
        })
        

    def action_confered(self):
        self.write({
            'state':'confered'
        })

    def action_aproved(self):
        self.write({
            'state':'aproved'
        })

    def action_review(self):
        self.write({
            'state':'review'
        })
    

    def action_cancel(self):
        self.write({
            'state':'cancel'
        })
    


class CalibrationMeasurementProcedureAnexos(models.Model):
    _name = 'engc.calibration.measurement.procedure.anexos'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Anexos do Procedimentos de Medições da Calibração'

    measurements_procedure_ids = fields.Many2one(string ='Procedimento de medição',comodel_name = 'engc.calibration.measurement.procedure')
    name = fields.Char("Título")
    text = fields.Html("Corpo do Texto")
    

class CalibrationMeasurementUnit (models.Model):
    _name = 'engc.calibration.measurement.unit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Unidade de Medida da Calibração'

    name = fields.Char("Unidade", tracking=True)

    simbolo = fields.Char("Símbolo", tracking=True)

    display_decimals = fields.Integer(
        string="Casas decimais",
        default=3,
        required=True,
        help="Quantas casas decimais usar ao imprimir valores desta unidade no "
             "certificado. Tempo em segundos costuma pedir 3; temperatura, 2.",
    )

    @api.constrains('display_decimals')
    def _check_display_decimals(self):
        for rec in self:
            if rec.display_decimals < 0 or rec.display_decimals > 6:
                raise ValidationError(
                    _("As casas decimais devem ficar entre 0 e 6 — 6 é a "
                      "precisão com que os valores são armazenados."))
