"""Direct-mode tests for the StreamingPayrollEscrow contract."""

import json
import re

from gltest.direct import create_address

APPROVE_JSON = json.dumps({"decision": "approve", "reasoning": "Milestone work done."})
DENY_JSON = json.dumps({"decision": "deny", "reasoning": "Milestone not finished."})
EVIDENCE_URL = "https://example.com/milestone"
EVIDENCE_BODY = "Milestone evidence delivered. PAYROLL_BODY_MARKER"


def _create(contract, vm, employer, employee, total=100, per=50, count=2):
    vm.sender = employer
    vm.value = total
    return contract.create_stream(
        employer=str(employer),
        employee=str(employee),
        total_amount=total,
        amount_per_milestone=per,
        milestone_count=count,
    )


def _release(contract, vm, employer, stream_id, index=1, llm_json=APPROVE_JSON, url=EVIDENCE_URL,
            justification="Milestone completed on schedule."):
    vm.sender = employer
    vm.mock_web(re.escape(url), {"status": 200, "body": EVIDENCE_BODY})
    vm.mock_llm(
        r"BEGIN UNTRUSTED EVIDENCE ---\s*" + re.escape(url) + r"[\s\S]*"
        + r"--- BEGIN FETCHED CONTENT ---\s*" + re.escape(EVIDENCE_BODY),
        llm_json,
    )
    return contract.release_milestone(
        stream_id=stream_id, milestone_index=index,
        evidence_url=url, justification=justification,
    )


def test_create_stream_validates(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/streaming_payroll_escrow.py")
    employer = create_address("employer")
    employee = create_address("employee")

    direct_vm.sender = employer
    direct_vm.value = 100
    with direct_vm.expect_revert("Employer and employee are required"):
        contract.create_stream(employer="", employee=str(employee),
                                total_amount=100, amount_per_milestone=50, milestone_count=2)
    with direct_vm.expect_revert("Employer and employee must differ"):
        contract.create_stream(        employer=str(employer), employee=str(employer),
                                total_amount=100, amount_per_milestone=50, milestone_count=2)
    with direct_vm.expect_revert("Total amount must be > 0"):
        contract.create_stream(employer=str(employer), employee=str(employee),
                                total_amount=0, amount_per_milestone=50, milestone_count=2)
    with direct_vm.expect_revert("Milestone count must be at least 1"):
        contract.create_stream(employer=str(employer), employee=str(employee),
                                total_amount=100, amount_per_milestone=50, milestone_count=0)
    with direct_vm.expect_revert("Total must equal amount_per_milestone * milestone_count"):
        contract.create_stream(employer=str(employer), employee=str(employee),
                                total_amount=100, amount_per_milestone=30, milestone_count=2)
    with direct_vm.expect_revert("Escrow funding must equal the stream total"):
        direct_vm.value = 50
        contract.create_stream(employer=str(employer), employee=str(employee),
                                total_amount=100, amount_per_milestone=50, milestone_count=2)
    with direct_vm.expect_revert("Escrow funding must equal the stream total"):
        direct_vm.value = 150
        contract.create_stream(employer=str(employer), employee=str(employee),
                                total_amount=100, amount_per_milestone=50, milestone_count=2)

    vid = _create(contract, direct_vm, employer, employee, total=100, per=50, count=2)
    s = contract.get_stream(vid)
    assert s["status"] == "active"
    assert s["total_amount"] == 100
    assert s["amount_per_milestone"] == 50
    assert s["milestone_count"] == 2
    assert s["released"] == 0


def test_release_guards(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/streaming_payroll_escrow.py")
    employer = create_address("employer")
    employee = create_address("employee")

    vid = _create(contract, direct_vm, employer, employee, total=100, per=50, count=2)

    direct_vm.sender = employee
    with direct_vm.expect_revert("Only employer can release milestones"):
        _release(contract, direct_vm, employee, vid, index=1)

    direct_vm.sender = employer
    with direct_vm.expect_revert("Milestone must be released sequentially"):
        _release(contract, direct_vm, employer, vid, index=2)

    with direct_vm.expect_revert("Stream not found"):
        contract.release_milestone(stream_id="nope", milestone_index=1,
                                  evidence_url=EVIDENCE_URL, justification="x")


def test_release_approve_flow(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/streaming_payroll_escrow.py")
    employer = create_address("employer")
    employee = create_address("employee")

    vid = _create(contract, direct_vm, employer, employee, total=100, per=50, count=2)
    result = _release(contract, direct_vm, employer, vid, index=1)
    assert result["decision"] == "approve"
    assert result["released"] == 1
    s = contract.get_stream(vid)
    assert s["released"] == 1
    assert s["status"] == "active"

    result = _release(contract, direct_vm, employer, vid, index=2)
    assert result["decision"] == "approve"
    assert result["released"] == 2
    s = contract.get_stream(vid)
    assert s["status"] == "completed"


def test_release_deny_leaves_state(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/streaming_payroll_escrow.py")
    employer = create_address("employer")
    employee = create_address("employee")

    vid = _create(contract, direct_vm, employer, employee, total=100, per=50, count=2)
    result = _release(contract, direct_vm, employer, vid, index=1, llm_json=DENY_JSON)
    assert result["decision"] == "denied"
    s = contract.get_stream(vid)
    assert s["released"] == 0
    assert s["status"] == "active"
    assert s["denial_reasoning"] != ""


def test_cancel_refunds_remaining(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/streaming_payroll_escrow.py")
    employer = create_address("employer")
    employee = create_address("employee")

    vid = _create(contract, direct_vm, employer, employee, total=100, per=50, count=2)
    _release(contract, direct_vm, employer, vid, index=1)
    direct_vm.sender = employer
    contract.cancel_stream(stream_id=vid)
    s = contract.get_stream(vid)
    assert s["status"] == "cancelled"
    assert s["released"] == 1
    assert s["total_withdrawn"] == 50


def test_release_exceeds_remaining(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/streaming_payroll_escrow.py")
    employer = create_address("employer")
    employee = create_address("employee")

    vid = _create(contract, direct_vm, employer, employee, total=100, per=50, count=2)
    _release(contract, direct_vm, employer, vid, index=1)
    _release(contract, direct_vm, employer, vid, index=2)
    assert contract.get_stream(vid)["status"] == "completed"
    with direct_vm.expect_revert("Stream is not active"):
        _release(contract, direct_vm, employer, vid, index=3)
