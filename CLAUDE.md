# Claude Code Configuration - Corporate Intelligence Platform

**Version**: 2.0 (Reorganized October 6, 2025)
**Auto-Loaded**: This file is automatically read by Claude Code at session start

---

## 📑 Documentation Structure

**This file (CLAUDE.md)**: Core instructions that Claude Code auto-loads
**Additional files** (for detailed reference):
- `AGENT_INSTRUCTIONS.md` - Detailed behavioral guidance
- `SPARC_SETUP.md` - SPARC methodology details
- `QUICK_START.md` - Tool setup and command examples

---

# ═══════════════════════════════════════════════════════
# AGENT OPERATING INSTRUCTIONS - MANDATORY COMPLIANCE
# ═══════════════════════════════════════════════════════

## 🎯 How These Work Together

**Layered Guidance (Complementary, Not Conflicting)**:
```
MANDATORY Directives  ← HOW to operate professionally (behavior, quality)
       ↓ Implemented through ↓
SPARC Methodology     ← WHAT process to follow (workflow, phases)
       ↓ Executed using ↓
Technical Tools       ← WHICH tools to use (MCP, agents, commands)
```

**Priority**: MANDATORY directives are foundational behavioral principles. SPARC and technical config implement these principles. They enhance each other, rarely conflict.

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
→ Details: See SPARC_SETUP.md and QUICK_START.md for coordination examples

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
# END MANDATORY DIRECTIVES - STRICT COMPLIANCE REQUIRED
# ═══════════════════════════════════════════════════════

---

## 🚨 CRITICAL: CONCURRENT EXECUTION & FILE MANAGEMENT

**ABSOLUTE RULES** (implements MANDATORY-18: Resource Optimization):

1. **ALL operations MUST be concurrent/parallel in a single message**
2. **NEVER save working files, text/mds and tests to the root folder**
3. **ALWAYS organize files in appropriate subdirectories**
4. **USE CLAUDE CODE'S TASK TOOL** for spawning agents concurrently

### ⚡ GOLDEN RULE: "1 MESSAGE = ALL RELATED OPERATIONS"

**MANDATORY PATTERNS**:
- **TodoWrite**: ALWAYS batch ALL todos in ONE call (5-10+ todos minimum)
- **Task tool**: ALWAYS spawn ALL agents in ONE message with full instructions
- **File operations**: ALWAYS batch ALL reads/writes/edits in ONE message
- **Bash commands**: ALWAYS batch ALL terminal operations in ONE message

### 📁 File Organization
**NEVER save to root. Use**: `/src`, `/tests`, `/docs`, `/config`, `/scripts`, `/examples`

---

## 🚀 Quick Reference

### SPARC Commands (see SPARC_SETUP.md for details)
```bash
npx claude-flow sparc tdd "<feature>"      # TDD workflow
npx claude-flow sparc run <mode> "<task>"  # Execute specific mode
npx claude-flow sparc batch <modes>        # Parallel execution
```

### Available Agents (see QUICK_START.md for full list)
**Core**: `coder`, `reviewer`, `tester`, `planner`, `researcher`
**Total**: 54 specialized agents available

### Agent Spawning Pattern (MANDATORY-6: Swarm Orchestration)
```javascript
// ✅ CORRECT: Spawn ALL agents in ONE message
Task("Research agent", "Analyze...", "researcher")
Task("Coder agent", "Implement...", "coder")
Task("Tester agent", "Create tests...", "tester")
```

### MCP vs Task Tool
- **Claude Code Task tool**: Actual agent execution (PRIMARY)
- **MCP tools**: Coordination setup only (OPTIONAL)

---

## 🎯 Key Principles Summary

1. **MANDATORY directives are universal** - behavioral foundation
2. **SPARC provides methodology** - systematic workflow
3. **Parallel execution critical** - batch operations (MANDATORY-18)
4. **Quality over speed** - test, validate, document (MANDATORY-8, 12)
5. **Professional communication** - direct, honest, objective (MANDATORY-2)
6. **Security first** - no secrets in code (MANDATORY-9)
7. **Context preservation** - build on prior work (MANDATORY-21)

---

## 📚 Additional Documentation (Human Reference)

**Detailed Guidance** (not auto-loaded, read when needed):
- `AGENT_INSTRUCTIONS.md` - Full MANDATORY directives with examples
- `SPARC_SETUP.md` - Complete SPARC methodology guide
- `QUICK_START.md` - Comprehensive tool and command reference

**Project Documentation**:
- `README.md` - Project overview
- `docs/deployment_validation_report_2025-10-06.md` - Deployment status
- `daily_reports/2025-10-06/` - Today's complete session report

---

## Support

- **Claude Flow**: https://github.com/ruvnet/claude-flow
- **Issues**: https://github.com/ruvnet/claude-flow/issues
- **Flow-Nexus**: https://flow-nexus.ruv.io

---

**Remember**:
- **This file (CLAUDE.md) is auto-loaded** - contains all mandatory directives
- **Other .md files** are human reference - read when you need detailed examples
- **MANDATORY directives always apply** - they're in this auto-loaded file
- **Claude Flow coordinates, Claude Code creates, MANDATORY directives ensure quality!**
