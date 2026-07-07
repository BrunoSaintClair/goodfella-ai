"""
Entry point principal do Goodfella CLI.

Este módulo contém a função `main()` que é registrada como console_script
no pyproject.toml, permitindo invocar o Goodfella diretamente via terminal:

    $ goodfella

"""


import sys
import time
import logging
import warnings

# Suprime warnings e logs de bibliotecas de terceiros (ChromaDB, Langchain, etc)
warnings.filterwarnings("ignore")
logging.getLogger("chromadb").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

from langchain_core.messages import SystemMessage, HumanMessage

from goodfella.core.env import init_environment
from goodfella.rag.chunker import run_indexing_pipeline
from goodfella.rag.db import get_client, get_collection
from goodfella.knowledge.rules import sync_rules
from goodfella.llm.factory import get_llm
from goodfella.llm.memory import load_history, save_message, clear_history
from goodfella.cli.ui import console, show_spinner, show_timer_spinner
from goodfella.cli.commands import handle_setup, handle_status, handle_refresh, handle_rebuild, handle_help, handle_review, handle_deep_review, handle_rule_add

def print_welcome():
    console.print("\n[bold magenta]🎩 Goodfella AI Pair Programmer[/bold magenta]")
    console.print("[warning]⚠️  Lembre-se de manter seu servidor LLM rodando (ex: 'ollama serve'), senão a aplicação não funcionará![/warning]")
    console.print("[info]Digite /help para ver a lista de comandos disponíveis.[/info]\n")

def main() -> None:
    """Ponto de entrada principal do comando `goodfella`.

    Inicializa o ambiente, sincroniza a base vetorial e
    inicia o loop REPL interativo com o usuário.
    """
    try:
        # 1. Setup do ambiente e Banco de Dados
        init_environment()
        
        with show_spinner("Sincronizando base de código e regras..."):
            sync_rules()
            run_indexing_pipeline()
            
        # 2. Inicialização da Instância LangChain
        llm = None
        try:
            llm = get_llm()
        except ValueError as e:
            console.print(f"\n[warning]Aviso de Configuração: {e}[/warning]")
            console.print("[info]Use o comando /setup para configurar seu provedor antes de interagir.[/info]")
        
        print_welcome()
        
        # 3. Loop REPL Interativo
        while True:
            try:
                user_input = console.input("[bold blue]❯[/bold blue] ")
            except (KeyboardInterrupt, EOFError):
                break
                
            if not user_input.strip():
                continue
                
            cmd = user_input.strip().lower()
            if cmd in ["/exit", "/quit"]:
                break
            elif cmd == "/clear":
                console.clear()
                print_welcome()
                continue
            elif cmd == "/reset":
                clear_history()
                console.print("[info]Histórico apagado.[/info]\n")
                continue
            elif cmd == "/setup":
                handle_setup()
                try:
                    llm = get_llm()
                    console.print("[success]Provedor LLM atualizado com sucesso.[/success]\n")
                except ValueError as e:
                    console.print(f"[warning]Aviso: {e}[/warning]\n")
                continue
            elif cmd == "/status":
                handle_status()
                continue
            elif cmd == "/refresh":
                handle_refresh()
                continue
            elif cmd == "/rebuild":
                handle_rebuild()
                continue
            elif cmd == "/help":
                handle_help()
                continue
            elif cmd.startswith("/rule add"):
                handle_rule_add()
                continue
                
            if not llm:
                try:
                    llm = get_llm()
                except ValueError as e:
                    console.print(f"\n[danger]Configuração Incompleta: {e}[/danger]")
                    console.print("[info]Dica: Use o comando /setup para configurar seu provedor.[/info]\n")
                    continue
            
            # Prepara a janela de contexto
            history = load_history()
            
            is_review_cmd = False
            
            if cmd.startswith("/review"):
                is_review_cmd = True
                user_msg, sys_prompt = handle_review(cmd)
                if not user_msg:
                    continue
                user_input = user_msg
                system_prompt = sys_prompt
            elif cmd.startswith("/deep-review"):
                is_review_cmd = True
                user_msg, sys_prompt = handle_deep_review(cmd)
                if not user_msg:
                    continue
                user_input = user_msg
                system_prompt = sys_prompt
            else:
                # Busca contexto relevante do projeto via RAG para enriquecer o chat
                rag_context = ""
                try:
                    client = get_client()
                    col = get_collection(client)
                    rag_results = col.query(query_texts=[user_input], n_results=3)
                    if rag_results and rag_results.get("documents") and rag_results["documents"][0]:
                        rag_context = "\n\n".join(rag_results["documents"][0])
                except Exception:
                    pass
                
                if rag_context:
                    system_prompt = (
                        "Você é o Goodfella, um AI Pair Programmer local-first.\n"
                        "Responda em português, de forma direta.\n\n"
                        "CONTEXTO DO PROJETO (fragmentos relevantes recuperados via RAG):\n"
                        f"{rag_context}\n\n"
                        "Use o contexto acima para embasar suas respostas quando relevante. "
                        "Se o contexto não for relevante para a pergunta, ignore-o."
                    )
                else:
                    system_prompt = (
                        "Você é o Goodfella, um AI Pair Programmer local-first.\n"
                        "Responda em português, de forma direta."
                    )
            
            messages = [SystemMessage(content=system_prompt)]
            messages.extend(history)
            messages.append(HumanMessage(content=user_input))
            
            console.print("\n[bold magenta]❖[/bold magenta] ", end="")
            full_response = ""
            
            try:
                start_time = time.time()
                stream_iter = llm.stream(messages)
                
                try:
                    if is_review_cmd:
                        with show_timer_spinner("Avaliando arquitetura e escrevendo Code Review..."):
                            first_chunk = next(stream_iter)
                    else:
                        with show_spinner("Pensando..."):
                            first_chunk = next(stream_iter)
                    
                    ttft_end = time.time()
                    print(first_chunk.content, end="", flush=True)
                    full_response += first_chunk.content
                    chunk_count = 1
                    
                    for chunk in stream_iter:
                        print(chunk.content, end="", flush=True)
                        full_response += chunk.content
                        chunk_count += 1
                        
                    total_time = time.time() - start_time
                    gen_time = time.time() - ttft_end
                    tps = chunk_count / gen_time if gen_time > 0 else 0
                    
                    console.print(f"\n\n[info]✓ Concluído em {total_time:.1f}s (Preparo: {ttft_end - start_time:.1f}s) | ~{chunk_count} tokens | Vel: {tps:.1f} t/s[/info]")
                except StopIteration:
                    pass
            except Exception as e:
                error_msg = str(e)
                error_msg_lower = error_msg.lower()
                
                # Falhas de conexão (geralmente Ollama)
                if "connection refused" in error_msg_lower or "errno 111" in error_msg_lower or "connecterror" in error_msg_lower:
                    console.print("\n[danger]Erro de Conexão: Não foi possível alcançar o provedor local (Ollama).[/danger]")
                    console.print("[info]Dica: Verifique se o servidor Ollama está rodando ('ollama serve').[/info]")
                    console.print("[info]Se deseja usar provedores em nuvem (OpenAI, Gemini), mude no comando /setup.[/info]")
                
                # Erros de Autenticação / Chave Inválida
                elif "authenticationerror" in error_msg_lower or "401" in error_msg_lower or "unauthorized" in error_msg_lower:
                    console.print("\n[danger]Erro de Autenticação: A chave de API fornecida é inválida ou expirou.[/danger]")
                    console.print("[info]Dica: Rode /setup para inserir uma chave de API válida para o provedor selecionado.[/info]")
                
                # Erros de Limite de Cota (Rate Limit)
                elif "ratelimiterror" in error_msg_lower or "429" in error_msg_lower or "quota" in error_msg_lower:
                    console.print("\n[danger]Erro de Cota (Rate Limit): O limite de requisições ou cota do provedor foi excedido.[/danger]")
                    console.print("[info]Dica: Verifique seu saldo na plataforma do provedor ou aguarde alguns instantes antes de tentar novamente.[/info]")
                
                # Erro de Modelo Inexistente
                elif "notfounderror" in error_msg_lower or "404" in error_msg_lower or "not found" in error_msg_lower:
                    console.print("\n[danger]Erro de Modelo: O modelo especificado não foi encontrado no provedor.[/danger]")
                    console.print("[info]Dica: Se estiver usando Ollama, certifique-se de ter feito o pull do modelo (ex: 'ollama pull qwen2.5-coder:1.5b').[/info]")
                    console.print("[info]Ou edite manualmente o arquivo ~/.goodfella_config para ajustar o nome do modelo.[/info]")
                
                # Fallback para erros genéricos
                else:
                    console.print(f"\n[danger]Erro inesperado do LLM: {error_msg}[/danger]")
                    console.print("[info]Dica: Verifique se sua conexão de internet está ativa e se os parâmetros estão corretos.[/info]")
                continue
            print("\n")
            
            save_message("user", user_input)
            save_message("ai", full_response)
            
    except Exception as e:
        console.print(f"\n[danger]Erro Fatal: {e}[/danger]")
        sys.exit(1)

if __name__ == "__main__":
    main()
