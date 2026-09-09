# 🎩 Goodfella CLI — Plano de Testes Práticos e Guia de Validação End-to-End

Este documento descreve detalhadamente todos os testes práticos, cenários de validação, procedimentos passo a passo, comandos e comportamentos esperados para homologar todas as funcionalidades do **Goodfella**.

---

## 📋 Sumário das Baterias de Teste

| Bateria | Foco da Validação | Comandos / Módulos Cobertos |
| :--- | :--- | :--- |
| **Bateria 1** | Ambiente, Instalação e Inicialização | [app.py](file:///home/bruno/Desktop/goodfella/src/goodfella/cli/app.py), [env.py](file:///home/bruno/Desktop/goodfella/src/goodfella/core/env.py), `.gitignore`, `.goodfella/` |
| **Bateria 2** | Provedores LLM (Local e Cloud) | [factory.py](file:///home/bruno/Desktop/goodfella/src/goodfella/llm/factory.py), `/setup`, `/status`, Ollama, OpenAI, Gemini, Anthropic, DeepSeek |
| **Bateria 3** | Motor RAG, Scanner e Sincronização | [scanner.py](file:///home/bruno/Desktop/goodfella/src/goodfella/rag/scanner.py), [chunker.py](file:///home/bruno/Desktop/goodfella/src/goodfella/rag/chunker.py), [sync.py](file:///home/bruno/Desktop/goodfella/src/goodfella/rag/sync.py), `/refresh`, `/rebuild` |
| **Bateria 4** | Regras de Arquitetura e Anti-Patterns | [rules.py](file:///home/bruno/Desktop/goodfella/src/goodfella/knowledge/rules.py), `/rule add`, regras locais e globais |
| **Bateria 5** | Revisão de Código e Arquitetura | [commands.py](file:///home/bruno/Desktop/goodfella/src/goodfella/cli/commands.py), `/review`, `/deep-review`, extração de sinais, zero hallucination |
| **Bateria 6** | REPL, UX e Isolamento de Memória | [memory.py](file:///home/bruno/Desktop/goodfella/src/goodfella/llm/memory.py), [ui.py](file:///home/bruno/Desktop/goodfella/src/goodfella/cli/ui.py), `/clear`, `/reset`, `/help`, streaming, TTFT |
| **Bateria 7** | Suíte Automatizada e CI/CD | [tests/test_config.py](file:///home/bruno/Desktop/goodfella/tests/test_config.py), `.github/workflows/ci.yml` |
| **Bateria 8** | Roteiro Rápido Hands-On (15 min) | Projeto Sandbox de demonstração passo a passo |

---

## 🛠️ Pré-Requisitos para Execução dos Testes

1. **Python:** `>= 3.11` com `uv` ou `pipx` instalado.
2. **Ollama:** Instalado e executando localmente (`ollama serve`).
   - Modelo para testes locais: `ollama pull qwen2.5-coder:1.5b` (ou `qwen2.5-coder:7b`).
3. **Chaves de API (Opcional para Nuvem):**
   - OpenAI (`OPENAI_API_KEY`)
   - Google Gemini (`GEMINI_API_KEY`)
   - Anthropic (`ANTHROPIC_API_KEY`)
   - DeepSeek (`DEEPSEEK_API_KEY`)
4. **Editor de Terminal:** `nano` ou `vim` configurado no PATH ou `$EDITOR`.

---

## 🧪 BATERIA 1: Instalação, Inicialização e Isolamento do Ambiente

### Teste 1.1 — Instalação e Ponto de Entrada da CLI
* **Objetivo:** Garantir que o comando `goodfella` esteja acessível globalmente ou no virtualenv.
* **Passos Práticos:**
  ```bash
  # Opção A: No ambiente de desenvolvimento (uv)
  uv sync --dev
  uv run goodfella --help # Ou testar entry point

  # Opção B: Instalação editável via pip
  pip install -e .
  goodfella
  ```
* **Critério de Sucesso:** A aplicação inicia, exibe a logo `🎩 Goodfella AI Pair Programmer` e entra no prompt `❯ `.

---

### Teste 1.2 — Auto-criação da pasta `.goodfella/` e injeção no `.gitignore`
* **Objetivo:** Validar se [init_environment()](file:///home/bruno/Desktop/goodfella/src/goodfella/core/env.py#L9-L34) cria o diretório isolado e protege o repositório contra commits acidentais do banco.
* **Passos Práticos:**
  1. Crie uma pasta temporária de teste:
     ```bash
     mkdir -p /tmp/teste-goodfella && cd /tmp/teste-goodfella
     git init
     ```
  2. Inicie o Goodfella e saia com `/exit`:
     ```bash
     goodfella
     ❯ /exit
     ```
  3. Verifique a existência dos arquivos criados:
     ```bash
     ls -la
     ls -la .goodfella/
     cat .gitignore
     ```
* **Critério de Sucesso:**
  - A pasta `.goodfella/` e a subpasta `.goodfella/chroma_db/` foram criadas.
  - O arquivo `.gitignore` contém a linha `.goodfella/`.

---

### Teste 1.3 — Idempotência do `.gitignore`
* **Objetivo:** Garantir que abrir a CLI repetidas vezes não duplica linhas no `.gitignore`.
* **Passos Práticos:**
  1. Execute `goodfella` e saia com `/exit` 3 vezes seguidas.
  2. Conte as ocorrências no `.gitignore`:
     ```bash
     grep -c "\.goodfella/" .gitignore
     ```
* **Critério de Sucesso:** O número de ocorrências é exatamente `1`.

---

### Teste 1.4 — Isolamento Multi-Projeto / Monorepo
* **Objetivo:** Validar que dois diretórios diferentes mantêm bancos vetoriais e históricos 100% independentes.
* **Passos Práticos:**
  1. Crie `/tmp/projeto_frontend` e `/tmp/projeto_backend`.
  2. Crie arquivos distintos em cada um (`App.tsx` no frontend, `main.py` no backend).
  3. Inicie o `goodfella` em cada pasta e execute `/status`.
* **Critério de Sucesso:** Os diretórios `.goodfella/` ficam isolados dentro de cada pasta, e os vetores de um projeto não aparecem no outro.

---

## 🤖 BATERIA 2: Provedores LLM (Local e Nuvem)

### Teste 2.1 — Modelo Local Padrão via Ollama
* **Objetivo:** Validar inferência 100% local com streaming de resposta e cálculo de telemetria.
* **Passos Práticos:**
  1. Certifique-se de que o Ollama está rodando (`ollama list`).
  2. Abra o Goodfella: `goodfella`.
  3. Envie uma mensagem simples no chat:
     ```text
     ❯ O que é o princípio da Responsabilidade Única (SRP)?
     ```
* **Critério de Sucesso:**
  - Resposta flui via streaming no terminal com spinner inicial `Pensando...`.
  - Ao final, exibe rodapé com métricas: `✓ Concluído em X.Xs (Preparo: X.Xs) | ~N tokens | Vel: X.X t/s`.
  - Resposta técnica coesa em português.

---

### Teste 2.2 — Tratamento de Erros com Ollama Offline
* **Objetivo:** Garantir que a aplicação não crashe se o daemon do Ollama estiver desligado.
* **Passos Práticos:**
  1. Pare o serviço do Ollama (`systemctl stop ollama` ou mate o processo).
  2. Inicie o Goodfella e envie qualquer pergunta no chat.
* **Critério de Sucesso:**
  - Mensagem de erro amigável em vermelho: `Erro de Conexão: Não foi possível alcançar o provedor local (Ollama)`.
  - Dica exibida sugerindo verificar `ollama serve` ou usar `/setup`.
  - O REPL **não encerra** (permanece vivo aguardando novo comando).

---

### Teste 2.3 — Troca Interativa de Provedores com `/setup`
* **Objetivo:** Validar a configuração do arquivo global `~/.goodfella_config` via menu interativo.
* **Passos Práticos:**
  1. Digite `/setup` no prompt do Goodfella.
  2. Selecione `openai` com as setas.
  3. Digite o modelo desejado (ex: `gpt-4o-mini`).
  4. Digite uma chave de teste (ex: `sk-fake-key-12345`).
  5. Verifique o arquivo físico:
     ```bash
     cat ~/.goodfella_config
     ```
* **Critério de Sucesso:**
  - O arquivo `~/.goodfella_config` é atualizado com `provider: "openai"`, modelo configurado e a chave correspondente.
  - A CLI recarrega a instância do LLM sem necessidade de reiniciar o programa.

---

### Teste 2.4 — Auditoria com `/status`
* **Objetivo:** Validar que `/status` reflete fielmente as configurações e saúde do banco.
* **Passos Práticos:**
  1. No Goodfella, execute `/status`.
* **Critério de Sucesso:** Exibe:
  - `Provedor Ativo: openai` (ou o que estiver configurado).
  - `Modelo Ativo: gpt-4o-mini`.
  - `API Key (openai): Configurada`.
  - `Vetores na base local: <total_de_vetores>`.

---

### Teste 2.5 — Validação de Provedores de Nuvem Reais (OpenAI / Gemini / Anthropic / DeepSeek)
* **Objetivo:** Validar conexão real, streaming e geração com chaves ativas.
* **Passos Práticos:**
  1. Use `/setup` e configure uma chave válida para cada um dos provedores:
     - **Gemini:** Provedor `gemini`, modelo `gemini-1.5-pro` (ou `gemini-2.0-flash`), chave `AIza...`
     - **OpenAI:** Provedor `openai`, modelo `gpt-4o`, chave `sk-...`
     - **Anthropic:** Provedor `anthropic`, modelo `claude-3-5-sonnet-20240620`, chave `sk-ant-...`
     - **DeepSeek:** Provedor `deepseek`, modelo `deepseek-coder`, chave `sk-...`
  2. Envie uma pergunta técnica: `Explique a diferença entre Inversão de Controle e Injeção de Dependência`.
* **Critério de Sucesso:**
  - Conexão estabelecida com sucesso.
  - Streaming ativo exibindo tokens em tempo real.
  - Velocidade e tempo final exibidos corretamente.

---

### Teste 2.6 — Tratamento de Erros de Autenticação (401) e Cota (429)
* **Objetivo:** Validar os blocos de captura de exceção em [app.py](file:///home/bruno/Desktop/goodfella/src/goodfella/cli/app.py#L207-L237).
* **Passos Práticos:**
  1. Configure uma chave deliberadamente inválida no `/setup` para OpenAI.
  2. Envie uma pergunta no chat.
* **Critério de Sucesso:**
  - Exibe: `Erro de Autenticação: A chave de API fornecida é inválida ou expirou`.
  - Sugere rodar `/setup`.
  - Aplicação continua estável no REPL.

---

## 🗄️ BATERIA 3: Ingestão de Código, RAG e Sincronização Just-In-Time

### Teste 3.1 — Respeito ao `.gitignore` e Diretórios Ignorados
* **Objetivo:** Validar que diretórios como `.venv`, `node_modules`, `__pycache__` e regras do `.gitignore` não são indexados.
* **Passos Práticos:**
  1. Em uma pasta de teste, crie a seguinte estrutura:
     ```bash
     mkdir -p src node_modules .venv ignore_me
     touch src/app.py node_modules/lib.js .venv/bin.py ignore_me/secret.py
     echo "ignore_me/" >> .gitignore
     ```
  2. Inicie o Goodfella e rode `/status`.
* **Critério de Sucesso:**
  - Apenas o arquivo `src/app.py` é escaneado e chunked.
  - Arquivos em `node_modules`, `.venv` e `ignore_me` são completamente ignorados.

---

### Teste 3.2 — Suporte a Múltiplas Linguagens e Chunking Inteligente
* **Objetivo:** Validar que o [chunker.py](file:///home/bruno/Desktop/goodfella/src/goodfella/rag/chunker.py) usa o splitter correto para cada linguagem (`.py`, `.ts`, `.go`, `.rs`, `.md`).
* **Passos Práticos:**
  1. Crie arquivos com código sintático real em Python, TypeScript e Go.
  2. Execute `/rebuild` para indexação completa.
  3. No chat, faça perguntas específicas sobre funções presentes em cada arquivo.
* **Critério de Sucesso:** O RAG recupera os trechos semanticamente corretos para compor o contexto do chat.

---

### Teste 3.3 — Sincronização JIT de Novos Arquivos
* **Objetivo:** Validar se novos arquivos criados durante a sessão são detectados via `mtime`.
* **Passos Práticos:**
  1. Com o Goodfella aberto, crie um novo arquivo em outro terminal:
     ```bash
     echo "def calculate_taxes(amount): return amount * 0.15" > src/tax.py
     ```
  2. No Goodfella, execute `/refresh`.
* **Critério de Sucesso:**
  - A sincronização detecta o novo arquivo e o indexa no ChromaDB.
  - O número de vetores em `/status` aumenta.

---

### Teste 3.4 — Sincronização JIT de Arquivos Modificados
* **Objetivo:** Validar que alterações em arquivos existentes substituem os vetores antigos (sem duplicar).
* **Passos Práticos:**
  1. Anote o número de vetores com `/status`.
  2. Modifique `src/tax.py` alterando a regra de negócio.
  3. Execute `/refresh` e depois `/status`.
* **Critério de Sucesso:**
  - O arquivo antigo é detectado como alterado (`current_mtime > indexed_mtime`).
  - Os vetores antigos são removidos e os novos são inseridos.
  - O total de vetores permanece proporcional (sem duplicação descontrolada).

---

### Teste 3.5 — Limpeza de Vetores Órfãos (Arquivos Deletados)
* **Objetivo:** Validar que deletar um arquivo do disco remove seus vetores do ChromaDB.
* **Passos Práticos:**
  1. Remova o arquivo `src/tax.py`:
     ```bash
     rm src/tax.py
     ```
  2. Execute `/refresh` no Goodfella e verifique `/status`.
* **Critério de Sucesso:** O número de vetores diminui e os dados do arquivo deletado não aparecem mais nas buscas do RAG.

---

### Teste 3.6 — Comando `/rebuild` (Botão de Pânico)
* **Objetivo:** Validar a recriação completa da base vetorial a partir do zero.
* **Passos Práticos:**
  1. Execute `/rebuild`.
  2. Responda `y` na confirmação.
* **Critério de Sucesso:**
  - A coleção existente no ChromaDB é limpa.
  - O pipeline de regras e escaneamento é reexecutado.
  - Mensagem `Base reconstruída com sucesso!` é exibida.

---

## 📜 BATERIA 4: Gestão de Regras de Arquitetura e Anti-Patterns

### Teste 4.1 — Adição Interativa de Regra Local via Editor
* **Objetivo:** Validar o fluxo do comando `/rule add` com abertura do editor de texto do sistema.
* **Passos Práticos:**
  1. No prompt, digite: `/rule add`.
  2. Selecione `Local (apenas para o projeto atual)`.
  3. Selecione `Regra (Diretriz arquitetural recomendada)`.
  4. Selecione `Digitar manualmente (abre editor de texto)`.
  5. Digite o nome: `evitar_side_effects.md`.
  6. No editor (`nano`/`vim`), adicione uma diretriz clara:
     ```markdown
     # Evitar Side Effects
     Funções de consulta não devem alterar o estado de entidades do domínio (CQS).
     ```
  7. Salve e saia do editor.
* **Critério de Sucesso:**
  - O arquivo é salvo em `.goodfella/rules/evitar_side_effects.md`.
  - A base de regras é sincronizada automaticamente no ChromaDB com metadado `is_rule: True`.

---

### Teste 4.2 — Importação de Arquivo de Anti-Pattern
* **Objetivo:** Validar a importação de um arquivo `.md` existente.
* **Passos Práticos:**
  1. Crie um arquivo em `/tmp/anti_pattern_anemic.md` com exemplos de modelo anêmico.
  2. No Goodfella, execute `/rule add`.
  3. Escolha `Local` -> `Anti-pattern` -> `Importar arquivo existente (.md)`.
  4. Forneça o caminho `/tmp/anti_pattern_anemic.md`.
* **Critério de Sucesso:**
  - O arquivo é copiado para `.goodfella/rules/anti_patterns/anti_pattern_anemic.md`.
  - As novas regras são indexadas no banco vetorial.

---

### Teste 4.3 — Regras Globais vs Regras Locais
* **Objetivo:** Garantir que regras criadas no escopo Global fiquem salvas em `~/.goodfella_config/rules` e sejam acessíveis em qualquer repositório.
* **Passos Práticos:**
  1. Adicione uma regra com escopo `Global`.
  2. Verifique o caminho físico `~/.goodfella_config/rules/`.
  3. Mude para outro diretório de projeto e inicie o Goodfella.
* **Critério de Sucesso:** A regra global é sincronizada no banco do novo projeto durante a inicialização.

---

## 🔍 BATERIA 5: Revisão de Código (`/review` e `/deep-review`)

### Teste 5.1 — `/review` Interativo com Seleção de Arquivos (Questionary)
* **Objetivo:** Validar a seleção via teclado (espaço para marcar, enter para confirmar).
* **Passos Práticos:**
  1. No prompt, digite apenas: `/review`.
  2. Na lista exibida com checkbox, selecione 1 ou 2 arquivos usando as setas e a barra de espaço.
  3. Pressione Enter.
* **Critério de Sucesso:**
  - O sistema exibe o spinner com cronômetro `Buscando regras no Banco Vetorial...`.
  - Executa a busca semântica no RAG filtrando por `is_rule: True`.
  - Envia o código numerado e as regras recuperadas para o LLM.

---

### Teste 5.2 — `/review` com Argumentos de Linha de Comando
* **Objetivo:** Validar a chamada direta passando múltiplos arquivos.
* **Passos Práticos:**
  1. Execute: `/review src/domain/user.py src/services/user_service.py`.
* **Critério de Sucesso:** O review inicia imediatamente com os arquivos informados, sem abrir o menu interativo.

---

### Teste 5.3 — Detecção de Anti-Patterns e Qualidade do Relatório
* **Objetivo:** Validar se o Goodfella detecta violações reais e formata a resposta no padrão estrito.
* **Passos Práticos:**
  1. Crie um arquivo propositalmente problemático `src/bad_god_class.py`:
     ```python
     class OrderManager:
         """God class com múltiplos acoplamentos e sem abstrações."""
         def __init__(self):
             self.db = "mysql://localhost"
             self.smtp = "smtp.mail.com"

         def save_to_db(self, order):
             # Acesso direto a banco
             pass

         def send_confirmation_email(self, user):
             # Envio direto de email
             pass

         def calculate_complex_discount(self, order):
             # Regra de negócio misturada com infra
             pass

         def generate_pdf_invoice(self, order):
             # Geração de PDF
             pass
     ```
  2. Execute `/review src/bad_god_class.py`.
* **Critério de Sucesso:**
  - O relatório retornado pelo Goodfella contém as seções obrigatórias:
    - `## Veredito`
    - `## Problemas`
    - `### <GRAVIDADE> <Nome do Problema>` com:
      - `- **Arquivo:** src/bad_god_class.py:L<linha>`
      - `- **Regra Violada:** <SOLID / GOD CLASS / Clean Architecture>`
      - `- **Problema:** <Explicação>`
      - `- **Correção:** <Sugestão>`
  - O assistente **NÃO** inventa arquivos inexistentes (Zero Hallucination).

---

### Teste 5.4 — `/deep-review` (Bypass de RAG e Contexto Integral)
* **Objetivo:** Validar o "Curinga da Nuvem", checagem de tamanho de tokens e confirmação de custo.
* **Passos Práticos:**
  1. Execute `/deep-review`.
  2. Observe o painel exibido:
     - Total de arquivos no projeto.
     - Estimativa de tokens (`~N tokens`).
     - Alerta de custos e dica sobre Prompt Caching.
  3. Pressione `N` para cancelar e valide se a operação é abortada com segurança.
  4. Execute novamente e pressione `y` para prosseguir.
* **Critério de Sucesso:**
  - O projeto completo (respeitando `.gitignore`) é empacotado e enviado ao modelo.
  - O prompt recebe a flag `is_deep=True`, permitindo análise cross-file entre módulos.
  - Resposta completa e detalhada sobre o design global do sistema.

---

## 💬 BATERIA 6: REPL, UX e Gerenciamento de Memória

### Teste 6.1 — Chat Livre com Enriquecimento Dinâmico de RAG
* **Objetivo:** Validar conversação livre fora dos comandos `/` e injeção transparente de contexto.
* **Passos Práticos:**
  1. Pergunte: `Onde no meu projeto está definida a classe OrderManager?`.
* **Critério de Sucesso:** O Goodfella consulta a base vetorial, recupera o snippet relevante e responde com precisão em linguagem natural.

---

### Teste 6.2 — Isolamento e Proteção do `chat_history.json`
* **Objetivo:** Garantir que fragmentos de código gigantescos recuperados pelo RAG **nunca** sejam salvos no JSON de histórico.
* **Passos Práticos:**
  1. Execute um `/review` ou pergunte algo complexo sobre o código.
  2. Abra o arquivo `.goodfella/chat_history.json`:
     ```bash
     cat .goodfella/chat_history.json
     ```
* **Critério de Sucesso:**
  - O JSON contém apenas o histórico de mensagens `{ "role": "user", "content": "..." }` e `{ "role": "ai", "content": "..." }`.
  - O contexto de System Prompt / RAG não foi gravado no arquivo, mantendo o histórico enxuto.

---

### Teste 6.3 — Limite da Janela Deslizante de Memória
* **Objetivo:** Validar que o histórico é limitado a `MAX_HISTORY_MESSAGES` (20 mensagens) para evitar estouro de contexto.
* **Passos Práticos:**
  1. Envie 25 mensagens curtas no chat.
  2. Verifique o número de mensagens carregadas no [load_history()](file:///home/bruno/Desktop/goodfella/src/goodfella/llm/memory.py#L20-L45).
* **Critério de Sucesso:** O histórico retornado para a chamada do modelo mantém no máximo as 20 mensagens mais recentes.

---

### Teste 6.4 — Comandos de Sessão (`/clear`, `/reset`, `/help`, `/quit`)
* **Objetivo:** Validar todos os comandos utilitários do REPL.
* **Passos Práticos:**
  1. `/help`: Verifica se lista todos os comandos com descrição e cores Rich.
  2. `/clear`: Verifica se a tela do terminal é limpa e o banner de boas-vindas é reexibido.
  3. `/reset`: Verifica se o arquivo `.goodfella/chat_history.json` é apagado.
  4. `/quit` ou `/exit`: Verifica encerramento gracioso do processo com código de saída 0.
* **Critério de Sucesso:** Todos os comandos executam sem lançar exceções.

---

## 🧪 BATERIA 7: Testes Automatizados e CI/CD

### Teste 7.1 — Execução da Suíte Pytest Local
* **Passos Práticos:**
  ```bash
  uv run pytest -v
  ```
* **Critério de Sucesso:** Todos os testes unitários em [tests/test_config.py](file:///home/bruno/Desktop/goodfella/tests/test_config.py) passam com status `PASSED`.

---

### Teste 7.2 — Execução da Pipeline de CI Local (via act)
* **Passos Práticos:**
  ```bash
  ./bin/act push
  ```
* **Critério de Sucesso:** O container do GitHub Actions roda com sucesso executando o checkout, setup do uv, instalação e pytest.

---

## 🚀 BATERIA 8: Roteiro Rápido Hands-On de Validação (15 Minutos)

Para uma validação prática completa e rápida de ponta a ponta, execute o roteiro abaixo em um diretório sandbox:

```bash
# 1. Criação do cenário de testes
mkdir -p /tmp/sandbox-goodfella/src
cd /tmp/sandbox-goodfella
git init

# 2. Criação de arquivo com violação de Clean Architecture / SOLID
cat << 'EOF' > src/user_service.py
class UserService:
    def create_user(self, name, email, raw_password):
        # Violação: lógica de banco, hash e envio de email tudo junto (God Method / Alto Acoplamento)
        import sqlite3, hashlib, smtplib
        conn = sqlite3.connect("app.db")
        hashed = hashlib.sha256(raw_password.encode()).hexdigest()
        conn.execute("INSERT INTO users VALUES (?, ?, ?)", (name, email, hashed))
        conn.commit()
        
        server = smtplib.SMTP("smtp.gmail.com")
        server.sendmail("noreply@app.com", email, "Bem-vindo!")
EOF

# 3. Execução da CLI
goodfella

# 4. No REPL do Goodfella, execute sequencialmente:
# Passo A: /status (Verificar saúde inicial)
# Passo B: /review src/user_service.py (Validar detecção de acoplamento e SRP)
# Passo C: /rule add (Criar uma regra local de exemplo)
# Passo D: /status (Verificar aumento de vetores)
# Passo E: Faça uma pergunta: "Como posso refatorar a classe UserService para seguir Clean Architecture?"
# Passo F: /reset (Zerar histórico)
# Passo G: /quit (Sair)
```

---

## 📊 Checklist de Validação Final (Homologação)

- [ ] Instalação via `pipx` e via `uv` funcionando.
- [ ] Criação de `.goodfella/` e proteção no `.gitignore`.
- [ ] Ollama local respondendo com streaming e métricas de tempo/velocidade.
- [ ] Provedores Cloud (OpenAI / Gemini / Anthropic / DeepSeek) configuráveis via `/setup`.
- [ ] Mensagens de erro amigáveis para falhas de conexão e chaves inválidas (sem traceback bruto).
- [ ] Sincronização Just-in-Time (JIT) indexando arquivos novos e limpando deletados.
- [ ] `/review` estruturado com identificação de arquivos, linhas numeradas e regras violadas.
- [ ] `/deep-review` calculando tokens, exibindo aviso de custo e analisando projeto completo.
- [ ] `chat_history.json` registrando estritamente perguntas e respostas sem poluição de contexto.
- [ ] Comandos utilitários (`/clear`, `/reset`, `/status`, `/refresh`, `/rebuild`, `/help`, `/quit`) funcionando perfeitamente.
