"""Preenche `display_decimals` para as unidades de medida já existentes.

Motivo (Task 6, Fase 1): o campo `display_decimals` (Integer, default=3) é
novo nesta versão. Um `default=` do ORM só é aplicado a registros criados
*depois* de o campo existir — as linhas de `engc.calibration.measurement.unit`
que já estavam na base (dev e produção) recebem o default do banco para uma
coluna inteira nova, que é `0`, não `3`.

Sem esta migração, toda unidade pré-existente (ex.: "Tempo", usada em
CAL0926.0001) imprimiria o certificado com ZERO casas decimais — ou seja,
reintroduziria silenciosamente o bug que esta task inteira existe para
corrigir (60,053 s viraria "60 s" em vez de manter os 2 dígitos antigos do
hardcode, pior ainda).

Não mexe em unidades que porventura já tenham sido configuradas com 0 casas
de propósito (ex.: uma futura unidade "Ciclos") DEPOIS do upgrade — só atua
sobre o estado imediatamente após a criação da coluna, quando tudo que não é
NULL é exatamente o default do banco (0).
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        UPDATE engc_calibration_measurement_unit
           SET display_decimals = 3
         WHERE display_decimals IS NULL
            OR display_decimals = 0
        """
    )
    _logger.info(
        "engc_os: %s unidade(s) de medida ajustada(s) para display_decimals=3.",
        cr.rowcount,
    )
