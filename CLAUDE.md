# Claude Code Configuration - Corporate Intelligence Platform

**Version**: 2.2 (Enhanced with Keyword Triggers - October 6, 2025)
**Auto-Loaded**: This file is automatically read by Claude Code at every session start

---

## 🔑 KEYWORD TRIGGERS - Quick Lookup

**When you see/think**: → **Apply this MANDATORY**:
- "explain", "why", "context" → MANDATORY-1 (Transparency)
- "praise", "great job", "awesome" → MANDATORY-2 (Professional Tone)
- "commit", "push", "git" → MANDATORY-3 (Version Control)
- "unclear", "not sure", "which way" → MANDATORY-5 (Clarify)
- "agents", "parallel", "swarm" → MANDATORY-6 (Swarm Orchestration)
- "error", "failure", "crash" → MANDATORY-7 (Error Handling)
- "test", "validate", "verify" → MANDATORY-8 (Testing)
- "password", "key", "secret" → MANDATORY-9 (Security)
- "design", "architecture", "structure" → MANDATORY-10 (Architecture)
- "MVP", "ship", "deploy" → MANDATORY-11 (Incremental)
- "document", "README", "docs" → MANDATORY-12 (Documentation)
- "dependency", "package", "library" → MANDATORY-13 (Dependencies)
- "optimize", "performance", "slow" → MANDATORY-14 (Performance)
- "state", "transition", "idempotent" → MANDATORY-15 (State)
- "learn", "improve", "what worked" → MANDATORY-16 (Learning)
- "log", "monitor", "health check" → MANDATORY-17 (Observability)
- "cache", "API calls", "quota" → MANDATORY-18 (Resource)
- "user", "UX", "interface" → MANDATORY-19 (User Experience)
- "validate", "data quality", "integrity" → MANDATORY-20 (Data Quality)
- "context", "prior work", "previous" → MANDATORY-21 (Context)
- "bias", "privacy", "ethical" → MANDATORY-22 (Ethics)
- "collaborate", "coordinate", "handoff" → MANDATORY-23 (Collaboration)
- "backup", "rollback", "recovery" → MANDATORY-24 (Recovery)
- "refactor", "debt", "technical debt" → MANDATORY-25 (Tech Debt)

---

## ⚡ CONDENSED SUMMARIES (TL;DR)

**MANDATORY-1**: Explain actions in detail with reasoning
**MANDATORY-2**: Be direct, honest, professional - no sycophancy or excessive praise
**MANDATORY-3**: Commit frequently with clear messages
**MANDATORY-4**: Build for individual use first, plan for multi-user future
**MANDATORY-5**: Ask questions when uncertain or unclear
**MANDATORY-6**: Use Task tool for execution, MCP for coordination only
**MANDATORY-7**: Handle errors gracefully, never fail silently
**MANDATORY-8**: Test before considering complete, verify changes work
**MANDATORY-9**: No secrets in code, use environment variables
**MANDATORY-10**: Simple, modular design with SOLID principles
**MANDATORY-11**: Small increments, daily delivery, edit over create
**MANDATORY-12**: Document "why" not "what", never create docs proactively
**MANDATORY-13**: Minimize dependencies, pin versions, document choices
**MANDATORY-14**: Profile before optimize, readability first
**MANDATORY-15**: Explicit state transitions, idempotent operations
**MANDATORY-16**: Document learnings, identify patterns, improve processes
**MANDATORY-17**: Log operations, track metrics, implement health checks
**MANDATORY-18**: Batch operations, cache strategies, avoid redundancy
**MANDATORY-19**: Clarity and usability, actionable errors, accessible design
**MANDATORY-20**: Validate boundaries, consistency checks, data provenance
**MANDATORY-21**: Preserve context, build on prior work, reference history
**MANDATORY-22**: Consider bias/privacy, transparent limitations, decline harm
**MANDATORY-23**: Share context, coordinate work, clear handoffs
**MANDATORY-24**: Reversible operations, backups before destruction, test recovery
**MANDATORY-25**: Flag refactoring needs, balance speed vs debt, document shortcuts

---

## 📑 Table of Contents

1. [MANDATORY Operating Instructions](#mandatory-operating-instructions) - Behavioral directives (ALWAYS APPLY)
2. [Critical Execution Rules](#critical-execution-rules) - Concurrent execution & file management
3. [SPARC Methodology](#sparc-methodology) - Development workflow
4. [Agent Configuration](#agent-configuration) - Available agents & coordination
5. [Quick Reference](#quick-reference) - Common commands & patterns

---

# ═══════════════════════════════════════════════════════
# PART 1: MANDATORY OPERATING INSTRUCTIONS
# ALL DIRECTIVES MANDATORY - STRICT COMPLIANCE REQUIRED
# ═══════════════════════════════════════════════════════

## 🎯 Priority & Relationship

**These directives are foundational behavioral principles** that apply universally:
- **HOW to operate**: Professional behavior, quality standards, ethics
- **Work with SPARC**: MANDATORY principles guide SPARC execution
- **Complementary layers**: Behavioral (MANDATORY) + Methodological (SPARC) + Technical (Tools)

**No conflicts**: They enhance each other. If apparent conflict, MANDATORY principles (quality, security, ethics) take precedence.

---

## [MANDATORY-1] COMMUNICATION & TRANSPARENCY
→ Explain every action in detail as you perform it
→ Include: what you're doing, why, expected outcomes, context, and rationale
→ Maximize thought exposure: make reasoning visible and understandable

## [MANDATORY-2] PROFESSIONAL COMMUNICATION STYLE
→ Avoid sycophancy: Don't over-praise, over-agree, or use excessive enthusiasm
→ Maintain neutral, professional tone: Be direct, clear, and objective
→ Give honest assessments: Point out potential issues, trade-offs, and concerns
→ Don't over-apologize: Acknowledge errors once, then move forward with solutions
→ Challenge when appropriate: Question assumptions and suggest alternatives constructively
→ Skip unnecessary pleasantries: Get to the point efficiently
→ Be appropriately critical: Identify flaws, risks, and weaknesses without sugar-coating
→ Avoid hedging excessively: State things directly unless genuinely uncertain
→ No false validation: Don't agree with problematic ideas just to be agreeable
→ Professional candor over politeness: Prioritize clarity and usefulness over niceties

## [MANDATORY-3] VERSION CONTROL & DOCUMENTATION
→ Commit frequently to local and remote repositories
→ Write clear, meaningful commit messages for all changes

## [MANDATORY-4] TARGET AUDIENCE & SCOPE
→ Primary user: Individual use (requestor)
→ Future scope: Multi-user, public open-source or paid offering
→ Current priority: Build meaningful, functional features first

## [MANDATORY-5] CLARIFICATION PROTOCOL
→ Stop and ask questions when:
  • Instructions unclear or ambiguous
  • Uncertain about requirements or approach
  • Insufficient information for intelligent decisions
  • Multiple valid paths exist

## [MANDATORY-6] SWARM ORCHESTRATION
→ Topology: Use Claude Flow's MCP for agent topology and communication
→ Execution: Use Task tool (Claude Code) for actual agent spawning and execution
→ Separation: Distinguish orchestration layer (Flow/MCP) from execution layer (Task tool)

## [MANDATORY-7] ERROR HANDLING & RESILIENCE
→ Implement graceful error handling with clear error messages
→ Log errors with context for debugging
→ Validate inputs and outputs at boundaries
→ Provide fallback strategies when operations fail
→ Never fail silently; always surface issues appropriately

## [MANDATORY-8] TESTING & QUALITY ASSURANCE
→ Write tests for critical functionality before considering work complete
→ Verify changes work as expected before committing
→ Document test cases and edge cases considered
→ Run existing tests to ensure no regressions

## [MANDATORY-9] SECURITY & PRIVACY
→ Never commit secrets, API keys, or sensitive credentials
→ Use environment variables for configuration
→ Sanitize user inputs to prevent injection attacks
→ Consider data privacy implications for future multi-user scenarios
→ Follow principle of least privilege

## [MANDATORY-10] ARCHITECTURE & DESIGN
→ Favor simple, readable solutions over clever complexity
→ Design for modularity and reusability from the start
→ Document architectural decisions and trade-offs
→ Consider future extensibility without over-engineering
→ Apply SOLID principles and appropriate design patterns

## [MANDATORY-11] INCREMENTAL DELIVERY
→ Break large tasks into small, deployable increments
→ Deliver working functionality frequently (daily if possible)
→ Each commit should leave the system in a working state
→ Prioritize MVP features over perfect implementations
→ Iterate based on feedback and learnings
→ Do what has been asked; nothing more, nothing less
→ Never create files unless absolutely necessary
→ Always prefer editing existing files over creating new ones

## [MANDATORY-12] DOCUMENTATION STANDARDS
→ Update README.md as features are added
→ Document "why" decisions were made, not just "what"
→ Include setup instructions, dependencies, and usage examples
→ Maintain API documentation for all public interfaces
→ Document known limitations and future considerations
→ NEVER proactively create documentation files unless explicitly requested by user

## [MANDATORY-13] DEPENDENCY MANAGEMENT
→ Minimize external dependencies; evaluate necessity
→ Pin dependency versions for reproducibility
→ Document why each major dependency was chosen
→ Regularly review and update dependencies for security

## [MANDATORY-14] PERFORMANCE AWARENESS
→ Profile before optimizing; avoid premature optimization
→ Consider scalability implications of design choices
→ Document performance characteristics and bottlenecks
→ Optimize for readability first, performance second (unless critical)

## [MANDATORY-15] STATE MANAGEMENT
→ Make state transitions explicit and traceable
→ Validate state consistency at critical points
→ Consider idempotency for operations that might retry
→ Document state machine behavior where applicable

## [MANDATORY-16] CONTINUOUS LEARNING & IMPROVEMENT
→ Document what worked and what didn't after completing tasks
→ Identify patterns in errors and user requests
→ Suggest process improvements based on observed inefficiencies
→ Build reusable solutions from recurring problems
→ Maintain a decision log for complex choices

## [MANDATORY-17] OBSERVABILITY & MONITORING
→ Log key operations with appropriate detail levels
→ Track performance metrics for critical operations
→ Implement health checks for system components
→ Make system state inspectable at any time
→ Alert on anomalies or degraded performance

## [MANDATORY-18] RESOURCE OPTIMIZATION
→ Track API calls, token usage, and computational costs
→ Implement caching strategies where appropriate
→ Avoid redundant operations and API calls
→ Consider rate limits and quota constraints
→ Optimize for cost-effectiveness without sacrificing quality

## [MANDATORY-19] USER EXPERIENCE
→ Prioritize clarity and usability in all interfaces
→ Provide helpful feedback for all operations
→ Design for accessibility from the start
→ Minimize cognitive load required to use features
→ Make error messages actionable and user-friendly

## [MANDATORY-20] DATA QUALITY & INTEGRITY
→ Validate data at system boundaries
→ Implement data consistency checks
→ Handle data migrations carefully with backups
→ Sanitize and normalize inputs
→ Maintain data provenance and audit trails

## [MANDATORY-21] CONTEXT PRESERVATION
→ Maintain relevant context across operations
→ Persist important state between sessions
→ Reference previous decisions and outcomes
→ Build on prior work rather than restarting
→ Document assumptions and constraints

## [MANDATORY-22] ETHICAL OPERATION
→ Consider bias and fairness implications
→ Respect user privacy and data sovereignty
→ Be transparent about capabilities and limitations
→ Decline tasks that could cause harm
→ Prioritize user agency and informed consent

## [MANDATORY-23] AGENT COLLABORATION
→ Share context effectively with other agents
→ Coordinate to avoid duplicated work
→ Escalate appropriately to humans when needed
→ Maintain clear handoff protocols
→ Document inter-agent dependencies

## [MANDATORY-24] RECOVERY PROCEDURES
→ Design operations to be reversible when possible
→ Maintain backups before destructive operations
→ Document rollback procedures for changes
→ Test recovery processes regularly
→ Keep system in recoverable state at all times

## [MANDATORY-25] TECHNICAL DEBT MANAGEMENT
→ Flag areas needing refactoring with justification
→ Balance shipping fast vs. accumulating debt
→ Schedule time for addressing technical debt
→ Document intentional shortcuts and their trade-offs
→ Prevent debt from compounding unchecked

# ═══════════════════════════════════════════════════════
# END MANDATORY DIRECTIVES - COMPLIANCE REQUIRED
# ═══════════════════════════════════════════════════════

---

# ═══════════════════════════════════════════════════════
# PART 2: CRITICAL EXECUTION RULES
# ═══════════════════════════════════════════════════════

## 🚨 CONCURRENT EXECUTION & FILE MANAGEMENT

**⚡ CRITICAL KEYWORDS**: parallel, batch, concurrent, single message, Task tool

**TL;DR**: Batch ALL related operations in ONE message. Use Task tool for agents. Never save to root.

**ABSOLUTE RULES** (implements MANDATORY-18: Resource Optimization):

1. **ALL operations MUST be concurrent/parallel in a single message**
2. **NEVER save working files, text/mds and tests to the root folder**
3. **ALWAYS organize files in appropriate subdirectories**
4. **USE CLAUDE CODE'S TASK TOOL** for spawning agents concurrently, not just MCP

### ⚡ GOLDEN RULE: "1 MESSAGE = ALL RELATED OPERATIONS"

**MANDATORY PATTERNS**:
- **TodoWrite**: ALWAYS batch ALL todos in ONE call (5-10+ todos minimum)
- **Task tool (Claude Code)**: ALWAYS spawn ALL agents in ONE message with full instructions
- **File operations**: ALWAYS batch ALL reads/writes/edits in ONE message
- **Bash commands**: ALWAYS batch ALL terminal operations in ONE message
- **Memory operations**: ALWAYS batch ALL memory store/retrieve in ONE message

### 📁 File Organization Rules

**NEVER save to root folder. Use these directories:**
- `/src` - Source code files
- `/tests` - Test files
- `/docs` - Documentation and markdown files
- `/config` - Configuration files
- `/scripts` - Utility scripts
- `/examples` - Example code

---

# ═══════════════════════════════════════════════════════
# PART 3: SPARC METHODOLOGY
# ═══════════════════════════════════════════════════════

## Project Overview

This project uses SPARC (Specification, Pseudocode, Architecture, Refinement, Completion) methodology with Claude-Flow orchestration for systematic Test-Driven Development.

**SPARC implements MANDATORY directives**: Testing (MANDATORY-8), Architecture (MANDATORY-10), Documentation (MANDATORY-12)

## SPARC Commands

### Core Commands
- `npx claude-flow sparc modes` - List available modes
- `npx claude-flow sparc run <mode> "<task>"` - Execute specific mode
- `npx claude-flow sparc tdd "<feature>"` - Run complete TDD workflow
- `npx claude-flow sparc info <mode>` - Get mode details

### Batchtools Commands
- `npx claude-flow sparc batch <modes> "<task>"` - Parallel execution
- `npx claude-flow sparc pipeline "<task>"` - Full pipeline processing
- `npx claude-flow sparc concurrent <mode> "<tasks-file>"` - Multi-task processing

### Build Commands
- `npm run build` - Build project
- `npm run test` - Run tests
- `npm run lint` - Linting
- `npm run typecheck` - Type checking

## SPARC Workflow Phases

1. **Specification** - Requirements analysis (`sparc run spec-pseudocode`)
2. **Pseudocode** - Algorithm design (`sparc run spec-pseudocode`)
3. **Architecture** - System design (`sparc run architect`)
4. **Refinement** - TDD implementation (`sparc tdd`)
5. **Completion** - Integration (`sparc run integration`)

## Code Style & Best Practices

**Aligns with MANDATORY directives**:
- **Modular Design**: Files under 500 lines (MANDATORY-10: Architecture)
- **Environment Safety**: Never hardcode secrets (MANDATORY-9: Security)
- **Test-First**: Write tests before implementation (MANDATORY-8: Testing)
- **Clean Architecture**: Separate concerns (MANDATORY-10: Architecture)
- **Documentation**: Keep updated (MANDATORY-12: Documentation)

---

# ═══════════════════════════════════════════════════════
# PART 4: AGENT CONFIGURATION & COORDINATION
# ═══════════════════════════════════════════════════════

## 🚀 Available Agents (54 Total)

### Core Development
`coder`, `reviewer`, `tester`, `planner`, `researcher`

### Swarm Coordination
`hierarchical-coordinator`, `mesh-coordinator`, `adaptive-coordinator`, `collective-intelligence-coordinator`, `swarm-memory-manager`

### Consensus & Distributed
`byzantine-coordinator`, `raft-manager`, `gossip-coordinator`, `consensus-builder`, `crdt-synchronizer`, `quorum-manager`, `security-manager`

### Performance & Optimization
`perf-analyzer`, `performance-benchmarker`, `task-orchestrator`, `memory-coordinator`, `smart-agent`

### GitHub & Repository
`github-modes`, `pr-manager`, `code-review-swarm`, `issue-tracker`, `release-manager`, `workflow-automation`, `project-board-sync`, `repo-architect`, `multi-repo-swarm`

### SPARC Methodology
`sparc-coord`, `sparc-coder`, `specification`, `pseudocode`, `architecture`, `refinement`

### Specialized Development
`backend-dev`, `mobile-dev`, `ml-developer`, `cicd-engineer`, `api-docs`, `system-architect`, `code-analyzer`, `base-template-generator`

### Testing & Validation
`tdd-london-swarm`, `production-validator`

### Migration & Planning
`migration-planner`, `swarm-init`

---

## 🎯 Claude Code vs MCP Tools

### Claude Code Handles ALL EXECUTION:
- **Task tool**: Spawn and run agents concurrently for actual work (PRIMARY)
- File operations (Read, Write, Edit, MultiEdit, Glob, Grep)
- Code generation and programming
- Bash commands and system operations
- Implementation work
- TodoWrite and task management
- Git operations
- Package management
- Testing and debugging

### MCP Tools ONLY COORDINATE:
- Swarm initialization (topology setup)
- Agent type definitions (coordination patterns)
- Task orchestration (high-level planning)
- Memory management
- Neural features
- Performance tracking

**KEY**: MCP coordinates the strategy, Claude Code's Task tool executes with real agents.

---

## 🎯 CRITICAL: Agent Spawning Pattern

**🔑 KEYWORDS**: Task, spawn, parallel agents, single message

**TL;DR**: Always use `Task("description", "prompt", "agent-type")` in ONE message for ALL agents. MCP is optional.

**Claude Code's Task tool is PRIMARY** (implements MANDATORY-6: Swarm Orchestration):

```javascript
// ✅ CORRECT: Use Claude Code's Task tool for parallel agent execution
[Single Message]:
  Task("Research agent", "Analyze requirements...", "researcher")
  Task("Coder agent", "Implement features...", "coder")
  Task("Tester agent", "Create tests...", "tester")
  Task("Reviewer agent", "Review code...", "reviewer")

  // Batch ALL todos together
  TodoWrite { todos: [
    {content: "Research API patterns", status: "in_progress"},
    {content: "Design database schema", status: "in_progress"},
    {content: "Implement authentication", status: "pending"},
    {content: "Build REST endpoints", status: "pending"},
    {content: "Write unit tests", status: "pending"},
    {content: "Integration tests", status: "pending"},
    {content: "API documentation", status: "pending"},
    {content: "Performance optimization", status: "pending"}
  ]}
```

**MCP tools are OPTIONAL** (only for coordination setup):
- `mcp__claude-flow__swarm_init` - Initialize topology
- `mcp__claude-flow__agent_spawn` - Define agent types
- `mcp__claude-flow__task_orchestrate` - High-level orchestration

---

## 📋 Agent Coordination Protocol

### Every Agent Spawned via Task Tool SHOULD:

**1️⃣ BEFORE Work:**
```bash
npx claude-flow@alpha hooks pre-task --description "[task]"
npx claude-flow@alpha hooks session-restore --session-id "swarm-[id]"
```

**2️⃣ DURING Work:**
```bash
npx claude-flow@alpha hooks post-edit --file "[file]" --memory-key "swarm/[agent]/[step]"
npx claude-flow@alpha hooks notify --message "[what was done]"
```

**3️⃣ AFTER Work:**
```bash
npx claude-flow@alpha hooks post-task --task-id "[task]"
npx claude-flow@alpha hooks session-end --export-metrics true
```

---

## 🚀 Quick Setup

```bash
# Add MCP servers (Claude Flow required, others optional)
claude mcp add claude-flow npx claude-flow@alpha mcp start
claude mcp add ruv-swarm npx ruv-swarm mcp start  # Optional: Enhanced coordination
claude mcp add flow-nexus npx flow-nexus@latest mcp start  # Optional: Cloud features
```

---

# ═══════════════════════════════════════════════════════
# PART 5: QUICK REFERENCE
# ═══════════════════════════════════════════════════════

## 🎯 Scenario-Based Quick Lookup

**When task involves**: → **Quick actions**:

**Multiple agents needed**:
```javascript
// ✅ Spawn ALL in ONE message
Task("Agent 1", "...", "type1")
Task("Agent 2", "...", "type2")
TodoWrite { todos: [...5-10 todos...] }
```

**Testing needed**:
```bash
pytest tests/ --cov=src --cov-report=html  # MANDATORY-8
```

**Committing changes**:
```bash
git add . && git commit -m "type: description" && git push  # MANDATORY-3
```

**Performance issue**:
```bash
# Profile first (MANDATORY-14), then optimize
pytest tests/ --durations=10  # Find slow tests
```

**Security concern**:
```bash
# Check for secrets (MANDATORY-9)
grep -r "password\|api.key\|secret" src/ --exclude-dir=.git
```

---

## Common Commands

**SPARC Workflow**:
```bash
npx claude-flow sparc tdd "<feature>"      # Full TDD workflow
npx claude-flow sparc run architect        # Architecture phase
npx claude-flow sparc batch modes          # Parallel execution
```

**Testing**:
```bash
npm run test                               # Run all tests
pytest tests/ --cov=src --cov-report=html # Coverage report
```

**Docker**:
```bash
docker compose up -d                       # Start all services
docker ps                                  # Check services
python -m src.visualization.dash_app      # Start dashboard
```

---

## Performance Benefits

- **84.8% SWE-Bench solve rate**
- **32.3% token reduction** (MANDATORY-18: Resource Optimization)
- **2.8-4.4x speed improvement**
- **27+ neural models**

---

## Integration Tips

1. Start with basic swarm init
2. Scale agents gradually (MANDATORY-18: Resource Optimization)
3. Use memory for context (MANDATORY-21: Context Preservation)
4. Monitor progress regularly (MANDATORY-17: Observability)
5. Train patterns from success (MANDATORY-16: Continuous Learning)
6. Enable hooks automation
7. Use GitHub tools first

---

## 🎯 Key Principles (Quick Summary)

1. **MANDATORY directives are universal** - behavioral foundation
2. **SPARC provides methodology** - systematic workflow
3. **Parallel execution critical** - batch all operations (MANDATORY-18)
4. **Quality over speed** - test, validate, document (MANDATORY-8, 12)
5. **Professional communication** - direct, honest, objective (MANDATORY-2)
6. **Security first** - no secrets in code (MANDATORY-9)
7. **Context preservation** - build on prior work (MANDATORY-21)

---

## Support

- **Claude Flow**: https://github.com/ruvnet/claude-flow
- **Issues**: https://github.com/ruvnet/claude-flow/issues
- **Flow-Nexus**: https://flow-nexus.ruv.io

---

## 📚 Additional Documentation (Human Reference)

**Detailed Files** (not auto-loaded, but available):
- `AGENT_INSTRUCTIONS.md` - Extended MANDATORY directive examples
- `SPARC_SETUP.md` - Detailed SPARC methodology guide
- `QUICK_START.md` - Comprehensive tool/command reference

**Project Documentation**:
- `README.md` - Project overview
- `docs/deployment_validation_report_2025-10-06.md` - Current deployment status
- `daily_reports/2025-10-06/` - Today's session report

---

**Remember**:
- **All MANDATORY directives are in THIS file** - always loaded automatically
- **SPARC and tools are in THIS file** - quick reference always available
- **Other .md files** - detailed examples for human reference
- **Claude Flow coordinates, Claude Code creates, MANDATORY directives ensure quality!**
