"""
Gerenciamento de configuração global do projeto Goodfella.
"""

import json
from pathlib import Path
from typing import Any, Dict

CONFIG_FILE_NAME = ".goodfella_config"

DEFAULT_CONFIG = {
    "provider": "Ollama",
    "models": {
        "ollama": "qwen2.5-coder:1.5b",
        "openai": "gpt-4o",
        "gemini": "gemini-1.5-pro",
        "anthropic": "claude-3-5-sonnet-20240620",
        "deepseek": "deepseek-coder"
    },
    "api_keys": {
        "openai": "",
        "gemini": "",
        "anthropic": "",
        "deepseek": ""
    }
}

def get_config_path() -> Path:
    """
    Retorna o caminho absoluto do arquivo de configuração global.
    """
    return Path.home() / CONFIG_FILE_NAME

def load_config() -> Dict[str, Any]:
    """
    Carrega as configurações globais do arquivo ~/.goodfella_config.
    Se o arquivo não existir ou for inválido, retorna o fallback (Ollama).
    """
    config_path = get_config_path()
    
    if not config_path.exists():
        return DEFAULT_CONFIG.copy()
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            
            # Merge simples para garantir chaves padrão
            merged_config = DEFAULT_CONFIG.copy()
            merged_config.update(user_config)
            
            # Merge profundo dos sub-dicionários (models e api_keys)
            for sub_key in ["models", "api_keys"]:
                if sub_key in user_config and isinstance(user_config[sub_key], dict):
                    merged_sub = DEFAULT_CONFIG[sub_key].copy()
                    merged_sub.update(user_config[sub_key])
                    merged_config[sub_key] = merged_sub
                
            return merged_config
    except (json.JSONDecodeError, IOError):
        # Em caso de falha de leitura ou JSON corrompido, evita quebrar a aplicação
        return DEFAULT_CONFIG.copy()

def save_config(config: Dict[str, Any]) -> None:
    """
    Salva o dicionário de configurações no arquivo global ~/.goodfella_config.
    """
    config_path = get_config_path()
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
