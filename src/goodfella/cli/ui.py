"""
Utilitários de interface de usuário (UI) e estilização usando a biblioteca Rich.
"""

from contextlib import contextmanager
from typing import Generator

from rich.console import Console
from rich.theme import Theme

# Define um tema base
custom_theme = Theme({
    "info": "dim white",
    "warning": "magenta",
    "danger": "bold red",
    "success": "bold green",
})

# Console global compartilhado por todo CLI
console = Console(theme=custom_theme)

@contextmanager
def show_spinner(message: str) -> Generator[None, None, None]:
    """
    Context manager que exibe um spinner animado enquanto uma operação lenta
    (ex: I/O de disco, ingestão RAG ou resposta do LLM) ocorre em background.
    
    Exemplo de uso:
        with show_spinner("Processando arquivos..."):
            do_heavy_work()
    """
    with console.status(f"[bold cyan]{message}[/bold cyan]", spinner="dots"):
        yield

class _TimerRenderable:
    """Objeto auxiliar que armazena o start_time para uso externo."""
    def __init__(self):
        self.start_time = 0.0

@contextmanager
def show_timer_spinner(message: str) -> Generator[_TimerRenderable, None, None]:
    """
    Context manager que exibe um spinner animado e expõe o timestamp de início
    para cálculo de tempo decorrido pelo código chamador.
    
    Exemplo de uso:
        with show_timer_spinner("Buscando regras...") as renderable:
            do_heavy_work()
            elapsed = time.time() - renderable.start_time
    """
    import time
    renderable = _TimerRenderable()
    renderable.start_time = time.time()
    with console.status(f"[bold cyan]{message}[/bold cyan]", spinner="dots"):
        yield renderable
