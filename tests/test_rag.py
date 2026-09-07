"""Testes do motor RAG, scanner e sincronização."""

import os
import time
from pathlib import Path

from goodfella.rag.scanner import scan_workspace
from goodfella.rag.chunker import (
    get_splitter_for_file,
    run_indexing_pipeline,
    EXTENSION_TO_LANGUAGE,
)
from goodfella.rag.db import get_client, get_collection
from goodfella.core.env import init_environment


class TestScanner:
    """Validação de escaneamento de arquivos e respeito a ignore rules (Teste 3.1)."""

    def test_gitignore_and_ignored_dirs(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        (tmp_path / "node_modules").mkdir()
        (tmp_path / ".venv").mkdir()
        (tmp_path / "ignore_me").mkdir()

        (tmp_path / "src" / "app.py").write_text("def hello(): return 'world'")
        (tmp_path / "node_modules" / "lib.js").write_text("console.log('node');")
        (tmp_path / ".venv" / "bin.py").write_text("print('venv')")
        (tmp_path / "ignore_me" / "secret.py").write_text("SECRET = '123'")

        (tmp_path / ".gitignore").write_text("ignore_me/\n")

        scanned = scan_workspace(tmp_path)
        scanned_rel = [str(p.relative_to(tmp_path)) for p in scanned]

        assert "src/app.py" in scanned_rel
        assert not any("node_modules" in s for s in scanned_rel)
        assert not any(".venv" in s for s in scanned_rel)
        assert not any("ignore_me" in s for s in scanned_rel)
        assert len(scanned_rel) == 1

    def test_unsupported_extensions_ignored(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (tmp_path / "src" / "data.csv").write_text("a,b,c\n1,2,3\n")
        (tmp_path / "src" / "app.py").write_text("print('ok')")

        scanned = scan_workspace(tmp_path)
        scanned_rel = [str(p.relative_to(tmp_path)) for p in scanned]

        assert "src/app.py" in scanned_rel
        assert "src/image.png" not in scanned_rel
        assert "src/data.csv" not in scanned_rel


class TestChunkerAndSplitters:
    """Validação de splitters e chunking inteligente para múltiplas linguagens (Teste 3.2)."""

    def test_splitters_for_supported_languages(self):
        languages = [
            ("main.py", ".py"),
            ("service.ts", ".ts"),
            ("handler.go", ".go"),
            ("lib.rs", ".rs"),
            ("doc.md", ".md"),
            ("script.js", ".js"),
        ]
        for filename, ext in languages:
            splitter = get_splitter_for_file(Path(filename))
            assert splitter is not None
            assert ext in EXTENSION_TO_LANGUAGE

    def test_multi_language_indexing_and_retrieval(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()

        (tmp_path / "calc.py").write_text(
            "def calculate_total(price, tax):\n    return price * (1 + tax)\n"
        )
        (tmp_path / "auth.ts").write_text(
            "export function authenticate(token: string): boolean {\n  return token === 'secret';\n}\n"
        )

        indexed_count = run_indexing_pipeline(tmp_path)
        assert indexed_count == 2

        client = get_client()
        col = get_collection(client)
        assert col.count() >= 2

        res_py = col.query(query_texts=["calculate price tax"], n_results=1)
        assert "calculate_total" in res_py["documents"][0][0]

        res_ts = col.query(query_texts=["authenticate token"], n_results=1)
        assert "authenticate" in res_ts["documents"][0][0]


class TestSyncAndJIT:
    """Validação de sincronização incremental JIT (Testes 3.3, 3.4, 3.5, 3.6)."""

    def test_jit_new_file(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("def main(): pass")

        run_indexing_pipeline(tmp_path)
        client = get_client()
        col = get_collection(client)
        count_init = col.count()

        time.sleep(0.05)
        (tmp_path / "src" / "tax.py").write_text("def calculate_taxes(amount): return amount * 0.15")

        indexed = run_indexing_pipeline(tmp_path)
        assert indexed == 1
        assert col.count() > count_init

    def test_jit_modified_file(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()

        (tmp_path / "src").mkdir()
        tax_file = tmp_path / "src" / "tax.py"
        tax_file.write_text("def calculate_taxes(amount): return amount * 0.15")

        run_indexing_pipeline(tmp_path)
        client = get_client()
        col = get_collection(client)
        count_before = col.count()

        time.sleep(0.1)
        tax_file.write_text("def calculate_taxes(amount): return amount * 0.25 # UPDATED")

        indexed = run_indexing_pipeline(tmp_path)
        assert indexed == 1
        assert col.count() == count_before

        res = col.query(query_texts=["calculate taxes"], n_results=1)
        assert "0.25 # UPDATED" in res["documents"][0][0]

    def test_jit_deleted_file_cleanup(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        init_environment()

        (tmp_path / "src").mkdir()
        tax_file = tmp_path / "src" / "tax.py"
        app_file = tmp_path / "src" / "app.py"
        tax_file.write_text("def calculate_taxes(amount): return amount * 0.15")
        app_file.write_text("def run_app(): pass")

        run_indexing_pipeline(tmp_path)
        client = get_client()
        col = get_collection(client)
        count_before = col.count()

        tax_file.unlink()
        run_indexing_pipeline(tmp_path)

        assert col.count() < count_before
        res = col.query(query_texts=["calculate taxes"], n_results=2)
        if res["documents"] and res["documents"][0]:
            for doc in res["documents"][0]:
                assert "calculate_taxes" not in doc
