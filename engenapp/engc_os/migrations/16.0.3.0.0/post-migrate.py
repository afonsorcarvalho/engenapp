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
         WHERE l.veff > 0 AND l.veff <= 100 AND l.veff_infinito
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

    # FIX 6 (revisão final da Fase 2): duplicatas legadas de
    # (certificado, unidade) sobrevivem ao upgrade — @api.constrains não
    # roda sobre dado já gravado. _select_uncertainty_at() escolhe
    # genericas[0] de forma determinística e não quebra, mas a interface
    # fica bloqueada: desmarcar is_generic ou preencher nominal_value em
    # qualquer uma delas dispara o constrains novo. Detecta e avisa; não
    # apaga nada.
    cr.execute("""
        SELECT l.certificate, c.certificate_number, i.name,
               l.unit_of_measurement, u.name, COUNT(*)
          FROM engc_calibration_instruments_uncertainty_lines l
          JOIN engc_calibration_instruments_certificates c
            ON c.id = l.certificate
          JOIN engc_calibration_instruments i
            ON i.id = c.instrument_id
          LEFT JOIN engc_calibration_measurement_unit u
            ON u.id = l.unit_of_measurement
         GROUP BY l.certificate, c.certificate_number, i.name,
                  l.unit_of_measurement, u.name
        HAVING COUNT(*) > 1
    """)
    for certificado_id, numero, padrao, unidade_id, unidade, total in cr.fetchall():
        _logger.warning(
            "engc_os: certificado %s (padrão %s, certificado id %s) tem %s "
            "linhas de incerteza na unidade %s (id %s) — o arranjo ambíguo "
            "que o bug original permitia. O @api.constrains novo não "
            "corrige dado já gravado no upgrade; _select_uncertainty_at() "
            "escolhe a primeira de forma determinística e não quebra, mas "
            "a interface fica bloqueada: desmarcar 'vale para toda a "
            "faixa' ou preencher um valor nominal em qualquer uma dessas "
            "linhas dispara o constrains. É preciso remover manualmente as "
            "linhas extras antes de registrar pontos para esta unidade "
            "neste certificado.",
            numero, padrao, certificado_id, total, unidade, unidade_id)

    # FIX 7 (revisão final da Fase 2): aviso de rollout, não migração de
    # dado. O `uncertainty` já gravado nas linhas de medição existentes foi
    # calculado sob o esquema antigo (um escalar por bloco de medição). O
    # caminho de proteção de compute do Odoo grava os novos campos
    # standard_* sem marcar `uncertainty` como sujo, então o valor
    # armazenado só migra para a base nova na primeira edição de QUALQUER
    # leitura da linha, no momento em que isso acontecer — não agora, no
    # upgrade. Nenhuma base conhecida tem calibração real hoje; isto é só
    # para avisar quem chegar a ter.
    cr.execute("SELECT COUNT(*) FROM engc_calibration_measurement_lines")
    total_linhas = cr.fetchone()[0]
    if total_linhas:
        _logger.warning(
            "engc_os: a base tem %s linha(s) de medição em "
            "engc_calibration_measurement_lines cujo campo 'uncertainty' "
            "gravado é anterior a esta fase (calculado sob o esquema "
            "antigo, um valor de padrão por bloco de medição). Esses "
            "valores permanecem como estão agora — esta migração NÃO os "
            "reescreve. Cada um será recalculado individualmente na "
            "PRIMEIRA VEZ que alguém editar uma leitura (measurement_"
            "quantity_value_1/2/3, true_quantity_value ou coverage_factor) "
            "dessa linha, na base nova de standard_*. Se preservar os "
            "valores originalmente emitidos importa para alguma dessas "
            "linhas, congele-os (exporte ou anote) antes de editar "
            "qualquer leitura.",
            total_linhas)
