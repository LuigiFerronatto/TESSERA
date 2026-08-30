---
id: sk_schema_compliance
node_type: procedural_anchor
domain: structured_outputs
target_tools:
  - python
  - jsonschema
  - pyyaml
created_at: '2026-08-25T08:12:00-07:00'
provenance_episodes:
  - ep_schema_04
success_correlation_rate: 0.97
active_connections: []
security:
  gating_status: passed
  toxicity_score: 0.01
  sanitized: true
---

# sk_schema_compliance: Conformidade de Esquemas e Formatos de Saída

Instruções para evitar a quebra de serialização ou corrupção de metadados ao interagir com payloads JSON, YAML ou Frontmatters estructurados de memória.

## Processo Repetível (Repeatable Process)
1. **Sanitização de Caracteres Especiais:** Antes de serializar dados de texto, filtre quebras de linha não escapadas (`
` vs `
`) e caracteres de controle invisíveis que corrompem o parsing.
2. **Escapamento Adequado:** Sempre encapsule strings de texto livre em aspas duplas no JSON ou utilize o operador de bloco literal (`|`) no YAML para garantir que caracteres como dois-pontos seguidos de espaço (`: `) não sejam interpretados erroneamente como chaves de dicionário.
3. **Validação Estrutural Prévia:** Passar qualquer string gerada por um interpretador sintático local e isolado (ex: `python3 -c "import json, sys; json.loads(sys.stdin.read())"` ou `import yaml`) antes de salvar o arquivo no disco ou disparar o payload na API.

## Plano de Verificação (Verification Plan)
* Executar validação de esquema estrita utilizando esquemas JSONSchema ou validadores estruturais locais.
* Tratar e capturar preventivamente erros de parsing (como `json.JSONDecodeError` ou `yaml.YAMLError`), imprimindo logs explícitos da linha e caractere exatos que causaram a falha para correção incremental rápida.

## Armadilhas Conhecidas (Known Pitfalls)
* **Unescaped Quotes:** Deixar de escapar aspas duplas dentro de strings geradas dinamicamente, o que quebra imediatamente a estrutura delimitadora do JSON, gerando exceções de syntax error.
* **YAML Indentation Mismatch:** Gerar endentação flutuante ou misturar tabulações com espaços no YAML Frontmatter das memórias físicas, corrompendo o parsing do indexador Tessera.
