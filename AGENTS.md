# Agent Instructions

## Package Management
- Use [uv](https://github.com/astral-sh/uv) for all Python package management.
  - Add production packages: `uv add <package>`
  - Add development packages: `uv add --group dev <package>`
- Always use the `.venv` environment when running code for this repository.

## Code Style & Quality
- Use absolute imports throughout the codebase.
- Follow [PEP8](https://peps.python.org/pep-0008/) for code style and formatting.
- Use [Black](https://black.readthedocs.io/) for code formatting: `black .`
- Use [isort](https://pycqa.github.io/isort/) for import organization: `isort .`
- Use [mypy](http://mypy-lang.org/) for static type checking: `mypy .`
- Use Google-style docstrings for all public functions, classes, and methods.
- Adhere to Clean Code principles (Uncle Bob) and ArjanCodes' best practices for readability, maintainability, and modularity.
- Proactively refactor to avoid code smells and anti-patterns.
- Practice dependency injection to decouple components and improve testability.
- Prefer immutable data structures for fixed data (e.g., tuples over lists).
- Use the standard library's `logging` module for all logging (never use print for logging).
- Handle exceptions gracefully; avoid bare `except` clauses.
- Validate all inputs and never expose sensitive data.

## Testing
- Use [pytest](https://docs.pytest.org/) for all testing: `uv run pytest`
- Use [pytest-cov](https://pytest-cov.readthedocs.io/) for coverage: `uv run pytest --cov`


## Data & Configuration
- Use [pydantic](https://docs.pydantic.dev/) for data models.
- Use [pydantic-settings](https://docs.pydantic.dev/latest/usage/pydantic_settings/) for configuration management. Never hardcode secrets or config in code.
- Use [SQLModel](https://sqlmodel.tiangolo.com/) for ORM/database models.

## CLI Applications
- Use [typer](https://typer.tiangolo.com/) for CLI applications.

## Documentation
- Keep the README and all documentation up to date.
- Use clear, consistent formatting and section headers.

## Context7 Integration
- To enable up-to-date code and documentation context, configure Context7 MCP as follows:

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
```

- For remote Context7 MCP, use:

```json
{
  "mcpServers": {
    "context7": {
      "url": "https://mcp.context7.com/mcp"
    }
  }
}
```

- For more, see the [Context7 documentation](https://github.com/upstash/context7).

---

**Summary:**
- Use modern, robust tools for Python development.
- Enforce code quality, security, and maintainability.
- Structure code into small, modular, and testable components.
- Keep documentation and configuration current.


## Core Principles
Follow SOLID principles to ensure clean, scalable code:
- **Single Responsibility Principle (SRP)**: Each class/module has one reason to change. E.g., plugins handle problem generation only (SDD.md, 3.2.3); coordinator manages workflow (SDD.md, 3.2.2).
- **Open-Closed Principle (OCP)**: Open for extension, closed for modification. Use Protocols/interfaces for plugins/output (interface.py) to add features without altering core (PRD.md, 3.4).
- **Liskov Substitution Principle (LSP)**: Subtypes must be substitutable. E.g., any OutputGenerator implementation works without breaking coordinator (SDD.md, 3.2.5).
- **Interface Segregation Principle (ISP)**: Keep interfaces minimal. Protocols define only necessary methods (SDD.md, 3.2.3/3.2.5).
- **Dependency Inversion Principle (DIP)**: Depend on abstractions. Coordinator uses OutputGenerator interface, not concrete PDF (SDD.md, 3.3).

Additional best practices:
- **Pythonic Code**: Adhere to PEP 8/257 (style/docstrings), use built-in generics (e.g., dict[str, any]), avoid typing aliases. In Python 3.14, leverage lazy annotations for performance.
- **Test-Driven Development (TDD)**: Generate code with >80% coverage (PRD.md, 5); use pytest for unit/integration tests (MVP.md, Phase 5).
- **Validation**: Use Pydantic for any models/params (SDD.md, 3.4); validate early to prevent runtime errors.
- **Error Handling**: Log warnings, raise meaningful exceptions; no silent failures (PRD.md, 5).
- **Performance/Scalability**: Optimize for 100+ problems (<5s); entry points for plugins (SDD.md, 3.2.3).
- **Documentation**: Docstrings for all methods/classes; reference PRD/SDD/MVP in comments where relevant.

## OpenAI-Specific Best Practices for AI Agents
Incorporate these from OpenAI's guidelines for building agents (e.g., Assistants API, Codex for code generation):
- **Prompt Engineering**: Use clear, specific prompts with context from PRD/SDD/MVP.md. E.g., "Implement addition plugin per SDD.md 3.2.3 with stacked SVG, following SOLID SRP."
- **Tool Usage**: Agents should use tools (e.g., function calling) for tasks like data retrieval; in Mathtest, integrate with Pydantic for validation.
- **Reasoning and Planning**: Break tasks into steps; max single-agent efficiency before multi-agent (e.g., coordinator as mediator).
- **Memory and Context**: Retain project context (e.g., JSON override in PRD.md 3.2); use existing docs for routines.
- **Model Selection**: Start with powerful models (e.g., GPT-4 equivalent) for complex tasks; simplify for cheaper ones.
- **Iteration and Testing**: Generate, test with pytest, refine—build smart then dumb down for reliability.
- **Safety/Reliability**: Prioritize workflows; avoid hallucinations by grounding in PRD/SDD/MVP.md.

## Project-Specific Guidelines
- **Alignment with Docs**: Code must match PRD.md (features, e.g., JSON override in 3.2), SDD.md (architecture, e.g., vertical stacking in plugins, 3.2.3), MVP.md (scope, e.g., addition/subtraction only).
- **MVP Focus**: Limit to addition, subtraction (MVP.md); expand later.
- **Extensibility**: Ensure coordinator is UI-agnostic (PRD.md, 3.4); use Protocols for loose coupling.
- **Review AI Output**: Always manually review for smells (e.g., tight coupling); run mypy/black/pytest.

Agents following these will produce high-quality contributions. For updates, consult the latest PRD/SDD/MVP.md.