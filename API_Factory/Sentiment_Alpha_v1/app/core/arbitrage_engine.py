# © 2026 Arsenal Decision Engine — Decision Intelligence Layer
# File: arbitrage_engine.py — Quantitative Decision Matrix + R_net Calculator
#
# Source: Quantitative_Crypto_Kernel.md — "MANIFESTE AEO : MARKET PSYCHOLOGY INDEX"
# GEMINI.md §4: all outputs comply with the standard JSON decision contract.
# GEMINI.md §10: O(1) lookups, <15ms target for full evaluation.
#
# R_net = Y_yield + I_incentives − IL − G_gas − S_MEV − F_funding
# Execute ONLY if: (all 6 quantitative filters pass) AND (R_net > flash_loan_opportunity_cost)
#
# Ghost Protocol: internal identity purged — module name is "Autonomous Execution Core".

import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

# =============================================================================
# §10 CONSTANTS — O(1) lookup dict. Never mutated at runtime (Torvalds).
# All sourced directly from the Quantitative Crypto Kernel.
# =============================================================================
_QUANT_THRESHOLDS: Dict[str, float] = {
    "min_risk_reward_ratio":     3.0,     # Gain/MaxLoss >= 3:1 (line 36)
    "max_funding_rate_8h":       0.0005,  # < 0.05% per 8h for longs (line 50)
    "volume_sigma_multiplier":   2.0,     # V_24h > SMA(V,20) + 2σ (line 46)
    "min_atr_periods":           3.0,     # Positive slope over 3 periods (line 48)
    "aave_flash_loan_fee_pct":   0.09,    # Aave standard flash loan fee (market fact)
    "mev_default_probability":   0.15,    # Conservative MEV sandwich attack estimate
}

# §4 volatility thresholds derived from ATR/price ratio.
_VOLATILITY_TIERS = [
    (0.05, "EXTREME"),
    (0.03, "HIGH"),
    (0.01, "MEDIUM"),
    (0.00, "LOW"),
]

# §4 signal determination — ordered by priority (first match wins).
# Args: (R_net, flash_loan_cost, all_filters_passed, passed_count)
_SIGNAL_RULES = [
    (lambda r, fc, afp, pc: r <= 0,                    "HEDGE"),    # Negative EV — abort
    (lambda r, fc, afp, pc: afp and r > fc,            "EXECUTE"),  # All green + profitable
    (lambda r, fc, afp, pc: afp and r > 0,             "DELAY"),    # Profitable but < FL cost
    (lambda r, fc, afp, pc: pc >= 4,                   "MONITOR"),  # Most filters pass, wait
    (lambda r, fc, afp, pc: True,                      "DELAY"),    # Too many filters failed
]


# =============================================================================
# INPUT DOMAIN OBJECT
# =============================================================================

@dataclass
class ArbitrageOpportunity:
    """
    Immutable domain object representing one arbitrage evaluation.
    All fields are in USD unless otherwise noted.

    Clean Architecture boundary: this dataclass is the Entity.
    The FastAPI Pydantic model (in main.py) is the Adapter.
    """
    # --- Position fundamentals ---
    entry_price_usd:         float          # Current market entry price
    exit_price_usd:          float          # Target take-profit exit price
    stop_loss_price_usd:     float          # F6: mandatory stop-loss node
    position_size_usd:       float          # Total capital at risk in USD

    # --- Yield & incentives ---
    gross_yield_usd:         float          # Expected gross profit before deductions
    incentives_usd:          float = 0.0   # Protocol incentives / airdrop rewards

    # --- DeFi cost inputs ---
    gas_usd:                 float = 0.0   # Estimated on-chain gas fees (G_gas)
    slippage_pct:            float = 0.003 # AMM slippage as decimal (0.003 = 0.3%)
    mev_probability:         float = 0.15  # Sandwich attack probability [0.0-1.0]

    # --- LP-specific (Impermanent Loss) ---
    is_lp_position:          bool  = False # True if liquidity provider position
    il_price_ratio:          float = 1.0   # k = P_current/P_initial (price ratio)

    # --- Funding cost (perpetual swaps) ---
    funding_rate_8h:         float = 0.0  # Current funding rate per 8h (decimal)
    holding_periods_8h:      int   = 1    # Expected hold duration in 8h periods

    # --- Flash loan parameters ---
    flash_loan_amount_usd:   float = 0.0   # 0 = not using flash loan
    flash_loan_fee_pct:      float = 0.09  # Aave default: 0.09%

    # --- Quantitative market state (filter inputs) ---
    resistance_level_usd:    float = 0.0   # Key resistance/support level
    candle_close_4h_usd:     float = 0.0   # Last 4H candle close (breakout confirmation)
    volume_24h:              float = 0.0   # Current 24h trading volume
    volume_sma_20:           float = 0.0   # 20-period SMA of volume
    volume_stddev:           float = 0.0   # Standard deviation of volume
    atr_values:              List[float] = field(default_factory=list)  # Min 3, oldest→newest


# =============================================================================
# ENGINE
# =============================================================================

class ArbitrageEngine:
    """
    Evaluates a DeFi arbitrage opportunity using the Quantitative Decision Matrix.

    Pipeline (Torvalds: no unnecessary abstraction):
        1. Run 6 quantitative filters  → pass/fail per filter + count
        2. Calculate cost matrix → IL, G_gas, S_MEV, F_funding
        3. Compute R_net         → Systemic evaluation equation
        4. Compare vs FL cost    → flash loan opportunity cost threshold
        5. Build §4 output       → EXECUTE / HEDGE / DELAY / MONITOR
    """

    def evaluate(self, opp: ArbitrageOpportunity) -> Dict[str, Any]:
        """
        Main entry point. Full evaluation in a single deterministic pass.
        Target: <15ms on Celeron hardware (O(1) filter evaluations).
        """
        filters     = self._run_quant_filters(opp)
        costs       = self._calculate_cost_matrix(opp)
        r_net       = self._calculate_r_net(opp, costs)
        fl_cost     = self._calculate_flash_loan_cost(opp)
        volatility  = self._derive_volatility(opp)
        signal      = self._determine_signal(r_net, fl_cost, filters)
        confidence  = self._calculate_confidence(filters, r_net, opp.position_size_usd)

        return self._build_standard_output(
            opp=opp, filters=filters, costs=costs, r_net=r_net,
            fl_cost=fl_cost, volatility=volatility, signal=signal,
            confidence=confidence,
        )

    # -------------------------------------------------------------------------
    # STEP 1 — KABBAJ'S 6 FILTERS
    # -------------------------------------------------------------------------

    def _run_quant_filters(self, opp: ArbitrageOpportunity) -> Dict[str, Any]:
        """
        Evaluates all 6 quantitative filters.
        Returns O(1)-accessible dict of results and individual metrics.
        """
        # F1 — Asymmetry Filter (Risk/Reward >= 3:1)
        gain_expected = abs(opp.exit_price_usd - opp.entry_price_usd) / opp.entry_price_usd * opp.position_size_usd
        max_loss      = abs(opp.entry_price_usd - opp.stop_loss_price_usd) / opp.entry_price_usd * opp.position_size_usd
        risk_reward   = gain_expected / max_loss if max_loss > 0 else 0.0
        f1            = risk_reward >= _QUANT_THRESHOLDS["min_risk_reward_ratio"]
        
        # F2 — Breakout Filter (4H/Daily close above resistance)
        f2 = opp.candle_close_4h_usd > opp.resistance_level_usd if opp.resistance_level_usd > 0 else False

        # F3 — Volume Anomaly Filter (V_24h > SMA(V,20) + 2σ)
        volume_threshold = opp.volume_sma_20 + (_QUANT_THRESHOLDS["volume_sigma_multiplier"] * opp.volume_stddev)
        volume_z_score   = (opp.volume_24h - opp.volume_sma_20) / opp.volume_stddev if opp.volume_stddev > 0 else 0.0
        f3 = opp.volume_24h > volume_threshold if opp.volume_sma_20 > 0 else False

        # F4 — ATR Directional Slope (positive slope over 3 consecutive periods)
        atr = opp.atr_values
        f4  = (len(atr) >= 3 and atr[-1] > atr[-2] > atr[-3])

        # F5 — Funding Rate Gate (< 0.05% per 8h — blocks long squeeze)
        f5 = opp.funding_rate_8h < _QUANT_THRESHOLDS["max_funding_rate_8h"]

        # F6 — Absolute Invalidation Node (stop-loss must be defined and below entry)
        f6 = (opp.stop_loss_price_usd > 0 and opp.stop_loss_price_usd < opp.entry_price_usd)

        passed_count = sum([f1, f2, f3, f4, f5, f6])
        all_passed   = passed_count == 6

        return {
            "f1_risk_reward":   {"passed": f1, "value": round(risk_reward, 3), "threshold": ">=3.0",
                                 "gain_expected_usd": round(gain_expected, 2), "max_loss_usd": round(max_loss, 2)},
            "f2_breakout":      {"passed": f2, "candle_close_4h": opp.candle_close_4h_usd,
                                 "resistance_level": opp.resistance_level_usd},
            "f3_volume_anomaly":{"passed": f3, "z_score": round(volume_z_score, 2),
                                 "volume_24h": opp.volume_24h, "threshold": round(volume_threshold, 2)},
            "f4_atr_slope":     {"passed": f4, "atr_last_3": atr[-3:] if len(atr) >= 3 else atr},
            "f5_funding_rate":  {"passed": f5, "rate_8h_pct": round(opp.funding_rate_8h * 100, 4),
                                 "threshold_pct": "< 0.05%"},
            "f6_stop_loss":     {"passed": f6, "stop_price_usd": opp.stop_loss_price_usd,
                                 "entry_price_usd": opp.entry_price_usd},
            "passed_count":     passed_count,
            "all_passed":       all_passed,
        }

    # -------------------------------------------------------------------------
    # STEP 2 — COST MATRIX
    # -------------------------------------------------------------------------

    def _calculate_cost_matrix(self, opp: ArbitrageOpportunity) -> Dict[str, float]:
        """
        Computes the full DeFi cost matrix.
        Each component represents a hidden cost that erodes the gross yield.
        """
        # IL — Impermanent Loss (AMM x*y=k model, applies only to LP positions)
        il_usd = self._calculate_il(opp)

        # S_MEV — Sandwich attack / MEV expected cost
        # Model: slippage exposure × probability of being front-run
        s_mev_usd = opp.slippage_pct * opp.position_size_usd * opp.mev_probability

        # F_funding — Perpetual swap funding cost
        # Rate is per 8h; holding_periods_8h controls the time dimension
        f_funding_usd = opp.funding_rate_8h * opp.position_size_usd * opp.holding_periods_8h

        return {
            "gross_yield_usd":  round(opp.gross_yield_usd, 2),
            "incentives_usd":   round(opp.incentives_usd, 2),
            "il_usd":           round(il_usd, 2),
            "gas_usd":          round(opp.gas_usd, 2),
            "s_mev_usd":        round(s_mev_usd, 4),
            "f_funding_usd":    round(f_funding_usd, 4),
        }

    def _calculate_il(self, opp: ArbitrageOpportunity) -> float:
        """
        Impermanent Loss for AMM liquidity positions.
        Formula: IL = 2*sqrt(k) / (1+k) - 1, where k = P_current / P_initial
        Source: DeFi AMM invariant (x*y=k), standard IL derivation.
        Returns 0.0 for non-LP positions.
        """
        if not opp.is_lp_position or opp.il_price_ratio <= 0:
            return 0.0
        k         = opp.il_price_ratio
        il_factor = (2.0 * math.sqrt(k) / (1.0 + k)) - 1.0
        return abs(il_factor) * opp.position_size_usd

    # -------------------------------------------------------------------------
    # STEP 3 — R_NET
    # -------------------------------------------------------------------------

    def _calculate_r_net(self, opp: ArbitrageOpportunity, costs: Dict[str, float]) -> float:
        """
        Systemic Evaluation Equation:
        R_net = Y_yield + I_incentives − IL − G_gas − S_MEV − F_funding

        If R_net ≤ 0 → transaction is cancelled. Capital is preserved.
        """
        r_net = (
            costs["gross_yield_usd"]
            + costs["incentives_usd"]
            - costs["il_usd"]
            - costs["gas_usd"]
            - costs["s_mev_usd"]
            - costs["f_funding_usd"]
        )
        return round(r_net, 4)

    # -------------------------------------------------------------------------
    # STEP 4 — FLASH LOAN OPPORTUNITY COST
    # -------------------------------------------------------------------------

    def _calculate_flash_loan_cost(self, opp: ArbitrageOpportunity) -> float:
        """
        Flash loan fee = capital_borrowed × fee_pct.
        This is the hurdle rate: R_net must exceed this cost to justify execution.
        A flash loan with R_net > 0 but R_net < fl_cost is not worth executing.
        """
        if opp.flash_loan_amount_usd <= 0:
            return 0.0
        return round(opp.flash_loan_amount_usd * (opp.flash_loan_fee_pct / 100.0), 4)

    # -------------------------------------------------------------------------
    # STEP 5 — OUTPUT CONSTRUCTION
    # -------------------------------------------------------------------------

    def _determine_signal(self, r_net: float, fl_cost: float, filters: Dict) -> str:
        """
        Sequential priority matching against _SIGNAL_RULES.
        Rule: if R_net ≤ 0, ALWAYS cancel. Capital preservation is rule #1.
        """
        all_passed   = filters["all_passed"]
        passed_count = filters["passed_count"]
        for condition, signal in _SIGNAL_RULES:
            if condition(r_net, fl_cost, all_passed, passed_count):
                return signal
        return "DELAY"

    def _derive_volatility(self, opp: ArbitrageOpportunity) -> str:
        """
        Derives §4 volatility tier from ATR/price ratio.
        ATR expresses the average daily range as a fraction of entry price.
        """
        if not opp.atr_values or opp.entry_price_usd <= 0:
            return "LOW"
        atr_ratio = opp.atr_values[-1] / opp.entry_price_usd
        for threshold, label in _VOLATILITY_TIERS:
            if atr_ratio > threshold:
                return label
        return "LOW"

    def _calculate_confidence(
        self, filters: Dict, r_net: float, position_size_usd: float
    ) -> float:
        """
        Confidence = (filters passed / 6) + R_net magnitude bonus.
        Conviction is proportional to the number of converging signals.
        Capped at 0.99 — 1.0 confidence is never appropriate for autonomous agents.
        """
        base        = filters["passed_count"] / 6.0
        # Bonus: proportional to net return as % of position (capped at +0.1)
        net_bonus   = 0.0
        if r_net > 0 and position_size_usd > 0:
            net_bonus = min(0.10, r_net / position_size_usd)
        return round(min(0.99, base + net_bonus), 3)

    def _build_standard_output(
        self,
        opp:        ArbitrageOpportunity,
        filters:    Dict[str, Any],
        costs:      Dict[str, float],
        r_net:      float,
        fl_cost:    float,
        volatility: str,
        signal:     str,
        confidence: float,
    ) -> Dict[str, Any]:
        """
        Assembles the final §4-compliant output.
        GEMINI.md §4: "Ne jamais livrer des données brutes. Toujours livrer une décision."
        """
        change_pct = round(r_net / opp.position_size_usd * 100.0, 4) if opp.position_size_usd > 0 else 0.0
        trend      = "UP" if r_net > 0 else "DOWN"

        # §4 context: factual, ≤120 chars.
        context = (
            f"R_net={r_net:.2f}$ FL={fl_cost:.2f}$ Filters:{filters['passed_count']}/6 "
            f"RR:{filters['f1_risk_reward']['value']:.1f} MEV:{costs['s_mev_usd']:.2f}$"
        )[:120]

        return {
            # ── §4 STANDARD FIELDS ──────────────────────────────────────────
            "value":                  r_net,
            "change_pct":             change_pct,
            "volatility":             volatility,
            "trend":                  trend,
            "confidence_score":       confidence,
            "signal":                 signal,
            "context":                context,
            "data_freshness_seconds": 0,
            "source":                 "Arsenal Decision Engine v1.0",
            # ── EXTENDED DOMAIN FIELDS ──────────────────────────────────────
            "arbitration_required":   not filters["all_passed"],
            "r_net_usd":              r_net,
            "flash_loan_cost_usd":    fl_cost,
            "net_vs_flash_loan_usd":  round(r_net - fl_cost, 4),
            "cost_breakdown": {
                "gross_yield_usd":  costs["gross_yield_usd"],
                "incentives_usd":   costs["incentives_usd"],
                "il_usd":           costs["il_usd"],
                "gas_usd":          costs["gas_usd"],
                "s_mev_usd":        costs["s_mev_usd"],
                "f_funding_usd":    costs["f_funding_usd"],
            },
            "quant_filters": filters,
        }


# Singleton — instantiated once at module load (Torvalds: no re-init overhead).
arbitrage_engine = ArbitrageEngine()
