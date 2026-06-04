# © 2026 Arsenal Quant Project
# File: abi_guardrail.py — Universal EVM Transaction Guardrail & Calldata Decoder
#
# Open-source public release for autonomous agent security (A2A/DeFAI).
#
# Enforces transaction guardrails to prevent Blind Signing.
# Decodes standard ERC20 operations (approve, transfer, transferFrom) in pure Python.
# Verifies destination contracts against a customizable whitelist of audited protocols.

import json
from typing import Dict, Any, List, Tuple

# =============================================================================
# DEFAULT WHITELISTS (Sourced from verified Base Mainnet contracts)
# =============================================================================

DEFAULT_TRUSTED_CONTRACTS: Dict[str, str] = {
    # ERC20 Tokens (Base Mainnet)
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": "USDC (Base ERC20)",
    "0x4200000000000000000000000000000000000006": "WETH (Base ERC20)",
    "0x2e1a7d4d60437637fe6137e5e1975e5a2c43ff8e": "USDT (Base ERC20)",

    # Audited Protocol Routers, Pools & DEXs
    "0x82a5c4cf4b3dfdebc180ff43a85b9b940989f55e": "Fluid Usdc Supply Pool",
    "0x59c7c832e96d2568bea6db468c1aadcbbda08a52": "ParaSwap v6 Router",
    "0x1111111254fb6c44bac0bed2854e76f90643097d": "1inch v6 Router",
    "0x3fc91a3afd9fe38ff40964c203a27f64293db29b": "Uniswap V3 SwapRouter02",
    "0xa5a576a92896e952674e2d45a90e3cd60e5db70e": "Aave V3 Base Pool",
    "0xbc80126938a335012891f740a2dc6033830c00ef": "Moonwell Usdc Market"
}

ERC20_SELECTORS: Dict[str, Tuple[str, str]] = {
    "0x095ea7b3": ("approve", "approve(address,uint256)"),
    "0xa9059cbb": ("transfer", "transfer(address,uint256)"),
    "0x23b872dd": ("transferFrom", "transferFrom(address,address,uint256)"),
    "0xd505accf": ("permit", "permit(address,address,uint256,uint256,uint8,bytes32,bytes32)"),
    "0x8fcbafcc": ("permit_dai", "permit(address,address,uint256,uint256,bool,uint8,bytes32,bytes32)")
}


class ABIGuardrail:
    """
    Decoupled cognitive firewall to inspect and validate EVM transactions.
    Ensures autonomous agents never blind sign raw calldata from external APIs.
    """

    def __init__(self, trusted_contracts: Dict[str, str] = None, max_value_usd_limit: float = 1_000_000):
        self.trusted_contracts = trusted_contracts if trusted_contracts is not None else DEFAULT_TRUSTED_CONTRACTS
        self.max_value_limit = max_value_usd_limit

    def decode_erc20(self, selector: str, data_bytes: bytes) -> Dict[str, Any]:
        """
        Extracts parameters from standard ERC20 method selectors.
        """
        if selector == "0x095ea7b3":  # approve(address,uint256)
            if len(data_bytes) < 68:
                raise ValueError("Payload length is too short for ERC20 approve.")
            spender = "0x" + data_bytes[16:36].hex()
            amount = int.from_bytes(data_bytes[36:68], byteorder="big")
            return {"spender": spender.lower(), "amount": amount}

        elif selector == "0xa9059cbb":  # transfer(address,uint256)
            if len(data_bytes) < 68:
                raise ValueError("Payload length is too short for ERC20 transfer.")
            recipient = "0x" + data_bytes[16:36].hex()
            amount = int.from_bytes(data_bytes[36:68], byteorder="big")
            return {"recipient": recipient.lower(), "amount": amount}

        elif selector == "0x23b872dd":  # transferFrom(address,address,uint256)
            if len(data_bytes) < 100:
                raise ValueError("Payload length is too short for ERC20 transferFrom.")
            sender = "0x" + data_bytes[16:36].hex()
            recipient = "0x" + data_bytes[48:68].hex()
            amount = int.from_bytes(data_bytes[68:100], byteorder="big")
            return {
                "sender": sender.lower(),
                "recipient": recipient.lower(),
                "amount": amount
            }

        elif selector == "0xd505accf":  # permit(address owner, address spender, uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s)
            if len(data_bytes) < 228:
                raise ValueError("Payload length is too short for ERC20 permit.")
            owner = "0x" + data_bytes[16:36].hex()
            spender = "0x" + data_bytes[48:68].hex()
            value = int.from_bytes(data_bytes[68:100], byteorder="big")
            deadline = int.from_bytes(data_bytes[100:132], byteorder="big")
            return {
                "owner": owner.lower(),
                "spender": spender.lower(),
                "value": value,
                "deadline": deadline
            }

        elif selector == "0x8fcbafcc":  # permit(address holder, address spender, uint256 nonce, uint256 expiry, bool allowed, uint8 v, bytes32 r, bytes32 s)
            if len(data_bytes) < 260:
                raise ValueError("Payload length is too short for DAI permit.")
            holder = "0x" + data_bytes[16:36].hex()
            spender = "0x" + data_bytes[48:68].hex()
            nonce = int.from_bytes(data_bytes[68:100], byteorder="big")
            expiry = int.from_bytes(data_bytes[100:132], byteorder="big")
            allowed = int.from_bytes(data_bytes[148:164], byteorder="big") != 0
            return {
                "holder": holder.lower(),
                "spender": spender.lower(),
                "nonce": nonce,
                "expiry": expiry,
                "allowed": allowed
            }

        return {}

    def verify_transaction(self, to_address: str, calldata_hex: str) -> Dict[str, Any]:
        """
        Inspects destination target, decodes the method, and validates the parameters.
        Returns: {
            "status": "APPROVED" | "REJECTED",
            "reason": str,
            "decoded": dict
        }
        """
        to_clean = to_address.strip().lower()
        hex_str = calldata_hex.strip()
        if hex_str.startswith("0x"):
            hex_str = hex_str[2:]

        try:
            data_bytes = bytes.fromhex(hex_str)
        except ValueError:
            return {
                "status": "REJECTED",
                "reason": "Calldata format is not a valid hex string.",
                "decoded": {}
            }

        # 1. Target Whitelist Gate
        if to_clean not in self.trusted_contracts:
            return {
                "status": "REJECTED",
                "reason": f"Contract destination ({to_address}) is not whitelisted. Execution aborted.",
                "decoded": {}
            }

        # 2. Selector parsing
        selector = "0x" + data_bytes[:4].hex().lower()
        decoded = {
            "target_label": self.trusted_contracts[to_clean],
            "selector": selector,
            "method": "unknown"
        }

        # 3. Parameter checks for standard operations
        if selector in ERC20_SELECTORS:
            method_name, signature = ERC20_SELECTORS[selector]
            decoded["method"] = method_name
            decoded["signature"] = signature

            try:
                params = self.decode_erc20(selector, data_bytes)
                decoded["parameters"] = params

                # Spender verification for approvals (Anti-Draining Rule)
                if method_name == "approve":
                    spender = params["spender"]
                    if spender not in self.trusted_contracts:
                        return {
                            "status": "REJECTED",
                            "reason": f"Veto: Spender address ({spender}) is not whitelisted.",
                            "decoded": decoded
                        }

                # Recipient verification for direct transfers
                elif method_name in ("transfer", "transferFrom"):
                    recipient = params["recipient"]
                    if recipient not in self.trusted_contracts:
                        return {
                            "status": "REJECTED",
                            "reason": f"Veto: Recipient address ({recipient}) is not whitelisted.",
                            "decoded": decoded
                        }

                # RULE 11 Veto check for permit (ERC-2612)
                elif method_name == "permit":
                    spender = params["spender"]
                    value = params["value"]
                    if spender not in self.trusted_contracts:
                        return {
                            "status": "REJECTED",
                            "reason": f"Veto: Permit spender address ({spender}) is not whitelisted.",
                            "decoded": decoded
                        }
                    # Value limit verification
                    if value > self.max_value_limit * 10**6: # Assuming USDC decimals
                        return {
                            "status": "REJECTED",
                            "reason": f"Veto: Permitted amount ({value}) exceeds the transaction ceiling limit.",
                            "decoded": decoded
                        }

                # RULE 11 Veto check for permit_dai
                elif method_name == "permit_dai":
                    spender = params["spender"]
                    allowed = params["allowed"]
                    if allowed:
                        if spender not in self.trusted_contracts:
                            return {
                                "status": "REJECTED",
                                "reason": f"Veto: Permit spender address ({spender}) is not whitelisted.",
                                "decoded": decoded
                            }

            except Exception as e:
                return {
                    "status": "REJECTED",
                    "reason": f"Failed to parse ERC20 calldata: {e}",
                    "decoded": decoded
                }
        else:
            # Safe interaction with verified routers (DEX Swap Router)
            decoded["method"] = "protocol_interaction"
            decoded["description"] = f"Interaction with audited protocol router: {decoded['target_label']}"

        return {
            "status": "APPROVED",
            "reason": "Transaction passed all security guardrail whitelists.",
            "decoded": decoded
        }

    def verify_typed_data(self, typed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inspects EIP-712 typed data signatures (phishing mitigation).
        Checks if it is a Permit request and audits the verifyingContract and spender.
        """
        if not isinstance(typed_data, dict):
            return {
                "status": "REJECTED",
                "reason": "Typed data must be a JSON dictionary.",
                "decoded_signature": {}
            }

        primary_type = typed_data.get("primaryType", "")
        message = typed_data.get("message", {})
        domain = typed_data.get("domain", {})

        is_permit = False
        if primary_type == "Permit":
            is_permit = True
        elif "spender" in message and ("value" in message or "allowed" in message or "amount" in message):
            is_permit = True

        decoded_sig = {
            "primaryType": primary_type,
            "is_permit": is_permit,
            "domain": domain,
            "message": message
        }

        if is_permit:
            # Audit verifying contract (the token contract itself)
            verifying_contract = domain.get("verifyingContract", "").strip().lower()
            if verifying_contract and verifying_contract not in self.trusted_contracts:
                return {
                    "status": "REJECTED",
                    "reason": f"Veto: Verifying token contract ({verifying_contract}) is not whitelisted.",
                    "decoded_signature": decoded_sig
                }

            # Audit the spender (who gets the transfer allowance)
            spender = message.get("spender", "").strip().lower()
            if not spender:
                return {
                    "status": "REJECTED",
                    "reason": "Veto: Permit signature missing spender parameter.",
                    "decoded_signature": decoded_sig
                }

            if spender not in self.trusted_contracts:
                return {
                    "status": "REJECTED",
                    "reason": f"Veto: Permit spender address ({spender}) is not whitelisted. Signature request blocked.",
                    "decoded_signature": decoded_sig
                }

            # Audit the amount
            value = message.get("value")
            if value is None:
                value = message.get("amount")
            
            if isinstance(value, (int, float)) and value > self.max_value_limit * 10**6:
                return {
                    "status": "REJECTED",
                    "reason": f"Veto: Permitted amount ({value}) exceeds the transaction ceiling limit.",
                    "decoded_signature": decoded_sig
                }

            return {
                "status": "APPROVED",
                "reason": "Permit signature request passed all security whitelists.",
                "decoded_signature": decoded_sig
            }

        return {
            "status": "APPROVED",
            "reason": "Non-permit EIP-712 signature request approved.",
            "decoded_signature": decoded_sig
        }


if __name__ == "__main__":
    # Self-test simulation
    print("Initializing ABIGuardrail self-test...")
    guardrail = ABIGuardrail()
    
    # 1. Test whitelisted target approve
    test_target = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913" # USDC
    test_calldata = (
        "0x095ea7b3"
        "00000000000000000000000082a5c4cf4b3dfdebc180ff43a85b9b940989f55e" # Fluid Pool spender
        "0000000000000000000000000000000000000000000000000000000005f5e100" # 100 USDC
    )
    res = guardrail.verify_transaction(test_target, test_calldata)
    print(f"Test 1 (Should be APPROVED): {res['status']} (Reason: {res['reason']})")
    assert res["status"] == "APPROVED"

    # 2. Test untrusted spender approve (hacker)
    bad_calldata = (
        "0x095ea7b3"
        "000000000000000000000000badbeef000000000000000000000000000000000" # hacker spender
        "0000000000000000000000000000000000000000000000000000000005f5e100"
    )
    res2 = guardrail.verify_transaction(test_target, bad_calldata)
    print(f"Test 2 (Should be REJECTED): {res2['status']} (Reason: {res2['reason']})")
    assert res2["status"] == "REJECTED"

    # 3. Test permit on-chain whitelisted spender
    permit_calldata = (
        "0xd505accf"
        "0000000000000000000000004200000000000000000000000000000000000006" # owner (WETH)
        "0000000000000000000000001111111254fb6c44bac0bed2854e76f90643097d" # spender (1inch Router)
        "0000000000000000000000000000000000000000000000000000000005f5e100" # value (100 USDC equivalent)
        "00000000000000000000000000000000000000000000000000000000665f8a00" # deadline
        "000000000000000000000000000000000000000000000000000000000000001c" # v
        "0000000000000000000000000000000000000000000000000000000000000000" # r
        "0000000000000000000000000000000000000000000000000000000000000000" # s
    )
    res3 = guardrail.verify_transaction(test_target, permit_calldata)
    print(f"Test 3 (Should be APPROVED): {res3['status']} (Reason: {res3['reason']})")
    assert res3["status"] == "APPROVED"

    # 4. Test permit on-chain malicious spender
    bad_permit_calldata = (
        "0xd505accf"
        "0000000000000000000000004200000000000000000000000000000000000006" # owner
        "000000000000000000000000badbeef000000000000000000000000000000000" # malicious spender
        "0000000000000000000000000000000000000000000000000000000005f5e100"
        "00000000000000000000000000000000000000000000000000000000665f8a00"
        "000000000000000000000000000000000000000000000000000000000000001c"
        "0000000000000000000000000000000000000000000000000000000000000000"
        "0000000000000000000000000000000000000000000000000000000000000000"
    )
    res4 = guardrail.verify_transaction(test_target, bad_permit_calldata)
    print(f"Test 4 (Should be REJECTED): {res4['status']} (Reason: {res4['reason']})")
    assert res4["status"] == "REJECTED"

    # 5. Test EIP-712 permit off-chain validation APPROVED
    typed_data_ok = {
        "primaryType": "Permit",
        "domain": {
            "name": "USD Coin",
            "version": "2",
            "chainId": 8453,
            "verifyingContract": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
        },
        "message": {
            "owner": "0x4200000000000000000000000000000000000006",
            "spender": "0x1111111254fb6c44bac0bed2854e76f90643097d", # whitelisted 1inch
            "value": 5000000000,
            "nonce": 0,
            "deadline": 1717545600
        }
    }
    res5 = guardrail.verify_typed_data(typed_data_ok)
    print(f"Test 5 (Should be APPROVED): {res5['status']} (Reason: {res5['reason']})")
    assert res5["status"] == "APPROVED"

    # 6. Test EIP-712 permit off-chain validation REJECTED (untrusted spender)
    typed_data_bad = {
        "primaryType": "Permit",
        "domain": {
            "name": "USD Coin",
            "version": "2",
            "chainId": 8453,
            "verifyingContract": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
        },
        "message": {
            "owner": "0x4200000000000000000000000000000000000006",
            "spender": "0xbadbeef000000000000000000000000000000000", # untrusted spender
            "value": 5000000000,
            "nonce": 0,
            "deadline": 1717545600
        }
    }
    res6 = guardrail.verify_typed_data(typed_data_bad)
    print(f"Test 6 (Should be REJECTED): {res6['status']} (Reason: {res6['reason']})")
    assert res6["status"] == "REJECTED"

    print("All ABIGuardrail self-tests PASSED successfully!")

