"""Consolida certificados duplicados de um mesmo padrão — sem apagar nada.

Motivo (relatório 2026-09-23, seção 3 e item P0 da seção 7): o QWeb do
certificado fazia `t-field` no recordset devolvido por
get_certificate_valid(). Em instrumentos com mais de um certificado válido
isso levanta `Expected singleton` e o PDF não sai. Caso real na base
labquali: QPT-014 - Registrador Digital, com R1661/2025, R1236/2026 e
"R1236/2026 - Inglês" simultaneamente válidos.

A decisão de modelagem foi tratar "mesmo certificado em outro idioma" como
UM registro com vários arquivos. Esta migração aplica isso ao que já existe.

NÃO DESTRUTIVA de propósito: num contexto ISO/IEC 17025 não se apaga
registro de certificado. As duplicatas continuam na base, apenas marcadas
com superseded_by_id; o binário de cada uma é copiado para uma linha de
`certificate_file_ids` do certificado mantido, com o número original
preservado no campo `name`. Nada se perde e dá para desfazer limpando o
superseded_by_id.

Critério de duplicata (conservador — os três têm que bater):
    mesmo instrument_id, mesmo date_calibration, mesmo validate_calibration.
Mantém-se o de menor id. Certificados que não batem nos três campos são
deixados em paz, mesmo que o número seja parecido: adivinhar por string
("- Inglês") apagaria diferenças legítimas.

NOTA (verificação 2026-09-23): a detecção de grupos duplicados é feita em
SQL puro (rápida e sem surpresas em `GROUP BY`), mas a cópia do binário é
feita via ORM, não SQL puro. `certificate_calibration` (no certificado) e
`file` (no arquivo novo) são `fields.Binary` com `attachment=True` (o
padrão do Odoo) — ou seja, o conteúdo mora em `ir_attachment`, NÃO numa
coluna da tabela. Um `SELECT certificate_calibration FROM
engc_calibration_instruments_certificates` falha com "column does not
exist" (confirmado por teste manual). Usar o ORM aqui é o jeito correto de
copiar esse conteúdo — ele cuida do `ir_attachment`/filestore por baixo,
coisa que SQL cru teria que reimplementar à mão.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    # Sem predicado sobre superseded_by_id: nesta primeira migração a coluna
    # acabou de ser criada por este mesmo upgrade e está toda NULL, então o
    # filtro seria no-op — e evitá-lo tira a dependência da ordem entre a
    # atualização do schema e o post-migrate.
    cr.execute(
        """
        SELECT instrument_id, date_calibration, validate_calibration,
               array_agg(id ORDER BY id)
          FROM engc_calibration_instruments_certificates
      GROUP BY instrument_id, date_calibration, validate_calibration
        HAVING count(*) > 1
        """
    )
    grupos = cr.fetchall()
    if not grupos:
        _logger.info("engc_os: nenhum certificado duplicado a consolidar.")
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    Certificate = env['engc.calibration.instruments.certificates']
    CertificateFile = env['engc.calibration.instruments.certificates.file']

    total = 0
    for instrument_id, _data_cal, _validade, ids in grupos:
        mantido, duplicatas = ids[0], ids[1:]
        for dup_id in duplicatas:
            dup = Certificate.browse(dup_id)
            CertificateFile.create({
                'certificate_id': mantido,
                'name': dup.certificate_number,
                'file': dup.certificate_calibration,
            })
            dup.write({'superseded_by_id': mantido})
            total += 1
        _logger.info(
            "engc_os: padrão %s — certificado %s mantido, %s marcado(s) como "
            "substituído(s): %s",
            instrument_id, mantido, len(duplicatas), duplicatas,
        )

    _logger.info(
        "engc_os: %s certificado(s) duplicado(s) consolidado(s) em %s grupo(s). "
        "Nada foi apagado.", total, len(grupos),
    )

    cr.execute(
        """
        SELECT c.instrument_id, count(*)
          FROM engc_calibration_instruments_certificates c
         WHERE c.superseded_by_id IS NULL
           AND c.validate_calibration >= CURRENT_DATE
      GROUP BY c.instrument_id
        HAVING count(*) > 1
        """
    )
    restantes = cr.fetchall()
    for instrument_id, quantos in restantes:
        _logger.warning(
            "engc_os: padrão %s ainda tem %s certificados válidos com datas "
            "DIFERENTES. O PDF vai usar o de calibração mais recente. Conferir "
            "se algum deveria ser variante de idioma de outro.",
            instrument_id, quantos,
        )
