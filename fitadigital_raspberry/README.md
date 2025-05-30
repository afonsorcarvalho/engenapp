# Documentação do Projeto FITADIGITAL

## Visão Geral

O projeto `fitadigital.py` realiza a leitura de dados de uma porta serial e processa esses dados em arquivos, organizando-os em ciclos conforme regras específicas. O script é altamente configurável via um arquivo YAML (`config.yaml`) e utiliza multithreading para garantir que a leitura e o processamento ocorram de forma assíncrona e eficiente.

---

## Estrutura do Script

- **Configuração**: Carrega parâmetros do arquivo `config.yaml`, como porta serial, diretórios de entrada/saída, módulo de processamento de cabeçalho, entre outros.
- **Logger**: Utiliza uma classe de logging customizada para registrar eventos e erros.
- **Importação Dinâmica**: Carrega dinamicamente o módulo responsável por processar o cabeçalho dos arquivos.
- **Classes Principais**:
  - `SerialReader`: Thread responsável por ler continuamente dados da porta serial e salvar em arquivos diários.
  - `FileProcessor`: Thread responsável por processar os arquivos de entrada, identificar ciclos e organizar os dados em arquivos separados por ciclo.

---

## Descrição das Classes e Métodos

### Classe: `SerialReader`

- **Objetivo**: Ler dados da porta serial e salvar em arquivos de texto, um para cada dia.
- **Principais métodos**:
  - `__init__(self, serial_port, output_dir)`: Inicializa a thread com a porta serial e diretório de saída.
  - `update_config(self, filename)`: Atualiza o arquivo de configuração com o nome do arquivo atualmente em uso.
  - `run(self)`: Executa a leitura contínua da porta serial, salvando os dados no arquivo do dia correspondente.

### Classe: `FileProcessor`

- **Objetivo**: Processar arquivos de entrada, identificar ciclos e criar arquivos separados para cada ciclo.
- **Principais métodos**:
  - `__init__(self, input_dir, output_dir)`: Inicializa a thread com diretórios de entrada e saída.
  - `update_config(self, filename, pointer_file)`: Atualiza o arquivo de configuração com o arquivo e ponteiro atual.
  - `add_files_cycle(self, lines, cycles_print)`: Cria arquivos para cada ciclo identificado, escrevendo apenas se houver alteração.
  - `file_processor_yesterday(self, file_name)`: Retorna o nome do arquivo do dia anterior ao arquivo atual.
  - `run(self)`: Executa o processamento contínuo dos arquivos, concatenando dados do dia atual e anterior, identificando ciclos e salvando arquivos.

---

## Fluxo de Execução

1. **Carregamento de Configuração**: O script lê o arquivo `config.yaml` para obter parâmetros necessários.
2. **Inicialização do Logger**: Cria um logger para registrar eventos.
3. **Importação do Processador de Cabeçalho**: Carrega dinamicamente o módulo responsável por identificar ciclos nos dados.
4. **Execução das Threads**:
   - A thread `SerialReader` lê dados da serial e salva em arquivos diários.
   - A thread `FileProcessor` processa os arquivos de entrada, identifica ciclos e organiza os dados em arquivos separados.

---

## Observações Importantes

- **Thread-Safety**: O acesso ao arquivo de configuração é protegido por locks para evitar condições de corrida.
- **Modularidade**: O processamento do cabeçalho é feito por um módulo externo, permitindo fácil customização.
- **Logs**: Todos os eventos importantes e erros são registrados em arquivos de log definidos na configuração.
- **Ciclos**: Os dados são organizados em ciclos, que são identificados pelo processador de cabeçalho e salvos em arquivos próprios.

---

## Exemplo de Configuração (`config.yaml`)

```yaml
current_file_input: output_2024-06-22.txt
current_file_processor: output_2024-06-22.txt
header_processor: header_baumer_hivac2_v1
input_dir: input_dir
path_log: logs
pointer_file: 0
processed_dir: ciclos
serial_port: /dev/ttyS0
```

---

## Dependências

- `pyserial`
- `pyyaml`
- `threading`
- `datetime`
- `os`
- `importlib`
- Classe customizada `Logger` (em `lib/logger.py`)

---

## Comentários Finais

O script é robusto para aplicações industriais ou laboratoriais que necessitam de leitura e processamento contínuo de dados seriais, com organização eficiente dos dados em ciclos e logs detalhados para auditoria e troubleshooting.

Se precisar de exemplos de uso, instruções de execução ou mais detalhes sobre algum método, consulte o código-fonte ou entre em contato com o autor.