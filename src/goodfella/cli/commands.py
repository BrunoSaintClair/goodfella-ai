"""
Módulo responsável pelos comandos utilitários da CLI.
"""

import shutil
import questionary
from rich.prompt import Prompt, Confirm
from pathlib import Path
from typing import Tuple, Optional

from goodfella.rag.scanner import scan_workspace

from goodfella.cli.ui import console, show_spinner
from goodfella.core.config import load_config, save_config, DEFAULT_CONFIG
from goodfella.core.env import init_environment
from goodfella.rag.db import get_client, get_collection, get_db_path
from goodfella.rag.chunker import run_indexing_pipeline
from goodfella.knowledge.rules import sync_rules, get_rules_directories

def handle_setup() -> None:
    """
    Inicia o assistente de configuração para definir provedor e chaves de API.
    """
    config = load_config()
    
    console.print("\n[bold magenta]=== Configuração do Goodfella ===[/bold magenta]")
    
    valid_providers = list(DEFAULT_CONFIG["models"].keys())
    current_provider = config.get("provider", "ollama").lower()
    
    default_idx = valid_providers.index(current_provider) if current_provider in valid_providers else 0
    
    provider = questionary.select(
        "Escolha o provedor padrão:",
        choices=valid_providers,
        default=valid_providers[default_idx]
    ).ask()
    
    if not provider:
        console.print("[warning]Operação cancelada.[/warning]\n")
        return
    
    config["provider"] = provider
    
    current_model = config["models"].get(provider, "")
    console.print(f"[info]Atenção: O nome do modelo deve ser escrito EXATAMENTE como exigido pelo {provider}.[/info]")
    model = Prompt.ask(f"Digite o modelo para {provider}", default=current_model)
    if model.strip():
        config["models"][provider] = model.strip()
    
    if provider != "ollama":
        current_key = config["api_keys"].get(provider, "")
        prompt_msg = f"Digite a API Key para {provider}"
        if current_key:
            prompt_msg += " (deixe em branco para manter a atual)"
            
        key = Prompt.ask(prompt_msg, password=True, default="")
        if key.strip():
            config["api_keys"][provider] = key.strip()
    
    save_config(config)
    console.print("[success]Configuração salva com sucesso![/success]\n")

def handle_status() -> None:
    """
    Exibe o status do banco de dados, provedor e configuração atual.
    """
    config = load_config()
    provider = config.get("provider", "ollama").lower()
    model = config["models"].get(provider, "N/A")
    has_key = bool(config["api_keys"].get(provider, ""))
    
    console.print("\n[bold magenta]=== Status do Goodfella ===[/bold magenta]")
    console.print(f"[info]Provedor Ativo:[/info] {provider}")
    console.print(f"[info]Modelo Ativo:[/info] {model}")
    
    if provider != "ollama":
        key_status = "[success]Configurada[/success]" if has_key else "[danger]Não Configurada[/danger]"
        console.print(f"[info]API Key ({provider}):[/info] {key_status}")
    
    try:
        client = get_client()
        col = get_collection(client)
        count = col.count()
        console.print(f"[info]Vetores na base local:[/info] {count}")
    except Exception as e:
        console.print(f"[danger]Erro ao acessar banco vetorial:[/danger] {e}")
    console.print()

def handle_refresh() -> None:
    """
    Força a sincronização do banco vetorial local (RAG).
    """
    console.print()
    with show_spinner("Sincronizando base de código e regras..."):
        sync_rules()
        run_indexing_pipeline()
    console.print("[success]Sincronização concluída![/success]\n")

def handle_rebuild() -> None:
    """
    Apaga completamente o banco vetorial local e força uma recriação.
    """
    console.print("\n[bold red]ATENÇÃO:[/bold red] Isso apagará fisicamente o banco vetorial do projeto.")
    console.print("Ele será reconstruído do zero, o que pode levar algum tempo.\n")
    
    if Confirm.ask("Deseja realmente prosseguir?"):
        db_path = get_db_path()
        try:
            if db_path.exists():
                shutil.rmtree(db_path, ignore_errors=True)
            console.print("[info]Banco apagado. Reconstruindo...[/info]")
            
            # Recria o diretório se necessário e roda a pipeline
            init_environment()
            with show_spinner("Reconstruindo base vetorial..."):
                sync_rules()
                run_indexing_pipeline()
            console.print("[success]Base reconstruída com sucesso![/success]\n")
        except Exception as e:
            console.print(f"[danger]Erro ao reconstruir base:[/danger] {e}\n")
    else:
        console.print("[info]Operação cancelada.[/info]\n")

def handle_help() -> None:
    """
    Exibe a lista de comandos disponíveis e suas descrições.
    """
    console.print("\n[bold magenta]=== Comandos Disponíveis ===[/bold magenta]")
    
    commands = [
        ("/help", "Exibe mensagem de ajuda com todos os comandos."),
        ("/setup", "Configura provedor (Ollama, OpenAI, Gemini) e chaves de API."),
        ("/status", "Mostra o status atual: provedor ativo, chaves e tamanho do banco vetorial."),
        ("/refresh", "Força a sincronização dos arquivos do projeto com o banco vetorial local."),
        ("/rebuild", "Apaga fisicamente o banco vetorial e reconstrói do zero (útil para corrupções)."),
        ("/review [arquivos]", "Inicia revisão de código cruzada com regras arquiteturais via RAG."),
        ("/deep-review", "Faz o bypass do RAG e empacota todo o projeto + regras para o LLM (O Curinga)."),
        ("/rule add", "Adiciona uma nova regra ou anti-pattern ao projeto (local ou global)."),
        ("/clear", "Limpa a tela do terminal."),
        ("/reset", "Apaga o histórico de conversação atual."),
        ("/exit ou /quit", "Encerra a aplicação.")
    ]
    
    for cmd, desc in commands:
        console.print(f"  [bold cyan]{cmd}[/bold cyan] - {desc}")
    console.print()

def handle_review(cmd: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Inicia o fluxo do comando /review.
    - Se chamado sem argumentos, exibe menu interativo para escolha de arquivos.
    - Se chamado com argumentos, pega os caminhos passados.
    Lê os arquivos, busca regras no RAG usando fragmentos do código e injeta 
    isso no System Prompt retornado, junto com uma breve mensagem de usuário.
    """
    parts = cmd.split(maxsplit=1)
    files_to_review = []
    
    if len(parts) == 1:
        valid_files = scan_workspace()
        if not valid_files:
            console.print("[warning]Nenhum arquivo encontrado no projeto para revisão.[/warning]")
            return None, None
            
        choices = [str(p.relative_to(Path.cwd())) for p in valid_files]
        selected = questionary.checkbox(
            "Selecione os arquivos para review (Espaço para marcar, Enter para confirmar):",
            choices=choices
        ).ask()
        
        if not selected:
            console.print("[info]Review cancelado.[/info]\n")
            return None, None
        files_to_review = selected
    else:
        raw_files = parts[1].replace(",", " ").split()
        files_to_review = raw_files
        
    code_contents = []
    for f in files_to_review:
        f_path = Path.cwd() / f
        if f_path.exists() and f_path.is_file():
            try:
                content = f_path.read_text(encoding="utf-8")
                code_contents.append(f"--- Arquivo: {f} ---\n{content}")
            except Exception:
                console.print(f"[warning]Erro ao ler {f}[/warning]")
        else:
            console.print(f"[warning]Arquivo {f} não encontrado.[/warning]")
            
    if not code_contents:
        return None, None
        
    combined_code = "\n\n".join(code_contents)
    
    client = get_client()
    col = get_collection(client)
    
    query_text = combined_code[:1000]
    
    try:
        results = col.query(
            query_texts=[query_text],
            n_results=5,
            where={"is_rule": True}
        )
        if results and results.get("documents") and len(results["documents"]) > 0:
            rules_context = "\n\n".join(results["documents"][0])
        else:
            rules_context = ""
    except Exception as e:
        console.print(f"[warning]Aviso: Falha ao buscar regras no RAG: {e}[/warning]")
        rules_context = ""
        
    system_prompt = (
        "Você é o Goodfella, um AI Pair Programmer focado em engenharia de software pragmática.\n"
        "Realize um Code Review estrito do código do projeto atual.\n\n"
        "CÓDIGO-FONTE A SER REVISADO:\n"
        f"{combined_code}\n\n"
        "REGRAS DE ARQUITETURA E ANTI-PATTERNS (RAG):\n"
        f"{rules_context}\n\n"
        "Forneça sua análise com base estritamente nas regras listadas (se aplicável) e nas boas práticas.\n"
        "Não se desculpe, seja direto e liste sugestões práticas de código."
    )
    
    user_message = f"/review {', '.join(files_to_review)}"
    
    return user_message, system_prompt


def handle_rule_add() -> None:
    """
    Inicia o fluxo do comando /rule add.
    Permite escolher o escopo (global ou local), o método de entrada
    (digitação manual ou importação de arquivo .md) e sincroniza
    a base de regras no ChromaDB.
    """
    import os
    import tempfile
    import subprocess
    
    console.print("\n[bold magenta]=== Adicionar Regra / Anti-pattern ===[/bold magenta]")
    
    # 1. Escopo
    scope = questionary.select(
        "Escolha o escopo da regra:",
        choices=[
            questionary.Choice("Local (apenas para o projeto atual)", "local"),
            questionary.Choice("Global (para todos os projetos da máquina)", "global")
        ]
    ).ask()
    
    if not scope:
        console.print("[warning]Operação cancelada.[/warning]\n")
        return
        
    # 2. Tipo (Regra ou Anti-pattern)
    doc_type = questionary.select(
        "Selecione o tipo de diretriz:",
        choices=[
            questionary.Choice("Regra (Diretriz arquitetural recomendada)", "rules"),
            questionary.Choice("Anti-pattern (Prática a ser evitada)", "anti_patterns")
        ]
    ).ask()
    
    if not doc_type:
        console.print("[warning]Operação cancelada.[/warning]\n")
        return
        
    rules_dirs = get_rules_directories()
    base_dir = rules_dirs[1] if scope == "local" else rules_dirs[0]
    target_dir = base_dir / doc_type
    
    # 3. Método de entrada
    method = questionary.select(
        "Como deseja adicionar?",
        choices=[
            "Digitar manualmente (abre editor de texto)",
            "Importar arquivo existente (.md)"
        ]
    ).ask()
    
    if not method:
        console.print("[warning]Operação cancelada.[/warning]\n")
        return
        
    rule_name = ""
    rule_content = ""
    
    if method == "Digitar manualmente (abre editor de texto)":
        rule_name = Prompt.ask("Digite o nome da regra (ex: evitar_eval.md)").strip()
        if not rule_name:
            console.print("[warning]Operação cancelada por falta de nome.[/warning]\n")
            return
        if not rule_name.endswith(".md"):
            rule_name += ".md"
            
        initial_content = (
            f"# {rule_name.replace('.md', '').replace('_', ' ').title()}\n\n"
            "## Descrição\n"
            "Descreva aqui a regra ou anti-pattern...\n\n"
            "## Exemplos\n"
            "Insira exemplos de código correto e incorreto...\n"
        )
        
        editors = [os.environ.get('EDITOR'), 'nano', 'vim', 'vi']
        editors = [e for e in editors if e]
        
        with tempfile.NamedTemporaryFile(suffix=".md", mode='w', delete=False, encoding='utf-8') as tf:
            tf.write(initial_content)
            tf_path = tf.name
            
        success = False
        for editor in editors:
            try:
                subprocess.call([editor, tf_path])
                success = True
                break
            except FileNotFoundError:
                continue
                
        if not success:
            console.print("[danger]Nenhum editor de texto encontrado (nano, vim, vi).[/danger]")
            console.print("[info]Configure a variável de ambiente $EDITOR ou use a opção de importação de arquivo.[/info]\n")
            try:
                os.unlink(tf_path)
            except OSError:
                pass
            return
            
        rule_content = Path(tf_path).read_text(encoding="utf-8")
        try:
            os.unlink(tf_path)
        except OSError:
            pass
            
        if not rule_content.strip() or rule_content == initial_content:
            console.print("[warning]Nenhuma alteração detectada. Regra não salva.[/warning]\n")
            return

    else:
        # Importar arquivo
        path_str = Prompt.ask("Digite o caminho do arquivo .md a ser importado").strip()
        if not path_str:
            console.print("[warning]Operação cancelada.[/warning]\n")
            return
            
        import_path = Path(path_str).expanduser().resolve()
        if not import_path.exists() or not import_path.is_file():
            console.print("[danger]Arquivo não encontrado ou inválido.[/danger]\n")
            return
            
        if import_path.suffix.lower() != ".md":
            console.print("[danger]Apenas arquivos Markdown (.md) são suportados.[/danger]\n")
            return
            
        try:
            rule_content = import_path.read_text(encoding="utf-8")
        except Exception as e:
            console.print(f"[danger]Erro ao ler o arquivo: {e}[/danger]\n")
            return
            
        suggested_name = import_path.name
        rule_name = Prompt.ask("Digite o nome de destino", default=suggested_name).strip()
        if not rule_name:
            rule_name = suggested_name
        if not rule_name.endswith(".md"):
            rule_name += ".md"
            
    # Salvar no destino
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_path = target_dir / rule_name
        dest_path.write_text(rule_content, encoding="utf-8")
        console.print(f"[success]Regra salva em: {dest_path.relative_to(Path.cwd()) if scope == 'local' else dest_path}[/success]")
    except Exception as e:
        console.print(f"[danger]Erro ao salvar arquivo de regra: {e}[/danger]\n")
        return
        
    # Re-vetorizar (RAG Sync)
    with show_spinner("Sincronizando novas regras no banco vetorial..."):
        try:
            sync_rules()
        except Exception as e:
            console.print(f"[danger]Erro na sincronização de regras: {e}[/danger]\n")
            return
            
    console.print("[success]Regras sincronizadas com sucesso![/success]\n")



def handle_deep_review(cmd: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Inicia o fluxo do comando /deep-review ("Curinga da Nuvem").
    Faz o bypass do ChromaDB e carrega fisicamente todo o repositório
    mais os arquivos de regras (.md) em um único pacote gigantesco.
    Alerta o usuário sobre custos e envia tudo no System Prompt.
    """
    console.print("\n[bold magenta]=== Iniciando Deep Review ===[/bold magenta]")
    console.print("[info]Fazendo varredura completa do repositório (bypass RAG)...[/info]")
    
    valid_files = scan_workspace()
    
    if not valid_files:
        console.print("[warning]Nenhum arquivo válido encontrado no projeto.[/warning]")
        return None, None
        
    code_contents = []
    total_chars = 0
    
    for f_path in valid_files:
        try:
            content = f_path.read_text(encoding="utf-8")
            rel_path = str(f_path.relative_to(Path.cwd()))
            formatted_content = f"--- Arquivo: {rel_path} ---\n{content}"
            code_contents.append(formatted_content)
            total_chars += len(formatted_content)
        except Exception:
            pass
            
    rules_contents = []
    rules_dirs = get_rules_directories()
    for r_dir in rules_dirs:
        if not r_dir.exists() or not r_dir.is_dir():
            continue
        for md_file in r_dir.glob("**/*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                rules_contents.append(f"--- Regra: {md_file.name} ---\n{content}")
                total_chars += len(content)
            except Exception:
                pass
                
    total_files = len(valid_files)
    approx_tokens = total_chars // 4
    
    console.print(f"\n[warning]O projeto contém {total_files} arquivos e ~{approx_tokens} tokens (incluindo as regras).[/warning]")
    console.print("Este comando enviará TODO O REPOSITÓRIO como contexto para o LLM.")
    console.print("Dependendo do provedor (ex: OpenAI, Anthropic, Gemini), isso pode [bold red]incorrer em altos custos[/bold red].")
    console.print("Dica: Use LLMs que suportam 'Prompt Caching'.")
    
    if not Confirm.ask("Deseja realmente prosseguir e realizar o Deep Review?"):
        console.print("[info]Operação cancelada.[/info]\n")
        return None, None
        
    combined_code = "\n\n".join(code_contents)
    combined_rules = "\n\n".join(rules_contents)
    
    system_prompt = (
        "Você é o Goodfella, um AI Pair Programmer Arquiteto Sênior.\n"
        "Foi solicitado um DEEP REVIEW. Isso significa que você tem acesso integral a toda a base de código "
        "deste projeto, além de todas as Regras de Arquitetura.\n\n"
        "Sua missão é identificar gargalos arquiteturais severos, acoplamento indevido, e sugerir melhorias "
        "sistêmicas de altíssimo nível. Relacione as diferentes partes do sistema.\n\n"
        "REGRAS E BOAS PRÁTICAS DO PROJETO:\n"
        f"{combined_rules}\n\n"
        "CÓDIGO-FONTE INTEGRAL DO PROJETO:\n"
        f"{combined_code}\n\n"
        "Por favor, seja extremamente objetivo e foque em problemas estruturais e bad smells globais."
    )
    
    user_message = "/deep-review"
    
    return user_message, system_prompt
