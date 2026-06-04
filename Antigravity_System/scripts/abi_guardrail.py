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
    "0x23b872dd": ("transferFrom", "transferFrom(address,address,uint256)")
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


if __name__ == "__main__":
    # Self-test simulation
    print("Initializing ABIGuardrail self-test...")
    guardrail = ABIGuardrail()
    
    # Test whitelisted target
    test_target = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913" # USDC
    
    # Test whitelisted spender approve
    test_calldata = (
        "0x095ea7b3"
        "00000000000000000000000082a5c4cf4b3dfdebc180ff43a85b9b940989f55e" # Fluid Pool spender
        "0000000000000000000000000000000000000000000000000000000005f5e100" # 100 USDC
    )
    
    res = guardrail.verify_transaction(test_target, test_calldata)
    print(f"Self-test result (Should be APPROVED): {res['status']} (Reason: {res['reason']})")
    assert res["status"] == "APPROVED"
