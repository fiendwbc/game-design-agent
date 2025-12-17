# Tasks: Multi-Agent Game Analysis System

**Input**: Design documents from `/specs/001-multi-agent-game-analyzer/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Summary

| Phase | Description | Tasks |
|-------|-------------|-------|
| Phase 1 | Setup | 8 |
| Phase 2 | Foundational | 12 |
| Phase 3 | US1 - Automated Game Play | 14 |
| Phase 4 | US2 - Mechanics Analysis | 8 |
| Phase 5 | US3 - UI Flow Mapping | 6 |
| Phase 6 | US4 - Art Style Analysis | 6 |
| Phase 7 | US5 - Document Generation | 8 |
| Phase 8 | US6 - QA Review | 5 |
| Phase 9 | Polish | 6 |
| **Total** | | **73** |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure per plan.md in src/
- [x] T002 Initialize Python project with uv and create pyproject.toml
- [x] T003 Add core dependencies: langchain>=1.0, langgraph>=1.0, google-genai>=1.50
- [x] T004 [P] Add utility dependencies: opencv-python, mss, pydirectinput, pydantic>=2.0
- [x] T005 [P] Add CLI dependencies: typer, rich
- [x] T006 [P] Add dev dependencies: pytest, pytest-asyncio, ruff, mypy
- [x] T007 [P] Configure ruff and mypy in pyproject.toml
- [x] T008 Create .env.example with GOOGLE_API_KEY placeholder

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Core Models (Shared by all stories)

- [x] T009 [P] Create base enums (SessionStatus, PlayStrategy, LogLevel, ActionType) in src/models/__init__.py
- [x] T010 [P] Create WindowRegion and SessionConfig models in src/models/session.py
- [x] T011 [P] Create NormalizedCoordinate and ActionCommand models in src/models/session.py
- [x] T012 [P] Create PlaySession model with full validation in src/models/session.py
- [x] T013 [P] Create AnalysisLog model in src/models/session.py

### Core Infrastructure

- [x] T014 Implement config management with .env support in src/config.py
- [x] T015 [P] Implement logging utilities with 3 levels (minimal/detailed/debug) in src/utils/logging.py
- [x] T016 [P] Implement retry decorator with exponential backoff in src/utils/retry.py
- [x] T017 Create BaseAgent abstract class with Gemini integration in src/agents/base.py
- [x] T018 Setup LangGraph state schema in src/orchestrator/graph.py
- [x] T019 Create CLI skeleton with typer in src/main.py
- [x] T020 Setup pytest fixtures in tests/conftest.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Automated Game Play Session (Priority: P1) 🎯 MVP

**Goal**: Configure and run automated gameplay on a target game window with visual AI decision-making

**Independent Test**: Launch system against any clickable game window and observe click/drag/wait actions based on visual input

### Capture Module

- [ ] T021 [P] [US1] Implement screen capture with mss (30+ FPS) in src/capture/screen.py
- [ ] T022 [P] [US1] Implement video segment synthesis with OpenCV in src/capture/video.py
- [ ] T023 [US1] Add region selection utility for window capture in src/capture/screen.py

### Control Module

- [ ] T024 [US1] Implement input controller with pydirectinput in src/control/input.py
- [ ] T025 [US1] Add coordinate normalization (0-1000 to screen coords) in src/control/input.py

### Player-Agent

- [ ] T026 [US1] Implement Player-Agent with gemini-2.0-flash in src/agents/player.py
- [ ] T027 [US1] Create action parsing prompt for click/drag/press/wait commands in src/agents/player.py
- [ ] T028 [US1] Add game-over/completion detection logic in src/agents/player.py

### Memory Module (Play Log)

- [ ] T029 [US1] Implement play_log memory module in src/memory/play_log.py

### Orchestrator Integration

- [ ] T030 [US1] Implement observe-think-act-record loop in src/orchestrator/nodes.py
- [ ] T031 [US1] Add step limiting and session termination in src/orchestrator/graph.py

### CLI Commands

- [ ] T032 [US1] Add `select-region` command in src/main.py
- [ ] T033 [US1] Add `run` command with session configuration in src/main.py
- [ ] T034 [US1] Add progress display with rich in src/main.py

**Checkpoint**: User Story 1 complete - system can play games automatically

---

## Phase 4: User Story 2 - Game Mechanics Analysis (Priority: P2)

**Goal**: Analyze and extract game mechanics (damage formulas, economy systems, core loops) during gameplay

**Independent Test**: Provide pre-recorded gameplay video clips and verify structured mechanics data extraction

### Models

- [ ] T035 [P] [US2] Create DamageEvent, EconomyEvent models in src/models/analysis.py
- [ ] T036 [P] [US2] Create MechanicsState model with LevelStructure enum in src/models/analysis.py

### Memory Module

- [ ] T037 [US2] Implement mechanics_state memory module in src/memory/mechanics_state.py

### Mechanics-Analyst Agent

- [ ] T038 [US2] Implement Mechanics-Analyst with gemini-3-pro-preview in src/agents/mechanics.py
- [ ] T039 [US2] Create HP bar detection and damage calculation prompt in src/agents/mechanics.py
- [ ] T040 [US2] Add economy system identification logic in src/agents/mechanics.py
- [ ] T041 [US2] Add core loop and level structure detection in src/agents/mechanics.py

### Orchestrator Integration

- [ ] T042 [US2] Add mechanics analysis node to LangGraph in src/orchestrator/nodes.py

**Checkpoint**: User Story 2 complete - system analyzes game mechanics

---

## Phase 5: User Story 3 - UI Flow Mapping (Priority: P2)

**Goal**: Automatically map all UI screens and their navigation relationships

**Independent Test**: Provide recordings of menu navigation and verify correct node-edge graph output

### Models

- [ ] T043 [P] [US3] Create UINode, UIEdge models in src/models/analysis.py
- [ ] T044 [P] [US3] Create UIFlowGraph model with add_node/add_edge methods in src/models/analysis.py

### Memory Module

- [ ] T045 [US3] Implement ui_flow_graph memory module in src/memory/ui_flow_graph.py

### UI-Agent

- [ ] T046 [US3] Implement UI-Agent with gemini-3-pro-preview in src/agents/ui_flow.py
- [ ] T047 [US3] Create screen state identification prompt in src/agents/ui_flow.py
- [ ] T048 [US3] Add transition detection and edge recording logic in src/agents/ui_flow.py

**Checkpoint**: User Story 3 complete - system maps UI flows

---

## Phase 6: User Story 4 - Art Style Analysis (Priority: P2)

**Goal**: Analyze and document the game's visual style (color palette, art style, effects)

**Independent Test**: Provide representative screenshots and verify color palette and style descriptor output

### Models

- [ ] T049 [P] [US4] Create Color, EffectPattern models in src/models/analysis.py
- [ ] T050 [P] [US4] Create ArtStyleState model in src/models/analysis.py

### Memory Module

- [ ] T051 [US4] Implement art_style_state memory module in src/memory/art_style_state.py

### Art-Agent

- [ ] T052 [US4] Implement Art-Agent with gemini-3-pro-preview in src/agents/art_style.py
- [ ] T053 [US4] Create color palette extraction prompt in src/agents/art_style.py
- [ ] T054 [US4] Add style tag and effect pattern identification in src/agents/art_style.py

**Checkpoint**: User Story 4 complete - system analyzes art style

---

## Phase 7: User Story 5 - Document Generation (Priority: P3)

**Goal**: Compile all analysis into professional documents (GDD, numerical tables, art report)

**Independent Test**: Provide mock structured analysis data and verify correctly formatted documents

### Models

- [ ] T055 [P] [US5] Create DocumentType, QAStatus enums in src/models/document.py
- [ ] T056 [P] [US5] Create QAFeedback, GeneratedDocument models in src/models/document.py

### Doc-Writer Agent

- [ ] T057 [US5] Implement Doc-Writer with gemini-3-pro-preview in src/agents/doc_writer.py
- [ ] T058 [US5] Create GDD generation template and prompt in src/agents/doc_writer.py
- [ ] T059 [US5] Create numerical analysis generation in src/output/numerical.py
- [ ] T060 [US5] Create art report generation in src/output/art_report.py

### Output Module

- [ ] T061 [US5] Implement GDD markdown generation in src/output/gdd.py
- [ ] T062 [US5] Add document file export (JSON + Markdown) in src/output/__init__.py

**Checkpoint**: User Story 5 complete - system generates documents

---

## Phase 8: User Story 6 - Quality Assurance Review (Priority: P3)

**Goal**: Self-check generated documents for completeness and consistency

**Independent Test**: Provide documents with intentional gaps/inconsistencies and verify QA-Critic identifies them

### QA-Critic Agent

- [ ] T063 [US6] Implement QA-Critic with gemini-3-pro-preview in src/agents/qa_critic.py
- [ ] T064 [US6] Create completeness validation prompt in src/agents/qa_critic.py
- [ ] T065 [US6] Create consistency validation prompt in src/agents/qa_critic.py

### Iterative Refinement

- [ ] T066 [US6] Implement QA feedback loop in src/orchestrator/nodes.py
- [ ] T067 [US6] Add document regeneration based on QA feedback in src/agents/doc_writer.py

**Checkpoint**: User Story 6 complete - system validates document quality

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T068 [P] Add `export` CLI command for analysis results in src/main.py
- [ ] T069 [P] Implement session state checkpointing (optional) in src/memory/__init__.py
- [ ] T070 Add cleanup for temporary files (video buffers, screenshots) in src/utils/__init__.py
- [ ] T071 [P] Create config.json example and validation in src/config.py
- [ ] T072 Run end-to-end test with sample game
- [ ] T073 Validate against quickstart.md scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ─────────────────────────────────────────────────────────────►
                                                                              │
Phase 2: Foundational ────────────────────────────────────────────────────────►
                         │
                         ▼ (blocks all user stories)
         ┌───────────────┼───────────────┬───────────────┐
         │               │               │               │
         ▼               ▼               ▼               ▼
Phase 3: US1      Phase 4: US2    Phase 5: US3    Phase 6: US4
(MVP - Play)      (Mechanics)     (UI Flow)       (Art Style)
         │               │               │               │
         └───────────────┴───────────────┴───────────────┘
                         │
                         ▼ (US5 depends on US2-4 analysis data)
                   Phase 7: US5
                   (Documents)
                         │
                         ▼ (US6 depends on US5 documents)
                   Phase 8: US6
                   (QA Review)
                         │
                         ▼
                   Phase 9: Polish
```

### User Story Dependencies

| Story | Depends On | Can Parallel With |
|-------|------------|-------------------|
| US1 - Automated Play | Foundational | None (MVP) |
| US2 - Mechanics | Foundational + US1 data | US3, US4 |
| US3 - UI Flow | Foundational + US1 data | US2, US4 |
| US4 - Art Style | Foundational + US1 data | US2, US3 |
| US5 - Documents | US2, US3, US4 analysis | None |
| US6 - QA Review | US5 documents | None |

### Parallel Opportunities

**Setup Phase (T001-T008)**:
- T004, T005, T006, T007 can run in parallel

**Foundational Phase (T009-T020)**:
- T009-T013 (models) can run in parallel
- T015, T016 (utils) can run in parallel

**User Story Phases**:
- US2 (T035-T042), US3 (T043-T048), US4 (T049-T054) can run in parallel after US1 completes
- Within each story, model tasks marked [P] can run in parallel

---

## Parallel Example: After Foundational Complete

```bash
# Team can split user stories:

# Developer A: User Story 1 (MVP)
Task: "Implement screen capture with mss in src/capture/screen.py"
Task: "Implement video segment synthesis with OpenCV in src/capture/video.py"
...

# After US1 complete, these can run in parallel:

# Developer B: User Story 2 (Mechanics)
Task: "Create DamageEvent, EconomyEvent models in src/models/analysis.py"
Task: "Implement Mechanics-Analyst in src/agents/mechanics.py"
...

# Developer C: User Story 3 (UI Flow)
Task: "Create UINode, UIEdge models in src/models/analysis.py"
Task: "Implement UI-Agent in src/agents/ui_flow.py"
...

# Developer D: User Story 4 (Art Style)
Task: "Create Color, EffectPattern models in src/models/analysis.py"
Task: "Implement Art-Agent in src/agents/art_style.py"
...
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (Automated Game Play)
4. **STOP and VALIDATE**: Test with real game window
5. Demo: System can play games and log actions

### Incremental Delivery

| Milestone | Stories Complete | Demo Capability |
|-----------|------------------|-----------------|
| MVP | US1 | Auto-play games |
| Alpha | US1 + US2/US3/US4 | Play + partial analysis |
| Beta | US1-US5 | Play + full analysis + documents |
| Release | US1-US6 | Play + analysis + QA'd documents |

### Suggested Sprint Plan (if applicable)

- **Sprint 1**: Phase 1-2 (Setup + Foundational) + Phase 3 (US1 MVP)
- **Sprint 2**: Phase 4-6 (US2 + US3 + US4) in parallel
- **Sprint 3**: Phase 7-8 (US5 + US6) + Phase 9 (Polish)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each user story is independently completable after Foundational
- US1 is the MVP - stop and validate before proceeding
- US2/US3/US4 can run in parallel after US1
- US5 requires US2-4 analysis data
- US6 requires US5 documents
- Commit after each task or logical group
