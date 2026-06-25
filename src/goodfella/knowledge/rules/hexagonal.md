# Arquitetura Hexagonal (Ports & Adapters)

## Princípio Central
A aplicação é o centro do universo. Ela se comunica com o mundo externo apenas através de **Ports** (interfaces) e **Adapters** (implementações). A aplicação não sabe — e não deve saber — quem está do outro lado.

## Anatomia

### Ports (Interfaces)
- **Driving Ports (Inbound):** Interfaces que o mundo externo usa para interagir com a aplicação
  - Ex: `OrderService`, `PaymentProcessor`
  - Implementados pelo **Application Core**
- **Driven Ports (Outbound):** Interfaces que a aplicação usa para interagir com o mundo externo
  - Ex: `OrderRepository`, `NotificationSender`, `PaymentGateway`
  - **Definidos** pelo Application Core, **implementados** por Adapters externos

### Adapters (Implementações)
- **Driving Adapters (Inbound):** Traduzem requests do mundo externo para chamadas ao Application Core
  - Ex: REST Controller, CLI Handler, GraphQL Resolver, Message Consumer
- **Driven Adapters (Outbound):** Implementam os Driven Ports com tecnologia específica
  - Ex: `PostgresOrderRepository`, `SMTPNotificationSender`, `StripePaymentGateway`

## Regra de Ouro
> **O Application Core NUNCA importa Adapters. Adapters SEMPRE importam o Core.**

## Sinais de Violação
- Application Core importando classes de framework (Flask, Django, Spring)
- Use cases que instanciam implementações concretas de repositórios
- Lógica de negócio dentro de controllers ou handlers de API
- Ports (interfaces) definidos na camada de infraestrutura
- Testes de unidade que precisam de banco de dados real

## Benefícios da Conformidade
- **Testabilidade:** Core testável sem infraestrutura (mocks implementam os Driven Ports)
- **Substituibilidade:** Trocar PostgreSQL por MongoDB exige apenas um novo Adapter
- **Clareza:** A fronteira entre "o que a aplicação faz" e "como ela faz" é explícita
- **Evolução:** Novos canais (CLI, API, Events) são apenas novos Driving Adapters

## Padrão de Correção
1. Identificar todas as dependências externas do Core
2. Criar Driven Ports (interfaces) para cada dependência
3. Mover implementações concretas para a camada de Adapters
4. Usar injeção de dependência (construtor) para conectar
5. Garantir que o módulo do Core não possui imports de frameworks
