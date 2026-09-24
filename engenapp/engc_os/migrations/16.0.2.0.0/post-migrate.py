"""Rede de segurança: garante `display_decimals = 3` nas unidades de medida
já existentes, para quem não passar pelo caminho normal de upgrade.

No caminho normal do Odoo 16, isto é redundante: `display_decimals` é
`required=True` com `default=3`, e o `_auto_init`/`_init_column` do ORM
preenche a coluna nova com esse default para as linhas já existentes ANTES
de aplicar a constraint NOT NULL. Verificado na prática: rodando `-u
engc_os` do zero na base `qualificacao-dev`, as 4 unidades pré-existentes
(Celsius, Bar, %UR, Tempo) já apareceram com `display_decimals = 3` e esta
migração não teve nada para corrigir (`0 unidade(s) ajustada(s)` no log).

Ainda assim, este script fica como rede de segurança NÃO-DESTRUTIVA para
caminhos de upgrade fora do padrão, onde esse backfill do ORM pode não ter
rodado — por exemplo uma restauração parcial de backup, uma coluna criada
por DDL manual, ou uma base que teve o campo adicionado sem o `default` (ex.
por um patch aplicado fora de ordem). Nesses casos, uma unidade com
`display_decimals = 0` faria o certificado imprimir os valores sem nenhuma
casa decimal — o mesmo tipo de bug que esta task inteira existe para
corrigir, só que na direção oposta (0 casas em vez de 2 truncadas).

Idempotente e conservador: só toca linhas em NULL ou 0; nunca sobrescreve
uma unidade que tenha sido configurada de propósito com 0 casas decimais
(ex.: uma futura unidade "Ciclos", contagem inteira) depois do upgrade.
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
