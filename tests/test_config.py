"""Testes de configuração do ambiente Goodfella."""

from goodfella import __version__
from goodfella.core.constants import (
    APP_NAME,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_OLLAMA_MODEL,
    GOODFELLA_DIR,
    IGNORED_DIRS,
    SUPPORTED_EXTENSIONS,
)


class TestPackageSetup:
    """Verifica que o pacote foi instalado corretamente."""

    def test_version_is_set(self):
        assert __version__ == "0.1.0"

    def test_version_is_semver(self):
        parts = __version__.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)


class TestConstants:
    """Verifica que as constantes core estão definidas."""

    def test_app_name(self):
        assert APP_NAME == "Goodfella"

    def test_goodfella_dir(self):
        assert GOODFELLA_DIR == ".goodfella"

    def test_ignored_dirs_contains_essentials(self):
        essentials = {"node_modules", ".venv", "__pycache__", ".git", ".goodfella"}
        assert essentials.issubset(IGNORED_DIRS)

    def test_supported_extensions_contains_python(self):
        assert ".py" in SUPPORTED_EXTENSIONS

    def test_supported_extensions_contains_js(self):
        assert ".js" in SUPPORTED_EXTENSIONS

    def test_chunk_size_is_reasonable(self):
        assert 500 <= DEFAULT_CHUNK_SIZE <= 5000

    def test_default_model_is_set(self):
        assert DEFAULT_OLLAMA_MODEL is not None
        assert len(DEFAULT_OLLAMA_MODEL) > 0


class TestEntryPoint:
    """Verifica que o entry point existe e é chamável."""

    def test_main_is_callable(self):
        from goodfella.cli.app import main
        assert callable(main)

    def test_main_returns_none(self):
        from goodfella.cli.app import main
        result = main()
        assert result is None
