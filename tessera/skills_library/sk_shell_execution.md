---
id: sk_shell_execution
node_type: procedural_anchor
domain: system_operation
target_tools:
  - bash
  - sh
created_at: '2026-08-25T08:12:00-07:00'
provenance_episodes:
  - ep_shell_05
success_correlation_rate: 0.99
active_connections: []
security:
  gating_status: passed
  toxicity_score: 0.01
  sanitized: true
---

# sk_shell_execution: Execução Segura de Comandos Shell

Regras de engenharia para interações seguras e resilientes com o interpretador de comandos bash, evitando loops órfãos, caminhos ambíguos ou falhas de encadeamento.

## Processo Repetível (Repeatable Process)
1. **Modo Defensivo (Set-Options):** Sempre que for gerar scripts executáveis de terminal de múltiplas linhas, adicione as diretivas de segurança `set -e` (para o script parar imediatamente diante de qualquer comando que falhe) e `set -o pipefail` (para capturar falhas no meio de pipelines).
2. **Uso de Caminhos Absolutos:** Evite caminhos relativos em comandos críticos como `rm`, `mv` ou `cd`. Utilize caminhos absolutos baseados no diretório do workspace (`/workspace/`) ou resolva o diretório do script dinamicamente (`$(dirname "$0")`).
3. **Encapsulamento de Parâmetros:** Sempre encapsule referências de caminhos e parâmetros em aspas duplas para evitar que nomes de arquivos com espaços em branco causem fragmentação de argumentos no shell.
4. **Proteção Contra Loops Infinitos:** Adicione um timeout explícito para comandos interativos ou de rede (usando a ferramenta `timeout` do Linux, ex: `timeout 10s curl ...`).

## Plano de Verificação (Verification Plan)
* Executar comandos de validação seca (`bash -n <script.sh>`) para testar a integridade estrutural das condições de controle antes da execução real.
* Monitorar o código de retorno de erro (`$?`) imediatamente após a execução do comando considerado crítico para determinar o fluxo de correção lógica.

## Armadilhas Conhecidas (Known Pitfalls)
* **Silent Pipe Failure:** Encadear múltiplos comandos usando pipe (`|`) sem ativar `pipefail`. Isso faz com que se o primeiro comando falhar de forma catastrófica, o shell ignore o erro e assuma o código de saída de sucesso do último comando do encadeamento.
* **Interactive Blockage:** Disparar comandos que exigem confirmação interativa do usuário via stdin (como confirmações do apt-get ou atualizações de banco) sem passar flags de automação (ex: `-y` ou `--non-interactive`), fazendo com que o agente trave em timeout eterno esperando resposta.
