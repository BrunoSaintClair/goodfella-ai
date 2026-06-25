# Anti-Pattern: God Class

## Definição
Uma God Class é uma classe que sabe demais, faz demais e controla demais. Ela centraliza responsabilidades que deveriam estar distribuídas entre múltiplas classes menores e coesas.

## Sinais de Detecção

### Métricas Quantitativas
- **LOC (Lines of Code):** Classe com mais de 500 linhas
- **Métodos:** Mais de 20 métodos públicos
- **Dependências:** Importa 10+ módulos/pacotes distintos
- **Parâmetros:** Construtor com 7+ parâmetros

### Sinais Qualitativos
- Nome genérico: `Manager`, `Handler`, `Processor`, `Controller`, `Helper`, `Utils`
- Classe que é modificada em quase todo PR/commit
- Métodos que não se relacionam entre si (baixa coesão)
- Difícil de testar isoladamente — precisa de muitos mocks
- Comentários dividindo a classe em "seções" (`# === User Logic ===`, `# === Payment Logic ===`)

## Exemplo Problemático
```python
class OrderManager:
    def create_order(self): ...
    def validate_payment(self): ...
    def send_email(self): ...
    def generate_pdf(self): ...
    def update_inventory(self): ...
    def calculate_shipping(self): ...
    def apply_discount(self): ...
    def sync_with_erp(self): ...
```

## Impacto
- **Manutenção:** Qualquer mudança arrisca efeitos colaterais em funcionalidades não relacionadas
- **Testabilidade:** Testes unitários se tornam testes de integração
- **Conflitos:** Múltiplos desenvolvedores editando a mesma classe simultaneamente
- **Compreensão:** Novos desenvolvedores levam semanas para entender a classe

## Correção
1. Identificar clusters de métodos relacionados (análise de coesão)
2. Extrair cada cluster em uma classe dedicada com responsabilidade única
3. Usar composição para orquestrar as novas classes menores
4. Aplicar SRP rigorosamente: cada nova classe serve a um único ator

## Princípios Violados
- **SRP** (principal) — Múltiplos motivos para mudar
- **OCP** — Difícil de estender sem modificar
- **ISP** — Clientes forçados a depender de métodos que não usam
