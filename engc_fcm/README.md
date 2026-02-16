# Engc FCM – Push Notifications (Firebase Cloud Messaging)

Módulo Odoo que implementa suporte a push notifications via Firebase Cloud Messaging (FCM) para integração com o app mobile Flutter.

## O que o módulo faz

1. **Registro do token FCM em `res.users`**
   - Campo `fcm_token` (Char, indexado) no modelo `res.users`.
   - Método `register_fcm_token(self, token)` para o app registrar o token após o login.
   - Chamada RPC: modelo `res.users`, método `register_fcm_token`, argumentos `args: [[user_id], token]`.

2. **Envio de push ao criar Solicitação de Serviço**
   - No modelo `engc.request.service` (Solicitação de Serviço), ao criar um novo registro, o módulo envia uma mensagem FCM para os usuários elegíveis.
   - **Usuários notificados:** usuários ativos que possuem `fcm_token` preenchido e que pertencem ao grupo **"Receber notificações push de Solicitação de Serviço"** (`engc_fcm.group_fcm_request_service_notify`).
   - Payload **data** da mensagem FCM (formato esperado pelo app Flutter):
     - `type`: `"new_request_service"`
     - `request_service_id`: ID do registro criado em string (ex.: `"123"`)
     - `title`: (opcional) ex.: "Nova Solicitação de Serviço"
     - `body`: (opcional) ex.: nome/código + "Programada: dd/mm/yyyy HH:MM" quando houver data programada
     - `schedule_date`: (opcional) data/hora programada formatada (dd/mm/yyyy HH:MM) quando preenchida

3. **Envio de push ao atualizar Solicitação de Serviço (técnico ou status)**
   - Ao alterar o **técnico** (`tecnicos`) ou o **status** (`state`) de uma Solicitação de Serviço, o módulo envia uma mensagem FCM para os mesmos usuários do grupo acima.
   - Payload **data** da mensagem de atualização:
     - `type`: `"request_service_updated"`
     - `request_service_id`: ID do registro em string
     - `title`: ex.: "Solicitação de Serviço: técnico alterado" ou "Solicitação de Serviço: status atualizado"
     - `body`: ex.: código + status; quando status = Concluído inclui "Data conclusão: dd/mm/yyyy HH:MM"
     - `event_type`: `"technician"` ou `"status"`
     - `state`: (apenas quando `event_type` = `"status"`) novo valor do status (ex.: `"in_progress"`, `"done"`, `"cancel"`)
     - `close_date`: (apenas quando status = `"done"`) data de conclusão formatada (dd/mm/yyyy HH:MM)

4. **Envio de push ao criar/atualizar Ordem de Serviço (engc.os)**
   - Ao **criar** uma OS: notificação para usuários do grupo **"Receber notificações push de Ordem de Serviço"** (`engc_fcm.group_fcm_os_notify`).
   - Ao **alterar o status** da OS: mesma audiência. Quando status = Concluída, o body inclui a data de conclusão (`date_finish`).
   - Payload **data**: `type`: `"new_os"` ou `"os_updated"`, `os_id`, `title`, `body`, `schedule_date` (data programada), e quando concluída `state`, `close_date`.

5. **Envio de push ao criar/atualizar Relatório de Atendimento (engc.os.relatorios)**
   - Ao **criar** um relatório: notificação para usuários do grupo **"Receber notificações push de Relatório de Atendimento"** (`engc_fcm.group_fcm_relatorio_atendimento_notify`).
   - Ao **alterar o status** (ex.: Concluído): mesma audiência. Quando status = Concluído, o body inclui a data de conclusão (`data_fim_atendimento`).
   - Payload **data**: `type`: `"new_relatorio_atendimento"` ou `"relatorio_atendimento_updated"`, `relatorio_id`, `os_id`, `title`, `body`, `data_atendimento`, `data_fim_atendimento`, e quando concluído `state`, `close_date`.

6. **API utilizada**
   - FCM HTTP v1: `POST https://fcm.googleapis.com/v1/projects/<project_id>/messages:send`
   - Autenticação: OAuth2 com Service Account do Firebase (Google Auth).

## Como obter as informações no Firebase (projeto novo)

Se você acabou de criar um projeto no Firebase (ex.: **engeapp-odoo**) e ainda não configurou nada, siga estes passos para preencher a tela de configuração FCM no Odoo.

### 1. Firebase Project ID

- Acesse [Firebase Console](https://console.firebase.google.com/) e selecione o projeto **engeapp-odoo**.
- Clique no ícone de **engrenagem** ao lado de "Visão geral do projeto" → **Configurações do projeto**.
- Na aba **Geral**, na seção "Seus apps", você verá **ID do projeto** (ex.: `engeapp-odoo` ou um valor como `engeapp-odoo-12345`).  
- Esse é o valor que vai no campo **"Firebase Project ID"** no Odoo. Se você preencher o JSON do Service Account (passo 2), o Project ID pode vir dentro do próprio JSON e o campo no Odoo fica opcional.

### 2. JSON do Service Account (obrigatório para enviar notificações)

O Service Account é uma “conta de serviço” que o Odoo usa para se autenticar na API do FCM. Você gera uma chave em formato JSON no Firebase.

1. No Firebase Console, no seu projeto **engeapp-odoo**, vá em **Configurações do projeto** (engrenagem) → aba **Contas de serviço**.
2. Role até a seção **"Firebase Admin SDK"**.
3. Clique em **"Gerar nova chave privada"** (ou "Generate new private key") e confirme. Será feito o download de um arquivo `.json` (ex.: `engeapp-odoo-firebase-adminsdk-xxxxx.json`).
4. **Opção A – Usar o conteúdo do JSON no Odoo:**  
   Abra esse arquivo com um editor de texto, copie **todo** o conteúdo (incluindo `{` e `}`) e cole no campo **"Conteúdo do JSON (Service Account)"** na tela de configuração FCM do Odoo.
5. **Opção B – Usar o caminho do arquivo no servidor:**  
   Coloque o arquivo JSON no servidor onde o Odoo roda (ex.: dentro do container ou em um volume montado), anote o caminho completo (ex.: `/opt/odoo/firebase-service-account.json`) e preencha o campo **"Caminho do arquivo JSON (Service Account)"** no Odoo.  
   Se o Odoo roda em Docker, o arquivo precisa estar em um volume acessível ao container (ex.: montar uma pasta do host onde você copiou o JSON).

**Importante:** Não compartilhe esse JSON nem o coloque em repositórios públicos; ele dá acesso ao projeto Firebase.

### 3. Resumo para preencher no Odoo

| Campo no Odoo | Onde obter |
|---------------|------------|
| **Firebase Project ID** | Configurações do projeto → Geral → "ID do projeto" (ou dentro do JSON, na chave `project_id`). |
| **Caminho do arquivo JSON** | Caminho no servidor onde você salvou o arquivo baixado (opcional se usar o campo abaixo). |
| **Conteúdo do JSON** | Conteúdo completo do arquivo `.json` baixado em "Contas de serviço" → "Gerar nova chave privada". |

Basta preencher **ou** o caminho do arquivo **ou** o conteúdo do JSON (e, se quiser, o Project ID). Depois clique em **Salvar** na tela de configurações do Odoo.

---

## Onde configurar o Service Account

- **Configurações no Odoo (recomendado):**  
  **Configurações** → **Geral** (ou a seção **Push (FCM)**) → preencher:
  - **Caminho do arquivo Service Account (JSON):** caminho no servidor do arquivo JSON do Service Account (ex.: `/opt/odoo/firebase-service-account.json`), **ou**
  - **Service Account JSON (conteúdo):** colar o conteúdo completo do JSON (alternativa ao caminho).
  - **Firebase Project ID:** opcional se o JSON já contiver `project_id`.

- **Variável de ambiente (alternativa):**  
  Defina `GOOGLE_APPLICATION_CREDENTIALS` com o caminho do arquivo JSON do Service Account no ambiente do Odoo (ex.: no `docker-compose` ou no script de inicialização do container).

- **Sobre prioridade dos parâmetros:**  
  Só precisa preencher **um** deles:
  - `engc_fcm.service_account_json` (conteúdo do JSON; **tem prioridade se preenchido**)
  - `engc_fcm.service_account_path` (caminho do arquivo JSON; só usado se o anterior estiver vazio)
  - `engc_fcm.project_id` (opcional, só necessário se não estiver dentro do JSON)

Se você já preencheu o `engc_fcm.service_account_json`, não precisa preencher os outros.  

Ordem de prioridade: `engc_fcm.service_account_json` → `engc_fcm.service_account_path` → `GOOGLE_APPLICATION_CREDENTIALS`.

## Onde o envio é disparado

- **Modelo:** `engc.request.service` (Solicitação de Serviço).  
- **Método:** sobrescrita de `create` no módulo `engc_fcm` (arquivo `models/engc_request_service.py`).  
- Após cada novo registro criado, é chamado `_send_fcm_new_request_service(record)`, que obtém os usuários elegíveis e envia a mensagem FCM para cada um via `fcm_client.send_fcm_data_message()` (arquivo `models/fcm_client.py`).  
- Falhas de envio (token inválido, rede, etc.) são apenas logadas; o `create` da solicitação não é interrompido.

## Dependência Python

Para o envio FCM funcionar, é necessário no ambiente onde o Odoo roda (ex.: no container Docker):

```bash
pip install google-auth requests
```

(`requests` costuma já estar instalado em instalações Odoo.)

## Notificação de teste não chega no dispositivo

1. **O que o wizard mostrou?**
   - **"Notificação de teste enviada com sucesso"** → Odoo conseguiu enviar para a API do FCM (status 200). Se o celular não exibiu:
     - **App em primeiro plano:** mensagens só com payload `data` (sem `notification`) **não** são mostradas automaticamente. O app Flutter precisa tratar `FirebaseMessaging.onMessage` e exibir uma notificação local (por exemplo com `flutter_local_notifications`).
     - **App em segundo plano ou fechado:** o sistema costuma exibir; confira se o app está nas permissões de notificação e se o canal FCM está configurado no Android.
   - **Mensagem de falha no wizard** → Verifique: (1) Configurações > Geral > Push (FCM) preenchidas (JSON ou caminho + Project ID); (2) logs do Odoo ao clicar em "Enviar notificação de teste" (procure por "FCM" ou "google-auth").

2. **Confirmar token no Odoo:** Usuários → edite o usuário (ex.: afonso@jgma.com.br) e confira se o campo "Token FCM" está preenchido após o login pelo app.

3. **Configurar o usuário para receber push (obrigatório):** Para receber cada tipo de notificação, o usuário precisa ter **Token FCM** preenchido e estar no grupo correspondente. Em **Configurações** → **Usuários e empresas** → **Usuários**, aba **Outros** (ou **Grupos**):
   - **Solicitação de Serviço:** marque **"Receber notificações push de Solicitação de Serviço"**.
   - **Ordem de Serviço:** marque **"Receber notificações push de Ordem de Serviço"**.
   - **Relatório de Atendimento:** marque **"Receber notificações push de Relatório de Atendimento"**.
   Salve. Sem o grupo, o usuário não recebe aquele tipo de push.

4. **Logs do servidor:** Ao enviar o teste, o módulo grava mensagens em log (sucesso ou falha). Execute o teste e consulte o log do container/servidor Odoo.

## Segurança

- Não commitar o arquivo JSON do Service Account no repositório.
- Em produção, prefira **caminho de arquivo** (com permissões restritas no servidor) ou **variável de ambiente** em vez de colar o JSON nas configurações.

## Resumo para o app Flutter

- **Registro do token:** RPC em `res.users` → `register_fcm_token` com `args: [[uid], token]`.
- **Notificações:** o app deve tratar:
  - `data.type == "new_request_service"`: nova solicitação criada; usar `data.request_service_id`, `data.title`, `data.body`, `data.schedule_date`.
  - `data.type == "request_service_updated"`: solicitação atualizada (técnico ou status); usar `data.event_type`, `data.request_service_id`, `data.title`, `data.body`, `data.state`, `data.close_date` (quando concluído).
  - `data.type == "new_os"`: nova ordem de serviço; usar `data.os_id`, `data.title`, `data.body`, `data.schedule_date`.
  - `data.type == "os_updated"`: OS atualizada (status); usar `data.os_id`, `data.title`, `data.body`, `data.state`, `data.close_date` (quando concluída).
  - `data.type == "new_relatorio_atendimento"`: novo relatório de atendimento; usar `data.relatorio_id`, `data.os_id`, `data.title`, `data.body`, `data.data_atendimento`, `data.data_fim_atendimento`.
  - `data.type == "relatorio_atendimento_updated"`: relatório atualizado (status); usar `data.relatorio_id`, `data.os_id`, `data.title`, `data.body`, `data.state`, `data.close_date` (quando concluído).

## Exemplos oficiais Firebase (referência)

- **Flutter (receber mensagens):** [firebase/quickstart-flutter – messaging](https://github.com/firebase/quickstart-flutter/tree/main/messaging)  
  - `FirebaseMessaging.onMessage` para mensagens em **primeiro plano** (no exemplo só faz `debugPrint`; para o usuário ver algo, é preciso exibir notificação local, ex.: `flutter_local_notifications`).  
  - `FirebaseMessaging.onBackgroundMessage` para mensagens em **segundo plano**.  
  - No sample, a observação: *"On Android, foreground notifications are not shown, only when the app is backgrounded"* — por isso, em primeiro plano o app precisa mostrar a notificação manualmente a partir do payload `data`.

- **Python (enviar mensagens):** [firebase/quickstart-python – messaging](https://github.com/firebase/quickstart-python/tree/master/messaging)  
  - Usa Service Account + OAuth2 + `POST` em `https://fcm.googleapis.com/v1/projects/<id>/messages:send` (mesmo padrão do módulo Odoo).  
  - O exemplo envia mensagens com `notification` (title/body) para **tópico**; o Odoo envia apenas **data** para **token**, para o app decidir como exibir.
