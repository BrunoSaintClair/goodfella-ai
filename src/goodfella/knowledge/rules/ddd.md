# Domain-Driven Design (DDD) — Tactical Patterns

## Princípio Central
O design do software deve refletir o domínio de negócio. O código é o modelo do domínio, não apenas uma representação técnica de tabelas do banco.

## Ubiquitous Language
- A linguagem do código deve espelhar a linguagem dos especialistas do domínio
- Nomes de classes, métodos e variáveis devem usar termos do negócio
- **Violação:** `DataProcessor`, `HelperManager`, `ServiceUtils` — nomes genéricos que não comunicam o domínio
- **Correção:** `OrderFulfillment`, `PaymentGateway`, `InventoryReservation` — nomes que revelam intenção

## Entidades (Entities)
- Objetos definidos por sua **identidade**, não por seus atributos
- Possuem um ciclo de vida contínuo e são rastreáveis
- **Violação:** Entidade sem identidade clara, comparada por todos os atributos
- **Sinal:** Entidade que é apenas um data class sem comportamento

## Objetos de Valor (Value Objects)
- Definidos por seus **atributos**, não por identidade
- Imutáveis — substituídos, nunca modificados
- Encapsulam validação e comportamento relacionado ao valor
- **Violação:** Usar primitivos (`str`, `int`) para representar conceitos do domínio (CPF, Email, Money)
- **Correção:** Criar Value Objects tipados: `CPF("123.456.789-00")`, `Money(100, "BRL")`

## Agregados (Aggregates)
- Cluster de Entidades e Value Objects com uma raiz (Aggregate Root)
- A raiz é o único ponto de entrada para modificações
- Garantem consistência transacional dentro do limite do agregado
- **Violação:** Modificar entidades filhas diretamente, bypassing a raiz
- **Sinal:** Repositórios para entidades que não são Aggregate Root

## Repositórios (Repositories)
- Abstraem a persistência de Agregados
- Interface definida no domínio, implementação na infraestrutura
- Operam com Aggregates inteiros, nunca com pedaços
- **Violação:** Repositório que expõe queries SQL ou retorna DTOs de banco
- **Correção:** Interface com métodos como `find_by_id()`, `save()`, `remove()`

## Domain Services
- Operações que não pertencem naturalmente a nenhuma Entity ou Value Object
- Stateless — recebem tudo que precisam via parâmetros
- **Violação:** Domain Service com estado mutável ou que acessa infraestrutura diretamente
- **Sinal:** Lógica de negócio em Application Services que deveria estar no domínio

## Domain Events
- Representam algo significativo que aconteceu no domínio
- Imutáveis e no passado: `OrderPlaced`, `PaymentConfirmed`
- Permitem desacoplamento entre Aggregates
- **Violação:** Eventos com lógica de negócio ou que modificam estado
