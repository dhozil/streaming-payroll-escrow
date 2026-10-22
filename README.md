<div align="center">

# Streaming Payroll Escrow

**Employer-funded milestone streaming: the employer escrows the full payment up front and releases each milestone only when delivered work passes LLM consensus against fetched evidence.

![GenLayer](https://img.shields.io/badge/GenLayer-Intelligent%20Contract-6a4cff)
![Python](https://img.shields.io/badge/Python-3.12-3776AB)
![Status](https://img.shields.io/badge/status-live%20on%20studionet-2ea44f)
![Tests](https://img.shields.io/badge/tests-6%20passed-2ea44f)

[Live Contract](https://explorer-studio.genlayer.com/address/0xEa03F4FeaD3BE16Ba8091Eac1290254d29bF54d8) 

[GenLayer Docs](https://docs.genlayer.com)

</div>

---

## Why

Milestone payments usually die in review: either the human reviewer (the employer) judges off-chain chat, or the contract asks an LLM to judge with no reliable way to see the actual delivered work. StreamingPayrollEscrow makes the employer the judge *on-chain*: they escrow the whole payment up front, then release milestones by judging evidence delivered by the employee - with LLM consensus, sequential release, and a refund path when work never gets delivered.

## Live Deployment

| | |
|---|---|
| **Contract** | [StreamingPayrollEscrow](https://explorer-studio.genlayer.com/address/0xEa03F4FeaD3BE16Ba8091Eac1290254d29bF54d8) |
| **Address** | `0xEa03F4FeaD3BE16Ba8091Eac1290254d29bF54d8` |
| **Network** | GenLayer studionet (chain `61999`) |
| **Status** | Deployed + verified on-chain |

## Highlights

- **Evidence-gated milestone release**: the employer releases a milestone by judging `evidence_url` + `justification` via LLM consensus (`gl.vm.run_nondet_unsafe` with eval/validator split); the fetched content is fenced as untrusted data
- **Sequential release**: milestone `N` can only be released after `N-1`, and released + approved amounts are tracked (`released`, `total_withdrawn`) with balance checks - no double-release, no skipping
- **Deny never moves funds**: an LLM `deny` stores the denial reasoning + timestamp and leaves `released` untouched; the employer retries or cancels
- **Cancel refunds the escrow**: cancelling an active stream refunds the un-released balance to the employer and marks the stream `cancelled`

## How It Works

```
create_stream (employer, employee, total = per_milestone * milestone_count, payable)
      |
      v
release_milestone (employer: milestone_index + evidence URL + justification)
      |   -> LLM consensus vs fetched evidence -> approve: released += 1, payout employee
      |   -> deny: store reasoning, no funds move
      v
cancel_stream (employer, active only) -> refund remaining to employer
```

## Methods

| Role | Method | Guard |
|---|---|---|
| Employer | `create_stream`, `release_milestone`, `cancel_stream` | employer-only writes; creation math validated (total == per_milestone * milestone_count); release sequential + balance checked |
| Any | `get_stream`, `get_all_streams` | read-only |

## Security Model

- **No permanent lock**: employer can cancel any active stream and refund the un-released escrow balance; approved milestones are paid out exactly once (status flip before transfer)
- **Sequencing**: milestones release strictly in order (`released + 1`), preventing cherry-picking of already-delivered work
- **Consensus**: every release runs through `gl.vm.run_nondet_unsafe` with independent validators that fetch the evidence themselves; unreachable evidence deterministically denies
- **Deny is feedback, not a lock**: denial reasoning is stored (non-empty, length-bounded, deterministic fallback) but never consumes/consumes the release attempt

## Test

```bash
gltest tests/ -q   # 6 passed
```

## Lint

```bash
genvm-lint check contracts/streaming_payroll_escrow.py
```

## Live Deployment

Deployed on GenLayer studionet (chain `61999`):
[`0xEa03F4FeaD3BE16Ba8091Eac1290254d29bF54d8`](https://explorer-studio.genlayer.com/address/0xEa03F4FeaD3BE16Ba8091Eac1290254d29bF54d8)