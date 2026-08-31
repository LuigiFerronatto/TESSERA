---
id: sk_service_lifecycle
node_type: procedural_anchor
domain: devops_operations
target_tools:
  - systemctl
  - lsof
  - netstat
created_at: '2026-08-25T08:12:00-07:00'
provenance_episodes:
  - ep_lifecycle_01
success_correlation_rate: 0.96
active_connections: []
security:
  gating_status: passed
  toxicity_score: 0.01
  sanitized: false
  threat_detected: false
  content_changed: false
  admission: accept
---

# sk_service_lifecycle: Gestão do Ciclo de Vida de Serviços em Segundo Plano

Procedimento estabilizador para inicialização, monitoramento e encerramento seguro de daemons e serviços de infraestrutura local em segundo plano.

## Processo Repetível (Repeatable Process)
1. **Varredura de Concorrência:** Antes de tentar inicializar qualquer serviço, verifique se a porta lógica pretendida está ocupada executando `lsof -i :<PORT>` ou `netstat -tuln | grep <PORT>`.
2. **Identificação e Resolução:** Se a porta estiver ocupada, identifique o PID do processo concorrente e decida se deve encerrá-lo (`kill -15 <PID>` para encerramento gracioso, ou `kill -9 <PID>` se persistir) ou remapear a porta do novo serviço.
3. **Inicialização Isolada:** Dispare a inicialização em segundo plano direcionando a saída padrão (stdout) e a saída de erro (stderr) para arquivos de log dedicados (ex: `nohup command > service.log 2>&1 &`).
4. **Captura do PID:** Capture imediatamente o PID do processo iniciado usando `echo $!` e salve em um arquivo de rastreamento local (ex: `/tmp/service.pid`).

## Plano de Verificação (Verification Plan)
* Executar chamadas de saúde do serviço (`curl -s -o /dev/null -w "%{http_code}" localhost:<PORT>/health`) em um loop de timeout de até 15 segundos para confirmar a prontidão operacional do serviço.
* Inspecionar as últimas 50 linhas do arquivo de log (`tail -n 50 service.log`) em busca de exceções de inicialização ou falhas de carregamento de dependências.

## Armadilhas Conhecidas (Known Pitfalls)
* **Handshake Blindness:** Tentar realizar chamadas de API ou conexões de banco de dados imediatamente após disparar o comando de inicialização, antes que o serviço tenha finalizado sua rotina interna de setup e esteja de fato pronto para receber conexões.
* **Orphan Processes:** Deixar de salvar ou monitorar o PID do processo iniciado, impedindo o encerramento seguro do serviço no final do ciclo da tarefa e gerando processos zumbis que travam as portas do sistema em execuções subsequentes.
