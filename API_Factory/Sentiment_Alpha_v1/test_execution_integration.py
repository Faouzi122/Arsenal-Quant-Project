#!/usr/bin/env python3
# © 2026 Arsenal Decision Engine — Decision Intelligence Layer
# File: test_execution_integration.py — Direct Aggregators & Guardrail Integration Tests
#
# Usage: python3 test_execution_integration.py

import sys
import os
import json

# Ensure parent directory is in path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.aggregator_client import aggregator_client
from app.services.smeltor_adapter import smeltor_adapter
from app.services.transaction_guardrail import transaction_guardrail
from app.core.arbitrage_engine import arbitrage_engine, ArbitrageOpportunity


def run_aggregator_tests():
    print("=" * 60)
    print("  RUNNING AGGREGATOR CLIENT UNIT TESTS")
    print("=" * 60)

    # Test Case 1: Fetch swap transaction from client (Base USDC -> WETH)
    print("Test Case 1: Get Swap transaction calldata from Aggregator Client")
    usdc = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
    weth = "0x4200000000000000000000000000000000000006"
    
    tx_data = aggregator_client.get_swap_transaction(
        chain_id=8453,
        src_token=usdc,
        dst_token=weth,
        amount=10_000_000 # 10 USDC
    )
    
    assert tx_data["status"] == "success", "Expected successful transaction construction"
    assert "transactions" in tx_data
    tx = tx_data["transactions"][0]
    assert tx["kind"] == "swap"
    assert tx["chainId"] == 8453
    assert tx["to"].startswith("0x")
    assert tx["data"].startswith("0x")
    print(f"  [PASS] Successfully retrieved {tx_data['provider']} transaction payload.")
    print(f"         Target router: {tx['to']}")
    print(f"         Calldata (first 32 chars): {tx['data'][:32]}...")
    print("-" * 60)


def run_adapter_tests():
    print("\n" + "=" * 60)
    print("  RUNNING ROUTING ADAPTER TESTS")
    print("=" * 60)

    # Test Case 2: Resolve Swap intent dynamically
    print("Test Case 2: Resolve swap intent dynamically via Aggregators")
    res_swap = smeltor_adapter.resolve_intent("Swap 50 USDC to ETH on Base")
    assert res_swap["status"] == "success"
    assert "DEX Aggregator" in res_swap["resolved_by"]
    assert len(res_swap["transactions"]) == 1
    assert res_swap["transactions"][0]["kind"] == "swap"
    assert res_swap["execution_sequence"][0]["simulation_status"] == "READY_FOR_LOCAL_SIGNING"
    print("  [PASS] Successfully resolved swap intent dynamically.")

    # Test Case 3: Resolve Earn intent via whitelisted layouts
    print("\nTest Case 3: Resolve earn intent via whitelisted layouts")
    res_earn = smeltor_adapter.resolve_intent("Earn USDC yield on Base")
    assert res_earn["status"] == "success"
    assert "Yield Router" in res_earn["resolved_by"]
    assert len(res_earn["transactions"]) == 2
    assert res_earn["transactions"][0]["kind"] == "approval"
    assert res_earn["transactions"][1]["kind"] == "deposit"
    print("  [PASS] Successfully resolved earn intent using whitelisted contracts.")
    print("-" * 60)


def run_security_guardrail_tests():
    print("\n" + "=" * 60)
    print("  RUNNING TRANSACTION GUARDRAIL AUDITS (RULE 11)")
    print("=" * 60)

    # Test Case 4: Verify that the resolved swap passes the guardrail
    print("Test Case 4: Inspecting resolved swap transaction")
    res_swap = smeltor_adapter.resolve_intent("Swap 10 USDC to ETH on Base")
    tx = res_swap["transactions"][0]
    audit = transaction_guardrail.inspect_transaction(to=tx["to"], data=tx["data"])
    assert audit["status"] == "APPROVED", f"Expected APPROVED, got {audit['status']} ({audit.get('reason')})"
    print(f"  [PASS] Transaction approved: {audit['decoded_call']['target_contract']}")

    # Test Case 5: Verify that the whitelisted Fluid Earn transactions pass the guardrail
    print("\nTest Case 5: Inspecting whitelisted Fluid Earn transactions")
    res_earn = smeltor_adapter.resolve_intent("Earn USDC yield on Base")
    tx_approve = res_earn["transactions"][0]
    tx_deposit = res_earn["transactions"][1]
    
    audit_approve = transaction_guardrail.inspect_transaction(to=tx_approve["to"], data=tx_approve["data"])
    audit_deposit = transaction_guardrail.inspect_transaction(to=tx_deposit["to"], data=tx_deposit["data"])
    
    assert audit_approve["status"] == "APPROVED"
    assert audit_deposit["status"] == "APPROVED"
    print("  [PASS] Both token approval and Fluid pool deposit approved safely.")

    # Test Case 6: Detect and block unknown target address
    print("\nTest Case 6: Veto checks on untrusted contract target")
    untrusted_target = "0xdeadbeef00000000000000000000000000000000"
    audit_untrusted = transaction_guardrail.inspect_transaction(to=untrusted_target, data="0x095ea7b3")
    assert audit_untrusted["status"] == "REJECTED"
    assert "not whitelisted" in audit_untrusted["reason"] or "not in the system whitelist" in audit_untrusted["reason"]
    print("  [PASS] Successfully blocked transaction targeting unverified contract address.")

    # Test Case 7: Detect and block unverified spender in approve (Anti-Draining)
    print("\nTest Case 7: Spender validation (Anti-Approval Drainer)")
    usdc = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
    untrusted_spender = "0x9999999999999999999999999999999999999999"
    malicious_data = f"0x095ea7b3000000000000000000000000{untrusted_spender[2:]}ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    
    audit_malicious = transaction_guardrail.inspect_transaction(to=usdc, data=malicious_data)
    assert audit_malicious["status"] == "REJECTED"
    assert "Security Veto" in audit_malicious["reason"]
    assert "spender address" in audit_malicious["reason"]
    print("  [PASS] Successfully blocked unverified token approval spender.")
    print("-" * 60)


def run_system_circuit_breaker_tests():
    print("\n" + "=" * 60)
    print("  RUNNING SYSTEM CIRCUIT BREAKER INTEGRATION")
    print("=" * 60)

    # Test Case 8: Safe trade execution results in APPROVED details
    print("Test Case 8: Safe Arbitrage Opportunity triggering EXECUTE")
    opp = ArbitrageOpportunity(
        entry_price_usd=3000.0,
        exit_price_usd=3200.0,
        stop_loss_price_usd=2950.0,
        position_size_usd=100000.0,
        gross_yield_usd=6000.0,
        incentives_usd=100.0,
        gas_usd=20.0,
        slippage_pct=0.001,
        mev_probability=0.1,
        is_lp_position=False,
        funding_rate_8h=0.0002,
        holding_periods_8h=1,
        flash_loan_amount_usd=100000.0,
        flash_loan_fee_pct=0.09,
        resistance_level_usd=3100.0,
        candle_close_4h_usd=3110.0,
        volume_24h=5000000.0,
        volume_sma_20=3000000.0,
        volume_stddev=500000.0,
        atr_values=[12.0, 15.0, 18.0]
    )

    # Mocking how main.py handles it
    result = arbitrage_engine.evaluate(opp)
    assert result["signal"] == "EXECUTE"
    
    intent = "Swap 10 USDC to ETH on Base"
    exec_details = smeltor_adapter.resolve_intent(intent, mock=True)
    
    verified_txs = []
    unsafe_detected = False
    for tx in exec_details.get("transactions", []):
        audit = transaction_guardrail.inspect_transaction(to=tx["to"], data=tx["data"])
        if audit["status"] == "REJECTED":
            unsafe_detected = True
            break
        verified_txs.append(audit["decoded_call"])
        
    assert not unsafe_detected
    result["execution_details"] = exec_details
    result["execution_details"]["audited_calls"] = verified_txs
    
    assert "audited_calls" in result["execution_details"]
    assert result["execution_details"]["audited_calls"][0]["method"] == "protocol_interaction"
    print("  [PASS] Successfully integrated security guardrail check into safe EXECUTE decision.")

    # Test Case 9: Injected malicious calldata triggers Signal Pivot to DELAY
    print("\nTest Case 9: Unsafe transaction triggering security veto (Signal Pivot)")
    untrusted_spender = "0x9999999999999999999999999999999999999999"
    compromised_details = {
        "status": "success",
        "transactions": [
            {
                "kind": "approval",
                "chainId": 8453,
                "to": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", # USDC
                "data": f"0x095ea7b3000000000000000000000000{untrusted_spender[2:]}ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
                "value": "0",
                "gas": "300000"
            }
        ]
    }

    result_attack = arbitrage_engine.evaluate(opp) # Normally EXECUTE
    assert result_attack["signal"] == "EXECUTE"

    unsafe_detected = False
    rejection_reason = ""
    for tx in compromised_details.get("transactions", []):
        audit = transaction_guardrail.inspect_transaction(to=tx["to"], data=tx["data"])
        if audit["status"] == "REJECTED":
            unsafe_detected = True
            rejection_reason = audit["reason"]
            break

    if unsafe_detected:
        result_attack["signal"] = "DELAY"
        result_attack["context"] = f"SECURITY SHIELD: Rejected transaction. Reason: {rejection_reason}"[:120]
        result_attack["execution_details"] = {
            "status": "rejected",
            "reason": rejection_reason,
            "transactions": []
        }

    assert result_attack["signal"] == "DELAY"
    assert len(result_attack["execution_details"]["transactions"]) == 0
    assert "Security Veto" in result_attack["context"]
    print("  [PASS] Successfully verified security circuit breaker: signal pivoted to DELAY, transactions purged.")
    print("=" * 60)


if __name__ == "__main__":
    run_aggregator_tests()
    run_adapter_tests()
    run_security_guardrail_tests()
    run_system_circuit_breaker_tests()
    print("\n🎉 ALL DIRECT AGGREGATOR & SECURITY GUARDRAIL TESTS PASSED SUCCESSFULLY! 🚀")
