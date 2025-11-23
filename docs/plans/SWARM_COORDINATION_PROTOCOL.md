# Swarm Coordination Protocol - Plan A & B Execution
**Date**: 2025-10-25
**Purpose**: Define agent coordination, communication, and handoff procedures
**Scope**: 10-day execution window (2025-10-25 to 2025-11-08)

---

## Protocol Overview

This document defines how swarm agents coordinate during Plan A (Production Deployment) and Plan B (Technical Debt Cleanup) execution. The protocol ensures:
- Efficient parallel execution
- Clear communication channels
- Conflict-free resource usage
- Transparent progress tracking
- Rapid issue resolution

**Key Principles**:
1. **Autonomy with Accountability**: Agents work independently but report progress
2. **Coordination Before Execution**: Pre-task hooks establish context
3. **Memory as Single Source of Truth**: All state stored in shared memory
4. **Clear Ownership**: Every task has one primary owner
5. **Escalation Paths Defined**: Blockers escalate quickly

---

## Swarm Architecture

### Topology Selection by Phase

**Days 1-3 (Infrastructure): HIERARCHICAL**
```
                 DevOps Lead
                 (Coordinator)
                      │
         ┌────────────┼────────────┐
         │            │            │
    Backend Pod   Security Pod  Infrastructure Pod
    (2 agents)    (2 agents)    (2 agents)
         │            │            │
    ┌────┴───┐   ┌────┴───┐   ┌────┴───┐
 Backend-01 02  Sec-01  02  Infra-01 02
```

**Rationale**: Infrastructure tasks require coordination and clear leadership for deployment decisions.

**Coordination Pattern**:
- Coordinator reviews all task completions
- Pods work independently within domain
- Cross-pod communication via coordinator
- Escalations go through coordinator

---

**Days 4-7 (Refactoring): MESH**
```
    Coder-01 ←→ Coder-02 ←→ Coder-03
        ↕           ↕           ↕
    Review-01 ←→ Review-02 ←→ Tester-01
        ↕           ↕           ↕
    Tester-02 ←→ Coder-04 ←→ Review-03
```

**Rationale**: Refactoring benefits from peer collaboration and cross-review.

**Coordination Pattern**:
- All agents can communicate directly
- Peer review across agents
- No central bottleneck
- Consensus-based decision making

---

**Days 8-9 (Validation): STAR**
```
                  QA Lead
                (Hub Agent)
                     │
        ┌────┬───┬───┼───┬───┬────┐
        │    │   │   │   │   │    │
      Test Perf Sec Int E2E Reg Doc
      -01  -01  -01 -01 -01 -01 -01
```

**Rationale**: Validation requires centralized coordination and reporting.

**Coordination Pattern**:
- All agents report to QA Lead
- Hub coordinates parallel validation
- Results aggregated centrally
- Go/No-Go decision by hub

---

**Day 10 (Deployment): RING**
```
    DevOps → Backend → Database → Frontend → SRE
       ↑                                       │
       └───────────────────────────────────────┘
```

**Rationale**: Deployment requires sequential handoffs with coordinated monitoring.

**Coordination Pattern**:
- Sequential execution (deployment stages)
- Each agent monitors specific subsystem
- Continuous communication around ring
- Any agent can trigger rollback

---

## Agent Allocation Matrix

### Specialized Agents by Day

| Day | Phase | Required Agents | Allocation | Topology |
|-----|-------|-----------------|------------|----------|
| **Day 1** | Infrastructure Foundation | 6 | DevOps (2), Security (2), Backend (2) | HIERARCHICAL |
| **Day 2** | Monitoring & Alerting | 6 | SRE (2), DevOps (2), Backend (2) | HIERARCHICAL |
| **Day 3** | Performance & Optimization | 6 | Performance (2), Backend (2), DB (2) | HIERARCHICAL |
| **Day 4** | Code Refactoring 1 | 4 | Coder (2), Reviewer (2) | MESH |
| **Day 5** | Code Refactoring 2 | 4 | Coder (2), Data Eng (2) | MESH |
| **Day 6** | Code Refactoring 3 | 4 | Backend (2), DB (1), Coder (1) | MESH |
| **Day 7** | Error Handling | 4 | Coder (2), Tester (2) | MESH |
| **Day 8** | Testing & Documentation | 5 | Tester (2), QA (1), Writer (2) | STAR |
| **Day 9** | Validation & Audit | 6 | Performance (2), Security (2), Tester (2) | STAR |
| **Day 10** | Deployment & Launch | 8-10 | Full swarm (all specialists) | RING |

### Agent Capabilities Matrix

| Agent Type | Core Skills | Secondary Skills | Typical Tasks |
|------------|-------------|------------------|---------------|
| **DevOps Engineer** | Infrastructure, Docker, CI/CD | Networking, Security | Deployment, environment config |
| **Security Auditor** | Penetration testing, Vuln scan | Code review, Compliance | Security fixes, audits |
| **Backend Developer** | Python, FastAPI, SQLAlchemy | PostgreSQL, Redis | API development, bug fixes |
| **Database Specialist** | PostgreSQL, Query optimization | Data modeling, Migrations | Index creation, query tuning |
| **SRE** | Monitoring, Observability | Incident response, Automation | Prometheus, Grafana setup |
| **Performance Engineer** | Load testing, Profiling | Optimization, Benchmarking | Locust, performance tuning |
| **Coder** | Refactoring, Code quality | Testing, Documentation | Code splitting, module creation |
| **Reviewer** | Code review, Quality assurance | Best practices, Mentoring | PR reviews, quality gates |
| **Tester** | Test automation, QA | Integration testing, Bug triage | Test suite execution, validation |
| **Data Engineer** | ETL pipelines, Data quality | API integration, Validation | Pipeline refactoring |
| **Technical Writer** | Documentation, Technical writing | Diagram creation, Tutorials | Runbooks, API docs |
| **QA Engineer** | Quality assurance, Test plans | Automation, Regression testing | Integration tests, E2E tests |

---

## Coordination Hooks Protocol

### Hook Lifecycle

Every task MUST execute hooks at these stages:
1. **pre-task**: Before starting work
2. **post-edit**: After each file modification
3. **notify**: After completing subtask
4. **post-task**: After finishing entire task
5. **session-end**: At end of day (optional)

### Hook Commands & Usage

#### 1. Pre-Task Hook

**When**: Before starting any task
**Purpose**: Initialize context, validate dependencies, reserve resources

**Command**:
```bash
npx claude-flow@alpha hooks pre-task \
  --description "Task 1.1: Backup Scripts Review and Validation" \
  --dependencies "none" \
  --estimated-duration "2h"
```

**What It Does**:
- Creates task ID for tracking
- Stores task context in memory
- Validates all dependencies available
- Allocates resources (database connections, etc.)
- Logs task start time

**Agent Responsibility**:
- MUST run before any code changes
- MUST specify accurate description
- MUST list all dependencies
- MUST provide realistic time estimate

---

#### 2. Post-Edit Hook

**When**: After modifying any file (code, config, docs)
**Purpose**: Track changes, update memory, enable coordination

**Command**:
```bash
npx claude-flow@alpha hooks post-edit \
  --file "src/api/v1/companies.py" \
  --memory-key "swarm/security/sql-injection-fix" \
  --description "Fixed SQL injection vulnerability with column whitelist"
```

**What It Does**:
- Stores file modification in memory
- Updates agent progress tracking
- Notifies dependent agents of changes
- Triggers automated validation (if configured)
- Increments progress percentage

**Agent Responsibility**:
- MUST run after each file save
- MUST provide meaningful description
- MUST use consistent memory-key naming
- SHOULD commit to git after validating

---

#### 3. Notify Hook

**When**: After completing subtask or milestone
**Purpose**: Alert team and dependent agents

**Command**:
```bash
npx claude-flow@alpha hooks notify \
  --message "Backup scripts validated - all tests passing, committed to git" \
  --priority "high" \
  --recipients "devops,coordinator"
```

**What It Does**:
- Sends notification to specified agents/channels
- Updates swarm coordination dashboard
- Logs milestone completion
- Triggers dependent task notifications
- Stores notification in memory for audit

**Agent Responsibility**:
- MUST notify after each significant milestone
- SHOULD use descriptive, actionable messages
- MUST set appropriate priority (low/medium/high/critical)
- SHOULD include next steps or handoff info

---

#### 4. Post-Task Hook

**When**: After completing entire task
**Purpose**: Finalize task, update metrics, hand off to next agent

**Command**:
```bash
npx claude-flow@alpha hooks post-task \
  --task-id "task-1761445750208-y7ezniwkn" \
  --status "completed" \
  --quality-score "9.5" \
  --notes "All backups validated, restore tested successfully"
```

**What It Does**:
- Marks task as completed in memory
- Stores final metrics (duration, quality)
- Releases allocated resources
- Triggers dependent tasks
- Updates swarm coordination status
- Exports task metrics

**Agent Responsibility**:
- MUST run after task fully completed
- MUST provide accurate status (completed/blocked/failed)
- SHOULD self-assess quality score (1-10)
- SHOULD document lessons learned in notes

---

#### 5. Session-End Hook (Optional)

**When**: At end of work session (typically end of day)
**Purpose**: Generate summary, persist state, prepare for next session

**Command**:
```bash
npx claude-flow@alpha hooks session-end \
  --export-metrics true \
  --generate-summary true \
  --session-id "swarm-day1-infra"
```

**What It Does**:
- Generates session summary report
- Exports all metrics to files
- Persists swarm state to disk
- Validates memory consistency
- Prepares for next session restore

**Agent Responsibility**:
- SHOULD run at end of each work session
- MUST specify unique session-id
- SHOULD review summary for accuracy

---

### Hook Failure Handling

**If Hook Fails**:
1. **Log Error**: Capture error message and context
2. **Continue Work**: Do not block task execution
3. **Manual Coordination**: Fall back to manual progress updates
4. **Report Issue**: Notify coordinator of hook failure
5. **Retry**: Attempt hook again with `--retry` flag

**Example**:
```bash
# Hook failed due to memory initialization error
# Continue work, report to coordinator, retry later
npx claude-flow@alpha hooks post-task --task-id "..." --retry --force
```

---

## Memory Coordination

### Memory Structure

```
.swarm/memory.db (SQLite)
├── tasks/
│   ├── task-{id}/
│   │   ├── description
│   │   ├── owner
│   │   ├── status (pending/in_progress/completed/blocked)
│   │   ├── progress (0-100%)
│   │   ├── dependencies
│   │   └── metadata
├── agents/
│   ├── agent-{id}/
│   │   ├── type
│   │   ├── status (idle/in_progress/completed/error)
│   │   ├── current_task
│   │   ├── completed_tasks[]
│   │   └── metrics
├── coordination/
│   ├── swarm/planner/
│   │   ├── execution-plan
│   │   ├── task-breakdown
│   │   └── status
│   ├── swarm/{agent-type}/
│   │   ├── progress
│   │   ├── findings
│   │   └── next-steps
└── metrics/
    ├── performance.json
    ├── system-metrics.json
    └── task-metrics.json
```

### Memory Access Patterns

**Read from Memory**:
```bash
# Get task status
npx claude-flow@alpha hooks memory-get --key "tasks/task-123/status"

# Get agent allocation
npx claude-flow@alpha hooks memory-get --key "agents/agent-001/current_task"

# Get swarm coordination state
npx claude-flow@alpha hooks memory-get --key "coordination/swarm/planner/execution-plan"
```

**Write to Memory**:
```bash
# Store task progress
npx claude-flow@alpha hooks memory-store \
  --key "swarm/devops/backup-validation" \
  --value '{"status":"completed","tests_passed":true,"rto":"12min"}' \
  --namespace "coordination"

# Store agent findings
npx claude-flow@alpha hooks memory-store \
  --key "swarm/security/sql-injection-fix" \
  --value '{"vulnerability":"fixed","tests":15,"score":10}' \
  --namespace "coordination"
```

### Memory Synchronization

**Frequency**: After each hook execution
**Method**: Atomic writes with optimistic locking
**Conflict Resolution**: Last-write-wins (with timestamp)
**Backup**: Hourly snapshots to `.swarm/memory-backups/`

---

## Communication Channels

### Primary Channels

1. **Memory Database** (`.swarm/memory.db`)
   - **Purpose**: State sharing, coordination
   - **Update Frequency**: Real-time (every hook)
   - **Access**: All agents (read/write)

2. **Claude Flow Notifications**
   - **Purpose**: Event-driven alerts
   - **Update Frequency**: On milestone completion
   - **Access**: Coordinator + dependent agents

3. **Daily Progress Reports**
   - **Purpose**: Human-readable status updates
   - **Update Frequency**: 3x daily (9 AM, 1 PM, 5 PM)
   - **Access**: All stakeholders

4. **Git Commits**
   - **Purpose**: Code change tracking
   - **Update Frequency**: After each file modification (batched)
   - **Access**: All team members

### Secondary Channels (Human Coordination)

5. **Slack / Teams** (if available)
   - **Purpose**: Real-time team communication
   - **Update Frequency**: As needed
   - **Access**: Human team members

6. **Email Summaries**
   - **Purpose**: Daily summaries to stakeholders
   - **Update Frequency**: Daily at 5 PM
   - **Access**: Project stakeholders

---

## Conflict Resolution

### Resource Conflicts

**Scenario**: Two agents need exclusive database access

**Resolution Protocol**:
1. **Detection**: Pre-task hook identifies conflict
2. **Coordination**: Agents negotiate via memory
3. **Priority**: Higher priority task gets access first
4. **Queueing**: Lower priority task waits or reschedules
5. **Notification**: Waiting agent notified when resource available

**Example**:
```bash
# Agent 1 (load testing) needs exclusive DB access
npx claude-flow@alpha hooks pre-task \
  --description "Load testing" \
  --resources "database:exclusive" \
  --priority "high"

# Agent 2 (query optimization) conflicts
# System detects conflict, queues Agent 2
# Agent 2 notified when Agent 1 completes
```

---

### Task Dependency Conflicts

**Scenario**: Task starts before dependency completes

**Resolution Protocol**:
1. **Detection**: Pre-task hook validates dependencies
2. **Blocking**: Task marked as "blocked" in memory
3. **Notification**: Coordinator alerted
4. **Auto-Resume**: Task auto-starts when dependency resolves
5. **Timeout**: If dependency fails, task escalated

**Example**:
```bash
# Task 1.4 depends on 1.2
npx claude-flow@alpha hooks pre-task \
  --description "Production deployment" \
  --dependencies "task-1.2:completed"

# If 1.2 not complete, task marked blocked
# Auto-resumes when 1.2 completes
```

---

### Code Conflict Resolution

**Scenario**: Two agents modify same file

**Resolution Protocol**:
1. **Prevention**: Post-edit hook locks file temporarily
2. **Detection**: Git merge conflict detected
3. **Notification**: Both agents notified
4. **Coordination**: Agents coordinate resolution via memory
5. **Manual Review**: If unresolved, escalate to reviewer

**Example**:
```bash
# Agent 1 modifies companies.py
npx claude-flow@alpha hooks post-edit --file "src/api/v1/companies.py"
# File locked for 5 minutes

# Agent 2 attempts to modify same file
# Pre-task hook detects lock, waits or chooses different task
```

---

## Progress Tracking

### Task Status States

- **PENDING**: Task not yet started, waiting for dependencies
- **IN_PROGRESS**: Agent actively working on task
- **BLOCKED**: Task waiting on external dependency or resource
- **COMPLETED**: Task successfully finished
- **FAILED**: Task encountered unrecoverable error
- **SKIPPED**: Task no longer needed (plan changed)

### Progress Reporting

**Every Agent MUST Report**:
1. **Task Start**: Pre-task hook
2. **25% Milestone**: Notify hook
3. **50% Milestone**: Notify hook
4. **75% Milestone**: Notify hook
5. **Task Completion**: Post-task hook

**Progress Calculation**:
```
Task Progress = (Completed Subtasks / Total Subtasks) × 100%
Phase Progress = (Completed Tasks / Total Tasks) × 100%
Overall Progress = (Completed Phases / Total Phases) × 100%
```

### Daily Reporting Schedule

**9:00 AM - Morning Standup**:
- Review yesterday's progress
- Identify today's priorities
- Allocate agents to tasks
- Review blockers

**1:00 PM - Midday Check**:
- Monitor task progress
- Address emerging blockers
- Reallocate agents if needed

**5:00 PM - End-of-Day Review**:
- Validate exit criteria
- Document lessons learned
- Plan tomorrow's work
- Update risk register

---

## Escalation Protocol

### Escalation Triggers

| Trigger | Severity | Response Time | Escalation Path |
|---------|----------|---------------|-----------------|
| Critical blocker | P0 | Immediate | Agent → Coordinator → Project Lead |
| Task failure | P1 | <1 hour | Agent → Coordinator |
| Performance degradation | P1 | <4 hours | Agent → Coordinator |
| Dependency delay | P2 | <1 day | Agent → Coordinator |
| Resource conflict | P2 | <1 day | Agents negotiate → Coordinator |
| Quality issue | P3 | <1 week | Agent → Reviewer |

### Escalation Procedure

1. **Agent Detects Issue**
   - Log issue in memory
   - Run notify hook with priority "critical"
   - Document issue details

2. **Coordinator Notified**
   - Reviews issue context from memory
   - Assesses impact on timeline
   - Determines resolution approach

3. **Resolution**
   - **If resolvable by agent**: Provide guidance, agent proceeds
   - **If requires reallocation**: Assign additional agents
   - **If blocks critical path**: Escalate to Project Lead
   - **If risk materialized**: Execute contingency plan

4. **Follow-Up**
   - Document resolution in memory
   - Update risk register
   - Notify all affected agents
   - Adjust plan if needed

---

## Agent Onboarding & Handoffs

### New Agent Onboarding

**When**: New agent joins swarm mid-execution

**Onboarding Steps**:
1. **Context Restore**:
   ```bash
   npx claude-flow@alpha hooks session-restore --session-id "swarm-day3"
   ```
2. **Review Memory**:
   - Read swarm coordination state
   - Review completed tasks
   - Understand current phase

3. **Receive Assignment**:
   - Coordinator assigns task
   - Agent reviews task dependencies
   - Agent confirms readiness

4. **Pre-Task Hook**:
   - Execute pre-task hook
   - Validate context loaded correctly

---

### Task Handoff Protocol

**When**: Task completed, next task can begin

**Handoff Steps**:
1. **Completing Agent**:
   - Run post-task hook (stores completion state)
   - Run notify hook (alerts dependent agents)
   - Document handoff notes in memory

2. **System**:
   - Updates dependent task status to "ready"
   - Notifies assigned agent
   - Unblocks resources

3. **Receiving Agent**:
   - Receives notification
   - Reviews handoff notes from memory
   - Runs pre-task hook (validates dependencies)
   - Begins work

**Handoff Checklist**:
- [ ] All task deliverables complete
- [ ] Quality validated (tests passing, code reviewed)
- [ ] Documentation updated
- [ ] Artifacts committed to git
- [ ] Memory state updated
- [ ] Dependent agents notified

---

## Quality Gates

### Pre-Deployment Quality Gates (Day 9)

**Every task must pass**:
1. **Code Quality**:
   - All tests passing (>95% pass rate)
   - Code coverage maintained (>85%)
   - No critical linting errors
   - Code review approved

2. **Performance**:
   - P95 latency <500ms
   - Error rate <1%
   - No memory leaks
   - Database queries optimized

3. **Security**:
   - Zero critical vulnerabilities
   - Zero high vulnerabilities (or mitigated)
   - Secrets properly managed
   - Security audit passed

4. **Documentation**:
   - All code documented
   - Runbooks updated
   - API documentation current

**Gate Enforcement**:
- Automated checks via pre-commit hooks
- Manual review by gate owner
- Blocker if any gate fails
- Re-validation after fixes

---

## Coordination Metrics

### Agent Performance Metrics

| Metric | Measurement | Target | Review Frequency |
|--------|-------------|--------|------------------|
| Task Completion Rate | Tasks completed / Tasks assigned | >90% | Daily |
| Quality Score | Avg quality score (1-10) | >8.0 | Per task |
| Blocker Rate | Blocked tasks / Total tasks | <15% | Daily |
| Collaboration Score | Cross-agent interactions | High | Weekly |
| Response Time | Time to respond to notifications | <1 hour | Daily |

### Swarm Efficiency Metrics

| Metric | Measurement | Target | Review Frequency |
|--------|-------------|--------|------------------|
| Parallelization Factor | Concurrent tasks / Serial tasks | >1.5x | Daily |
| Resource Utilization | Active agents / Total agents | >75% | Hourly |
| Communication Overhead | Coordination time / Work time | <20% | Daily |
| Rework Rate | Tasks redone / Tasks completed | <10% | Weekly |

---

## Emergency Procedures

### Critical Blocker Procedure

**When**: Critical task blocked, threatens launch

**Immediate Actions**:
1. **Agent**: Run notify hook with priority "critical"
2. **Coordinator**: Assess impact on critical path
3. **Decision** (within 15 minutes):
   - Reallocate additional agents
   - Adjust timeline
   - Activate contingency plan
   - Escalate to Project Lead

---

### Swarm Failure Recovery

**When**: Multiple agents fail or coordination breaks

**Recovery Steps**:
1. **Detect**: Coordinator monitors agent heartbeats
2. **Isolate**: Identify failed agents
3. **Preserve**: Snapshot memory state
4. **Restore**: Restart failed agents from last known state
5. **Validate**: Verify memory consistency
6. **Resume**: Continue from last checkpoint

---

## Appendix: Example Agent Day

### Agent-001 (DevOps Engineer) - Day 1

**Assigned Task**: 1.1 Backup Scripts Review and Validation

**Timeline**:
```
09:00 - Pre-Task Hook
      npx claude-flow@alpha hooks pre-task \
        --description "Review and validate backup scripts" \
        --dependencies "none"
      [Output: task-001 created]

09:15 - Start Work
      Review 4 backup scripts:
      - scripts/backup/postgres-backup.sh
      - scripts/backup/minio-backup.sh
      - scripts/backup/monitor-backups.sh
      - scripts/backup/verify-backups.sh

09:45 - Post-Edit Hook (first fix)
      npx claude-flow@alpha hooks post-edit \
        --file "scripts/backup/postgres-backup.sh" \
        --memory-key "swarm/devops/backup-postgres-fix" \
        --description "Fixed checksum validation logic"

10:30 - Notify Hook (milestone)
      npx claude-flow@alpha hooks notify \
        --message "PostgreSQL backup script validated - tests passing" \
        --priority "medium"

11:00 - Notify Hook (milestone)
      npx claude-flow@alpha hooks notify \
        --message "MinIO backup script validated - integrity confirmed" \
        --priority "medium"

11:30 - Post-Edit Hook (commit)
      git add scripts/backup/*.sh
      git commit -m "feat: validate and fix backup scripts"

11:45 - Post-Task Hook
      npx claude-flow@alpha hooks post-task \
        --task-id "task-001" \
        --status "completed" \
        --quality-score "9.5" \
        --notes "All backups validated, RTO measured at 12min"

11:45 - Next Assignment
      Coordinator assigns Task 1.2 (Environment Config)
      Wait for handoff from Task 1.1 completion
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-25
**Protocol Owner**: Planner Agent + Swarm Coordinator
**Mandatory Review**: Before Day 1 execution begins
