import os
import json
import sys
import time
import hashlib

def create_audit_report(signal_file):
    """
    Transforms the raw ADK Scout signal JSON into a monetized diagnostic teaser report.
    Integrates L402 HTTP 402 payment requirements.
    """
    try:
        with open(signal_file, 'r') as f:
            signal = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Signal file not found at: {signal_file}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"[ERROR] Invalid JSON formatting in: {signal_file}")
        sys.exit(1)

    target = signal.get("ecosystem_target", "Unknown Architecture")
    pain = signal.get("description_of_inefficiency", "Inefficiency detected.")
    pain_level = signal.get("pain_level_usd_estimate", "Unknown")
    opp_type = signal.get("opportunity_type", "COST_WASTE")
    bias = signal.get("behavioral_bias_identified", "Unclassified")
    strategic = signal.get("strategic_signal", "")

    # Adapt economic impact narrative to signal type (Gerber systematization)
    impact_narratives = {
        "COST_WASTE": (
            "The current system executes compute cycles and tool calls recursively\n"
            "without context verification, resulting in excessive API billing."
        ),
        "MISSING_METRIC": (
            "Critical cost visibility is absent. Teams operate without unified\n"
            "spend tracking, leading to budget overruns discovered only at invoice time."
        ),
        "UNCERTAINTY": (
            "A latent vulnerability or architectural ambiguity creates unquantified\n"
            "risk exposure. Exploitation or cascading failure may cause severe losses."
        ),
    }
    impact_text = impact_narratives.get(opp_type, impact_narratives["COST_WASTE"])

    # Compute deterministic SHA-256 verifiability hash of the sorted signal input
    signal_str = json.dumps(signal, sort_keys=True)
    verifiability_hash = hashlib.sha256(signal_str.encode('utf-8')).hexdigest()

    report_content = f"""=================================================================
ANTIGRAVITY ENGINE - AI COST INTELLIGENCE AUDIT
=================================================================
TIMESTAMP  : {time.strftime("%Y-%m-%d %H:%M:%S")}
TARGET     : {target}
TYPE       : {opp_type}
STATUS     : SEVERE INEFFICIENCY DETECTED
=================================================================

[1] INFRASTRUCTURE DIAGNOSTIC
{pain}

[2] ESTIMATED ECONOMIC IMPACT
Financial Loss Level: {pain_level}
Behavioral Bias: {bias}
{impact_text}

[3] STRATEGIC SIGNAL
{strategic}

[4] ACTION REQUIRED (LOCKED)
To unlock the exact optimization recommendation and the corrected 
configuration saving up to 20% of your operational budget,
please settle the L402 invoice below.

-----------------------------------------------------------------
PAYMENT REQUIRED (L402 Protocol)
Endpoint: https://api.arsenal-quant.com/v1/unlock-audit
Price: 50,000 SATs (~$20 USD)
-----------------------------------------------------------------

[5] VERIFIABILITY SIGNATURE
Engine ID : Antigravity Engine v1.0 (Decision Layer)
Audit Hash: {verifiability_hash}
"""

    output_dir = "/home/faouzi/Antigravity_System/04_Strategy_Gerber/Audit_Factory/Strategic_Signals"
    os.makedirs(output_dir, exist_ok=True)

    output_filename = f"Audit_Report_{int(time.time())}.txt"
    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, 'w') as f:
        f.write(report_content)

    print(f"[SUCCESS] Audit teaser report generated at: {output_path}")
    print(f"[INFO] Type: {opp_type} | Pain: {pain_level} | Target: {target}")
    return output_path

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 generate_audit.py <path_to_signal_json>")
        sys.exit(1)

    create_audit_report(sys.argv[1])
