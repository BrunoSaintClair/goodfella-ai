"""
Constantes globais do projeto Goodfella.

Centraliza todas as constantes utilizadas pelo sistema para
evitar magic strings e facilitar manutenção.
"""

# === Diretórios e Arquivos ===
GOODFELLA_DIR = ".goodfella"
CHROMA_DIR = "chroma_db"
CHAT_HISTORY_FILE = "chat_history.json"
CONFIG_FILE = "config.toml"
GLOBAL_CONFIG_FILE = ".goodfella_config"

# === Diretórios Ignorados na Ingestão ===
IGNORED_DIRS: frozenset[str] = frozenset({
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    ".goodfella",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "target",
    ".idea",
    ".vscode",
    "vendor",
    "coverage",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "egg-info",
})

# === Extensões Suportadas para Ingestão ===
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".kt", ".go", ".rs", ".rb",
    ".c", ".cpp", ".h", ".hpp", ".cs",
    ".php", ".swift", ".scala", ".ex", ".exs",
    ".md", ".txt", ".yaml", ".yml", ".toml",
    ".json", ".xml", ".html", ".css", ".scss",
    ".sql", ".sh", ".bash", ".zsh",
    ".dockerfile", ".tf", ".hcl",
})

# === Chunking ===
DEFAULT_CHUNK_SIZE = 1500
DEFAULT_CHUNK_OVERLAP = 200

# === Modelos ===
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:1.5b"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"

# === Prefixos de Comando ===
COMMAND_PREFIX = "/"

# === Metadados ===
APP_NAME = "Goodfella"
APP_DESCRIPTION = "Strict Pair Programmer CLI"
