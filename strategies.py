# Fichier: strategies.py
# Implémentation des stratégies de trading pour le Projet Arsenal
# Version: V1.3.44.A (Logique BTC Breakout Championne pour Déploiement)

import pandas as pd
import logging # Ajout pour le log dans __init__
from arsenal_simulator import BaseStrategy, Signal

# Setup logger for this module if needed, or rely on root logger
log = logging.getLogger(__name__)

# --- NOMS DE COLONNES (Mappage Final) ---
COL_ATR = 'atr_14_h1'
COL_EMA_100_D = 'ema_100_daily'
COL_EMA_200_D = 'ema_200_daily'
COL_DONCHIAN_H20_D = 'donchian_high_20_daily'
PRICE_COL_1H = 'close_1h' # Close H1 renommé par le simulateur

# --- PLACEHOLDER ---
class LaVagueDAvalancheStrategy(BaseStrategy):
    """Placeholder."""
    def __init__(self, params=None):
        p = params or {}
        super().__init__(
            initial_sl_atr=p.get('initial_sl_atr'),
            trailing_sl_atr=p.get('trailing_sl_atr')
        )
    def generate_signal(self, row: pd.Series, previous_row: pd.Series) -> Signal:
        return Signal.HOLD

# --- Stratégie BTC Breakout V1.3 (Logique Championne) ---
class BTCBreakoutStrategy(BaseStrategy):
    """
    Stratégie: BTC Breakout v1.3-S (Logique Championne)
    Configuration OOS Validée: ISL=2.5, TSL=5.0
    PARAMÈTRES HARDCODÉS POUR DÉPLOIEMENT
    """
    def __init__(self, params=None): # params est ignoré ici
        # V1.3.44: Hardcodage des paramètres Champions validés OOS
        super().__init__(
            initial_sl_atr=2.5,  # Configuration Championne FIXE
            trailing_sl_atr=5.0  # Configuration Championne FIXE
        )
        # Log de confirmation (utiliser le logger importé)
        log.info(f"BTCBreakoutStrategy initialisée avec paramètres CHAMPIONS (ISL=2.5, TSL=5.0)")

    def generate_signal(self, row: pd.Series, previous_row: pd.Series) -> Signal:
        """
        Logique finale de la stratégie BTC Breakout V1.3 (Daily).
        """
        required_cols = [
            COL_EMA_100_D, COL_EMA_200_D, PRICE_COL_1H,
            COL_DONCHIAN_H20_D, COL_ATR
        ]
        if previous_row is None or row is None: return Signal.HOLD
        # Vérification NaNs avant de vérifier l'existence des colonnes
        if row.isnull().any() or previous_row.isnull().any():
             # Optionnel: log.debug(f"NaN détecté à {row.name}. HOLD.")
             return Signal.HOLD
        if not all(col in row.index for col in required_cols):
             # log.warning(f"Colonne manquante à {row.name}. Requis: {required_cols}. HOLD.")
             return Signal.HOLD

        try:
            # --- Condition 1 (Régime Bull - Spécification Finale Architecte) ---
            # Close_J > EMA(100, Daily) ET EMA(100, Daily) > EMA(200, Daily)
            condition_regime_price = row[PRICE_COL_1H] > row[COL_EMA_100_D]
            condition_regime_emas = row[COL_EMA_100_D] > row[COL_EMA_200_D]
            condition_regime = condition_regime_price and condition_regime_emas

            # --- Condition 2 (Breakout Frais - Spécification Finale Architecte) ---
            # Close_J > Donchian_High(20, Daily) ET Close_J-1 <= Donchian_High(20, Daily)
            breakout_aujourdhui = row[PRICE_COL_1H] > row[COL_DONCHIAN_H20_D]
            # Assurer que previous_row a bien la colonne avant d'y accéder
            if COL_DONCHIAN_H20_D not in previous_row.index or PRICE_COL_1H not in previous_row.index:
                 return Signal.HOLD # Données incomplètes sur la ligne précédente
            breakout_hier = previous_row[PRICE_COL_1H] <= previous_row[COL_DONCHIAN_H20_D]
            condition_trigger_breakout = breakout_aujourdhui and breakout_hier

            # --- Validation Finale ---
            entree_valide = condition_regime and condition_trigger_breakout

            if entree_valide:
                return Signal.BUY
            else:
                return Signal.HOLD
        except (KeyError, TypeError, ValueError) as e:
            # log.warning(f"Erreur mineure generate_signal à {row.name}: {e}") # Optionnel
            return Signal.HOLD
