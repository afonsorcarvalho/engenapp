FROM odoo:16.0
USER root
LABEL maintainer="AFR Soluções Inteligentes"

# python3-venv necessário para criar o venv (ensurepip)
# OCR (afr_ecm F3.1): tesseract-ocr + langs por/eng + poppler-utils (pdftotext, pdftoppm)
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-venv \
        tesseract-ocr tesseract-ocr-por tesseract-ocr-eng \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copia o requirements.txt do projeto (google-auth, cryptography 43, signxml 4, erpbrasil, etc.)
COPY requirements.txt /opt/odoo/requirements_project.txt

# Venv com dependências do projeto; cryptography 43 compatível com signxml 4 e pyOpenSSL 24.
ARG VENV_PATH=/opt/odoo/venv
ARG PIP_VERBOSE=0
RUN python3 -m venv "$VENV_PATH" && \
    . "${VENV_PATH}/bin/activate" && \
    pip install --upgrade pip && \
    pip install --no-cache-dir $( [ "$PIP_VERBOSE" = "1" ] && echo "-v" ) -r /opt/odoo/requirements_project.txt && \
    python -m spacy download pt_core_news_sm && \
    echo "--- Verificação ---" && python -c "import cryptography; print('cryptography', cryptography.__version__)" && python -c "import google.auth; print('google-auth OK')" && python -c "import erpbrasil.assinatura; print('erpbrasil.assinatura OK')" && python -c "import yake, spacy; spacy.load('pt_core_news_sm'); print('yake + spacy pt_core_news_sm OK')"

# Wrapper: usa Python do sistema (tem o módulo odoo) e PYTHONPATH do venv (tem google-auth, cryptography).
# Script em arquivo para evitar escape de aspas no Dockerfile.
COPY scripts/odoo_venv_wrapper.sh /opt/odoo/venv/bin/odoo
RUN chmod +x /opt/odoo/venv/bin/odoo

# Runtime: Odoo e scripts usam o venv (PATH com venv primeiro)
ENV PATH="${VENV_PATH}/bin:${PATH}"

# Patch Odoo 16 website: evita AttributeError 'NoneType' has no attribute 'context' ao carregar registry sem request HTTP
COPY scripts/patch_website_request.py /tmp/patch_website_request.py
RUN python3 /tmp/patch_website_request.py

# Patch Odoo tools/mail.py: lxml 5 + lxml_html_clean não expõem clean.defs; usar defs de lxml.html
RUN ODOO_MAIL="$(find /usr/lib -path '*/odoo/tools/mail.py' 2>/dev/null | head -1)" && \
    test -n "$ODOO_MAIL" && test -f "$ODOO_MAIL" && \
    sed -i 's/from lxml\.html import clean$/from lxml.html import clean, defs/' "$ODOO_MAIL" && \
    sed -i 's/clean\.defs/defs/g' "$ODOO_MAIL"

USER odoo