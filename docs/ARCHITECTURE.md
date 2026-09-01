# Architecture

## Overview

MilestoneVault is a single GenLayer Intelligent Contract that combines escrow state management with nondeterministic evidence evaluation. The frontend handles presentation; the contract handles all state transitions and money movement.

## System Components

```
┌─────────────────────────────────────────┐
│  Frontend (HTML/JS)                     │
│  - Wallet connection                    │
│  - Contract interaction                 │
│  - Transaction lifecycle                │
│  - Result display                       │
└──────────────┬──────────────────────────┘
               │ ethers.js calls
┌──────────────▼──────────────────────────┐
│  Intelligent Contract                   │
│  milestone_vault.py                     │
│                                         │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │ Escrow      │  │ Evaluator        │  │
│  │ State       │  │ (run_nondet_     │  │
│  │ Machine     │  │  unsafe)         │  │
│  │             │  │                  │  │
│  │ Projects    │  │ Leader: fetch +  │  │
│  │ Milestones  │  │ evaluate         │  │
│  │ Disputes    │  │                  │  │
│  │ Balance     │  │ Validator:       │  │
│  │             │  │ independent      │  │
│  │ Settlement  │  │ re-evaluation    │  │
│  └─────────────┘  └──────────────────┘  │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  GenLayer Nondeterministic Layer         │
│                                         │
│  gl.nondet.web.render(url)              │
│      → fetches live web evidence        │
│                                         │
│  gl.nondet.exec_prompt(prompt)          │
│      → LLM extracts structured facts    │
│                                         │
│  gl.vm.run_nondet_unsafe(leader, val)   │
│      → consensus between validators     │
└─────────────────────────────────────────┘
```

## Contract Storage

All entities are stored as JSON strings in `TreeMap[str, str]`:

| Storage | Key | Value |
|---------|-----|-------|
| `projects` | `"p-1"` | JSON project data |
| `milestones` | `"m-1"` | JSON milestone data |
| `disputes` | `"d-1"` | JSON dispute data |

Counters and balance use `u256`.

## State Machines

### Project State

```
CREATED → FUNDED → ACTIVE → COMPLETED
                            → CANCELLED
```

- `CREATED`: project exists, no funds deposited
- `FUNDED`: at least one funding transaction confirmed
- `ACTIVE`: milestones have been created
- `COMPLETED`: all milestones resolved
- `CANCELLED`: project cancelled by buyer

### Milestone State

```
PENDING → SUBMITTED → EVALUATING → APPROVED → RELEASED
                                    → REJECTED
                                    → INCONCLUSIVE

REJECTED → DISPUTED → RE_EVALUATING → APPROVED → RELEASED
                                       → REJECTED
                                       → INCONCLUSIVE
```

### Dispute State

```
OPEN → RESOLVED
```

## Data Flow

### Create + Fund + Evaluate

1. `create_project(provider, description)` → stores project as CREATED
2. `fund_project(project_id)` [payable] → transitions to FUNDED, updates balance
3. `create_milestone(project_id, description, criteria, amount)` → stores milestone as PENDING, transitions project to ACTIVE
4. `submit_evidence(milestone_id, urls)` → stores URLs, transitions to SUBMITTED
5. `evaluate_milestone(milestone_id)` → triggers GenLayer consensus → deterministic settlement

### Evaluation Pipeline

```
evaluate_milestone(milestone_id)
    │
    ├─ Parse stored URLs and criteria
    │
    ├─ leader_fn():
    │   ├─ Validate all URLs (SSRF check)
    │   ├─ Fetch each URL via gl.nondet.web.render()
    │   ├─ Sanitize content (strip scripts/styles)
    │   ├─ Build evaluation prompt (system rules + untrusted evidence)
    │   ├─ Call gl.nondet.exec_prompt() for structured evaluation
    │   ├─ Parse JSON response
    │   └─ Derive verdict deterministically from criterion results
    │
    ├─ validator_fn(leader_result):
    │   ├─ Validate leader result structure
    │   ├─ Independently call leader_fn() (full re-evaluation)
    │   ├─ Compare verdict (exact match)
    │   └─ Compare each criterion status (exact match)
    │
    └─ Settlement:
        ├─ APPROVED → _release_milestone() → funds sent to provider
        ├─ REJECTED → status = REJECTED, funds locked
        └─ INCONCLUSIVE → status = INCONCLUSIVE, funds locked
```

## Settlement Logic

```
_release_milestone(milestone):
    1. Check not already paid (double payout prevention)
    2. Calculate: amount ≤ funded - released (solvency check)
    3. Update project.total_released
    4. Decrease contract.balance
    5. Mark milestone as paid
    6. provider_addr = self.provider_addresses[project_id]  (native Address)
    7. _EoaRecipient(provider_addr).emit_transfer(value=u256(amount))
```

The provider address is stored natively as `Address` in `provider_addresses: TreeMap[str, Address]`. No string conversion or caller-supplied address is used for payout.

## Over-Allocation Prevention

When creating a milestone, the contract checks:

```
milestone.amount ≤ project.total_funded - project.total_released
```

This prevents the buyer from creating milestones that exceed the available escrow.
