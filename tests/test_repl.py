"""Testes de REPL, UX e Gerenciamento de Memória (Bateria 6)."""

import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from goodfella.core.env import init_environment, GOODFELLA_DIR
from goodfella.llm.memory import (
    MAX_HISTORY_MESSAGES,
    get_history_path,
    load_history,
    clear_history,
    save_message,
)
from goodfella.cli.ui import console, custom_theme, show_spinner, show_timer_spinner
from goodfella.cli.app import (
    extract_chunk_text,
    print_welcome,
    main,
)
from goodfella.cli.commands import handle_help


class TestChatHistoryMemory:
    """Validação das operações de persistência e gerenciamento de histórico."""

    def test_get_history_path_resolution(self, tmp_path: Path):
        # 1. Caminho padrão baseado no Path.cwd()
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            default_path = get_history_path()
            assert default_path == tmp_path / GOODFELLA_DIR / "chat_history.json"

        # 2. Caminho customizado explicitamente fornecido
        custom_dir = tmp_path / "custom_workspace"
        custom_path = get_history_path(custom_dir)
        assert custom_path == custom_dir / GOODFELLA_DIR / "chat_history.json"

    def test_save_message_creates_file_and_directory(self, tmp_path: Path):
        history_file = tmp_path / GOODFELLA_DIR / "chat_history.json"
        assert not history_file.exists()

        save_message("user", "Olá Goodfella!", workspace_dir=tmp_path)

        assert history_file.exists()
        data = json.loads(history_file.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0] == {"role": "user", "content": "Olá Goodfella!"}

    def test_save_message_appends_sequential_messages(self, tmp_path: Path):
        save_message("user", "Pergunta 1", workspace_dir=tmp_path)
        save_message("ai", "Resposta 1", workspace_dir=tmp_path)
        save_message("user", "Pergunta 2", workspace_dir=tmp_path)
        save_message("ai", "Resposta 2", workspace_dir=tmp_path)

        history_file = tmp_path / GOODFELLA_DIR / "chat_history.json"
        data = json.loads(history_file.read_text(encoding="utf-8"))
        assert len(data) == 4
        assert [m["role"] for m in data] == ["user", "ai", "user", "ai"]
        assert [m["content"] for m in data] == [
            "Pergunta 1",
            "Resposta 1",
            "Pergunta 2",
            "Resposta 2",
        ]

    def test_save_message_recovers_from_corrupted_json(self, tmp_path: Path):
        history_file = tmp_path / GOODFELLA_DIR / "chat_history.json"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        history_file.write_text("{corrupted: json string...", encoding="utf-8")

        # Não deve lançar exceção e deve sobrescrever com novo histórico válido
        save_message("user", "Recuperação", workspace_dir=tmp_path)

        data = json.loads(history_file.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0] == {"role": "user", "content": "Recuperação"}

    def test_load_history_when_file_not_found(self, tmp_path: Path):
        messages = load_history(workspace_dir=tmp_path)
        assert messages == []

    def test_load_history_handles_corrupted_json(self, tmp_path: Path):
        history_file = tmp_path / GOODFELLA_DIR / "chat_history.json"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        history_file.write_text("invalid json [}{", encoding="utf-8")

        messages = load_history(workspace_dir=tmp_path)
        assert messages == []

    def test_load_history_converts_roles_to_langchain_messages(self, tmp_path: Path):
        save_message("user", "Como implementar SRP?", workspace_dir=tmp_path)
        save_message("ai", "Crie classes focadas em uma única responsabilidade.", workspace_dir=tmp_path)
        save_message("other", "Ignorar papel desconhecido", workspace_dir=tmp_path)

        messages = load_history(workspace_dir=tmp_path)
        assert len(messages) == 2

        assert isinstance(messages[0], HumanMessage)
        assert messages[0].content == "Como implementar SRP?"

        assert isinstance(messages[1], AIMessage)
        assert messages[1].content == "Crie classes focadas em uma única responsabilidade."

    def test_clear_history_removes_file(self, tmp_path: Path):
        save_message("user", "Teste clear", workspace_dir=tmp_path)
        history_file = tmp_path / GOODFELLA_DIR / "chat_history.json"
        assert history_file.exists()

        clear_history(workspace_dir=tmp_path)
        assert not history_file.exists()
        assert load_history(workspace_dir=tmp_path) == []

    def test_clear_history_safe_when_file_does_not_exist(self, tmp_path: Path):
        history_file = tmp_path / GOODFELLA_DIR / "chat_history.json"
        assert not history_file.exists()

        # Deve executar sem levantar nenhuma exceção
        clear_history(workspace_dir=tmp_path)


class TestMemorySlidingWindow:
    """Validação da janela deslizante de memória (Teste 6.3 - Limite de 20 mensagens)."""

    def test_max_history_constant(self):
        assert MAX_HISTORY_MESSAGES == 20

    def test_load_history_sliding_window_under_limit(self, tmp_path: Path):
        for i in range(10):
            save_message("user", f"Msg {i}", workspace_dir=tmp_path)

        messages = load_history(workspace_dir=tmp_path)
        assert len(messages) == 10
        assert messages[0].content == "Msg 0"
        assert messages[-1].content == "Msg 9"

    def test_load_history_sliding_window_at_limit(self, tmp_path: Path):
        for i in range(20):
            save_message("user", f"Msg {i}", workspace_dir=tmp_path)

        messages = load_history(workspace_dir=tmp_path)
        assert len(messages) == 20
        assert messages[0].content == "Msg 0"
        assert messages[-1].content == "Msg 19"

    def test_load_history_sliding_window_over_limit_discards_oldest(self, tmp_path: Path):
        # Salva 25 mensagens curtas
        for i in range(25):
            role = "user" if i % 2 == 0 else "ai"
            save_message(role, f"Mensagem {i}", workspace_dir=tmp_path)

        # O JSON físico retém todas as mensagens salvas
        history_file = tmp_path / GOODFELLA_DIR / "chat_history.json"
        raw_data = json.loads(history_file.read_text(encoding="utf-8"))
        assert len(raw_data) == 25

        # Mas load_history() deve truncar mantendo estritamente as 20 mais recentes
        messages = load_history(workspace_dir=tmp_path)
        assert len(messages) == 20

        # As mensagens de 0 a 4 foram descartadas; as mensagens de 5 a 24 foram mantidas
        assert messages[0].content == "Mensagem 5"
        assert messages[-1].content == "Mensagem 24"


class TestMemoryIsolation:
    """Validação do isolamento de memória (Teste 6.2 - Proteção do chat_history.json)."""

    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.get_collection")
    @patch("goodfella.cli.app.get_client")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_rag_context_and_system_prompt_never_saved_to_history(
        self,
        mock_pipeline,
        mock_sync,
        mock_init,
        mock_get_client,
        mock_get_col,
        mock_get_llm,
        tmp_path: Path,
        monkeypatch,
    ):
        """Fragmentos de código do RAG e system prompts NUNCA devem poluir o chat_history.json."""
        monkeypatch.chdir(tmp_path)
        init_environment()

        # Simula retorno do RAG com fragmento extenso de código
        huge_code_snippet = (
            "class OrderManager:\n"
            "    def process(self):\n"
            + "\n".join([f"        step_{i}()" for i in range(50)])
        )
        mock_col = MagicMock()
        mock_col.query.return_value = {"documents": [[huge_code_snippet]]}
        mock_get_col.return_value = mock_col

        # Simula resposta do LLM via streaming
        mock_llm = MagicMock()
        chunk1 = MagicMock()
        chunk1.content = "A classe OrderManager "
        chunk2 = MagicMock()
        chunk2.content = "está definida em src/order.py."
        mock_llm.stream.return_value = iter([chunk1, chunk2])
        mock_get_llm.return_value = mock_llm

        inputs = ["Onde no meu projeto está definida a classe OrderManager?", "/exit"]
        with patch.object(console, "input", side_effect=inputs):
            main()

        # Verifica o arquivo chat_history.json gerado
        history_file = tmp_path / GOODFELLA_DIR / "chat_history.json"
        assert history_file.exists()

        data = json.loads(history_file.read_text(encoding="utf-8"))
        assert len(data) == 2

        # 1. Pergunta do usuário (limpa, sem contexto RAG)
        assert data[0]["role"] == "user"
        assert data[0]["content"] == "Onde no meu projeto está definida a classe OrderManager?"
        assert "CONTEXTO DO PROJETO" not in data[0]["content"]
        assert "step_40" not in data[0]["content"]

        # 2. Resposta da IA (apenas o texto gerado)
        assert data[1]["role"] == "ai"
        assert data[1]["content"] == "A classe OrderManager está definida em src/order.py."
        assert "CONTEXTO DO PROJETO" not in data[1]["content"]

    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.handle_review")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_review_system_prompt_never_saved_to_history(
        self,
        mock_pipeline,
        mock_sync,
        mock_init,
        mock_review,
        mock_get_llm,
        tmp_path: Path,
        monkeypatch,
    ):
        """Ao executar /review, o prompt de review e regras não devem ser salvos no chat_history.json."""
        monkeypatch.chdir(tmp_path)
        init_environment()

        review_sys_prompt = "Você é um Code Reviewer estrito. Siga as regras arquiteturais."
        review_user_msg = "Revisar arquivo src/service.py com o código:\n1: class Service: pass"
        mock_review.return_value = (review_user_msg, review_sys_prompt)

        mock_llm = MagicMock()
        chunk = MagicMock()
        chunk.content = "## Veredito\nAprovado com ressalvas."
        mock_llm.stream.return_value = iter([chunk])
        mock_get_llm.return_value = mock_llm

        inputs = ["/review src/service.py", "/exit"]
        with patch.object(console, "input", side_effect=inputs):
            main()

        history_file = tmp_path / GOODFELLA_DIR / "chat_history.json"
        data = json.loads(history_file.read_text(encoding="utf-8"))
        assert len(data) == 2

        # Verifica que o system prompt estrito do review não foi salvo no JSON
        raw_json_text = history_file.read_text(encoding="utf-8")
        assert review_sys_prompt not in raw_json_text
        assert "Você é um Code Reviewer estrito" not in raw_json_text


class TestUIComponents:
    """Validação de componentes visuais, spinners, temas e utilitários de UI."""

    def test_custom_theme_definition(self):
        assert "info" in custom_theme.styles
        assert "warning" in custom_theme.styles
        assert "danger" in custom_theme.styles
        assert "success" in custom_theme.styles

    def test_show_spinner_context_manager(self):
        with patch.object(console, "status") as mock_status:
            mock_status.return_value.__enter__ = MagicMock()
            mock_status.return_value.__exit__ = MagicMock()

            with show_spinner("Sincronizando regras..."):
                pass

            mock_status.assert_called_once()
            args, kwargs = mock_status.call_args
            assert "Sincronizando regras..." in args[0]
            assert kwargs.get("spinner") == "dots"

    def test_show_timer_spinner_records_start_time(self):
        with patch.object(console, "status") as mock_status:
            mock_status.return_value.__enter__ = MagicMock()
            mock_status.return_value.__exit__ = MagicMock()

            t0 = time.time()
            with show_timer_spinner("Buscando regras no RAG...") as renderable:
                assert renderable.start_time >= t0
                assert renderable.start_time <= time.time()

            mock_status.assert_called_once()
            args, kwargs = mock_status.call_args
            assert "Buscando regras no RAG..." in args[0]
            assert kwargs.get("spinner") == "dots"

    def test_extract_chunk_text_string(self):
        assert extract_chunk_text("Olá mundo") == "Olá mundo"

    def test_extract_chunk_text_list_of_strings(self):
        chunks = ["Texto ", "dividido ", "em partes."]
        assert extract_chunk_text(chunks) == "Texto dividido em partes."

    def test_extract_chunk_text_list_of_dicts(self):
        chunks = [{"text": "Token A "}, {"text": "Token B"}]
        assert extract_chunk_text(chunks) == "Token A Token B"

    def test_extract_chunk_text_fallback_none_and_other_types(self):
        assert extract_chunk_text(None) == ""
        assert extract_chunk_text(12345) == "12345"

    @patch("goodfella.cli.app.load_config")
    def test_print_welcome_ollama_provider(self, mock_load_config):
        mock_load_config.return_value = {"provider": "ollama"}
        with patch.object(console, "print") as mock_print:
            print_welcome()
            printed_texts = [str(call.args[0]) for call in mock_print.call_args_list if call.args]
            full_output = " ".join(printed_texts)
            assert "Goodfella AI Pair Programmer" in full_output
            assert "ollama serve" in full_output
            assert "GPU" in full_output

    @patch("goodfella.cli.app.load_config")
    def test_print_welcome_cloud_provider(self, mock_load_config):
        mock_load_config.return_value = {"provider": "openai"}
        with patch.object(console, "print") as mock_print:
            print_welcome()
            printed_texts = [str(call.args[0]) for call in mock_print.call_args_list if call.args]
            full_output = " ".join(printed_texts)
            assert "Goodfella AI Pair Programmer" in full_output
            assert "Provedor de Nuvem Ativo: Openai" in full_output


class TestSessionCommands:
    """Validação dos comandos utilitários de sessão (/clear, /reset, /help, /quit, /exit)."""

    def test_handle_help_prints_all_commands(self):
        with patch.object(console, "print") as mock_print:
            handle_help()
            printed_texts = [str(call.args[0]) for call in mock_print.call_args_list if call.args]
            full_output = " ".join(printed_texts)

            # Valida presença de todos os comandos documentados
            expected_commands = [
                "/help",
                "/setup",
                "/status",
                "/refresh",
                "/rebuild",
                "/review",
                "/deep-review",
                "/rule add",
                "/clear",
                "/reset",
                "/exit ou /quit",
            ]
            for cmd in expected_commands:
                assert cmd in full_output

    @patch("goodfella.cli.app.handle_help")
    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_repl_executes_help_command(
        self, mock_pipe, mock_sync, mock_init, mock_llm, mock_help, tmp_path: Path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        inputs = ["/help", "/exit"]
        with patch.object(console, "input", side_effect=inputs):
            main()
        mock_help.assert_called_once()

    @patch("goodfella.cli.app.print_welcome")
    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_repl_executes_clear_command(
        self, mock_pipe, mock_sync, mock_init, mock_llm, mock_welcome, tmp_path: Path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        inputs = ["/clear", "/exit"]
        with patch.object(console, "clear") as mock_clear, patch.object(console, "input", side_effect=inputs):
            main()
        mock_clear.assert_called_once()
        # print_welcome é chamado no início da CLI e novamente no /clear
        assert mock_welcome.call_count == 2

    @patch("goodfella.cli.app.clear_history")
    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_repl_executes_reset_command(
        self, mock_pipe, mock_sync, mock_init, mock_llm, mock_clear_hist, tmp_path: Path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        inputs = ["/reset", "/exit"]
        with patch.object(console, "input", side_effect=inputs):
            main()
        mock_clear_hist.assert_called_once()

    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_repl_clean_exit_with_quit_and_exit(
        self, mock_pipe, mock_sync, mock_init, mock_llm, tmp_path: Path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)

        # 1. Encerramento com /exit
        with patch.object(console, "input", side_effect=["/exit"]):
            main()

        # 2. Encerramento com /quit
        with patch.object(console, "input", side_effect=["/quit"]):
            main()

        # 3. Encerramento com espaços e maiúsculas
        with patch.object(console, "input", side_effect=["  /QUIT  "]):
            main()

    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_repl_warns_on_unknown_slash_command(
        self, mock_pipe, mock_sync, mock_init, mock_get_llm, tmp_path: Path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        inputs = ["/desconhecido", "/rule", "/", "/exit"]
        with patch.object(console, "input", side_effect=inputs), patch.object(console, "print") as mock_print:
            main()

        printed_texts = [str(call.args[0]) for call in mock_print.call_args_list if call.args]
        full_output = " ".join(printed_texts)

        assert "Comando não reconhecido" in full_output
        assert "/help" in full_output
        assert "comandos possíveis" in full_output

        # O LLM nunca deve ser acionado para comandos desconhecidos
        mock_llm.stream.assert_not_called()


class TestFreeChatDynamicRAG:
    """Validação de conversação livre com enriquecimento dinâmico de RAG (Teste 6.1)."""

    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.get_collection")
    @patch("goodfella.cli.app.get_client")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_free_chat_enriches_system_prompt_with_rag_snippet(
        self,
        mock_pipe,
        mock_sync,
        mock_init,
        mock_client,
        mock_col,
        mock_get_llm,
        tmp_path: Path,
        monkeypatch,
    ):
        monkeypatch.chdir(tmp_path)
        init_environment()

        # RAG encontra código relevante
        rag_doc = "class PaymentGateway:\n    def charge(self, card, amount): pass"
        mock_collection = MagicMock()
        mock_collection.query.return_value = {"documents": [[rag_doc]]}
        mock_col.return_value = mock_collection

        # LLM Mock
        mock_llm = MagicMock()
        mock_chunk = MagicMock()
        mock_chunk.content = "A classe PaymentGateway gerencia as cobranças."
        mock_llm.stream.return_value = iter([mock_chunk])
        mock_get_llm.return_value = mock_llm

        inputs = ["Como funciona a integração de pagamentos?", "/exit"]
        with patch.object(console, "input", side_effect=inputs):
            main()

        # Verifica chamada ao RAG
        mock_collection.query.assert_called_once_with(
            query_texts=["Como funciona a integração de pagamentos?"],
            n_results=3,
        )

        # Verifica mensagens enviadas ao LLM
        mock_llm.stream.assert_called_once()
        messages = mock_llm.stream.call_args[0][0]

        system_msg = messages[0]
        human_msg = messages[-1]

        assert isinstance(system_msg, SystemMessage)
        assert "CONTEXTO DO PROJETO (fragmentos relevantes recuperados via RAG):" in system_msg.content
        assert "class PaymentGateway" in system_msg.content

        assert isinstance(human_msg, HumanMessage)
        assert human_msg.content == "Como funciona a integração de pagamentos?"

    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.get_collection")
    @patch("goodfella.cli.app.get_client")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_free_chat_without_rag_results_uses_default_prompt(
        self,
        mock_pipe,
        mock_sync,
        mock_init,
        mock_client,
        mock_col,
        mock_get_llm,
        tmp_path: Path,
        monkeypatch,
    ):
        monkeypatch.chdir(tmp_path)
        init_environment()

        # RAG retorna nenhum documento
        mock_collection = MagicMock()
        mock_collection.query.return_value = {"documents": [[]]}
        mock_col.return_value = mock_collection

        mock_llm = MagicMock()
        mock_chunk = MagicMock()
        mock_chunk.content = "Resposta sem contexto prévio."
        mock_llm.stream.return_value = iter([mock_chunk])
        mock_get_llm.return_value = mock_llm

        inputs = ["O que é TDD?", "/exit"]
        with patch.object(console, "input", side_effect=inputs):
            main()

        messages = mock_llm.stream.call_args[0][0]
        system_msg = messages[0]
        assert isinstance(system_msg, SystemMessage)
        assert "CONTEXTO DO PROJETO" not in system_msg.content
        assert "Você é o Goodfella, um AI Pair Programmer local-first." in system_msg.content

    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.get_client")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_free_chat_resilient_to_rag_exception(
        self,
        mock_pipe,
        mock_sync,
        mock_init,
        mock_client,
        mock_get_llm,
        tmp_path: Path,
        monkeypatch,
    ):
        monkeypatch.chdir(tmp_path)
        init_environment()

        # Simula erro de conexão ou leitura no ChromaDB
        mock_client.side_effect = RuntimeError("ChromaDB temporarily unavailable")

        mock_llm = MagicMock()
        mock_chunk = MagicMock()
        mock_chunk.content = "Resposta mesmo com falha no RAG."
        mock_llm.stream.return_value = iter([mock_chunk])
        mock_get_llm.return_value = mock_llm

        inputs = ["Pergunta mesmo com falha RAG", "/exit"]
        with patch.object(console, "input", side_effect=inputs):
            main()

        # Chat prossegue normalmente com o prompt básico sem crash
        mock_llm.stream.assert_called_once()
        messages = mock_llm.stream.call_args[0][0]
        system_msg = messages[0]
        assert "CONTEXTO DO PROJETO" not in system_msg.content


class TestREPLErrorHandlingAndStreaming:
    """Validação de resiliência a erros no REPL, streaming e TTFT."""

    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_repl_ollama_offline_connection_refused(
        self, mock_pipe, mock_sync, mock_init, mock_get_llm, tmp_path: Path, monkeypatch
    ):
        """Teste 2.2 / REPL: Falha de conexão amigável sem derrubar o REPL."""
        monkeypatch.chdir(tmp_path)

        mock_llm = MagicMock()
        mock_llm.stream.side_effect = ConnectionRefusedError("[Errno 111] Connection refused")
        mock_get_llm.return_value = mock_llm

        inputs = ["Pergunta com Ollama desligado", "/exit"]
        with patch.object(console, "input", side_effect=inputs), patch.object(console, "print") as mock_print:
            main()

        printed_texts = [str(call.args[0]) for call in mock_print.call_args_list if call.args]
        full_output = " ".join(printed_texts)
        assert "Erro de Conexão: Não foi possível alcançar o provedor local (Ollama)" in full_output
        assert "ollama serve" in full_output

    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_repl_authentication_error_401(
        self, mock_pipe, mock_sync, mock_init, mock_get_llm, tmp_path: Path, monkeypatch
    ):
        """Teste 2.6 / REPL: Tratamento amigável de erro 401."""
        monkeypatch.chdir(tmp_path)

        mock_llm = MagicMock()
        mock_llm.stream.side_effect = Exception("AuthenticationError: 401 Unauthorized api_key invalid")
        mock_get_llm.return_value = mock_llm

        inputs = ["Pergunta com chave inválida", "/exit"]
        with patch.object(console, "input", side_effect=inputs), patch.object(console, "print") as mock_print:
            main()

        printed_texts = [str(call.args[0]) for call in mock_print.call_args_list if call.args]
        full_output = " ".join(printed_texts)
        assert "Erro de Autenticação: A chave de API fornecida é inválida ou expirou" in full_output
        assert "/setup" in full_output

    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_repl_rate_limit_error_429(
        self, mock_pipe, mock_sync, mock_init, mock_get_llm, tmp_path: Path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)

        mock_llm = MagicMock()
        mock_llm.stream.side_effect = Exception("RateLimitError: 429 Too Many Requests, quota exceeded")
        mock_get_llm.return_value = mock_llm

        inputs = ["Pergunta estourando cota", "/exit"]
        with patch.object(console, "input", side_effect=inputs), patch.object(console, "print") as mock_print:
            main()

        printed_texts = [str(call.args[0]) for call in mock_print.call_args_list if call.args]
        full_output = " ".join(printed_texts)
        assert "Erro de Cota (Rate Limit)" in full_output

    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_repl_model_not_found_error_404(
        self, mock_pipe, mock_sync, mock_init, mock_get_llm, tmp_path: Path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)

        mock_llm = MagicMock()
        mock_llm.stream.side_effect = Exception("NotFoundError: 404 model not found")
        mock_get_llm.return_value = mock_llm

        inputs = ["Pergunta para modelo que não existe", "/exit"]
        with patch.object(console, "input", side_effect=inputs), patch.object(console, "print") as mock_print:
            main()

        printed_texts = [str(call.args[0]) for call in mock_print.call_args_list if call.args]
        full_output = " ".join(printed_texts)
        assert "Erro de Modelo: O modelo especificado não foi encontrado no provedor" in full_output

    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_repl_generic_error_recovery(
        self, mock_pipe, mock_sync, mock_init, mock_get_llm, tmp_path: Path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)

        mock_llm = MagicMock()
        mock_llm.stream.side_effect = RuntimeError("Falha de rede inesperada")
        mock_get_llm.return_value = mock_llm

        inputs = ["Pergunta erro genérico", "/exit"]
        with patch.object(console, "input", side_effect=inputs), patch.object(console, "print") as mock_print:
            main()

        printed_texts = [str(call.args[0]) for call in mock_print.call_args_list if call.args]
        full_output = " ".join(printed_texts)
        assert "Erro inesperado do LLM: Falha de rede inesperada" in full_output

    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_repl_skips_empty_input_and_handles_signals(
        self, mock_pipe, mock_sync, mock_init, mock_llm, tmp_path: Path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)

        # 1. Inputs vazios continuam no loop sem invocar LLM
        inputs = ["   ", "", "\t", "/exit"]
        with patch.object(console, "input", side_effect=inputs):
            main()

        # 2. KeyboardInterrupt encerra graciosamente o REPL
        with patch.object(console, "input", side_effect=KeyboardInterrupt):
            main()

        # 3. EOFError encerra graciosamente o REPL
        with patch.object(console, "input", side_effect=EOFError):
            main()

    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_repl_streaming_telemetry_output(
        self, mock_pipe, mock_sync, mock_init, mock_get_llm, tmp_path: Path, monkeypatch
    ):
        """Valida que o streaming emite métricas de conclusão, tempo e velocidade."""
        monkeypatch.chdir(tmp_path)

        mock_llm = MagicMock()
        chunk1 = MagicMock()
        chunk1.content = "Primeira parte "
        chunk2 = MagicMock()
        chunk2.content = "segunda parte."
        mock_llm.stream.return_value = iter([chunk1, chunk2])
        mock_get_llm.return_value = mock_llm

        inputs = ["Conte-me algo", "/exit"]
        with patch.object(console, "input", side_effect=inputs), patch.object(console, "print") as mock_print:
            main()

        printed_texts = [str(call.args[0]) for call in mock_print.call_args_list if call.args]
        full_output = " ".join(printed_texts)
        assert "✓ Concluído em" in full_output
        assert "Preparo:" in full_output
        assert "tokens" in full_output
        assert "Vel:" in full_output
        assert "t/s" in full_output

    @patch("goodfella.cli.app.get_llm")
    @patch("goodfella.cli.app.init_environment")
    @patch("goodfella.cli.app.sync_rules")
    @patch("goodfella.cli.app.run_indexing_pipeline")
    def test_repl_handles_empty_stream_gracefully(
        self, mock_pipe, mock_sync, mock_init, mock_get_llm, tmp_path: Path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)

        mock_llm = MagicMock()
        mock_llm.stream.return_value = iter([])  # Stream encerra imediatamente (StopIteration)
        mock_get_llm.return_value = mock_llm

        inputs = ["Stream vazio", "/exit"]
        with patch.object(console, "input", side_effect=inputs):
            main()
