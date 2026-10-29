# Agents Instructions

This file contains additional guidance for AI agents and other AI editors including AI PR reviewers.

## Project Context

- Hercules is an open-source hybrid power plant simulator.
- Hercules is often paired with Hycon for controls and ENPAX for cost modeling.

## Rules for agents

- Prefer simple, concise implementations over clever abstractions.
- Keep changes scoped to the requested task. Avoid broad refactors unless requested.
- Reduce the verbosity of your comments, more text and detail is not always better.
- If `.venv/` exists, use `.venv/bin/python` for running examples, tests, etc. (e.g. `.venv/bin/python -m pytest`).
- Append "(AI)" to inline comments written by an agent (not docstrings).

## Communication

- Avoid flattery, avoid filler phrases, prefer technical clarity over marketing tone.

## Git rules

- Agents can use information gathering commands like diff
- Agents should never push, pull or fetch
- Agents should avoid committing, but can commit with permission

## Commands

- Test: `.venv/bin/python -m pytest tests/` when `.venv/` exists; otherwise `pytest tests/` (or a single file, e.g. `pytest tests/battery_simple_test.py`).
- Lint/format: `ruff check --fix . && ruff format .`
- Pre-commit: `pre-commit run --all-files`

## Python Style

- Use Google-style docstrings for public functions, classes, and methods
- Docstring `Args` entries should state units where relevant
  (e.g. `energy_capacity (float): Deliverable energy capacity in kWh.`).
- Format with Ruff.
- Run `pre-commit run --all-files` before finishing.
- Favor readability first: straightforward control flow, minimal nesting, clear
  names. Avoid heavy abstractions (extra inheritance layers, dataclasses,
  metaclasses) beyond what `ComponentBase`
  (`hercules/plant_components/component_base.py`) requires.

## Tests

- Write self-contained test functions, comprehensible to a human reviewer, with simple
  inline inputs (no fixtures) and a short comment stating the purpose.
- Focus on core behavior and catching regressions rather than exhaustive edge cases;
  prefer fewer, targeted tests.

## Important references in docs

- Follow the unit conventions in docs/units.md
