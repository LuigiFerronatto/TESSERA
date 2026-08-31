---
id: sk_runtime_verification
node_type: procedural_anchor
domain: task_validation
target_tools:
  - pytest
  - flake8
  - black
created_at: '2026-08-25T08:12:00-07:00'
provenance_episodes:
  - ep_verification_03
success_correlation_rate: 0.95
active_connections: []
security:
  gating_status: passed
  toxicity_score: 0.01
  sanitized: false
  threat_detected: false
  content_changed: false
  admission: accept
---

# sk_runtime_verification: Verificação Ativa em Tempo de Execução

Diretriz metodológica para impedir a validação estática cega. Obriga o agente a provar a corretude do código e das configurações executando-os ativamente.

## Processo Repetível (Repeatable Process)
1. **Análise de Sintaxe (Linter):** Rodar analisadores estáticos locais no arquivo de código modificado (ex: `flake8 <file.py>` ou `black --check <file.py>`) para capturar erros de sintaxe elementares antes da execução.
2. **Restaurar Contexto Secundário:** Isolar o ambiente de teste sempre que possível, gravando inputs de teste controlados (mocks) em diretórios temporários (`/tmp/`).
3. **Execução Física Ativa:** Executar fisicamente o script modificado ou a suíte de testes correspondente (ex: `python3 <file.py>` ou `pytest <test_file.py>`) capturando o código de saída do terminal (`$?`).
4. **Inspeção de Saída Dinâmica:** Avaliar o conteúdo impresso em stdout/stderr para garantir que nenhuma exceção mascarada por blocos `try-except` genéricos tenha ocorrido silenciosamente.

## Plano de Verificação (Verification Plan)
* Garantir que a execução retorne estritamente o código de saída zero (`0`).
* Escrever e rodar um script de validação secundário e independente para ler e validar se as saídas produzidas (arquivos gerados, modificações no banco) batem com o esquema esperado pela tarefa.

## Armadilhas Conhecidas (Known Pitfalls)
* **Static Verification Blindness:** Declarar uma tarefa como concluída baseando-se apenas na leitura estática do código ("parece correto"). Inúmeros bugs de importação ausente, incompatibilidade de tipo ou lógica interna só se manifestam quando o código é de fato executado pelo interpretador em tempo de execução.
* **Database Overwrite:** Executar rotinas de teste diretamente sobre o banco de dados principal de produção sem criar instâncias ou transações de rollback temporárias, gerando poluição ou perda acidental de dados reais.
