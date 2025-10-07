# Claude Code Configuration - Corporate Intelligence Platform

**Version**: 2.0 (Reorganized October 6, 2025)
**Purpose**: Central navigation hub for all project guidance

---

## 📑 Navigation - Read in This Order

### 1️⃣ **AGENT_INSTRUCTIONS.md** (START HERE)
**Universal Operating Principles - MANDATORY Compliance**

25 behavioral directives covering:
- Communication & professionalism
- Version control & documentation
- Testing & quality assurance
- Security & privacy
- Architecture & design
- Error handling & resilience
- Resource optimization
- And 18 more critical guidelines

**Why read first**: Establishes HOW to work professionally across all tasks

---

### 2️⃣ **SPARC_SETUP.md** (READ SECOND)
**Development Methodology & Workflow**

SPARC framework configuration:
- 5 development phases (Specification → Completion)
- SPARC commands and batchtools
- Code style & best practices
- Hooks integration
- Performance benefits (84.8% SWE-Bench solve rate)

**Why read second**: Defines WHAT development process to follow

---

### 3️⃣ **QUICK_START.md** (READ THIRD)
**Technical Configuration & Command Reference**

Tools and setup:
- MCP server setup (Claude Flow, ruv-swarm, flow-nexus)
- 54 available agents with descriptions
- Concurrent execution patterns (correct vs wrong)
- Agent coordination protocol
- File organization rules
- Command examples

**Why read third**: Specifies WHICH tools and commands to use

---

## 🎯 Quick Links

**Getting Started**:
- New to project? → Start with AGENT_INSTRUCTIONS.md
- Need commands? → Jump to QUICK_START.md
- Understanding workflow? → Review SPARC_SETUP.md

**Common Tasks**:
- Spawn agents → QUICK_START.md (Task tool examples)
- Write tests → SPARC_SETUP.md (Refinement phase)
- Commit code → AGENT_INSTRUCTIONS.md (MANDATORY-3)
- Handle errors → AGENT_INSTRUCTIONS.md (MANDATORY-7)

---

## 🔗 Relationship Between Documents

```
┌─────────────────────────────────────────────────┐
│  AGENT_INSTRUCTIONS.md                          │
│  Universal Behavioral Principles (HOW)          │
│  • Professional communication                   │
│  • Quality standards                            │
│  • Ethical operation                            │
│  • Resource optimization                        │
├─────────────────────────────────────────────────┤
│         ↓ Implemented through ↓                 │
├─────────────────────────────────────────────────┤
│  SPARC_SETUP.md                                 │
│  Development Methodology (WHAT)                 │
│  • 5 SPARC workflow phases                      │
│  • Test-driven development                      │
│  • Hooks integration                            │
│  • Code style alignment                         │
├─────────────────────────────────────────────────┤
│         ↓ Executed using ↓                      │
├─────────────────────────────────────────────────┤
│  QUICK_START.md                                 │
│  Technical Tools & Commands (WHICH)             │
│  • MCP setup                                    │
│  • Agent spawning (Task tool)                   │
│  • Concurrent execution patterns                │
│  • File organization                            │
└─────────────────────────────────────────────────┘
```

**They're complementary layers** that work together:
- MANDATORY principles ensure professional execution
- SPARC provides systematic development workflow
- Technical tools enable efficient implementation

---

## 🚀 Quick Commands

**Most Common Operations**:

```bash
# Spawn parallel test generation agents
Task("API Tests", "Create endpoint tests...", "tester")
Task("DB Tests", "Create model tests...", "tester")
Task("Pipeline Tests", "Create ingestion tests...", "tester")

# Run SPARC workflow
npx claude-flow sparc tdd "new feature name"

# Execute build
npm run build && npm run test
```

---

## 📊 Project Stats (Current)

- **Code Lines**: ~46,000 lines
- **Test Coverage**: 70%+ framework (759+ tests)
- **Grade**: A (95/100) - Production-ready
- **Documentation**: 17 comprehensive reports
- **Agents Used**: 54 available, actively using ~12

---

## 🎓 Key Principles (Summary)

1. **MANDATORY directives are non-negotiable** - universal behavioral standards
2. **SPARC provides the methodology** - systematic development workflow
3. **Parallel execution is critical** - batch all related operations
4. **Quality over speed** - test, validate, document
5. **Professional communication** - direct, honest, objective

---

## 📚 Additional Documentation

**Architecture**:
- `docs/architecture/` - System design documents
- `docs/deployment_validation_report_2025-10-06.md` - Deployment readiness

**Testing**:
- `tests/TEST_SUMMARY_REPORT.md` - Test coverage overview
- `tests/load-testing/` - Performance testing suite

**Daily Reports**:
- `daily_reports/2025-10-06/` - Today's complete session report
- `daily_reports/2025-10-05/` - Yesterday's session report

---

## Support

- **Claude Flow**: https://github.com/ruvnet/claude-flow
- **Issues**: https://github.com/ruvnet/claude-flow/issues
- **Flow-Nexus**: https://flow-nexus.ruv.io

---

**Remember**:
- **Read AGENT_INSTRUCTIONS.md first** for mandatory operating principles
- **Consult SPARC_SETUP.md** for development methodology
- **Reference QUICK_START.md** for tools and commands

**Claude Flow coordinates, Claude Code creates, MANDATORY directives ensure quality!**
