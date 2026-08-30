# Apresentação: Tessera — a memória do LAO

`tessera-apresentacao.html` é um deck de 22 slides em HTML puro (sem build
step), seguindo o manual de marca Blip (`.agents/skills/blip-brand-presentations/`):
logo, paleta 50/35/15, tipografia Carbona, chat-bubble motif, mascotes LAO-3D
e footer de classificação.

## Como visualizar

Abra direto no navegador — não precisa de servidor:

```bash
xdg-open Tessera/docs/slides/tessera-apresentacao.html
# ou
google-chrome Tessera/docs/slides/tessera-apresentacao.html
```

**Navegação**: scroll normal, ou setas `↑`/`↓`/`PageUp`/`PageDown`/`espaço`
(scroll-snap, um slide por vez).

## Estrutura do deck

| # | Slide | Conteúdo |
|---|---|---|
| 1 | Capa | Título + mascote pensando |
| 2 | Decodificando o Nome | O que é memória Atômica, Adaptativa e Topológica |
| 3 | Fundamentação científica | QUMem, LiveMem, Range Retrieval |
| 4 | O LAO | O contexto do Lab e o preço da amnésia |
| 5 | O Paradoxo da Caixa de Sapato | A ilusão do texto: o labirinto do grep e o state contamination do RAG |
| 6 | A Solução | Divisor introduzindo o Tessera |
| 7 | As Gavetas | Factual, Preference, Procedural (Particionamento) |
| 8 | O Bolo de Cenoura (Interação) | Slide interativo de abertura com mascote e balões de fala |
| 9 | A Análise | Em qual gaveta entra? Pode ser atualizada? |
| 10 | A Mudança | O fator temporal: Meses depois as preferências mudam |
| 11 | O Colapso | Por que Grep, Glob e RAG Clássico criam Frankesteins |
| 12 | A Evolução | Ciclo evolutivo: brute-force → especialista → memory-graph → Tessera |
| 13 | Episódios | Fronteiras dinâmicas de episódio (Timeout e TF-IDF) |
| 14 | Pipeline 3-Agentes | Need → Planner → Inference (Estimação de Estado) |
| 15 | Resolução de Conflitos | Lógica algorítmica para evitar contaminação temporal |
| 16 | Indexação por grafo | O "Quadro de Cortiça" e o poder do DW-PR |
| 17 | Decomposição | Extração g_φ atômica de episódios |
| 18 | Servidor MCP | Agnosticismo e protocolo unificado |
| 19 | Hora da Demo | Comparação prática no terminal (Tessera vs. Grep) |
| 20 | Onboarding e Setup | tessera doctor e tessera quickstart (Plug & Play) |
| 21 | Auto-melhoria | Citação sobre gaps de processo + mascote pesquisando |
| 22 | Fechamento | Obrigado + mascote celebrando |

## Assets embutidos (`assets/`)

- **Logos**: `LOGO_PRIMARIA_fundo_claro.svg` (fundo claro), `LOGO_SECUNDARIA_fundo_escuro.svg` (fundo escuro) — copiados de `.agents/skills/blip-brand-presentations/assets/logos/`.
- **Fontes**: 5 pesos da Carbona (`Regular`/`Medium`/`Bold`/`ExtraBold`/`Black`) via `@font-face`.
- **Mascotes**: 7 variantes do LAO-3D (`assets/lao-3d/` no repo raiz), escolhidas por contexto conforme `.agents/skills/lao-newsletter/LAO_MASCOTS_GUIDE.md` (thinking → problema/pesquisa; research-book → fundamentação científica; happy-birthday → fechamento).

## Editar/estender

O arquivo é auto-contido (CSS embutido no `<head>`, sem dependências
externas de CDN). Para adicionar um slide, copie um bloco `<section
class="slide ...">...</section>` existente e ajuste — a numeração
`NN / 15` é injetada automaticamente via JS na carga da página? **Não** —
está hardcoded em cada slide (`<div class="slide-index">`); se adicionar
slides, atualize manualmente os números e o total no `.navhint`.
