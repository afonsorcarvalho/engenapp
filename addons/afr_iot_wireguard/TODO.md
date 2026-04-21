# TODO — afr_iot_wireguard

## Em curso

## Pendente
- Adicionar logging de eventos críticos (activation, revoke, enrollment creation)
- Implementar endpoint REST para revogação de dispositivos (device revoke API)
- Reforçar validações de entrada e tratamento de erros edge cases
- Verificar implementação completa do controller activate.py

## Feito
- 2026-04-21 — Expandir testes: validação pubkey/device_id, rate limit behavior, edge cases
- 2026-04-21 — Implementar rate limiting em POST /api/enroll (table-based, cron sweep)
- 2026-04-21 — Criar README.md com instruções de instalação e setup do daemon
