# SPARC Methodology Setup - Corporate Intelligence Platform

**Purpose**: SPARC development methodology configuration and workflow guidance
**Scope**: Project-specific development process
**Foundation**: Implements principles from AGENT_INSTRUCTIONS.md (MANDATORY directives)

---

## 🎯 How This Relates to Agent Instructions

**AGENT_INSTRUCTIONS.md** defines **HOW to operate** (behavior, quality, ethics)
**THIS FILE** defines **WHAT methodology to follow** (SPARC phases, workflow)

**They work together**:
- MANDATORY-8 (Testing & QA) ← **enforces quality in** → SPARC Refinement phase
- MANDATORY-10 (Architecture) ← **guides design in** → SPARC Architecture phase
- MANDATORY-11 (Incremental Delivery) ← **shapes workflow** → SPARC Completion phase

---

## Project Overview

This project uses **SPARC** (Specification, Pseudocode, Architecture, Refinement, Completion) methodology with Claude-Flow orchestration for systematic Test-Driven Development.

**SPARC + MANDATORY Directives = Professional, Systematic Development**

---

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

---

## SPARC Workflow Phases

### 1. **Specification** - Requirements analysis
**Command**: `sparc run spec-pseudocode`
**MANDATORY Alignment**: MANDATORY-5 (Clarification Protocol), MANDATORY-11 (Incremental Delivery)
**Purpose**: Define clear requirements and scope

### 2. **Pseudocode** - Algorithm design
**Command**: `sparc run spec-pseudocode`
**MANDATORY Alignment**: MANDATORY-10 (Architecture & Design)
**Purpose**: Design approach before implementation

### 3. **Architecture** - System design
**Command**: `sparc run architect`
**MANDATORY Alignment**: MANDATORY-10 (Architecture), MANDATORY-14 (Performance Awareness)
**Purpose**: Define system structure and patterns

### 4. **Refinement** - TDD implementation
**Command**: `sparc tdd`
**MANDATORY Alignment**: MANDATORY-8 (Testing & QA), MANDATORY-7 (Error Handling)
**Purpose**: Implement with test-driven development

### 5. **Completion** - Integration
**Command**: `sparc run integration`
**MANDATORY Alignment**: MANDATORY-11 (Incremental Delivery), MANDATORY-16 (Continuous Learning)
**Purpose**: Integrate and validate complete functionality

---

## Code Style & Best Practices

**Note**: These align with MANDATORY directives - see AGENT_INSTRUCTIONS.md for comprehensive guidance

- **Modular Design**: Files under 500 lines (MANDATORY-10: Architecture & Design)
- **Environment Safety**: Never hardcode secrets (MANDATORY-9: Security & Privacy)
- **Test-First**: Write tests before implementation (MANDATORY-8: Testing & QA)
- **Clean Architecture**: Separate concerns (MANDATORY-10: Architecture & Design)
- **Documentation**: Keep updated (MANDATORY-12: Documentation Standards)

---

## Performance Benefits (SPARC + Claude Flow)

- **84.8% SWE-Bench solve rate**
- **32.3% token reduction** (aligns with MANDATORY-18: Resource Optimization)
- **2.8-4.4x speed improvement**
- **27+ neural models**

---

## Hooks Integration

### Pre-Operation
- Auto-assign agents by file type
- Validate commands for safety (MANDATORY-7: Error Handling)
- Prepare resources automatically
- Optimize topology by complexity
- Cache searches (MANDATORY-18: Resource Optimization)

### Post-Operation
- Auto-format code
- Train neural patterns
- Update memory (MANDATORY-21: Context Preservation)
- Analyze performance (MANDATORY-14: Performance Awareness)
- Track token usage (MANDATORY-18: Resource Optimization)

### Session Management
- Generate summaries
- Persist state (MANDATORY-21: Context Preservation)
- Track metrics (MANDATORY-17: Observability & Monitoring)
- Restore context
- Export workflows

---

## Advanced Features (v2.0.0)

- 🚀 Automatic Topology Selection
- ⚡ Parallel Execution (2.8-4.4x speed) - implements MANDATORY-18 (Resource Optimization)
- 🧠 Neural Training
- 📊 Bottleneck Analysis - implements MANDATORY-14 (Performance Awareness)
- 🤖 Smart Auto-Spawning
- 🛡️ Self-Healing Workflows - implements MANDATORY-7 (Error Handling)
- 💾 Cross-Session Memory - implements MANDATORY-21 (Context Preservation)
- 🔗 GitHub Integration

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

## Support

- Documentation: https://github.com/ruvnet/claude-flow
- Issues: https://github.com/ruvnet/claude-flow/issues
- Flow-Nexus Platform: https://flow-nexus.ruv.io

---

## 📚 See Also

- **AGENT_INSTRUCTIONS.md** - Universal MANDATORY operating directives (HOW to work)
- **QUICK_START.md** - Tool setup, agents, commands, examples (WHICH tools)
- **README.md** - Project overview and getting started

---

**Remember**: Claude Flow coordinates, Claude Code creates!

**SPARC provides the methodology, MANDATORY directives ensure professional execution.**
