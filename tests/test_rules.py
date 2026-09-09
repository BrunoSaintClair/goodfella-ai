"""Testes de Gestão de Regras de Arquitetura e Anti-Patterns (Bateria 4)."""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from goodfella.core.env import init_environment, GOODFELLA_DIR
from goodfella.knowledge.rules import get_rules_directories, sync_rules
from goodfella.rag.db import get_client, get_collection
from goodfella.cli.commands import handle_rule_add


class TestRuleDirectories:
    """Validação de resolução de diretórios de regras."""

    def test_get_rules_directories_structure(self, tmp_path: Path):
        dirs = get_rules_directories(tmp_path)
        assert len(dirs) == 3

        builtin_dir, global_dir, local_dir = dirs
        assert builtin_dir.exists()
        assert (builtin_dir / "rules").exists()
        assert (builtin_dir / "anti_patterns").exists()

        assert global_dir == Path.home() / ".goodfella_config" / "rules"
        assert local_dir == tmp_path / GOODFELLA_DIR / "rules"


class TestSyncRulesBuiltin:
    """Validação de indexação e recuperação das regras nativas do pacote."""

    def test_builtin_rules_and_antipatterns_indexed(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()

        indexed_count = sync_rules(tmp_path)
        assert indexed_count >= 7  # 4 rules + 3 anti-patterns

        client = get_client()
        col = get_collection(client)
        assert col.count() >= 7

        # Verifica se todos os metadados têm is_rule: True
        rules_data = col.get(where={"is_rule": True})
        assert len(rules_data["ids"]) >= 7
        for rid in rules_data["ids"]:
            assert rid.startswith("RULE::")

        # Busca semântica por SOLID
        res_solid = col.query(query_texts=["Single Responsibility Principle responsabilidade única"], n_results=1, where={"is_rule": True})
        assert len(res_solid["documents"][0]) > 0
        assert "SOLID" in res_solid["documents"][0][0] or "responsabilidade" in res_solid["documents"][0][0].lower()

        # Busca semântica por God Class
        res_god = col.query(query_texts=["God Class classe Deus muitos métodos acoplamento"], n_results=1, where={"is_rule": True})
        assert len(res_god["documents"][0]) > 0
        assert "God Class" in res_god["documents"][0][0] or "responsabilidade" in res_god["documents"][0][0].lower()


class TestLocalRuleAddition:
    """Validação de adição de regra local (Teste 4.1)."""

    def test_local_rule_saved_and_synced(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()

        local_rules_dir = tmp_path / GOODFELLA_DIR / "rules"
        local_rules_dir.mkdir(parents=True, exist_ok=True)

        rule_file = local_rules_dir / "evitar_side_effects.md"
        rule_file.write_text(
            "# Evitar Side Effects\n"
            "Funções de consulta não devem alterar o estado de entidades do domínio (CQS).\n"
            "Queries devem ser puras e idempotentes.\n",
            encoding="utf-8"
        )

        sync_rules(tmp_path)

        client = get_client()
        col = get_collection(client)

        res = col.query(query_texts=["CQS funções de consulta side effects idempotente"], n_results=1, where={"is_rule": True})
        assert len(res["documents"][0]) > 0
        assert "Evitar Side Effects" in res["documents"][0][0]
        assert str(rule_file.absolute()) in res["metadatas"][0][0]["file_path"]


class TestAntiPatternImport:
    """Validação de importação de Anti-Pattern (Teste 4.2)."""

    def test_antipattern_import_and_sync(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()

        # Simula arquivo externo para importação
        external_file = tmp_path / "anti_pattern_anemic.md"
        external_file.write_text(
            "# Modelo Anêmico (Anemic Domain Model)\n"
            "Entidades de domínio que contêm apenas getters e setters sem regras de negócio.\n"
            "A lógica fica espalhada em classes de serviço procedurais.\n",
            encoding="utf-8"
        )

        # Destino de importação de anti-pattern local
        dest_dir = tmp_path / GOODFELLA_DIR / "rules" / "anti_patterns"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / "anti_pattern_anemic.md"
        dest_file.write_text(external_file.read_text(encoding="utf-8"), encoding="utf-8")

        sync_rules(tmp_path)

        client = get_client()
        col = get_collection(client)

        res = col.query(query_texts=["modelo anêmico getters setters serviço procedural"], n_results=1, where={"is_rule": True})
        assert len(res["documents"][0]) > 0
        assert "Modelo Anêmico" in res["documents"][0][0]
        assert str(dest_file.absolute()) in res["metadatas"][0][0]["file_path"]


class TestGlobalVsLocalRules:
    """Validação de regras Globais vs Locais e isolamento multi-projeto (Teste 4.3)."""

    def test_global_rules_accessible_across_projects(self, tmp_path: Path, monkeypatch):
        # 1. Configura diretório global mockado
        mock_home = tmp_path / "home"
        global_rules_dir = mock_home / ".goodfella_config" / "rules"
        global_rules_dir.mkdir(parents=True, exist_ok=True)

        global_rule = global_rules_dir / "diretriz_seguranca.md"
        global_rule.write_text(
            "# Diretriz Global de Segurança\n"
            "Nunca trafegar senhas em texto puro ou logar tokens de autorização.\n",
            encoding="utf-8"
        )
        monkeypatch.setattr(Path, "home", lambda: mock_home)

        # 2. Projeto A com regra local específica
        proj_a = tmp_path / "projeto_a"
        proj_a.mkdir()
        monkeypatch.chdir(proj_a)
        init_environment()

        local_rule_a = proj_a / GOODFELLA_DIR / "rules" / "regra_exclusiva_a.md"
        local_rule_a.parent.mkdir(parents=True, exist_ok=True)
        local_rule_a.write_text("# Regra Projeto A\nUso obrigatório de FastAPI no backend.\n", encoding="utf-8")

        sync_rules(proj_a)

        client_a = get_client()
        col_a = get_collection(client_a)

        res_a_global = col_a.query(query_texts=["senhas texto puro tokens segurança"], n_results=1, where={"is_rule": True})
        assert "Diretriz Global de Segurança" in res_a_global["documents"][0][0]

        res_a_local = col_a.query(query_texts=["FastAPI backend"], n_results=1, where={"is_rule": True})
        assert "Regra Projeto A" in res_a_local["documents"][0][0]

        # 3. Projeto B (novo diretório): deve ter a regra global, mas NÃO a regra local do Projeto A
        proj_b = tmp_path / "projeto_b"
        proj_b.mkdir()
        monkeypatch.chdir(proj_b)
        init_environment()

        sync_rules(proj_b)

        client_b = get_client()
        col_b = get_collection(client_b)

        res_b_global = col_b.query(query_texts=["senhas texto puro tokens segurança"], n_results=1, where={"is_rule": True})
        assert "Diretriz Global de Segurança" in res_b_global["documents"][0][0]

        # Verifica que regra_exclusiva_a não existe no banco do projeto B
        all_rules_b = col_b.get(where={"is_rule": True})
        all_paths_b = [meta["file_path"] for meta in all_rules_b["metadatas"]]
        assert not any("regra_exclusiva_a" in p for p in all_paths_b)


class TestOrphanRulesCleanup:
    """Validação de limpeza de regras deletadas."""

    def test_deleted_rule_is_cleaned_from_db(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()

        local_rules_dir = tmp_path / GOODFELLA_DIR / "rules"
        local_rules_dir.mkdir(parents=True, exist_ok=True)

        temp_rule = local_rules_dir / "regra_temporaria.md"
        temp_rule.write_text("# Regra Temporária\nEsta regra será deletada em breve.\n", encoding="utf-8")

        sync_rules(tmp_path)

        client = get_client()
        col = get_collection(client)

        res = col.query(query_texts=["Regra Temporária deletada"], n_results=1, where={"is_rule": True})
        assert "Regra Temporária" in res["documents"][0][0]

        # Deleta a regra física e ressincroniza
        temp_rule.unlink()
        sync_rules(tmp_path)

        all_rules = col.get(where={"is_rule": True})
        all_paths = [meta["file_path"] for meta in all_rules["metadatas"]]
        assert not any("regra_temporaria" in p for p in all_paths)


class TestHandleRuleAddInteractive:
    """Validação da CLI interativa handle_rule_add com mocks de UI."""

    @patch("goodfella.cli.commands.questionary.select")
    @patch("goodfella.cli.commands.Prompt.ask")
    def test_handle_rule_add_import_file_local_rule(
        self, mock_prompt_ask, mock_questionary_select, tmp_path: Path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        init_environment()

        # Arquivo de origem
        source_md = tmp_path / "custom_rule.md"
        source_md.write_text("# Minha Regra Custom\nUse sempre tipagem estática.\n", encoding="utf-8")

        mock_scope = MagicMock()
        mock_scope.ask.return_value = "local"

        mock_type = MagicMock()
        mock_type.ask.return_value = "rules"

        mock_method = MagicMock()
        mock_method.ask.return_value = "Importar arquivo existente (.md)"

        mock_questionary_select.side_effect = [mock_scope, mock_type, mock_method]
        mock_prompt_ask.side_effect = [str(source_md), "custom_rule.md"]

        handle_rule_add()

        dest_file = tmp_path / GOODFELLA_DIR / "rules" / "custom_rule.md"
        assert dest_file.exists()
        assert "Minha Regra Custom" in dest_file.read_text(encoding="utf-8")

        # Verifica se o ChromaDB foi atualizado
        client = get_client()
        col = get_collection(client)
        res = col.query(query_texts=["tipagem estática custom"], n_results=1, where={"is_rule": True})
        assert "Minha Regra Custom" in res["documents"][0][0]

    @patch("goodfella.cli.commands.questionary.select")
    @patch("goodfella.cli.commands.Prompt.ask")
    def test_handle_rule_add_import_file_local_antipattern(
        self, mock_prompt_ask, mock_questionary_select, tmp_path: Path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        init_environment()

        source_md = tmp_path / "anti_eval.md"
        source_md.write_text("# Anti Eval\nNunca utilize eval() no código.\n", encoding="utf-8")

        mock_scope = MagicMock()
        mock_scope.ask.return_value = "local"

        mock_type = MagicMock()
        mock_type.ask.return_value = "anti_patterns"

        mock_method = MagicMock()
        mock_method.ask.return_value = "Importar arquivo existente (.md)"

        mock_questionary_select.side_effect = [mock_scope, mock_type, mock_method]
        mock_prompt_ask.side_effect = [str(source_md), "anti_eval.md"]

        handle_rule_add()

        dest_file = tmp_path / GOODFELLA_DIR / "rules" / "anti_patterns" / "anti_eval.md"
        assert dest_file.exists()
        assert "Anti Eval" in dest_file.read_text(encoding="utf-8")

        client = get_client()
        col = get_collection(client)
        res = col.query(query_texts=["eval código anti eval"], n_results=1, where={"is_rule": True})
        assert "Anti Eval" in res["documents"][0][0]

    @patch("subprocess.call")
    @patch("goodfella.cli.commands.questionary.select")
    @patch("goodfella.cli.commands.Prompt.ask")
    def test_handle_rule_add_editor_success(
        self, mock_prompt_ask, mock_questionary_select, mock_subprocess_call, tmp_path: Path, monkeypatch
    ):
        """Teste 4.1: Edição manual via editor de texto com alteração bem-sucedida."""
        monkeypatch.chdir(tmp_path)
        init_environment()

        mock_scope = MagicMock()
        mock_scope.ask.return_value = "local"

        mock_type = MagicMock()
        mock_type.ask.return_value = "rules"

        mock_method = MagicMock()
        mock_method.ask.return_value = "Digitar manualmente (abre editor de texto)"

        mock_questionary_select.side_effect = [mock_scope, mock_type, mock_method]
        mock_prompt_ask.return_value = "evitar_side_effects.md"

        def fake_editor(cmd):
            tf_path = Path(cmd[1])
            tf_path.write_text(
                "# Evitar Side Effects\n"
                "Funções de consulta não devem alterar o estado de entidades do domínio (CQS).\n",
                encoding="utf-8",
            )
            return 0

        mock_subprocess_call.side_effect = fake_editor

        handle_rule_add()

        dest_file = tmp_path / GOODFELLA_DIR / "rules" / "evitar_side_effects.md"
        assert dest_file.exists()
        assert "Evitar Side Effects" in dest_file.read_text(encoding="utf-8")

        client = get_client()
        col = get_collection(client)
        res = col.query(query_texts=["CQS consulta entidades side effects"], n_results=1, where={"is_rule": True})
        assert "Evitar Side Effects" in res["documents"][0][0]

    @patch("subprocess.call")
    @patch("goodfella.cli.commands.questionary.select")
    @patch("goodfella.cli.commands.Prompt.ask")
    def test_handle_rule_add_editor_no_changes(
        self, mock_prompt_ask, mock_questionary_select, mock_subprocess_call, tmp_path: Path, monkeypatch
    ):
        """Abortar quando o editor é fechado sem nenhuma alteração."""
        monkeypatch.chdir(tmp_path)
        init_environment()

        mock_scope = MagicMock()
        mock_scope.ask.return_value = "local"

        mock_type = MagicMock()
        mock_type.ask.return_value = "rules"

        mock_method = MagicMock()
        mock_method.ask.return_value = "Digitar manualmente (abre editor de texto)"

        mock_questionary_select.side_effect = [mock_scope, mock_type, mock_method]
        mock_prompt_ask.return_value = "regra_sem_alteracao.md"
        mock_subprocess_call.return_value = 0

        handle_rule_add()

        dest_file = tmp_path / GOODFELLA_DIR / "rules" / "regra_sem_alteracao.md"
        assert not dest_file.exists()

    @patch("subprocess.call")
    @patch("goodfella.cli.commands.questionary.select")
    @patch("goodfella.cli.commands.Prompt.ask")
    def test_handle_rule_add_editor_not_found(
        self, mock_prompt_ask, mock_questionary_select, mock_subprocess_call, tmp_path: Path, monkeypatch
    ):
        """Tratamento de erro quando nenhum editor está disponível no sistema."""
        monkeypatch.chdir(tmp_path)
        init_environment()

        mock_scope = MagicMock()
        mock_scope.ask.return_value = "local"

        mock_type = MagicMock()
        mock_type.ask.return_value = "rules"

        mock_method = MagicMock()
        mock_method.ask.return_value = "Digitar manualmente (abre editor de texto)"

        mock_questionary_select.side_effect = [mock_scope, mock_type, mock_method]
        mock_prompt_ask.return_value = "regra_qualquer.md"
        mock_subprocess_call.side_effect = FileNotFoundError()

        handle_rule_add()

        dest_file = tmp_path / GOODFELLA_DIR / "rules" / "regra_qualquer.md"
        assert not dest_file.exists()

    @patch("goodfella.cli.commands.questionary.select")
    @patch("goodfella.cli.commands.Prompt.ask")
    def test_handle_rule_add_global_scope(
        self, mock_prompt_ask, mock_questionary_select, tmp_path: Path, monkeypatch
    ):
        """Teste 4.3: Criação de regra com escopo Global via CLI."""
        mock_home = tmp_path / "home"
        mock_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(Path, "home", lambda: mock_home)

        proj_dir = tmp_path / "meu_projeto"
        proj_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(proj_dir)
        init_environment()

        source_md = tmp_path / "regra_global_seguranca.md"
        source_md.write_text("# Regra Global de Segurança\nNunca expor secrets no código.\n", encoding="utf-8")

        mock_scope = MagicMock()
        mock_scope.ask.return_value = "global"

        mock_type = MagicMock()
        mock_type.ask.return_value = "rules"

        mock_method = MagicMock()
        mock_method.ask.return_value = "Importar arquivo existente (.md)"

        mock_questionary_select.side_effect = [mock_scope, mock_type, mock_method]
        mock_prompt_ask.side_effect = [str(source_md), "regra_global_seguranca.md"]

        handle_rule_add()

        dest_file = mock_home / ".goodfella_config" / "rules" / "regra_global_seguranca.md"
        assert dest_file.exists()
        assert "Regra Global de Segurança" in dest_file.read_text(encoding="utf-8")

        # Verifica se o banco vetorial do projeto atual recebeu a regra global
        client = get_client()
        col = get_collection(client)
        res = col.query(query_texts=["secrets segurança expor"], n_results=1, where={"is_rule": True})
        assert "Regra Global de Segurança" in res["documents"][0][0]

    @patch("goodfella.cli.commands.questionary.select")
    def test_handle_rule_add_cancel_menu(self, mock_questionary_select, tmp_path: Path, monkeypatch):
        """Cancelamento gracioso quando o usuário cancela a seleção no menu."""
        monkeypatch.chdir(tmp_path)
        init_environment()

        mock_scope = MagicMock()
        mock_scope.ask.return_value = None

        mock_questionary_select.return_value = mock_scope

        handle_rule_add()

    @patch("goodfella.cli.commands.questionary.select")
    @patch("goodfella.cli.commands.Prompt.ask")
    def test_handle_rule_add_invalid_import_file(
        self, mock_prompt_ask, mock_questionary_select, tmp_path: Path, monkeypatch
    ):
        """Validação de arquivos inexistentes ou com extensão não Markdown."""
        monkeypatch.chdir(tmp_path)
        init_environment()

        mock_scope = MagicMock()
        mock_scope.ask.return_value = "local"

        mock_type = MagicMock()
        mock_type.ask.return_value = "rules"

        mock_method = MagicMock()
        mock_method.ask.return_value = "Importar arquivo existente (.md)"

        # Caso A: Arquivo inexistente
        mock_questionary_select.side_effect = [mock_scope, mock_type, mock_method]
        mock_prompt_ask.side_effect = ["/caminho/inexistente.md"]

        handle_rule_add()
        assert not (tmp_path / GOODFELLA_DIR / "rules" / "inexistente.md").exists()

        # Caso B: Arquivo não é .md
        txt_file = tmp_path / "arquivo.txt"
        txt_file.write_text("não markdown", encoding="utf-8")

        mock_questionary_select.side_effect = [mock_scope, mock_type, mock_method]
        mock_prompt_ask.side_effect = [str(txt_file)]

        handle_rule_add()
        assert not (tmp_path / GOODFELLA_DIR / "rules" / "arquivo.txt").exists()
