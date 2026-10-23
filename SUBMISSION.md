# Submission: Streaming Payroll Escrow

## Category
Intelligent Contracts

## Contract Name
Streaming Payroll Escrow

## Summary
A reusable GenLayer primitive for milestone-based streaming payroll: the employer escrows the full payment up front (total == per_milestone * milestone_count) and releases each milestone only when delivered work passes LLM consensus against fetched evidence and the employer's justification; denials store feedback without moving funds, and the employer can cancel to refund the un-released escrow.

## What Makes This Unique
- **Escrow-first streaming**: the full payment is locked at creation, so the employee can trust the milestone sequence while the employer retains judgment power
- **Evidence-gated release**: each milestone release runs through `gl.vm.run_nondet_unsafe` with eval/validator consensus; the contract fetches the evidence URL on-chain and embeds it (fenced, untrusted) into the release prompt
- **Sequential release**: milestone N requires N-1 released, preventing skipped or retroactive releases; released/withdrawn amounts tracked with balance checks
- **Deny is feedback, not a lock**: denial stores reasoning (bounded, deterministic fallback) and moves no funds; cancel refunds the un-released balance

## How Consensus Is Used
The contract uses `gl.vm.run_nondet_unsafe()` with custom eval/validator functions. The validator independently fetches the evidence URL and re-runs the LLM judgment against the milestone. Consensus requires the validator to match the leader's decision. Unreachable evidence deterministically denies. Scores/decisions use exact-match consensus (`SCORE_TOLERANCE = 5`).

## Technical Details
- Python-based GenLayer Intelligent Contract
- Uses `gl.nondet.exec_prompt(response_format="json")` for release decisions
- Uses `gl.nondet.web.get()` for contract-side evidence acquisition (non-200 -> deny)
- TreeMap storage: streams keyed by id with employer/employee/amounts/milestones/status lifecycle
- Integer-only domain (wei amounts; milestone counts/amounts as u256); time gates via `datetime` against consensus time
- Constants: `MAX_STREAMS = 100`, `MAX_JUSTIFICATION_CHARS = 2000`, `MAX_REASONING_CHARS = 2000`, `SCORE_TOLERANCE = 5`

## Use Case
Milestone billing for contractors, streaming salaries for DAO/team payroll, escrowed work payments, and any arrangement where work is delivered incrementally and payment should follow verified delivery.

## Verification
- 6/6 direct-mode unit tests (creation guards, release guards, approve flow with sequential payouts, deny-leaves-funds, cancel refund, release-exceeds-remaining)
- `genvm-lint check` + validation pass (5 methods: 2 view, 3 write)
- On-chain verified on studionet: payable creation, sequential-release revert, cancel refund flow

## Live Deployment
Deployed on GenLayer studionet (chain `61999`):
[`0xEa03F4FeaD3BE16Ba8091Eac1290254d29bF54d8`](https://explorer-studio.genlayer.com/address/0xEa03F4FeaD3BE16Ba8091Eac1290254d29bF54d8)

## Steward Request Response
**Request**: Please submit matching source and deployment that enforce the escrow funding invariant at creation: the actual payable value must equal the stream's recorded total (and therefore amount per milestone times milestone count), so an underfunded stream cannot draw on another stream's balance and an overpayment cannot be stranded. Please include tests showing underpayment and overpayment revert, while exact funding supports all milestone payouts and cancellation refunds the precise unreleased remainder.

**Fix**: `create_stream` now reverts unless `msg.value == total_amount` at creation. Underpayment/overpayment tests added; exact funding supports milestone payouts and cancellation refunds the unreleased remainder.

## Source Code
See `contracts/streaming_payroll_escrow.py`

## Steward Request Response
No steward-request fixes required for this contract (no disputed lifecycle path was flagged).