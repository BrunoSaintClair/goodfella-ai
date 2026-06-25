# Clean Architecture

## Princípio Central
A arquitetura deve ser independente de frameworks, testável, independente de UI, independente de banco de dados e independente de qualquer agente externo.

## Regra de Dependência
As dependências de código-fonte devem apontar **apenas para dentro**, em direção às policies de alto nível. Nada em um círculo interno pode saber qualquer coisa sobre algo em um círculo externo.

## Camadas (de dentro para fora)

### 1. Entities (Enterprise Business Rules)
- Encapsulam as regras de negócio mais gerais e de alto nível
- São os objetos menos propensos a mudar quando algo externo muda
- Podem ser objetos com métodos ou conjuntos de estruturas de dados e funções
- **Violação comum:** Entidades que importam frameworks ORM ou possuem decorators de serialização

### 2. Use Cases (Application Business Rules)
- Contêm regras de negócio específicas da aplicação
- Orquestram o fluxo de dados de/para as Entities
- Não devem ser afetados por mudanças na UI, banco de dados ou frameworks
- **Violação comum:** Use cases que fazem queries SQL diretamente ou manipulam HTTP requests/responses

### 3. Interface Adapters
- Convertem dados do formato mais conveniente para use cases/entities para o formato mais conveniente para algum agente externo (DB, Web, etc.)
- Contém Controllers, Gateways, Presenters
- **Violação comum:** Adapters que contêm lógica de negócio ao invés de apenas conversão

### 4. Frameworks & Drivers (External)
- Camada mais externa: frameworks web, banco de dados, UI
- Geralmente não se escreve muito código aqui além de glue code
- **Violação comum:** Lógica de negócio dentro de controllers ou handlers de framework

## Sinais de Violação
- Imports cruzando camadas na direção errada
- Entidades de domínio com annotations de framework (`@Entity`, `@JsonProperty`)
- Use cases retornando DTOs de framework ou objetos HTTP
- Lógica de negócio em controllers, middlewares ou resolvers
- Testes que precisam de banco de dados ou servidor HTTP para rodar

## Padrão de Correção
1. Extrair interfaces (ports) na camada interna
2. Implementar adaptadores (adapters) na camada externa
3. Usar injeção de dependência para conectar as camadas
4. Garantir que cada camada só conhece as interfaces da camada imediatamente interna
