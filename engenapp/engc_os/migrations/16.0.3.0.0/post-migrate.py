"""Rede de segurança do backfill da Fase 2 e auditoria de Veff.

Sobre o backfill: `is_generic` e `veff_infinito` são booleanos com
`default=True`, e o `_init_column` do Odoo 16 preenche coluna nova a partir
do default — para booleano, o UPDATE só roda quando o default é truthy, que
é o nosso caso (models.py, `_init_column`: `necessary = value` para
`field.type == 'boolean'`). Verificado no fonte do container, não suposto.

Logo, no caminho normal de upgrade este script não encontra nada a fazer.
Ele existe pelo mesmo motivo do script da 16.0.2.0.0: restauração parcial de
backup, ou coluna criada por DDL manual. É idempotente e não apaga nada.

Sobre o Veff: a convenção antiga do campo era "preencha qualquer número
maior que 100 para infinito", que é confusa e já produziu dado errado. Esta
migração converte SÓ o caso inequívoco (> 100) para o booleano novo. Não
converte valores finitos: `veff = 2` é legítimo do ponto de vista do modelo,
e só o certificado em papel sabe se está certo. Esses casos saem num WARNING
para conferência manual.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        UPDATE engc_calibration_instruments_uncertainty_lines
           SET is_generic = true
         WHERE is_generic IS NULL
    """)
    genericas = cr.rowcount
    cr.execute("""
        UPDATE engc_calibration_instruments_uncertainty_lines
           SET veff_infinito = true
         WHERE veff_infinito IS NULL
    """)
    infinitos = cr.rowcount
    if genericas or infinitos:
        _logger.info(
            "engc_os: backfill defensivo — %s linha(s) is_generic, "
            "%s linha(s) veff_infinito.", genericas, infinitos)
    else:
        _logger.info(
            "engc_os: backfill já aplicado pelo _auto_init, nada a fazer.")

    cr.execute("""
        UPDATE engc_calibration_instruments_uncertainty_lines
           SET veff_infinito = true, veff = 0
         WHERE veff > 100
    """)
    if cr.rowcount:
        _logger.info(
            "engc_os: %s linha(s) com veff > 100 convertidas para "
            "'Veff infinito' — era a convenção antiga do campo.", cr.rowcount)

    cr.execute("""
        SELECT l.id, l.veff, c.certificate_number, i.name
          FROM engc_calibration_instruments_uncertainty_lines l
          JOIN engc_calibration_instruments_certificates c
            ON c.id = l.certificate
          JOIN engc_calibration_instruments i
            ON i.id = c.instrument_id
         WHERE l.veff > 0 AND l.veff <= 100
    """)
    for linha_id, veff, numero, padrao in cr.fetchall():
        _logger.warning(
            "engc_os: linha de incerteza %s (padrão %s, certificado %s) tem "
            "Veff FINITO = %s gravado, mas 'Veff infinito' está MARCADO — é o "
            "default que o upgrade aplicou a todas as linhas antigas. "
            "Conferir no certificado em papel: se ele declara um valor finito, "
            "DESMARQUE 'Veff infinito' nesta linha para que o número seja "
            "usado. A Fase 3 lê o booleano, não o número: se ficar marcado, "
            "o valor %s será descartado em silêncio.",
            linha_id, padrao, numero, veff, veff)
