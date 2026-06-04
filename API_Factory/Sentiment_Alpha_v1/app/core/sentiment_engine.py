import re
import time
from typing import Dict, Any

# Pre-compiled regex for Celeron optimization (Torvalds).
# Compiled once at class init — never recompiled during high-frequency calls.

# §4 GEMINI.md v3.0 — Stable mappings for standard output fields.
_TREND_MAP: Dict[str, str] = {
    "bullish": "UP",
    "bearish": "DOWN",
    "neutral": "STABLE",
}

_SIGNAL_MAP = [
    (lambda s, arb: arb,         "DELAY"),
    (lambda s, arb: s > 65,      "EXECUTE"),
    (lambda s, arb: s < 35,      "HEDGE"),
    (lambda s, arb: True,        "MONITOR"),
]


class SentimentEngine:
    def __init__(self):
        # Systemic Fear & Greed Lexicon based on market psychology.
        self.bullish_keywords = {"surge", "record", "growth", "bull", "buy", "profit", "rally", "outperform", "dividend", "breakout"}
        self.bearish_keywords = {"crash", "sell", "bear", "drop", "loss", "recession", "panic", "bankrupt", "downgrade", "plunge"}

        # Fast tokenizer regex — single compile, O(1) reuse.
        self.word_pattern = re.compile(r'\b\w+\b')

    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------

    def analyze_market_mood(self, text: str) -> Dict[str, Any]:
        """
        Analyzes market mood from news text.
        Optimized for Celeron: O(1) set intersection instead of heavy NLP.
        Returns a §4-compliant JSON dictionary (GEMINI.md v3.0).
        """
        t_start = time.monotonic_ns()

        if not text:
            return self._arbitration_request("Empty text provided", elapsed_ns=0)

        # Fast tokenization and lowercasing.
        tokens = set(self.word_pattern.findall(text.lower()))

        bull_hits = len(tokens.intersection(self.bullish_keywords))
        bear_hits = len(tokens.intersection(self.bearish_keywords))
        total_hits = bull_hits + bear_hits

        if total_hits == 0:
            # SharedPlan: flag for human review when signals are invisible.
            return self._arbitration_request(
                "No decisive market signals detected. Arbitration requested.",
                elapsed_ns=time.monotonic_ns() - t_start
            )

        # Fear & Greed Index (0 = Extreme Fear, 100 = Extreme Greed).
        # Base 50. Each net signal hit moves the score by 10 points.
        net_sentiment = bull_hits - bear_hits
        score = max(0, min(100, 50 + (net_sentiment * 10)))

        internal_trend = "bullish" if score > 50 else "bearish" if score < 50 else "neutral"
        confidence     = round(min(0.99, 0.5 + (total_hits * 0.1)), 2)
        elapsed_ns     = time.monotonic_ns() - t_start

        return self._to_standard_output(
            score=score,
            bull_hits=bull_hits,
            bear_hits=bear_hits,
            total_hits=total_hits,
            internal_trend=internal_trend,
            confidence=confidence,
            arbitration_required=False,
            arbitration_reason=None,
            elapsed_ns=elapsed_ns,
        )

    # -------------------------------------------------------------------------
    # PRIVATE HELPERS
    # -------------------------------------------------------------------------

    def _to_standard_output(
        self,
        score: int,
        bull_hits: int,
        bear_hits: int,
        total_hits: int,
        internal_trend: str,
        confidence: float,
        arbitration_required: bool,
        arbitration_reason: str | None,
        elapsed_ns: int,
    ) -> Dict[str, Any]:
        """
        Maps internal computation results to the §4 standard output contract.
        GEMINI.md §4: "Ne jamais livrer des données brutes. Toujours livrer une décision."
        """
        # Determine §4 volatility from signal density.
        if total_hits >= 5:
            volatility = "EXTREME"
        elif total_hits >= 3:
            volatility = "HIGH"
        elif total_hits >= 1:
            volatility = "MEDIUM"
        else:
            volatility = "LOW"

        # DUP Shadow State — propagate volatility for next payment challenge (O(1) write).
        # Import is local to avoid circular dependencies at module load time.
        try:
            from app.services.uncertainty_pricing import update_market_state
            update_market_state(volatility)
        except Exception:
            pass  # Never block a decision on a pricing hook failure.

        # Determine §4 signal (actionable decision).
        signal = next(v for (fn, v) in _SIGNAL_MAP if fn(score, arbitration_required))

        # §4 context: factual, ≤120 chars.
        context = f"Bull:{bull_hits} Bear:{bear_hits} Net:{bull_hits - bear_hits} Hits:{total_hits}"[:120]

        output: Dict[str, Any] = {
            # --- §4 Standard Fields ---
            "value":                  score,
            "change_pct":             0.0,   # Phase 3: requires session persistence.
            "volatility":             volatility,
            "trend":                  _TREND_MAP.get(internal_trend, "STABLE"),
            "confidence_score":       confidence,
            "signal":                 signal,
            "context":                context,
            "data_freshness_seconds": 0,     # On-demand analysis is always fresh.
            "source":                 "Arsenal Decision Engine v1.0",
            # --- Extended Domain Fields (preserved for rich clients) ---
            "arbitration_required":   arbitration_required,
        }

        if arbitration_reason:
            output["arbitration_reason"] = arbitration_reason

        return output

    def _arbitration_request(self, reason: str, elapsed_ns: int = 0) -> Dict[str, Any]:
        """
        SharedPlan integration: agent cannot confidently determine sentiment.
        Flags for human arbitration instead of producing a speculative signal.
        Returns a §4-compliant output with signal=DELAY.
        """
        return self._to_standard_output(
            score=50,
            bull_hits=0,
            bear_hits=0,
            total_hits=0,
            internal_trend="neutral",
            confidence=0.0,
            arbitration_required=True,
            arbitration_reason=reason,
            elapsed_ns=elapsed_ns,
        )


engine = SentimentEngine()
