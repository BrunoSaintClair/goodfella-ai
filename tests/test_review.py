"""Testes de Revisão de Código e Arquitetura (Bateria 5)."""

import os
import re
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from goodfella.core.env import init_environment, GOODFELLA_DIR
from goodfella.knowledge.rules import sync_rules
from goodfella.rag.db import get_client, get_collection
from goodfella.cli.commands import (
    extract_code_signals,
    add_line_numbers,
    format_rules_context,
    build_review_prompt,
    handle_review,
    handle_deep_review,
)


class TestReviewHelpers:
    """Validação das funções auxiliares de extração de sinais, formatação e prompts."""

    def test_extract_code_signals_classes_and_god_class(self):
        # 1. Classe simples com poucos métodos
        code_simple = (
            "class SimpleService:\n"
            "    def execute(self):\n"
            "        pass\n"
        )
        signals = extract_code_signals(code_simple)
        assert "classes: SimpleService" in signals
        assert "god class" not in signals

        # 2. Possível God Class (mais de 10 métodos)
        methods = "\n".join([f"    def method_{i}(self):\n        pass" for i in range(12)])
        code_god = f"class HugeManager:\n{methods}\n"
        signals_god = extract_code_signals(code_god)
        assert "classes: HugeManager" in signals_god
        assert "possível god class" in signals_god
        assert "12 métodos" in signals_god

        # 3. Múltiplas classes
        code_multi = (
            "class Foo:\n    pass\n\n"
            "class Bar:\n    pass\n"
        )
        signals_multi = extract_code_signals(code_multi)
        assert "Foo" in signals_multi and "Bar" in signals_multi

    def test_extract_code_signals_functions(self):
        code_funcs = (
            "def calculate_total(a, b):\n    return a + b\n\n"
            "def format_currency(val):\n    return f'R$ {val}'\n"
        )
        signals = extract_code_signals(code_funcs)
        assert "funções: calculate_total, format_currency" in signals

    def test_extract_code_signals_imports(self):
        # Mais de 8 imports indica alto acoplamento
        code_imports = "\n".join([f"import lib_{i}" for i in range(10)]) + "\n\nx = 1\n"
        signals = extract_code_signals(code_imports)
        assert "10 imports (alto acoplamento)" in signals

    def test_extract_code_signals_fallback(self):
        # Sem classes, defs ou imports
        code_raw = (
            "# Apenas comentário\n"
            "a = 10\n"
            "b = 20\n"
            "print(a + b)\n"
        )
        signals = extract_code_signals(code_raw)
        assert "a = 10" in signals
        assert "print(a + b)" in signals

    def test_add_line_numbers(self):
        code = "def foo():\n    return 42"
        numbered = add_line_numbers(code)
        expected = "1: def foo():\n2:     return 42"
        assert numbered == expected

    def test_format_rules_context_empty(self):
        context = format_rules_context({})
        assert context == "Nenhuma regra disponível."

    def test_format_rules_context_with_rules(self):
        rule_files = {
            "/path/to/solid.md": "Diretrizes de SRP, OCP, LSP, ISP e DIP.",
            "/path/to/anti_patterns/god_class.md": "Evitar classes excessivamente grandes.",
        }
        context = format_rules_context(rule_files)
        assert "=== REGRA: SOLID ===" in context
        assert "=== FIM REGRA: SOLID ===" in context
        assert "=== REGRA: GOD CLASS ===" in context
        assert "=== FIM REGRA: GOD CLASS ===" in context
        assert "Diretrizes de SRP" in context
        assert "Evitar classes excessivamente grandes." in context

    def test_build_review_prompt_shallow(self):
        code_blocks = ["--- Arquivo: src/user.py ---\n1: class User:\n2:     pass"]
        rules_context = "=== REGRA: SOLID ===\nSRP\n=== FIM REGRA: SOLID ==="
        file_names = ["src/user.py"]

        prompt = build_review_prompt(
            code_blocks=code_blocks,
            rules_context=rules_context,
            file_names=file_names,
            is_deep=False,
        )

        # Regras de escopo restrito (Zero Hallucination)
        assert "ATENÇÃO: Analise EXCLUSIVAMENTE os arquivos listados: `src/user.py`" in prompt
        assert "NÃO mencione, cite ou invente nomes de arquivos" in prompt
        assert "ZERO ALUCINAÇÃO" in prompt
        assert "AGRUPE PROBLEMAS" in prompt
        assert "NÃO DESOBEDEÇA O FORMATO" in prompt

        # Formato de resposta Markdown obrigatório
        assert "## Veredito" in prompt
        assert "## Problemas" in prompt
        assert "### <NÍVEL DE GRAVIDADE> <Nome do Problema>" in prompt
        assert "- **Arquivo:** <nome_do_arquivo>:L<linha>" in prompt
        assert "- **Regra Violada:** <Nome da regra>" in prompt
        assert "- **Problema:** <Descrição do problema>" in prompt
        assert "- **Correção:** <Sugestão de correção>" in prompt

        # Código e contexto injetados
        assert "--- Arquivo: src/user.py ---" in prompt
        assert "=== REGRA: SOLID ===" in prompt

    def test_build_review_prompt_deep(self):
        code_blocks = ["--- Arquivo: src/app.py ---\n1: pass"]
        rules_context = "=== REGRA: CLEAN ARCH ===\nArch\n=== FIM REGRA: CLEAN ARCH ==="
        file_names = ["src/app.py"]

        prompt = build_review_prompt(
            code_blocks=code_blocks,
            rules_context=rules_context,
            file_names=file_names,
            is_deep=True,
        )

        assert "Você tem acesso ao código-fonte INTEGRAL do projeto." in prompt
        assert "cross-file" in prompt
        assert "ATENÇÃO: Analise EXCLUSIVAMENTE" not in prompt


class TestHandleReviewInteractive:
    """Validação do fluxo /review interativo via questionary (Teste 5.1)."""

    def test_handle_review_empty_workspace(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()

        # Sem arquivos válidos no projeto
        user_msg, sys_prompt = handle_review("/review")
        assert user_msg is None
        assert sys_prompt is None

    @patch("goodfella.cli.commands.questionary.checkbox")
    def test_handle_review_selection_canceled(self, mock_checkbox, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()

        (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")

        mock_ask = MagicMock()
        mock_ask.ask.return_value = None  # Usuário cancelou ou pressionou Ctrl+C
        mock_checkbox.return_value = mock_ask

        user_msg, sys_prompt = handle_review("/review")
        assert user_msg is None
        assert sys_prompt is None

        # Usuário não marcou nenhum arquivo
        mock_ask.ask.return_value = []
        user_msg, sys_prompt = handle_review("/review")
        assert user_msg is None
        assert sys_prompt is None

    @patch("goodfella.cli.commands.questionary.checkbox")
    def test_handle_review_interactive_success(self, mock_checkbox, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()
        sync_rules(tmp_path)

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        user_file = src_dir / "user_service.py"
        user_file.write_text(
            "class UserService:\n"
            "    def register(self, email):\n"
            "        pass\n",
            encoding="utf-8",
        )

        mock_ask = MagicMock()
        mock_ask.ask.return_value = ["src/user_service.py"]
        mock_checkbox.return_value = mock_ask

        user_msg, sys_prompt = handle_review("/review")

        # Verifica se o questionary recebeu a lista de escolhas relativas
        assert mock_checkbox.called
        choices = mock_checkbox.call_args[1]["choices"]
        assert "src/user_service.py" in choices

        # Valida retorno
        assert user_msg == "/review src/user_service.py"
        assert sys_prompt is not None
        assert "src/user_service.py" in sys_prompt
        assert "1: class UserService:" in sys_prompt
        assert "2:     def register(self, email):" in sys_prompt
        assert "## Veredito" in sys_prompt
        assert "## Problemas" in sys_prompt

    @patch("goodfella.cli.commands.get_collection")
    @patch("goodfella.cli.commands.questionary.checkbox")
    def test_handle_review_rag_exception_resilience(
        self, mock_checkbox, mock_get_collection, tmp_path: Path, monkeypatch
    ):
        """Garante resiliência caso ocorra falha na busca vetorial."""
        monkeypatch.chdir(tmp_path)
        init_environment()

        test_file = tmp_path / "main.py"
        test_file.write_text("x = 1\n", encoding="utf-8")

        mock_ask = MagicMock()
        mock_ask.ask.return_value = ["main.py"]
        mock_checkbox.return_value = mock_ask

        # Simula erro no ChromaDB
        mock_col = MagicMock()
        mock_col.query.side_effect = Exception("ChromaDB connection timeout")
        mock_get_collection.return_value = mock_col

        user_msg, sys_prompt = handle_review("/review")
        assert user_msg == "/review main.py"
        assert sys_prompt is not None
        assert "Nenhuma regra disponível." in sys_prompt
        assert "1: x = 1" in sys_prompt


class TestHandleReviewCommandLine:
    """Validação da chamada direta com argumentos de linha de comando (Teste 5.2)."""

    @patch("goodfella.cli.commands.questionary.checkbox")
    def test_handle_review_cli_single_file(self, mock_checkbox, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()
        sync_rules(tmp_path)

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        user_file = src_dir / "user.py"
        user_file.write_text("class User:\n    id: int\n", encoding="utf-8")

        user_msg, sys_prompt = handle_review("/review src/user.py")

        # Não deve abrir o menu interativo Questionary
        assert not mock_checkbox.called
        assert user_msg == "/review src/user.py"
        assert "src/user.py" in sys_prompt
        assert "1: class User:" in sys_prompt

    @patch("goodfella.cli.commands.questionary.checkbox")
    def test_handle_review_cli_multiple_files_space_and_comma(
        self, mock_checkbox, tmp_path: Path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        init_environment()
        sync_rules(tmp_path)

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        file_a = src_dir / "a.py"
        file_b = src_dir / "b.py"
        file_a.write_text("def fn_a(): pass\n", encoding="utf-8")
        file_b.write_text("def fn_b(): pass\n", encoding="utf-8")

        # Passagem separada por espaço
        user_msg, sys_prompt = handle_review("/review src/a.py src/b.py")
        assert not mock_checkbox.called
        assert user_msg == "/review src/a.py, src/b.py"
        assert "--- Arquivo: src/a.py ---" in sys_prompt
        assert "--- Arquivo: src/b.py ---" in sys_prompt
        assert "1: def fn_a(): pass" in sys_prompt
        assert "1: def fn_b(): pass" in sys_prompt

        # Passagem separada por vírgula
        user_msg2, sys_prompt2 = handle_review("/review src/a.py,src/b.py")
        assert user_msg2 == "/review src/a.py, src/b.py"
        assert "--- Arquivo: src/a.py ---" in sys_prompt2
        assert "--- Arquivo: src/b.py ---" in sys_prompt2

    def test_handle_review_cli_nonexistent_files(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()

        # Todos arquivos informados não existem
        user_msg, sys_prompt = handle_review("/review nonexistent1.py nonexistent2.py")
        assert user_msg is None
        assert sys_prompt is None

    def test_handle_review_cli_partial_existing_files(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()
        sync_rules(tmp_path)

        existing = tmp_path / "existing.py"
        existing.write_text("val = 100\n", encoding="utf-8")

        user_msg, sys_prompt = handle_review("/review existing.py missing.py")
        assert user_msg is not None
        assert sys_prompt is not None
        assert "--- Arquivo: existing.py ---" in sys_prompt
        assert "--- Arquivo: missing.py ---" not in sys_prompt


class TestAntiPatternDetectionAndQuality:
    """Validação da detecção de anti-patterns e qualidade do relatório (Teste 5.3)."""

    def test_bad_god_class_signals_and_rules_retrieval(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()
        sync_rules(tmp_path)

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        god_class_file = src_dir / "bad_god_class.py"
        god_class_code = (
            "class OrderManager:\n"
            "    '''God class com múltiplos acoplamentos e sem abstrações.'''\n"
            "    def __init__(self):\n"
            "        self.db = 'mysql://localhost'\n"
            "        self.smtp = 'smtp.mail.com'\n\n"
            "    def save_to_db(self, order):\n"
            "        pass\n\n"
            "    def send_confirmation_email(self, user):\n"
            "        pass\n\n"
            "    def calculate_complex_discount(self, order):\n"
            "        pass\n\n"
            "    def generate_pdf_invoice(self, order):\n"
            "        pass\n"
        )
        god_class_file.write_text(god_class_code, encoding="utf-8")

        # 1. Valida extração de sinais
        signals = extract_code_signals(god_class_code)
        assert "OrderManager" in signals

        # 2. Executa handle_review
        user_msg, sys_prompt = handle_review("/review src/bad_god_class.py")
        assert user_msg == "/review src/bad_god_class.py"

        # 3. Valida se o RAG recuperou regras relevantes (SOLID ou GOD CLASS)
        assert "=== REGRA:" in sys_prompt
        assert any(rule in sys_prompt for rule in ["GOD CLASS", "SOLID", "CLEAN ARCHITECTURE"])

        # 4. Valida se o prompt exige estritamente a estrutura definida no critério de sucesso
        assert "## Veredito" in sys_prompt
        assert "## Problemas" in sys_prompt
        assert "### <NÍVEL DE GRAVIDADE> <Nome do Problema>" in sys_prompt
        assert "- **Arquivo:** <nome_do_arquivo>:L<linha>" in sys_prompt
        assert "- **Regra Violada:** <Nome da regra>" in sys_prompt
        assert "- **Problema:** <Descrição do problema>" in sys_prompt
        assert "- **Correção:** <Sugestão de correção>" in sys_prompt

    def test_strict_report_format_conformance(self):
        """Valida se uma resposta típica de LLM adere exatamente ao schema esperado pelo teste 5.3."""
        sample_llm_response = (
            "## Veredito\n"
            "O arquivo `src/bad_god_class.py` viola os princípios de responsabilidade única (SRP) "
            "e alta coesão, acumulando funções de persistência, notificação e formatação.\n\n"
            "## Problemas\n\n"
            "### ALTA Violação de Responsabilidade Única (God Class)\n"
            "- **Arquivo:** src/bad_god_class.py:L1-L20\n"
            "- **Regra Violada:** GOD CLASS\n"
            "- **Problema:** A classe OrderManager concentra infraestrutura (db, smtp) e regras de negócio.\n"
            "- **Correção:** Separar em repositório (OrderRepository), serviço de email (EmailNotifier) e cálculo.\n\n"
            "### MÉDIA Acoplamento com Infraestrutura Direta\n"
            "- **Arquivo:** src/bad_god_class.py:L3-L5\n"
            "- **Regra Violada:** CLEAN ARCHITECTURE\n"
            "- **Problema:** Strings de conexão e servidor SMTP instanciados diretamente na entidade/gerenciador.\n"
            "- **Correção:** Injetar dependências via construtor por meio de interfaces.\n"
        )

        assert "## Veredito" in sample_llm_response
        assert "## Problemas" in sample_llm_response

        # Regex para validar cada problema
        problem_pattern = re.compile(
            r"###\s+(ALTA|MÉDIA|BAIXA)\s+(.+)\n"
            r"-\s+\*\*Arquivo:\*\*\s+([^\n]+)\n"
            r"-\s+\*\*Regra Violada:\*\*\s+([^\n]+)\n"
            r"-\s+\*\*Problema:\*\*\s+([^\n]+)\n"
            r"-\s+\*\*Correção:\*\*\s+([^\n]+)",
            re.MULTILINE,
        )
        matches = problem_pattern.findall(sample_llm_response)
        assert len(matches) == 2
        assert matches[0][0] == "ALTA"
        assert "src/bad_god_class.py" in matches[0][2]
        assert matches[0][3] == "GOD CLASS"


class TestDeepReview:
    """Validação do comando /deep-review (Curinga da Nuvem) (Teste 5.4)."""

    def test_deep_review_empty_workspace(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()

        user_msg, sys_prompt = handle_deep_review("/deep-review")
        assert user_msg is None
        assert sys_prompt is None

    @patch("goodfella.cli.commands.Confirm.ask")
    def test_deep_review_user_cancels(self, mock_confirm, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()

        (tmp_path / "main.py").write_text("print('test')", encoding="utf-8")

        mock_confirm.return_value = False  # Usuário digita 'n'
        user_msg, sys_prompt = handle_deep_review("/deep-review")

        assert mock_confirm.called
        assert user_msg is None
        assert sys_prompt is None

    @patch("goodfella.cli.commands.Confirm.ask")
    def test_deep_review_user_confirms(self, mock_confirm, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "app.py").write_text("def run():\n    return True\n", encoding="utf-8")
        (src_dir / "config.py").write_text("DEBUG = True\n", encoding="utf-8")

        # Arquivo no .gitignore (não deve ser incluído no deep review)
        (tmp_path / "ignored.py").write_text("SECRET = 'abc'", encoding="utf-8")
        (tmp_path / ".gitignore").write_text("ignored.py\n", encoding="utf-8")

        # Regra local criada
        rules_dir = tmp_path / GOODFELLA_DIR / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        (rules_dir / "custom_rule.md").write_text(
            "# Custom Rule\nSeguir princípios de código limpo.\n", encoding="utf-8"
        )

        mock_confirm.return_value = True  # Usuário digita 'y'
        user_msg, sys_prompt = handle_deep_review("/deep-review")

        assert user_msg == "/deep-review"
        assert sys_prompt is not None

        # Valida flag is_deep (cross-file e acesso integral)
        assert "Você tem acesso ao código-fonte INTEGRAL do projeto." in sys_prompt
        assert "cross-file" in sys_prompt

        # Valida inclusão dos arquivos válidos numerados
        assert "--- Arquivo: src/app.py ---" in sys_prompt
        assert "1: def run():" in sys_prompt
        assert "--- Arquivo: src/config.py ---" in sys_prompt
        assert "1: DEBUG = True" in sys_prompt

        # Valida respeito ao .gitignore
        assert "ignored.py" not in sys_prompt

        # Valida inclusão das regras bypass RAG (lidas do disco)
        assert "=== REGRA: CUSTOM RULE ===" in sys_prompt
        assert "Seguir princípios de código limpo." in sys_prompt

    @patch("goodfella.cli.commands.Confirm.ask")
    @patch("goodfella.cli.commands.console.print")
    def test_deep_review_panel_output_content(
        self, mock_console_print, mock_confirm, tmp_path: Path, monkeypatch
    ):
        """Valida se o painel exibido no deep-review contém contagem, tokens e alertas de custo."""
        monkeypatch.chdir(tmp_path)
        init_environment()

        (tmp_path / "index.py").write_text("print('hello world')", encoding="utf-8")

        mock_confirm.return_value = False
        handle_deep_review("/deep-review")

        # Concatena todas as chamadas de console.print
        printed_messages = " ".join([str(call.args[0]) for call in mock_console_print.call_args_list if call.args])

        assert "arquivos e ~" in printed_messages
        assert "tokens" in printed_messages
        assert "altos custos" in printed_messages
        assert "Prompt Caching" in printed_messages


class TestReviewDeduplicationAndChatIsolation:
    """Validação de deduplicação de regras no RAG e isolamento de histórico no chat."""

    @patch("goodfella.cli.commands.get_collection")
    @patch("goodfella.cli.commands.show_timer_spinner")
    def test_rule_deduplication_by_file_path(
        self, mock_spinner, mock_get_collection, tmp_path: Path, monkeypatch
    ):
        """Garante que múltiplos chunks do mesmo arquivo de regra não dupliquem o contexto."""
        monkeypatch.chdir(tmp_path)
        init_environment()

        rule_file = tmp_path / "solid.md"
        rule_file.write_text("# SOLID\nPrincípios de responsabilidade única.\n", encoding="utf-8")

        test_file = tmp_path / "app.py"
        test_file.write_text("class App: pass\n", encoding="utf-8")

        # Mock do Chroma retornando 3 chunks do mesmo arquivo
        mock_col = MagicMock()
        mock_col.query.return_value = {
            "metadatas": [
                [
                    {"file_path": str(rule_file)},
                    {"file_path": str(rule_file)},
                    {"file_path": str(rule_file)},
                ]
            ]
        }
        mock_get_collection.return_value = mock_col

        mock_timer_renderable = MagicMock()
        mock_timer_renderable.start_time = 0.0
        mock_spinner.return_value.__enter__.return_value = mock_timer_renderable

        user_msg, sys_prompt = handle_review("/review app.py")

        # O bloco === REGRA: SOLID === deve ocorrer EXATAMENTE 1 vez
        assert sys_prompt.count("=== REGRA: SOLID ===") == 1
        assert sys_prompt.count("=== FIM REGRA: SOLID ===") == 1
        assert mock_spinner.called
        assert "Buscando regras no Banco Vetorial..." in mock_spinner.call_args[0][0]

    def test_review_chat_history_isolation(self, tmp_path: Path, monkeypatch):
        """Valida que comandos de review não poluem o chat_history.json com system prompts gigantes."""
        from goodfella.llm.memory import save_message, load_history
        monkeypatch.chdir(tmp_path)
        init_environment()

        user_input = "/review src/bad_god_class.py"
        fake_ai_review = "## Veredito\nProblemas encontrados.\n"

        # Simula fluxo do app.py ao salvar no histórico
        save_message("user", user_input)
        save_message("ai", fake_ai_review)

        history = load_history()
        assert len(history) == 2
        assert history[0].content == user_input
        assert history[1].content == fake_ai_review

        # Confirma que o arquivo JSON contém apenas a mensagem enxuta
        history_file = tmp_path / GOODFELLA_DIR / "chat_history.json"
        assert history_file.exists()
        raw_json = history_file.read_text(encoding="utf-8")
        assert "ZERO ALUCINAÇÃO" not in raw_json
        assert "=== REGRA:" not in raw_json

