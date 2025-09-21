
# ADK WPP — MVP Hamburgueria (Hexagonal + LiteLLM)

Bot de pedidos com roteamento LLM, **coalescência real por janela de inatividade**, memória em Postgres,
e conector oficial WhatsApp Cloud API. Agentes interagem com **tools** tipadas (Pydantic), e o dispatcher
aplica **preflight** para cancelar respostas quando novas mensagens chegarem antes do envio.

## Coalescência (como funciona)
- Debounce por **HB_COALESCE_WINDOW_MS** (padrão 1200ms). Se novas mensagens surgem do mesmo `wa_id`,
  o relógio reinicia até atingir inatividade (máx = 3x a janela).
- Concurrency-safe: **Postgres advisory locks** (`pg_try_advisory_lock`) + lock local (sem Redis).
- O webhook agrega mensagens novas com `id > last_processed_inbox_id` (do snapshot) e gera um pacote lógico
  com `texto_unificado` e `max_inbox_id`.
- O **dispatcher** valida se chegaram mensagens após `max_inbox_id` (preflight). Se sim, **cancela** o envio.
- Após envio bem-sucedido, o snapshot avança `last_processed_inbox_id`.

## Agentes & Tools
- **saudacao**: boas-vindas.
- **cardapio**: lista opções (serviço `menu_service`).
- **carrinho**: utiliza tools tipadas (`cart_tools`) para adicionar/remover e calcular subtotal.


## Modo LLM-first (agentes orientados a prompt)
- Agentes `saudacao`, `cardapio`, `carrinho` agora usam **prompts** e **tool-calling**.
- O Python não formata mais a resposta final; o LLM retorna `{ "texto": "..." }` (validado por Pydantic).
- O orquestrador é 100% LLM (sem regex) e retorna o agente em JSON.


## Prompts PT-BR, orientados a objetivo (LLM-first)
- `core/prompting.py` centraliza prompts com **Jinja2** e variáveis (persona, políticas, janelas, contexto).
- Agentes não têm resposta hardcoded; o LLM escreve o texto final com base nos **objetivos** e nos **tools**.

- O roteador (`adk/orchestrator.py`) usa prompt em PT-BR e aceita **JSON ou texto** (tolerante, sem travar UX).



### PromptBuilder avançado
- Router conhece **agentes e tools** e enxerga as **últimas mensagens** do cliente.
- Agentes recebem **objetivo**, **políticas**, **ferramentas** e **exemplos few-shot** para guiar o LLM.
- Totalmente escalável: adicione agentes/tools e o Router os descobre via DI automaticamente.


## Cenário do cliente (microempreendedor) e transbordo humano
- Objetivo: automatizar pedidos que chegam pelo WhatsApp, reduzindo atraso e desorganização. O empreendedor só revisa/manda depois — e pode **intervir** quando quiser.

- **Transbordo (handoff)**: pause a LLM por contato e atenda manualmente.

  - `POST /handoff/pause` { "wa_id": "559999..." }

  - `POST /handoff/resume` { "wa_id": "559999..." }

  - Quando pausado, o webhook/simulação **não** processa LLM, apenas registra evento.



## Sem WhatsApp Business (teste rápido)

- Use `POST /simulate` para testar a conversa sem Meta:

  ```json

  { "wa_id": "5599999999999", "text": "quero 2 BX2" }

  ```

  Retorna:

  ```json

  { "preview": { "wa_id":"...", "texto":"..." }, "agent": "cardapio", "window_msgs": 1 }

  ```



## Logs e auditoria

- Logs JSON com `trace_id` e eventos em `conversation_events` registram: inbox_saved, coalesce_done, router_choice, agent_output, outbox_enqueued, dispatch_*.



---

# Guia para Desenvolvedores (Júnior → Pleno)

Este repositório é um **MVP orientado a LLM** para automatizar vendas de uma hamburgueria via WhatsApp:
- **Coalescência** real (janela de inatividade + advisory locks)
- **Roteamento por LLM** (PromptBuilder em PT-BR, com personas, políticas e exemplos)
- **Agentes por domínio** (saudação, cardápio, carrinho, **endereço**, **pagamento/PIX**)
- **Ferramentas (tools)** tipadas (Pydantic) executadas no servidor
- **Transbordo humano (handoff)** por contato
- **Logs JSON** + **eventos de auditoria** no banco
- **/simulate** para testar sem WhatsApp Business

## Arquitetura (visão rápida)
- `core/` — configuração, DI (kink), logging, PromptBuilder (Jinja2), LLMClient (LiteLLM + tool loop), coalescência.
- `adk/` — orquestrador + agentes (LLM-first) + toolkit de tools.
- `domain/services/` — serviços puros (menu, carrinho).
- `repo/` — modelos e repositório: inbox/outbox, estado, eventos.
- `api/` — Flask: webhook Meta, **/simulate**, **/handoff**.
- `tasks/` — dispatcher do outbox.

## Fluxo (resumo)
1. **Entrada** (webhook ou `/simulate`) → salva Inbox → checa `handoff` → **coalescência** → contexto.
2. **Orquestrador LLM** decide o agente ideal (prompt PT-BR com contexto + ferramentas disponíveis).
3. **Agente LLM** conversa, decide se chama **tools** (get_menu, add_to_cart, upsert_address, create_pix_charge, ...).
4. Gera **texto final** → **Outbox** (no webhook) ou **preview** (no `/simulate`).
5. **Dispatcher** envia (com preflight). Em sucesso, avança `last_processed_inbox_id`.

## Transbordo (Handoff)
- Pausar LLM por contato (atendimento humano manual no WhatsApp):
  ```bash
  curl -X POST /handoff/pause  -H "Content-Type: application/json" -d '{"wa_id":"5591999999999","reason":"manual"}'
  curl -X POST /handoff/resume -H "Content-Type: application/json" -d '{"wa_id":"5591999999999"}'
  ```
- Quando pausado, o pipeline registra evento e **não processa**.

## Teste sem Meta: `/simulate`
```bash
curl -X POST http://localhost:8000/simulate -H "Content-Type: application/json"       -d '{"wa_id":"5591999999999","text":"quero pagar"}'
```
Resposta:
```json
{ "preview": { "wa_id": "...", "texto": "..." }, "agent": "pagamento", "window_msgs": 1 }
```

## PromptBuilder (PT-BR)
- Local: `core/prompting.py`
- O **Router** conhece agentes e tools; recebe últimas mensagens e contexto (snapshot/memory).
- **Agentes** recebem: objetivo, políticas, ferramentas e **exemplos few-shot**.
- **Dica**: Ajuste `persona_chave` e `estilo_chave` para calibrar o tom.

## Como criar um novo agente
1. Crie um arquivo em `adk/agents/novo.py` com:
   ```python
   from .llm_agent import AgenteLLM
   from ..runtime.toolkit import ToolSpec
   from pydantic import BaseModel
   from ...repo import repo  # ou services

   class MinhaToolArgs(BaseModel):
       conversation_id: str

   def tool_minha(args: MinhaToolArgs):
       return {"ok": True, "data": 123}

   AgenteNovo = AgenteLLM(
       nome="novo",
       objetivo="Explique aqui a missão do agente",
       exemplos=[{"user":"exemplo", "plano":"como agir", "resposta":"o que seria ideal"}],
       tool_policy="Quando usar ferramenta, confirme antes...",
   )
   AgenteNovo.register_tool(ToolSpec(name="minha_tool", description="faz tal coisa", args_schema=MinhaToolArgs, func=tool_minha))
   ```
2. Registre no DI (`core/di.py`):
   ```python
   from ..adk.agents.novo import AgenteNovo
   di["agents"]["novo"] = AgenteNovo
   ```
3. Pronto: o **Router** passa a “enxergar” esse agente e suas tools no prompt automaticamente.

## Convenções de código
- **Pydantic v2** para args/retornos de tools.
- **Docstrings PT-BR** explicando propósito e invariantes.
- **Sem hardcode** de texto de resposta: o LLM escreve, seguindo objetivos/políticas do PromptBuilder.
- **Tools idempotentes**: podem ser chamadas mais de uma vez sem efeitos colaterais inesperados.
- **Logs JSON** com `trace_id` (veja `core/logging.py`).

## Agentes incluídos
- `saudacao`: acolhe e direciona.
- `cardapio`: consulta menu, adiciona itens via SKU.
- `carrinho`: listar/adicionar/remover itens; calcula subtotal.
- `endereco`: captura, normaliza e salva endereço.
- `pagamento`: cria cobrança PIX (mock) e consulta status.

## Pagamento (PIX mock)
- Tools: `get_cart_state` → `create_pix_charge` → `check_pix_status`.
- Dados guardados em `snapshot.payments` com `status` (`pending|approved|expired|cancelled`).
- **Operador** pode atualizar status (ex.: via SQL ou endpoint futuro).

## Próximos passos sugeridos
- Migrations Alembic para event store e tabelas extra (se necessário).
- Tool de “custom item” e observações de cozinha.
- Validação de endereço com serviço externo.
- Endpoint administrativo para marcar `approved` em pagamentos (mock).

---


## Catálogo LLM-first (no prompt)
- Arquivo: `config/catalog.json` (edite livremente — categorias, itens, regras, prazos, etc.).
- O **PromptBuilder** injeta um **resumo** do catálogo em todos os prompts (router e agentes).
- Itens fora do catálogo são aceitos via `add_custom_item` (LLM decide quando usar).
- Atualize em runtime:
  ```bash
  curl -X POST http://localhost:8000/admin/reload-config
  ```

### Exemplo mínimo de `catalog.json`
Veja `config/catalog.json` incluído no repo (exemplo pronto).

## Few-shots reais do cliente
- Adicione conversas reais em `config/few_shots/*.md` e use-as para refinar exemplos nos agentes.
- Sugestão: separe por tema (`pagamento.md`, `endereco.md`, `customizacoes.md`).

## Publicar no Git (passo-a-passo)
**Sugestão de nome do repositório:** `adk-burger-whatsapp-llm`

**Descrição (≤350 chars):** MVP LLM-first para automação de pedidos por WhatsApp. Coalescência, roteador LLM, agentes (cardápio, carrinho, endereço, pagamento PIX mock), tools Pydantic, transbordo humano, /simulate sem Meta, logs JSON, PromptBuilder PT-BR com catálogo no prompt.



Passos:

```bash
cd <pasta do projeto>

git init

git checkout -b main

echo -e ".venv/\n__pycache__/\n*.pyc\n.env\n.DS_Store" > .gitignore

git add .

git commit -m "MVP: LLM-first WhatsApp bot (coalescência + PromptBuilder + agents + tools + handoff + simulate)"

# Crie o repo no GitHub (nome: adk-burger-whatsapp-llm) e conecte:

git remote add origin git@github.com:SEUUSER/adk-burger-whatsapp-llm.git

git push -u origin main

```


## Dicas de evolução

- Persistir catálogo em DB e versionar mudanças.

- Ingerir few-shots automaticamente nos prompts conforme tema.

- Métricas de tokens e taxa de tool-calls por agente.

- Endpoint admin para aprovar PIX (mock) e imprimir pedidos.

- Conteúdo do catálogo pode ser chunkado quando crescer muito (RAG futuro).

