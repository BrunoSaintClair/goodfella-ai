"""
Pipeline de divisão de textos (Chunking) e indexação no banco vetorial.
"""

from pathlib import Path
from typing import List, Union

from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from goodfella.core.constants import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
from goodfella.rag.db import get_client, get_collection
from goodfella.rag.sync import sync_workspace

EXTENSION_TO_LANGUAGE = {
    ".py": Language.PYTHON,
    ".js": Language.JS,
    ".ts": Language.TS,
    ".tsx": Language.TS,
    ".jsx": Language.JS,
    ".java": Language.JAVA,
    ".kt": Language.KOTLIN,
    ".go": Language.GO,
    ".rs": Language.RUST,
    ".rb": Language.RUBY,
    ".cpp": Language.CPP,
    ".c": Language.CPP,
    ".h": Language.CPP,
    ".hpp": Language.CPP,
    ".cs": Language.CSHARP,
    ".php": Language.PHP,
    ".swift": Language.SWIFT,
    ".scala": Language.SCALA,
    ".ex": Language.ELIXIR,
    ".exs": Language.ELIXIR,
    ".md": Language.MARKDOWN,
    ".html": Language.HTML,
}

def get_splitter_for_file(file_path: Path) -> RecursiveCharacterTextSplitter:
    """
    Retorna o text splitter otimizado para a linguagem do arquivo.
    Se não for uma linguagem conhecida, faz o fallback para o divisor genérico.
    """
    ext = file_path.suffix.lower()
    
    if ext in EXTENSION_TO_LANGUAGE:
        return RecursiveCharacterTextSplitter.from_language(
            language=EXTENSION_TO_LANGUAGE[ext],
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP
        )
        
    return RecursiveCharacterTextSplitter(
        chunk_size=DEFAULT_CHUNK_SIZE,
        chunk_overlap=DEFAULT_CHUNK_OVERLAP
    )

def index_files(files: List[Path], workspace_dir: Union[Path, str] = None) -> None:
    """
    Lê os arquivos, quebra o conteúdo em chunks preservando a semântica 
    e insere os vetores no ChromaDB.
    """
    if not files:
        return
        
    if workspace_dir is None:
        workspace_dir = Path.cwd()
    elif isinstance(workspace_dir, str):
        workspace_dir = Path(workspace_dir)
        
    client = get_client()
    collection = get_collection(client)
    
    docs_to_add = []
    metadatas_to_add = []
    ids_to_add = []
    
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            if not content.strip():
                continue
                
            splitter = get_splitter_for_file(file_path)
            chunks = splitter.split_text(content)
            
            mtime = file_path.stat().st_mtime
            rel_path = str(file_path.relative_to(workspace_dir))
            abs_path = str(file_path.absolute())
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{abs_path}::{i}"
                
                docs_to_add.append(chunk)
                metadatas_to_add.append({
                    "file_path": abs_path,
                    "relative_path": rel_path,
                    "mtime": mtime,
                    "chunk_index": i
                })
                ids_to_add.append(chunk_id)
                
        except (UnicodeDecodeError, IOError):
            # Ignora binários não detectados ou erros de permissão de leitura
            pass
            
    if docs_to_add:
        # ChromaDB possui limites em chamadas de batching. 
        # Lotes de 5000 são considerados seguros para ingestões locais sem estourar limites.
        batch_size = 5000
        for i in range(0, len(docs_to_add), batch_size):
            collection.upsert(
                documents=docs_to_add[i:i + batch_size],
                metadatas=metadatas_to_add[i:i + batch_size],
                ids=ids_to_add[i:i + batch_size]
            )

def run_indexing_pipeline(workspace_dir: Union[Path, str] = None) -> int:
    """
    Orquestra a sincronização (diff) e injeta o backlog no indexador.
    Retorna o total de arquivos que precisaram de (re)indexação.
    """
    files_to_index = sync_workspace(workspace_dir)
    
    if files_to_index:
        index_files(files_to_index, workspace_dir)
        
    return len(files_to_index)
