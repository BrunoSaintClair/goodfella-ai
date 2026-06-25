# 🎩 Goodfella

**Strict Pair Programmer CLI** — Um assistente de IA focado estritamente em Engenharia de Software que atua como um Pair Programmer Rigoroso e Arquiteto de Software.

## O que é?

O Goodfella analisa códigos, detecta violações de princípios (SOLID, Clean Architecture, DDD, etc.) e sugere melhorias. Ele **não altera código diretamente** — apenas aconselha.

## Características

- 🔒 **Local-First** — Processamento padrão 100% local via Ollama
- ☁️ **Multi-Provedor** — Suporte a OpenAI, Anthropic, Gemini
- 🧠 **RAG Inteligente** — Base vetorial com ChromaDB embutido
- 📂 **Isolamento por Projeto** — Contextos independentes por diretório
- 💬 **Chat Interativo** — REPL fluido no terminal com Rich

## Instalação

### Via pip (quando publicado)

```bash
pip install goodfella
```

### Via código-fonte

```bash
git clone <repo-url>
cd goodfella
uv sync
uv run goodfella
```

## Uso

```bash
# Inicia o chat interativo no diretório do seu projeto
$ goodfella
```

### Comandos Principais

| Comando | Descrição |
|---------|-----------|
| `/review` | Revisão estrita de Clean Architecture/SOLID |
| `/deep-review` | Análise completa via modelo Cloud (bypass do RAG) |
| `/setup` | Assistente de configuração de provedor |
| `/status` | Saúde do sistema e provedor ativo |
| `/rule add` | Adicionar regra customizada |
| `/rebuild` | Reconstruir banco vetorial do zero |
| `/quit` | Encerrar e salvar histórico |

## Stack Técnica

- **Python** + **uv**
- **LangChain** — Orquestração de IA
- **ChromaDB** — Banco vetorial embutido
- **Rich** — Interface de terminal
- **Ollama** — LLM local (padrão)

## Licença

Proprietary / All Rights Reserved

O código-fonte é disponibilizado apenas para visualização e fins educacionais. É estritamente proibido modificar, distribuir, sublicenciar ou utilizar este projeto (ou qualquer parte dele) para fins comerciais sem autorização prévia por escrito.
