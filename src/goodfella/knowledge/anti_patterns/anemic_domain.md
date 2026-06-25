# Anti-Pattern: Anemic Domain Model

## Definição
Um Modelo de Domínio Anêmico é uma estrutura de dados que contém apenas atributos (getters/setters) sem nenhum comportamento de negócio. Toda a lógica reside em "services" externos, transformando as entidades em meros containers de dados.

> "The fundamental horror of this anti-pattern is that it's so contrary to the basic idea of object-oriented design; which is to combine data and process together." — Martin Fowler

## Sinais de Detecção

### No Modelo
- Classes com apenas atributos e propriedades, sem métodos de negócio
- Uso excessivo de `dataclass` ou `NamedTuple` para entidades de domínio que deveriam ter comportamento
- Entidades sem validação interna — validação feita externamente
- Setters públicos para todos os atributos sem invariantes

### Nos Services
- Services que manipulam diretamente os atributos das entidades
- Lógica de negócio duplicada entre services diferentes
- Services com nomes como `OrderService.validate_order(order)` — a validação deveria estar em `Order`
- Regras de negócio espalhadas em múltiplas camadas

## Exemplo Problemático
```python
# Entidade anêmica — apenas dados
@dataclass
class Order:
    items: list
    status: str
    total: float

# Service gordo — toda a lógica aqui
class OrderService:
    def calculate_total(self, order: Order) -> float:
        return sum(item.price * item.qty for item in order.items)

    def can_cancel(self, order: Order) -> bool:
        return order.status not in ("shipped", "delivered")

    def apply_discount(self, order: Order, pct: float):
        order.total = order.total * (1 - pct)
```

## Exemplo Corrigido
```python
# Entidade rica — comportamento junto dos dados
class Order:
    def __init__(self, items: list[OrderItem]):
        self._items = items
        self._status = OrderStatus.PENDING

    @property
    def total(self) -> Money:
        return sum(item.subtotal for item in self._items)

    def can_cancel(self) -> bool:
        return self._status not in (OrderStatus.SHIPPED, OrderStatus.DELIVERED)

    def apply_discount(self, percentage: Percentage) -> None:
        if not self.can_cancel():
            raise DomainError("Cannot modify a shipped order")
        for item in self._items:
            item.apply_discount(percentage)
```

## Impacto
- **Perda de encapsulamento:** Qualquer service pode manipular o estado da entidade de forma inconsistente
- **Duplicação:** Mesma regra de negócio implementada em múltiplos services
- **Fragilidade:** Mudança em uma regra exige atualizar N services
- **Anti-OOP:** O código parece procedural disfarçado de orientado a objetos

## Princípios Violados
- **Encapsulamento** (fundamental) — Dados expostos sem proteção
- **SRP** — Services assumem responsabilidades que pertencem às entidades
- **Tell, Don't Ask** — Código pergunta o estado e decide externamente
- **DDD** — Modelo não reflete o domínio real
