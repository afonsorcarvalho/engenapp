# FITADIGITAL
Sistema de monitoramento e processamento de dados para equipamentos médicos.

## Configuração do Serviço no Raspberry Pi

### 1. Pré-requisitos
```bash
# Atualizar o sistema
sudo apt-get update
sudo apt-get upgrade

# Instalar dependências do sistema
sudo apt-get install -y \
    openssl \
    libssl-dev \
    python3-dev \
    python3-pip \
    python3-venv \
    python3-full \
    build-essential \
    vim-common \
    xxd \
    git

# Verificar versão do OpenSSL
openssl version
# Deve ser OpenSSL 1.1.1 ou superior
```

### 2. Configuração do Ambiente Python
```bash
# Criar diretório para o projeto (se ainda não existir)
mkdir -p /home/pi/fitadigital_raspberry
cd /home/pi/fitadigital_raspberry

# Criar ambiente virtual
python3 -m venv venv

# Ativar o ambiente virtual
source venv/bin/activate

# Atualizar pip
pip install --upgrade pip

# Instalar todas as dependências Python
pip install -r requirements.txt

# Desativar o ambiente virtual (quando terminar)
deactivate
```

### 3. Configuração do Serviço
```bash
# Copiar o arquivo de serviço
sudo cp fitadigital.service /etc/systemd/system/

# Editar o arquivo de serviço para usar o Python do ambiente virtual
sudo nano /etc/systemd/system/fitadigital.service
```

Conteúdo do arquivo `fitadigital.service`:
```ini
[Unit]
Description=Serviço Fitadigital para Raspberry Pi
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/fitadigital_raspberry
ExecStart=/home/pi/fitadigital_raspberry/venv/bin/python /home/pi/fitadigital_raspberry/start_fitadigital.py
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=fitadigital

[Install]
WantedBy=multi-user.target
```

```bash
# Recarregar o systemd
sudo systemctl daemon-reload

# Habilitar o serviço para iniciar com o sistema
sudo systemctl enable fitadigital.service

# Iniciar o serviço
sudo systemctl start fitadigital.service

# Verificar status do serviço
sudo systemctl status fitadigital.service
```

## Dependências

### Python
Todas as dependências Python estão listadas no arquivo `requirements.txt`:
- `pyserial` (>=3.5) - Para comunicação serial
- `pyyaml` (>=6.0.1) - Para manipulação do arquivo config.yaml
- `cryptography` (>=41.0.0) - Para operações criptográficas
- `PyPDF2` (>=3.0.0) - Para manipulação de PDFs
- `reportlab` (>=4.0.0) - Para geração de PDFs

Dependências de desenvolvimento (opcional):
- `pytest` (>=7.4.0) - Para testes unitários
- `black` (>=23.7.0) - Para formatação de código
- `flake8` (>=6.1.0) - Para verificação de estilo de código

### Sistema
- OpenSSL 1.1.1 ou superior
- Python 3.8 ou superior
- Git 2.25.0 ou superior
- GCC/G++ 9.0 ou superior (para compilação de extensões Python)
