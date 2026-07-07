"""
Gerenciamento de memória e histórico de conversas do Goodfella.
"""

import json
from pathlib import Path
from typing import List, Dict

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from goodfella.core.env import GOODFELLA_DIR

MAX_HISTORY_MESSAGES = 20

def get_history_path(workspace_dir: Path = None) -> Path:
    if workspace_dir is None:
        workspace_dir = Path.cwd()
    return workspace_dir / GOODFELLA_DIR / "chat_history.json"

def load_history(workspace_dir: Path = None) -> List[BaseMessage]:
    """
    Carrega o histórico salvo e o converte para o formato de mensagens do LangChain.
    """
    history_path = get_history_path(workspace_dir)
    messages = []
    
    if not history_path.exists():
        return messages
        
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        for msg in data:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "ai":
                messages.append(AIMessage(content=msg.get("content", "")))
    except (json.JSONDecodeError, IOError):
        pass
    
    if len(messages) > MAX_HISTORY_MESSAGES:
        messages = messages[-MAX_HISTORY_MESSAGES:]
        
    return messages

def clear_history(workspace_dir: Path = None) -> None:
    """
    Limpa o histórico da sessão atual.
    """
    history_path = get_history_path(workspace_dir)
    if history_path.exists():
        try:
            history_path.unlink()
        except IOError:
            pass

def save_message(role: str, content: str, workspace_dir: Path = None) -> None:
    """
    Salva uma nova mensagem no histórico local de forma isolada.
    Nota: Apenas a interação (Q&A) bruta é salva. O contexto do RAG não é persistido
    aqui para não inflar o JSON infinitamente.
    """
    history_path = get_history_path(workspace_dir)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    
    data: List[Dict[str, str]] = []
    if history_path.exists():
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
            
    data.append({"role": role, "content": content})
    
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
