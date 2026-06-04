# © 2026 Arsenal Decision Engine — Decision Intelligence Layer
# File: transaction_guardrail.py — Universal EVM Transaction Security Guardrail
#
# Rule 11 (Defense in Depth): Prevents blind signing attacks by verifying target
# contracts, decoding ERC20 approvals, and validating spender parameters locally.
# Zero external dependencies (high performance, mechanical sympathy).

import json
from typing import Dict, Any, List, Tuple

# =============================================================================
# SAFETY WHITELISTS & POLICIES (Strict boundaries)
# =============================================================================

# Whitelisted protocol contracts on Base (chainId 8453)
_TRUSTED_TARGETS: Dict[str, str] = {
    # ERC20 Tokens (Base)
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": "USDC (Base ERC20)",
    "0x4200000000000000000000000000000000000006": "WETH (Base ERC20)",
    "0x2e1a7d4d60437637fe6137e5e1975e5a2c43ff8e": "USDT (Base ERC20)",

    # Audited Protocol Routers & Pools
    "0x82a5c4cf4b3dfdebc180ff43a85b9b940989f55e": "Fluid Usdc Supply Pool (Fluid APY)",
    "0x59c7c832e96d2568bea6db468c1aadcbbda08a52": "ParaSwap v6 Router (DEX Aggregator)",
    "0x1111111254fb6c44bac0bed2854e76f90643097d": "1inch v6 Router (DEX Aggregator)",
    "0x3fc91a3afd9fe38ff40964c203a27f64293db29b": "Uniswap V3 SwapRouter02 (DEX)",
    "0xa5a576a92896e952674e2d45a90e3cd60e5db70e": "Aave V3 Base Pool (Lending)",
    "0xbc80126938a335012891f740a2dc6033830c00ef": "Moonwell Usdc Market (Lending)"
}

# Standard ERC20 Method Selectors (EVM first 4 bytes of calldata)
_ERC20_SELECTORS: Dict[str, Tuple[str, str]] = {
    "0x095ea7b3": ("approve", "approve(address,uint256)"),
    "0xa9059cbb": ("transfer", "transfer(address,uint256)"),
    "0x23b872dd": ("transferFrom", "transferFrom(address,address,uint256)")
}

# Maximum allowed transaction value/amount for safety checks (e.g. $10,000,000 equivalent)
_MAX_TRANSACTION_LIMIT: int = 10_000_000 * 10**6  # 10M USDC (6 decimals)


class TransactionGuardrail:
    """
    Cognitive Firewall for On-Chain AI Agents.
    Decodes raw hex data locally and rejects transactions that violate security invariants.
    """

    @staticmethod
    def decode_erc20_params(selector: str, data_bytes: bytes) -> Dict[str, Any]:
        """
        Parses standard ERC20 parameters from calldata bytes using offset indexing.
        """
        if selector == "0x095ea7b3":  # approve(address,uint256)
            if len(data_bytes) < 68:
                raise ValueError("Calldata too short for ERC20 approve")
            # Extract 32-byte spender and 32-byte amount
            spender_word = data_bytes[4:36]
            amount_word = data_bytes[36:68]
            # Address is the last 20 bytes of the 32-byte word
            spender = "0x" + spender_word[12:].hex()
            amount = int.from_bytes(amount_word, byteorder="big")
            return {"spender": spender.lower(), "amount": amount}

        elif selector == "0xa9059cbb":  # transfer(address,uint256)
            if len(data_bytes) < 68:
                raise ValueError("Calldata too short for ERC20 transfer")
            recipient_word = data_bytes[4:36]
            amount_word = data_bytes[36:68]
            recipient = "0x" + recipient_word[12:].hex()
            amount = int.from_bytes(amount_word, byteorder="big")
            return {"recipient": recipient.lower(), "amount": amount}

        elif selector == "0x23b872dd":  # transferFrom(address,address,uint256)
            if len(data_bytes) < 100:
                raise ValueError("Calldata too short for ERC20 transferFrom")
            sender_word = data_bytes[4:36]
            recipient_word = data_bytes[36:68]
            amount_word = data_bytes[68:100]
            sender = "0x" + sender_word[12:].hex()
            recipient = "0x" + recipient_word[12:].hex()
            amount = int.from_bytes(amount_word, byteorder="big")
            return {
                "sender": sender.lower(),
                "recipient": recipient.lower(),
                "amount": amount
            }

        return {}

    def inspect_transaction(self, to: str, data: str, value: str = "0") -> Dict[str, Any]:
        """
        Inspects an on-chain transaction proposal.
        Returns: {
            "status": "APPROVED" | "REJECTED",
            "reason": str,
            "decoded_call": dict
        }
        """
        to_clean = to.strip().lower()
        data_clean = data.strip()
        
        # Ensure data is hex-encoded
        if data_clean.startswith("0x"):
            data_hex = data_clean[2:]
        else:
            data_hex = data_clean

        try:
            data_bytes = bytes.fromhex(data_hex)
        except ValueError:
            return {
                "status": "REJECTED",
                "reason": "Invalid hex format in calldata.",
                "decoded_call": {}
            }

        # 1. Target Whitelisting Check (Destination verification)
        if to_clean not in _TRUSTED_TARGETS:
            return {
                "status": "REJECTED",
                "reason": f"Destination target contract {to} is not in the system whitelist.",
                "decoded_call": {}
            }

        # 2. Extract Selector (first 4 bytes)
        selector = "0x" + data_bytes[:4].hex().lower()
        decoded_call = {
            "target_contract": _TRUSTED_TARGETS[to_clean],
            "selector": selector,
            "method": "unknown"
        }

        # 3. Analyze Function Call
        if selector in _ERC20_SELECTORS:
            method_name, signature = _ERC20_SELECTORS[selector]
            decoded_call["method"] = method_name
            decoded_call["signature"] = signature
            
            try:
                params = self.decode_erc20_params(selector, data_bytes)
                decoded_call["parameters"] = params

                # RULE 11 Veto check for 'approve'
                if method_name == "approve":
                    spender = params["spender"]
                    amount = params["amount"]

                    # Spender must be whitelisted
                    if spender not in _TRUSTED_TARGETS:
                        return {
                            "status": "REJECTED",
                            "reason": f"Security Veto: Approval spender address {spender} is not whitelisted. Blind signing blocked.",
                            "decoded_call": decoded_call
                        }
                    
                    # Prevent overflow or absurdly high approvals
                    if amount > _MAX_TRANSACTION_LIMIT:
                        return {
                            "status": "REJECTED",
                            "reason": f"Security Veto: Approved amount {amount} exceeds the transaction ceiling limit.",
                            "decoded_call": decoded_call
                        }

                # Veto check for direct transfer out of wallet to untrusted address
                elif method_name in ("transfer", "transferFrom"):
                    recipient = params["recipient"]
                    if recipient not in _TRUSTED_TARGETS:
                        # Allow internal transfer only to whitelisted protocols
                        return {
                            "status": "REJECTED",
                            "reason": f"Security Veto: Transfer recipient address {recipient} is not whitelisted.",
                            "decoded_call": decoded_call
                        }

            except Exception as e:
                return {
                    "status": "REJECTED",
                    "reason": f"Failed to parse ERC20 calldata: {e}",
                    "decoded_call": decoded_call
                }
        else:
            # For non-standard methods targeting whitelisted protocol routers (like DEX swaps),
            # we approve them but flag the action sequence for tracing.
            decoded_call["method"] = "protocol_interaction"
            decoded_call["description"] = f"Interaction with verified protocol router {decoded_call['target_contract']}"

        return {
            "status": "APPROVED",
            "reason": "Transaction passed all security guardrail whitelists.",
            "decoded_call": decoded_call
        }


# Singleton instance
transaction_guardrail = TransactionGuardrail()
