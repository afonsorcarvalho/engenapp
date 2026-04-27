# Pacote de testes standalone do submódulo fita_digital (sem Odoo).
# Inclui: ``test_dataobject_fita_digital``, ``test_reader_fita_digital``,
# ``test_fixture_arquivos`` (usa ``tests/fixtures/*.txt``).
#
# Execução (na raiz do addon afr_supervisorio_ciclos)::
#
#   PYTHONPATH=. python -m unittest discover -s fita_digital/tests -p "test_*.py"
#
# Nota: pytest, ao usar este diretório como parte do pacote do addon, tende a
# importar ``afr_supervisorio_ciclos/__init__.py`` (dependência de Odoo). Use
# unittest conforme acima para testes isolados.
