"""
Mecanismo de sincronização do RAG.
"""

from pathlib import Path
from typing import List, Dict, Union

from goodfella.rag.db import get_client, get_collection
from goodfella.rag.scanner import scan_workspace

def get_indexed_files_mtime(collection) -> Dict[str, float]:
    """
    Retorna um dicionário mapeando o caminho absoluto do arquivo 
    para o seu timestamp de modificação (mtime) registrado no ChromaDB.
    """
    result = collection.get(include=["metadatas"])
    metadatas = result.get("metadatas", [])
    
    indexed_files = {}
    for meta in metadatas:
        if meta and "file_path" in meta and "mtime" in meta:
            file_path = str(meta["file_path"])
            mtime = float(meta["mtime"])
            
            if file_path not in indexed_files:
                indexed_files[file_path] = mtime
                
    return indexed_files

def sync_workspace(workspace_dir: Union[Path, str] = None) -> List[Path]:
    """
    Sincroniza os arquivos físicos com o banco vetorial baseado em mtime.
    Remove documentos deletados ou desatualizados e retorna a lista de arquivos 
    que precisam ser indexados/reindexados.
    """
    if workspace_dir is None:
        workspace_dir = Path.cwd()
    elif isinstance(workspace_dir, str):
        workspace_dir = Path(workspace_dir)
        
    client = get_client()
    collection = get_collection(client)
    
    # 1. Escaneia a árvore física atual validada
    valid_files_paths = scan_workspace(workspace_dir)
    
    current_files = {}
    for p in valid_files_paths:
        try:
            # Armazena string absoluta e timestamp de modificação atual
            current_files[str(p.absolute())] = p.stat().st_mtime
        except FileNotFoundError:
            pass 
            
    # 2. Resgata o mapa de arquivos que já existem no ChromaDB
    indexed_files = get_indexed_files_mtime(collection)
    
    # 3. Faz a diferença (Diff)
    current_paths_set = set(current_files.keys())
    indexed_paths_set = set(indexed_files.keys())
    
    # Órfãos diretos: existem no banco, mas não mais no disco (foram apagados/renomeados)
    orphan_files = indexed_paths_set - current_paths_set
    
    files_to_index = []
    
    for file_path, current_mtime in current_files.items():
        if file_path not in indexed_files:
            # Arquivo novo
            files_to_index.append(Path(file_path))
        else:
            # Arquivo existente. Modificou?
            indexed_mtime = indexed_files[file_path]
            if current_mtime > indexed_mtime:
                # Foi atualizado. Marca para reindexar e marca o velho para ser apagado.
                files_to_index.append(Path(file_path))
                orphan_files.add(file_path)
                
    # 4. Remove vetores obsoletos ou órfãos do ChromaDB
    if orphan_files:
        orphan_list = list(orphan_files)
        # Apaga em lotes usando query no metadado para não estourar a RAM do Chroma
        batch_size = 100
        for i in range(0, len(orphan_list), batch_size):
            batch = orphan_list[i:i + batch_size]
            collection.delete(
                where={"file_path": {"$in": batch}}
            )
            
    return files_to_index
