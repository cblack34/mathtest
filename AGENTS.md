# AGENTS.md

A single, authoritative brief for AI coding agents working in this repository. Keep it short, specific, and up to date. Treat this file as the **source of truth** for agent behavior and constraints.

> If any instruction here conflicts with other docs, **this file wins for agents**. Humans can use README/CONTRIBUTING; agents must follow AGENTS.md.

---

## 1) Purpose & Scope

* Enable safe, high‑quality, repeatable changes to this codebase using OpenAI‑class coding models.
* Optimize for correctness, security, maintainability, and testability.
* Minimize tokens/cost by using targeted context and efficient workflows.
* Applies to local and CI agents, including ChatGPT/Codex-style tools, Assistants, or CLI agents.

**Non‑goals:** speculative refactors, large cross‑cutting redesigns, or vendor‑specific lock‑in without approval.

---

## 2) Quickstart (Commands agents may run)

Always use the local **.venv** managed by **uv**.

```bash
# Create & sync environment
uv venv --seed --python 3.14
uv sync
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Add packages
uv add <package>                 # prod deps
uv add --group dev <package>     # dev deps

# Code quality
uv run black .
uv run isort .
uv run mypy .

# Tests
uv run pytest                     # fast unit tests
uv run pytest --cov               # with coverage

```

---

## 3) Code Style & Quality (enforced)

* **Imports:** use **absolute imports** only.
* **Style:** follow **PEP 8**; format with **Black**; organize imports with **isort**.
* **Types:** **mypy** required on all changed files; prefer precise types; avoid `Any` leaks.
* **Docstrings:** use **Google‑style** for all public symbols.
* **Clean Code principles:** small, cohesive modules; meaningful names; single responsibility.
* **Refactoring:** proactively remove code smells/anti‑patterns; prefer composition over inheritance.
* **Dependency injection:** pass dependencies in constructors/factories; avoid global state.
* **Immutability:** use immutable types for fixed data (e.g., tuples, `frozenset`).
* **Logging:** use `logging` (never `print`) with structured messages; no secrets in logs.
* **Exceptions:** handle narrowly; avoid bare `except`; raise meaningful errors.
* **Input validation:** validate early (use Pydantic models/validators where applicable).
* **Security:** never hard‑code secrets; use settings and env vars; scrub sensitive data from outputs.
* **Python 3.14 annotations:** Lazy by default (PEP 649/749). Do **not** use `from __future__ import annotations`; avoid quoted forward refs. For runtime needs, use `typing.get_type_hints()` or `annotationlib.get_annotations()`.

---

## 4) Testing Policy

* **Framework:** `pytest` with `pytest-cov`.
* **Coverage target:** ≥ **80%** for new/changed code.
* **Kinds of tests:** unit first; integration where value is high; avoid end‑to‑end by default.
* **Determinism:** no network or time‑based flakiness; use fakes/mocks.
* **Test gen:** when creating code, also generate corresponding tests.

Run:

```bash
uv run pytest --maxfail=1 -q
uv run pytest --cov
```

---

## 5) Data Models & Configuration

* **Data models:** use **Pydantic**.
* **Settings:** use **pydantic‑settings**; keep `.env`/secrets out of VCS.
* **ORM/DB:** use **SQLModel** for models and persistence.

---

## 6) CLI Applications

* Use **Typer** for CLIs (type‑safe, autocompletion, built‑in help).

---

## 7) Documentation

* Keep `README.md` and in‑repo docs current.
* Use clear headings, task‑oriented examples, and short code snippets.
* Reference PRD/SDD/MVP where relevant in docstrings or comments.

---

## 8) External Docs via Context7 MCP

Use Context7 **only** to fetch *external library/framework documentation* (e.g., **pytest**, **pydantic**, **SQLModel**, **Typer**) into the model’s context. Do **not** use it for our internal modules or project files.

**Why/what it does:** Context7 provides up‑to‑date, version‑specific docs and examples pulled from official sources and injects them into the prompt. It’s purpose‑built for dependency APIs, not for reading this repo. Configure it in your MCP client (e.g., Cursor, Claude Desktop) and request specific libraries + versions. Examples:

* “Use context7 to load `pytest` fixtures API (pytest==8.x)`.”
* “Use context7 to load `pydantic-settings` 2.x configuration examples.”

**Configuration (local):**

```json
{
  "mcpServers": {
    "context7": { "command": "npx", "args": ["-y", "@upstash/context7-mcp"] }
  }
}
```

**Configuration (remote):**

```json
{
  "mcpServers": {
    "context7": { "url": "https://mcp.context7.com/mcp" }
  }
}
```

**Usage rules:**

* Scope requests narrowly: library name + **pinned version** + topic (e.g., “`sqlmodel 0.0.x` session lifecycle”).
* Prefer *exact* endpoints/pages (symbols, functions) over broad topic pulls.
* Never paste large doc dumps into code/comments; summarize, cite section names, and keep snippets minimal.
* Treat third‑party MCP servers as **untrusted**: no secrets; review outputs; keep token budgets tight; log library + version pulled.
* For internal code context, read files directly from the repo; do **not** use Context7.

**Security notes:**

* Use only trusted MCP servers (e.g., the official `@upstash/context7-mcp`). Audit community servers before use; lock versions and review permissions. Supply‑chain incidents with malicious MCP servers have been reported — rotate credentials if compromise is suspected.

---

## 9) Core Architectural Principles

Follow **SOLID**:

* **SRP:** each module has one reason to change (e.g., plugins only generate problems; coordinator manages workflow).
* **OCP:** extend via protocols/interfaces; do not modify stable cores.
* **LSP:** any subtype must be drop‑in substitutable.
* **ISP:** keep interfaces minimal and focused.
* **DIP:** depend on abstractions; consumers import protocols, not concrete classes.

**Additional:**

* Pythonic code (PEP 8/257), modern typing (`dict[str, T]` etc.).
* Validation with Pydantic; fail fast with clear errors.
* Performance: optimize for 100+ problems < 5s where specified; prefer linear algorithms; cache pure functions when helpful.
* Coordinator must be **UI‑agnostic**; expose clean programmatic interfaces.

### 9.1 Python 3.14 Feature Guidance

**Version target:** Python 3.14 across the repo.

**Deferred (lazy) annotations — PEP 649 & PEP 749:**

* Remove `from __future__ import annotations` (deprecated; no longer needed in 3.14).
* Don’t quote forward references.
* If you need runtime annotation values, use `annotationlib.get_annotations()` or `typing.get_type_hints()`; avoid reading `__annotations__` directly (especially on classes). See porting notes in 3.14 docs.

**Template string literals — PEP 750:**

* Use `t"..."` only when you need **templating semantics** (placeholders intended for later substitution). Keep using f-strings for straightforward interpolation.
* Do not mix `t` and `f` prefixes in the same literal; don’t concatenate template objects and plain strings without explicit conversion.
* For untrusted input, always validate/escape via a dedicated formatter function before rendering templates.

**Multiple interpreters — PEP 734:**

* Prefer the stdlib `concurrent.interpreters` module when you need isolated, in‑process concurrency.
* Avoid cross‑interpreter object sharing; communicate via queues/channels.

**Free‑threaded Python (no‑GIL) — PEP 779 / PEP 703):**

* Supported in 3.14 but **optional**. Do not rely on the GIL for safety; make shared state thread‑safe.
* Only enable no‑GIL CI when dependencies are compatible.

**Porting checklist to 3.14:**

* [ ] Remove all `from __future__ import annotations`.
* [ ] Unquote forward refs; ensure libraries that introspect annotations use `annotationlib`/`typing.get_type_hints`.
* [ ] Audit any direct reads of `__annotations__` and replace with supported APIs.
* [ ] Keep templating secure; adopt t‑strings only where templates are truly needed.

---

## 10) OpenAI‑Specific Agent Practices

### 10.1 Reasoning & Planning

* Break work into **plan → execute → verify → summarize**.
* Keep detailed reasoning **internal**; surface concise rationales only.
* Before code changes, write a short **plan** and a **test plan**.

### 10.2 Tool Use

* Use tools for retrieval, execution, and validation: running tests, type checks, linters.
* Prefer structured outputs (JSON) for intermediate steps; validate with Pydantic where possible.

### 10.3 Model Selection

* Use strongest available model for **planning/design**; switch to efficient model for **repetitive edits**.
* Avoid unnecessary re‑prompting; cache facts from docs; reuse context.

### 10.4 Iteration & Self‑check

* After generating code, **run** `mypy`, `pytest`, and linters; fix before proposing PRs.
* Verify outputs against requirements in PRD/SDD/MVP and this file.

### 10.5 Safety & Reliability

* Never fabricate APIs or files; if unknown, state what is missing and request targeted docs.
* Avoid destructive changes (schema drops, API removals) without explicit approval.
* Respect licenses and third‑party attribution.

---

## 11) Prompting Patterns (for agents)

Use these compact templates to steer actions. Keep to the token budget and avoid fluff.

### 11.1 Task Brief (single feature)

```
You are a coding agent working in this repo. Goal: <one‑sentence outcome>.
Constraints: follow AGENTS.md; only edit files under <paths>; keep diffs small.
Plan: list 3‑5 steps.
Deliverables: PR with code + tests, summary explaining design/trade‑offs.
Verification: run mypy/pytest/linters; include results.
```

### 11.2 Bug Fix

```
Given failing test <path::name> and error <message>, fix minimal surface area.
Include regression test. Keep public API stable unless specified.
```

### 11.3 Refactor (safe)

```
Refactor for readability/maintainability without changing behavior.
Add or update tests to prove no behavior change.
```

### 11.4 Retrieval Discipline

```
Before coding, list exact files to read (max N). Summarize key constraints in 5 bullets.
If info is missing, stop and request specific docs.
```

### 11.5 Output Discipline

```
Return: (1) diff or patch; (2) commands you ran; (3) test/linters output; (4) brief rationale.
No verbose chain‑of‑thought.
```

---

## 12) Project‑Specific Guardrails

* **Scope (MVP):** implement **addition** and **subtraction** only unless directed otherwise.
* **Extensibility:** plugins vertically stack; coordinator mediates; use Protocols for loose coupling.
* **Review:** humans review for smells/tight coupling; always run `mypy/black/pytest` before proposing changes.

---

## 13) PR & Commit Conventions

* Use **Conventional Commits** (e.g., `feat:`, `fix:`, `docs:`, `refactor:`).
* PR description must include:

  * Problem statement & acceptance criteria
  * Approach & rationale (brief)
  * Test plan & results (paste `pytest --cov` summary)
  * Risk/Security considerations

---

## 14) Stop Conditions

Agents must stop and request approval when:

* A change alters public APIs, CLI interfaces, or database schemas.
* Any migration, data deletion, or large refactor is proposed.
* Coverage would drop below target or tests cannot be made deterministic.
* Secrets/credentials would be introduced or rotated.

---

## 15) Checklist (agent must satisfy before proposing PR)

* [ ] Read relevant sections of PRD.md/SDD.md/MVP.md.
* [ ] Kept edits minimal, modular, and in‑scope.
* [ ] Added/updated **tests** and **docstrings**.
* [ ] Ran: `black`, `isort`, `mypy`, `pytest --cov` (all green, coverage ≥ 80%).
* [ ] No prints; only `logging`. No bare `except`.
* [ ] No secrets or hard‑coded config; used pydantic‑settings.
* [ ] Absolute imports only.
* [ ] Removed all `from __future__ import annotations`; unquoted forward references; updated any annotation-introspection to use `annotationlib.get_annotations`/`typing.get_type_hints`.
* [ ] If using templating (SQL/HTML/shell), prefer t-strings with an explicit processing function; no f-strings for untrusted input.
* [ ] Changelog/PR body completed with rationale and test results.

---

## 16) Appendix: Commands & Tools (recap)

* **uv** for env/pkg mgmt (see Quickstart).
* **Formatting & QA:** `black`, `isort`, `mypy`, `pytest`, `pytest-cov`.
* **Models & Config:** `pydantic`, `pydantic‑settings`.
* **ORM:** `SQLModel`.
* **CLI:** `typer`.

---

## 17) Maintenance

* Keep this file under **500 lines**; prune stale rules.
* Update when dependencies, build, or policies change.
* For monorepos, place an `AGENTS.md` at the root and optionally in key subprojects with non‑conflicting, more specific rules.

---

## 18) Summary for Agents

* Use modern, robust Python tooling (`uv`, `.venv`).
* Enforce code quality, security, and maintainability.
* Keep changes small, modular, tested, and documented.
* Ground in PRD/SDD/MVP and this AGENTS.md; do not guess.
