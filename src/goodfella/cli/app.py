"""
Entry point principal do Goodfella CLI.

Este módulo contém a função `main()` que é registrada como console_script
no pyproject.toml, permitindo invocar o Goodfella diretamente via terminal:

    $ goodfella

"""


from rich.console import Console

console = Console()

def main() -> None:
    """Ponto de entrada principal do comando `goodfella`.

    Inicializa o ambiente, conecta ao banco vetorial e
    inicia o loop REPL interativo.
    """
    console.print("\n[bold green]🎩 Goodfella CLI inicializado com sucesso![/bold green]")

if __name__ == "__main__":
    main()
