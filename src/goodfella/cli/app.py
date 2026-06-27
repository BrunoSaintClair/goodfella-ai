"""
Entry point principal do Goodfella CLI.

Este módulo contém a função `main()` que é registrada como console_script
no pyproject.toml, permitindo invocar o Goodfella diretamente via terminal:

    $ goodfella

"""


import sys
import logging
import warnings

# Suprime warnings e logs de bibliotecas de terceiros (ChromaDB, Langchain, etc)
warnings.filterwarnings("ignore")
logging.getLogger("chromadb").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

from langchain_core.messages import SystemMessage, HumanMessage

from goodfella.core.env import init_environment
from goodfella.rag.chunker import run_indexing_pipeline
from goodfella.knowledge.rules import sync_rules
from goodfella.llm.factory import get_llm
from goodfella.llm.memory import load_history, save_message, clear_history
from goodfella.cli.ui import console, show_spinner
from goodfella.cli.commands import handle_setup, handle_status, handle_refresh, handle_rebuild, handle_help, handle_review, handle_deep_review

def print_welcome():
    console.print("\n[bold magenta]🎩 Goodfella AI Pair Programmer[/bold magenta]")
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
            llm = get_llm()
        
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
                
            # Prepara a janela de contexto
            history = load_history()
            
            if cmd.startswith("/review"):
                user_msg, sys_prompt = handle_review(cmd)
                if not user_msg:
                    continue
                user_input = user_msg
                system_prompt = sys_prompt
            elif cmd.startswith("/deep-review"):
                user_msg, sys_prompt = handle_deep_review(cmd)
                if not user_msg:
                    continue
                user_input = user_msg
                system_prompt = sys_prompt
            else:
                system_prompt = (
                    "Você é o Goodfella, um AI Pair Programmer local-first ultra focado em "
                    "engenharia de software pragmática. Responda sempre em português, de forma direta."
                )
            
            messages = [SystemMessage(content=system_prompt)]
            messages.extend(history)
            messages.append(HumanMessage(content=user_input))
            
            console.print("\n[bold magenta]❖[/bold magenta] ", end="")
            full_response = ""
            
            try:
                for chunk in llm.stream(messages):
                    print(chunk.content, end="", flush=True)
                    full_response += chunk.content
            except Exception as e:
                error_msg = str(e)
                if "Connection refused" in error_msg or "Errno 111" in error_msg:
                    console.print("\n[danger]Erro: Não foi possível conectar ao Ollama (Connection refused).[/danger]")
                    console.print("[info]Dica: Verifique se o Ollama está rodando no seu terminal com 'ollama serve'.[/info]")
                    console.print("[info]Se deseja usar OpenAI ou Gemini, configure-os usando o comando /setup.[/info]")
                else:
                    console.print(f"\n[danger]Erro de LLM: {error_msg}[/danger]")
                continue
            print("\n")
            
            save_message("user", user_input)
            save_message("ai", full_response)
            
    except Exception as e:
        console.print(f"\n[danger]Erro Fatal: {e}[/danger]")
        sys.exit(1)

if __name__ == "__main__":
    main()
