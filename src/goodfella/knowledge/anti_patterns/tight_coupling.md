# Anti-Pattern: Tight Coupling (Acoplamento Forte)

## Definição
Acoplamento forte ocorre quando módulos, classes ou componentes são tão interconectados que uma mudança em um exige mudanças em cascata nos demais. O sistema se comporta como um monólito rígido ao invés de um conjunto de peças substituíveis.

## Sinais de Detecção

### Dependências Diretas
- Classes que instanciam suas dependências diretamente (`self.repo = MySQLRepo()`)
- Import de implementações concretas ao invés de abstrações/interfaces
- Módulos de domínio/negócio que importam frameworks ou bibliotecas de infraestrutura
- `from flask import request` dentro de um use case

### Rigidez Estrutural
- Impossível trocar o banco de dados sem reescrever lógica de negócio
- Impossível testar uma classe sem subir toda a infraestrutura
- Mudança em um módulo quebra testes de módulos não relacionados
- Arquivos circulares de dependência (A importa B, B importa A)

### Sintomas no Dia-a-Dia
- "Não consigo mudar X sem quebrar Y"
- PRs que tocam 15+ arquivos para uma mudança conceitual simples
- Testes que falham em cascata por uma mudança pontual
- Deploy de um módulo exige redeploy de outros

## Exemplo Problemático
```python
class OrderUseCase:
    def __init__(self):
        # Acoplamento direto a implementações concretas
        self.repo = PostgresOrderRepository()
        self.notifier = SMTPEmailSender()
        self.cache = RedisCache()

    def place_order(self, data):
        order = Order(**data)
        self.repo.save(order)           # Acoplado ao Postgres
        self.notifier.send(order.email)  # Acoplado ao SMTP
        self.cache.invalidate("orders")  # Acoplado ao Redis
```

## Exemplo Corrigido
```python
class OrderUseCase:
    def __init__(
        self,
        repo: OrderRepository,          # Interface/Protocol
        notifier: NotificationPort,      # Interface/Protocol
        cache: CachePort,               # Interface/Protocol
    ):
        self._repo = repo
        self._notifier = notifier
        self._cache = cache

    def place_order(self, data):
        order = Order(**data)
        self._repo.save(order)
        self._notifier.send(order.email)
        self._cache.invalidate("orders")
```

## Níveis de Acoplamento (do pior ao melhor)
1. **Content Coupling** — Módulo acessa internals de outro módulo
2. **Common Coupling** — Módulos compartilham estado global mutável
3. **Control Coupling** — Módulo controla o fluxo de outro via flags
4. **Stamp Coupling** — Módulos compartilham estruturas de dados complexas
5. **Data Coupling** — Módulos compartilham apenas dados primitivos necessários
6. **Message Coupling** ✅ — Módulos se comunicam apenas via mensagens/interfaces

## Correção
1. **Definir interfaces** (Protocols em Python) para cada dependência externa
2. **Injeção de dependência** via construtor — nunca instanciar dentro da classe
3. **Dependency Inversion** — camada interna define o contrato, camada externa implementa
4. **Composition Root** — único lugar no app onde as dependências concretas são montadas

## Princípios Violados
- **DIP** (principal) — Alto nível depende de baixo nível
- **OCP** — Trocar implementação exige modificar a classe consumidora
- **Clean Architecture** — Regra de dependência violada (core importa infra)
- **Hexagonal** — Ports não existem, adapters acoplados diretamente
