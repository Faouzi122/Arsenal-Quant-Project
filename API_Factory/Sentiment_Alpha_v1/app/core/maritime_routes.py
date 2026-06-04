# © 2026 Arsenal Decision Engine — Decision Intelligence Layer
# File: maritime_routes.py — Maritime Psychology Index & Freight Risk Engine
# GEMINI.md §4: all outputs comply with the standard JSON decision contract.
# Ghost Protocol: internal identity purged for public compatibility.

import re
from typing import Dict, Any, Optional

# §4 GEMINI.md v3.0 — Stable field mappings.
_FREIGHT_TREND_TO_STD: Dict[str, str] = {
    "surge_expected":    "UP",
    "discount_expected": "DOWN",
    "volatile_stable":   "STABLE",
    "stable":            "STABLE",
    "out_of_zone":       "STABLE",
}

_RISK_TO_VOLATILITY = [
    (lambda r: r >= 75, "EXTREME"),
    (lambda r: r >= 60, "HIGH"),
    (lambda r: r >= 40, "MEDIUM"),
    (lambda r: True,    "LOW"),
]

_SIGNAL_MAP = [
    (lambda r, arb: arb,     "DELAY"),
    (lambda r, arb: r > 65,  "ALERT"),
    (lambda r, arb: r < 35,  "HEDGE"),
    (lambda r, arb: True,    "MONITOR"),
]


class MaritimeSentimentEngine:
    def __init__(self):
        # Market Psychology Index Lexicon.
        self.fear_keywords = {
            "strike", "blockade", "tension", "war", "delay", "congestion",
            "piracy", "shortage", "disruption", "hurricane", "drought",
            "missile", "reroute", "tariffs", "military", "escalation",
            "redirect", "surcharge", "escalations", "surcharges"
        }
        self.greed_keywords = {
            "expansion", "capacity", "drop", "discount", "record",
            "growth", "surplus", "resume", "safe", "consumer demand"
        }

        # MISSION_11 Contextual Negations (N-Grams).
        self.safety_ngrams = {"no risk", "remain fluid", "remain clear", "clear and fluid", "no delay", "resolved"}

        self.heavy_fear_keywords    = {"ilwu", "long beach", "port of la"}
        self.critical_reroute_keywords = {"cape of good hope", "cape routing"}

        self.routes = {
            "suez_europe":  {"suez", "red sea", "egypt", "bab el-mandeb", "yemen", "rotterdam", "antwerp", "europe", "hamburg", "bremen"},
            "transpacific": {"trans-pacific", "los angeles", "long beach", "ilwu", "tariffs", "usa", "west coast"},
            "shanghai":     {"shanghai", "ningbo", "china", "yantian", "asia"},
            "panama_canal": {"panama", "canal", "gatun"},
        }
        self.carriers    = {"msc", "maersk", "cma", "cosco", "hapag", "evergreen"}
        self.word_pattern = re.compile(r'\b[\w-]+\b')

    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------

    def analyze_maritime_risk(self, text: str, zone: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes maritime freight risk from news text.
        Returns a §4-compliant output (GEMINI.md v3.0).
        """
        if not text:
            return self._to_standard_output({
                "risk_index": 50,
                "freight_trend_prediction": "stable",
                "affected_routes": [],
                "affected_carriers": [],
                "confidence": 0.0,
                "arbitration_required": True,
                "arbitration_reason": "Empty text provided.",
            })

        # Sentence-level contextual isolation (Clean Architecture).
        sentences = text.lower().replace('!', '.').replace('?', '.').split('.')

        route_risk  = {r: 50 for r in self.routes}
        route_hits  = {r: 0  for r in self.routes}
        affected_carriers    = set()
        global_arbitration   = False

        for sentence in sentences:
            if not sentence.strip():
                continue

            tokens = set(self.word_pattern.findall(sentence))

            # Identify routes mentioned in this sentence.
            s_routes = [
                r for r, kws in self.routes.items()
                if tokens.intersection(kws) or any(kw in sentence for kw in kws if ' ' in kw)
            ]
            apply_to = s_routes if s_routes else list(self.routes.keys())
            affected_carriers.update(tokens.intersection(self.carriers))

            fear  = len(tokens.intersection(self.fear_keywords))
            greed = len(tokens.intersection(self.greed_keywords))
            fear += len(tokens.intersection(self.heavy_fear_keywords))

            # N-Gram contextual override — safety phrase neutralises fear.
            if any(ngram in sentence for ngram in self.safety_ngrams):
                fear   = 0
                greed += 2

            if any(kw in sentence for kw in self.critical_reroute_keywords):
                fear += 10

            if fear == 0 and greed == 0:
                continue

            net_fear   = fear - greed
            local_risk = max(0, min(100, 50 + (net_fear * 15)))

            for r in apply_to:
                if local_risk > 50:
                    route_risk[r] = max(route_risk[r], local_risk)
                elif local_risk < 50:
                    route_risk[r] = min(route_risk[r], local_risk)
                route_hits[r] += (fear + greed)

                if fear > 0 and greed > 0:
                    global_arbitration = True

        active_routes = [r for r, hits in route_hits.items() if hits > 0]

        if not active_routes:
            return self._to_standard_output({
                "risk_index": 50,
                "freight_trend_prediction": "stable",
                "affected_routes": [],
                "affected_carriers": list(affected_carriers),
                "confidence": 0.0,
                "arbitration_required": True,
                "arbitration_reason": "AI-Conflict Resolution Layer: No volatility detected in text.",
            })

        if zone and zone not in active_routes:
            return self._to_standard_output({
                "risk_index": 50,
                "freight_trend_prediction": "out_of_zone",
                "affected_routes": active_routes,
                "affected_carriers": list(affected_carriers),
                "confidence": 0.0,
                "arbitration_required": False,
                "zone_filtered": True,
            })

        final_risk = (
            route_risk[zone]
            if zone
            else sum(route_risk[r] for r in active_routes) / len(active_routes)
        )

        if final_risk > 65:
            trend = "surge_expected"
        elif final_risk < 35:
            trend = "discount_expected"
        else:
            trend = "volatile_stable"

        return self._to_standard_output({
            "risk_index": int(final_risk),
            "freight_trend_prediction": trend,
            "affected_routes": active_routes,
            "affected_carriers": list(affected_carriers),
            "confidence": 0.9 if not global_arbitration else 0.5,
            "arbitration_required": global_arbitration,
        })

    def compare_corridors(self, text: str) -> Dict[str, Any]:
        """
        Compares Transpacific and Suez/Europe corridors.
        Returns a §4-compliant root object with rich nested corridor data.
        """
        transpacific = self.analyze_maritime_risk(text, zone="transpacific")
        suez         = self.analyze_maritime_risk(text, zone="suez_europe")

        tp_risk = transpacific.get("value", 50) if not transpacific.get("zone_filtered") else 50
        sz_risk = suez.get("value", 50)         if not suez.get("zone_filtered")         else 50

        if tp_risk == sz_risk == 50:
            most_volatile = "none"
        else:
            most_volatile = "transpacific" if abs(tp_risk - 50) > abs(sz_risk - 50) else "suez_europe"

        max_risk      = max(tp_risk, sz_risk)
        arb_required  = transpacific.get("arbitration_required", False) or suez.get("arbitration_required", False)
        arb_reason    = transpacific.get("arbitration_reason") or suez.get("arbitration_reason")

        # §4 fields at root level — derived from the most volatile corridor.
        volatility = next(v for (fn, v) in _RISK_TO_VOLATILITY if fn(max_risk))
        signal     = next(v for (fn, v) in _SIGNAL_MAP if fn(max_risk, arb_required))
        trend_raw  = "surge_expected" if max_risk > 65 else "discount_expected" if max_risk < 35 else "volatile_stable"
        context    = f"Volatile:{most_volatile} TP:{tp_risk} SZ:{sz_risk}"[:120]

        return {
            # --- §4 Standard Fields ---
            "value":                  max_risk,
            "change_pct":             0.0,
            "volatility":             volatility,
            "trend":                  _FREIGHT_TREND_TO_STD.get(trend_raw, "STABLE"),
            "confidence_score":       min(transpacific.get("confidence_score", 0.5), suez.get("confidence_score", 0.5)),
            "signal":                 signal,
            "context":                context,
            "data_freshness_seconds": 0,
            "source":                 "Arsenal Decision Engine v1.0",
            # --- Extended Domain Fields ---
            "most_volatile_corridor": most_volatile,
            "transpacific": {
                "market_psychology_index":  tp_risk,
                "transparency_index":       100 - tp_risk,
                "freight_trend_prediction": transpacific.get("trend", "STABLE"),
                **self._calculate_pricing("transpacific", tp_risk)
            },
            "suez_europe": {
                "market_psychology_index":  sz_risk,
                "transparency_index":       100 - sz_risk,
                "freight_trend_prediction": suez.get("trend", "STABLE"),
                **self._calculate_pricing("suez_europe", sz_risk)
            },
            "arbitration_required": arb_required,
            **({"arbitration_reason": arb_reason} if arb_reason else {}),
        }

    # -------------------------------------------------------------------------
    # PRIVATE HELPERS
    # -------------------------------------------------------------------------

    def _to_standard_output(self, internal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maps internal maritime computation results to the §4 standard contract.
        GEMINI.md §4: "Ne jamais livrer des données brutes. Toujours livrer une décision."
        """
        risk          = internal.get("risk_index", 50)
        arb           = internal.get("arbitration_required", False)
        trend_raw     = internal.get("freight_trend_prediction", "stable")
        routes        = internal.get("affected_routes", [])
        carriers      = internal.get("affected_carriers", [])
        confidence    = internal.get("confidence", 0.0)

        volatility = next(v for (fn, v) in _RISK_TO_VOLATILITY if fn(risk))
        signal     = next(v for (fn, v) in _SIGNAL_MAP         if fn(risk, arb))

        routes_str   = ",".join(routes)   if routes   else "global"
        carriers_str = ",".join(carriers) if carriers else "unknown"
        context      = f"Routes:{routes_str} Carriers:{carriers_str} Risk:{risk}"[:120]

        output: Dict[str, Any] = {
            # --- §4 Standard Fields ---
            "value":                  risk,
            "change_pct":             0.0,
            "volatility":             volatility,
            "trend":                  _FREIGHT_TREND_TO_STD.get(trend_raw, "STABLE"),
            "confidence_score":       confidence,
            "signal":                 signal,
            "context":                context,
            "data_freshness_seconds": 0,
            "source":                 "Arsenal Decision Engine v1.0",
            # --- Extended Domain Fields (preserved for rich clients) ---
            "affected_routes":        routes,
            "affected_carriers":      carriers,
            "arbitration_required":   arb,
        }

        if "arbitration_reason" in internal:
            output["arbitration_reason"] = internal["arbitration_reason"]
        if internal.get("zone_filtered"):
            output["zone_filtered"] = True

        return output

    def _calculate_pricing(self, zone: str, risk_index: int) -> Dict[str, Any]:
        """Calculates True Price (base freight + all hidden surcharges)."""
        import os
        import json

        # Load scraped carbon / surcharge data from the scraper pipeline.
        intel_path        = os.getenv("MARKET_INTEL_PATH", "/app/data/market_intelligence.json")
        eua_price         = 72.45
        rerouting_surcharge = 1150.00
        transit_delay     = 12

        if os.path.exists(intel_path):
            try:
                with open(intel_path, 'r') as f:
                    intel = json.load(f)
                    eua_price           = intel.get("eua_price_eur", 72.45)
                    rerouting_surcharge = intel.get("rerouting_surcharge_premium_usd", 1150.00)
                    transit_delay       = intel.get("estimated_transit_delay_days", 12)
            except Exception:
                pass

        BASE_RATES_20FT = {"transpacific": 1800, "suez_europe": 1200}
        BASE_RATES_40FT = {"transpacific": 2400, "suez_europe": 1800}

        base_20 = BASE_RATES_20FT.get(zone, 1500)
        base_40 = BASE_RATES_40FT.get(zone, 2000)

        surcharge_multiplier   = max(0, (risk_index - 40) / 100.0)
        sentiment_surcharge_20 = base_20 * surcharge_multiplier
        sentiment_surcharge_40 = base_40 * surcharge_multiplier

        if zone == "suez_europe":
            # EU ETS Carbon surcharge + Cape rerouting + delay holding costs.
            carbon_surcharge_20 = round(eua_price * 8.5, 2)
            carbon_surcharge_40 = round(eua_price * 17.0, 2)
            delay_cost          = transit_delay * 50.0
            surcharge_20 = round(sentiment_surcharge_20 + rerouting_surcharge + carbon_surcharge_20 + delay_cost, 2)
            surcharge_40 = round(sentiment_surcharge_40 + (rerouting_surcharge * 1.5) + carbon_surcharge_40 + delay_cost, 2)
        else:
            surcharge_20 = round(sentiment_surcharge_20, 2)
            surcharge_40 = round(sentiment_surcharge_40, 2)

        true_20 = base_20 + surcharge_20
        true_40 = base_40 + surcharge_40
        status  = (
            "MARKET_ALIGNED"      if risk_index <= 50 else
            "CAUTION_OVERPRICED"  if risk_index < 75  else
            "SEVERE_SURCHARGE_RISK"
        )

        return {
            "container_20_feet": {
                "base_freight_rate_usd":    base_20,
                "hidden_surcharges_detected": surcharge_20,
                "true_price_estimated":     true_20,
                "transparency_status":      status,
            },
            "container_40_feet": {
                "base_freight_rate_usd":    base_40,
                "hidden_surcharges_detected": surcharge_40,
                "true_price_estimated":     true_40,
                "transparency_status":      status,
            },
        }


maritime_engine = MaritimeSentimentEngine()
