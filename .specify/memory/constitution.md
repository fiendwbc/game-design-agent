<!--
===============================================================================
SYNC IMPACT REPORT
===============================================================================
Version Change: 0.0.0 → 1.0.0 (MAJOR - Initial constitution establishment)

Modified Principles: N/A (initial creation)

Added Sections:
  - Core Principles (4 principles)
    - I. Code Quality Standards
    - II. Testing Standards
    - III. User Experience Consistency
    - IV. Performance Requirements
  - Quality Gates (new section)
  - Development Workflow (new section)
  - Governance

Removed Sections: N/A (initial creation)

Templates Requiring Updates:
  - .specify/templates/plan-template.md: ✅ No changes needed (Constitution Check
    section already exists and will be populated based on these principles)
  - .specify/templates/spec-template.md: ✅ No changes needed (User Scenarios and
    Success Criteria sections align with UX and Performance principles)
  - .specify/templates/tasks-template.md: ✅ No changes needed (Test phases and
    quality checkpoints align with Testing Standards principle)

Follow-up TODOs: None
===============================================================================
-->

# Game Design Agent Constitution

## Core Principles

### I. Code Quality Standards

All code in this project MUST adhere to the following non-negotiable quality standards:

- **Type Safety**: All Python code MUST include type hints for function parameters and
  return values. Pydantic models MUST be used for data validation at system boundaries.
- **Modularity**: Each agent (Player-Agent, Mechanics-Analyst, UI-Agent, Art-Agent,
  Doc-Writer, QA-Critic) MUST be implemented as an independent, self-contained module
  with clearly defined interfaces.
- **Single Responsibility**: Functions MUST have a single, well-defined purpose.
  Functions exceeding 50 lines SHOULD be refactored into smaller units.
- **Documentation**: Public APIs and complex algorithms MUST include docstrings.
  Configuration options MUST be documented with examples.
- **Error Handling**: All external API calls (Gemini, pydirectinput, mss) MUST have
  explicit error handling with meaningful error messages. Silent failures are prohibited.

**Rationale**: A multi-agent system requires clean interfaces between components.
Type safety and modularity ensure agents can be developed, tested, and maintained
independently while integrating reliably.

### II. Testing Standards

Testing is MANDATORY for this project. The following requirements apply:

- **Test-First Development**: For new features affecting agent behavior or data
  processing, tests MUST be written before implementation (Red-Green-Refactor).
- **Unit Test Coverage**: Core logic (action parsing, memory management, document
  generation) MUST have unit tests covering success paths and error conditions.
- **Integration Tests**: Agent-to-agent communication and LangGraph state transitions
  MUST have integration tests verifying correct data flow.
- **Contract Tests**: JSON schemas for agent outputs (action JSON, mechanics JSON,
  UI flow JSON) MUST have contract tests ensuring schema compliance.
- **Visual Regression**: Changes to screenshot processing or video analysis SHOULD
  include visual regression tests with sample game footage.

**Rationale**: The system relies on multiple agents producing structured outputs that
other agents consume. Testing ensures outputs remain compatible and transformations
are correct across the pipeline.

### III. User Experience Consistency

All user-facing outputs MUST maintain consistency:

- **Document Format Stability**: Generated GDD, numerical analysis, and art style
  reports MUST follow established schemas. Schema changes require version increments.
- **Output Reproducibility**: Given the same game footage and configuration, the
  system SHOULD produce semantically equivalent outputs (acknowledging LLM variance).
- **Progress Visibility**: Long-running operations MUST provide progress feedback
  (step counts, current phase, estimated completion).
- **Error Clarity**: User-visible errors MUST include: what failed, why it failed,
  and suggested remediation steps.
- **Localization Ready**: User-facing strings SHOULD be externalized to support
  future internationalization (Chinese/English at minimum).

**Rationale**: The system targets game design teams who need reliable, professional
outputs. Consistency in format and quality builds trust and enables workflow
integration.

### IV. Performance Requirements

The system MUST meet these performance targets:

- **Real-time Operation**: The Player-Agent loop (Observe → Think → Act → Record)
  MUST complete within 10 seconds per iteration to maintain game responsiveness.
- **Memory Efficiency**: Memory modules (play_log, mechanics_state, ui_flow_graph,
  art_style_state) MUST implement pagination or summarization to stay within
  Gemini's context window limits.
- **Video Processing**: Screenshot capture (mss) MUST achieve 30+ FPS. Video
  encoding for Gemini MUST complete within 2 seconds for a 5-second clip.
- **Document Generation**: Final document generation phase SHOULD complete within
  5 minutes for a standard play session (50-100 game steps).
- **Resource Cleanup**: All video buffers, temporary files, and API connections
  MUST be properly released after use. Memory leaks are prohibited.

**Rationale**: The system operates in a real-time game environment where delays
break the feedback loop. Performance constraints ensure the system remains usable
as a practical tool rather than a proof-of-concept.

## Quality Gates

The following gates MUST be passed before code is merged:

| Gate | Requirement | Enforcement |
|------|-------------|-------------|
| Linting | All code passes ruff/black checks | CI automated |
| Type Checking | mypy passes with no errors | CI automated |
| Unit Tests | 100% of unit tests pass | CI automated |
| Integration Tests | All integration tests pass | CI automated |
| Contract Tests | All agent output schemas validate | CI automated |
| Performance | Critical paths meet timing requirements | Manual review |
| Documentation | Public APIs documented | PR review |

## Development Workflow

### Code Review Requirements

- All changes MUST be submitted via pull request
- PRs MUST have at least one approval before merge
- PRs affecting agent interfaces MUST be reviewed by component owners
- Large PRs (>500 lines) SHOULD be split into smaller, logical commits

### Branch Strategy

- `main`: Production-ready code only
- `develop`: Integration branch for feature work
- `feature/*`: Individual feature development
- `fix/*`: Bug fixes
- `docs/*`: Documentation-only changes

### Commit Standards

- Commit messages MUST follow conventional commits format
- Breaking changes MUST be marked with `BREAKING CHANGE:` in commit body
- Each commit SHOULD be atomic and independently buildable

## Governance

This constitution is the authoritative source for development standards in the
Game Design Agent project. All contributors MUST comply with these principles.

### Amendment Process

1. Propose changes via pull request to this file
2. Changes require approval from project maintainers
3. Breaking changes to principles require migration plan
4. Version increment follows semantic versioning:
   - MAJOR: Principle removal or incompatible redefinition
   - MINOR: New principle or significant expansion
   - PATCH: Clarification or wording improvement

### Compliance

- All PRs MUST verify compliance with applicable principles
- Reviewers MUST check Constitution compliance as part of review
- Exceptions MUST be documented in PR description with justification
- Complexity beyond these principles MUST be explicitly justified

**Version**: 1.0.0 | **Ratified**: 2025-12-16 | **Last Amended**: 2025-12-16
