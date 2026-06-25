# Princípios SOLID

## S — Single Responsibility Principle (SRP)
**"Uma classe deve ter um, e somente um, motivo para mudar."**

- Cada módulo/classe deve ser responsável por apenas uma parte da funcionalidade
- "Motivo para mudar" = um ator ou stakeholder
- **Violação comum:** Classes que fazem validação, persistência e formatação de output ao mesmo tempo
- **Sinal:** Classe com métodos que servem a diferentes atores (ex: `calcularSalario()` + `gerarRelatorio()` + `salvarNoBanco()`)
- **Correção:** Extrair responsabilidades em classes separadas, cada uma servindo um único ator

## O — Open/Closed Principle (OCP)
**"Entidades de software devem ser abertas para extensão, mas fechadas para modificação."**

- Comportamento novo deve ser adicionado sem alterar código existente
- Usar abstrações (interfaces, classes abstratas) como pontos de extensão
- **Violação comum:** Cadeias de `if/elif/else` ou `switch/case` que crescem a cada novo tipo
- **Sinal:** Toda nova feature exige modificar uma classe existente em múltiplos pontos
- **Correção:** Strategy Pattern, Plugin Architecture, Polimorfismo

## L — Liskov Substitution Principle (LSP)
**"Objetos de uma superclasse devem ser substituíveis por objetos de suas subclasses sem quebrar a aplicação."**

- Subtipos devem honrar o contrato do tipo base
- Pré-condições não podem ser fortalecidas no subtipo
- Pós-condições não podem ser enfraquecidas no subtipo
- **Violação comum:** Subclasse que lança exceção em método herdado (`NotImplementedError` sem justificativa)
- **Sinal:** Checks de tipo (`isinstance()`) antes de chamar métodos do objeto
- **Correção:** Refatorar hierarquia, usar composição sobre herança, definir contratos mais precisos

## I — Interface Segregation Principle (ISP)
**"Nenhum cliente deve ser forçado a depender de métodos que não utiliza."**

- Interfaces devem ser pequenas e focadas
- Preferir muitas interfaces específicas a uma interface geral
- **Violação comum:** Interface "god" com 15+ métodos onde cada implementação só usa 3-4
- **Sinal:** Implementações com múltiplos métodos vazios ou `raise NotImplementedError`
- **Correção:** Quebrar interface grande em interfaces menores e coesas

## D — Dependency Inversion Principle (DIP)
**"Módulos de alto nível não devem depender de módulos de baixo nível. Ambos devem depender de abstrações."**

- Abstrações não devem depender de detalhes
- Detalhes devem depender de abstrações
- **Violação comum:** Use case que instancia diretamente `MySQLRepository()` ao invés de receber `Repository` via construtor
- **Sinal:** `import` de implementações concretas em módulos de alto nível
- **Correção:** Definir interfaces/protocolos, usar injeção de dependência, factory pattern

## Relação entre SOLID e Clean Architecture
- **SRP** → Cada camada tem uma responsabilidade clara
- **OCP** → Novas features são adicionadas via novas implementações, não modificando código existente
- **LSP** → Implementações de ports/interfaces devem ser intercambiáveis
- **ISP** → Ports devem ser granulares e específicos por use case
- **DIP** → Camadas internas definem interfaces, camadas externas implementam
