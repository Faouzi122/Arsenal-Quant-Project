# Fichier: run_backtest.py
# Lanceur de backtests pour le Projet Arsenal
# Version: V1.3.37.B (Correction Capital Initial + Rapport Complet)

import argparse
import logging
import sys
import pandas as pd
from tqdm import tqdm 

# Import des "briques" (V1.3.37.A)
from arsenal_simulator import DataConnector, PortfolioManager, Signal

# Import des stratégies (V1.3.35.A)
from strategies import LaVagueDAvalancheStrategy, BTCBreakoutStrategy

# --- CONFIGURATION LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger()

# --- CONFIGURATION CONNEXION DB (V1.3.12) ---
DATABASE_URL = "postgresql://user:MonNouveauMotDePasseSécurisé123@localhost:5432/arsenal_db"

# --- NOMS DE COLONNES ---
COL_ATR = 'atr_14_h1'

# --- Mappage des stratégies ---
STRATEGY_MAP = {
    "LaVagueDAvalancheStrategy": LaVagueDAvalancheStrategy,
    "BTCBreakoutStrategy": BTCBreakoutStrategy,
}

# --- MOTEUR DE SIMULATION (V1.3.30) ---
class Simulator:
    """Moteur de backtesting."""
    def __init__(self, data_connector, strategy, portfolio):
        self.data_connector = data_connector
        self.strategy = strategy 
        self.portfolio = portfolio
        log.info("[Simulator] Moteur initialisé.")

    def _prepare_data(self, data_1h, data_daily, start_date, end_date):
        log.info("[Simulator] Préparation et fusion des données (resample)...")
        data_1h.index = pd.to_datetime(data_1h.index)
        data_daily.index = pd.to_datetime(data_daily.index)
        data_1h = data_1h.loc[start_date:end_date]
        data_daily = data_daily.loc[start_date:end_date]
        daily_features_resampled = data_daily.resample('1H').ffill()
        merged_df = data_1h.join(daily_features_resampled, how='left', rsuffix='_daily_raw')
        merged_df.ffill(inplace=True); merged_df.bfill(inplace=True) 

        if 'close_daily_raw' in merged_df.columns:
            merged_df.rename(columns={'close': 'close_1h', 'open': 'open_1h'}, inplace=True)
            merged_df.rename(columns={'close_daily_raw': 'close', 'open_daily_raw': 'open'}, inplace=True)
        
        required_sim_cols = ['open_1h', 'close_1h', 'low', COL_ATR] # Ajout 'low'
        if not all(col in merged_df.columns for col in required_sim_cols):
             log.error(f"[Simulator] FATAL: Colonnes H1, Low ou ATR manquantes. Requis: {required_sim_cols}")
             log.error(f"Colonnes disponibles: {list(merged_df.columns)}")
             return pd.DataFrame() 

        log.info(f"[Simulator] Données fusionnées. Total lignes 1H: {len(merged_df)}")
        return merged_df

    def run_simulation(self, data_1h, data_daily, start_date, end_date):
        processed_data = self._prepare_data(data_1h, data_daily, start_date, end_date)
        if processed_data.empty: return {}

        log.info("[Simulator] Démarrage de la simulation (boucle principale)...")
        OPEN_PRICE_COL = 'open_1h' 
        ATR_COL = COL_ATR          

        for i in tqdm(range(1, len(processed_data)), desc="Simulation"):
            if i < 1: continue
            current_row = processed_data.iloc[i]
            previous_row = processed_data.iloc[i-1]
            
            try:
                # 1. Mise à jour Equity + TSL
                self.portfolio.update_equity(timestamp=current_row.name, current_price=current_row[OPEN_PRICE_COL])
                # 2. Vérif Sorties (SL/TSL)
                self.portfolio.check_exit_conditions(current_row)
                # 3. Signal d'Entrée
                signal = self.strategy.generate_signal(current_row, previous_row)
                # 4. Exécution Entrée
                if signal == Signal.BUY:
                    self.portfolio.execute_entry(
                        timestamp=current_row.name,
                        entry_price=current_row[OPEN_PRICE_COL],
                        current_atr=current_row[ATR_COL] 
                    )
            except KeyError as e:
                log.error(f"[Simulator] FATAL: KeyError: {e}. Vérifiez ETL/Mappage.")
                log.error(f"Colonnes disponibles: {list(current_row.index)}")
                return {} 
            except Exception as e:
                log.error(f"[Simulator] Erreur Inconnue: {e}")
                import traceback; traceback.print_exc()
                return {}

        log.info("[Simulator] Simulation terminée.")
        # 5. Générer le rapport complet (V1.3.37)
        report = self.portfolio.generate_report()
        return report

# --- Classe Lanceur ---
class BacktestRunner:
    """Orchestre l'exécution du backtest."""
    def __init__(self, db_url):
        self.db_url = db_url
        self.data_connector = None
        self.strategy_name = None
        self.strategy_class = None
        self.params = {}

    def setup_connector(self):
        try:
            self.data_connector = DataConnector(self.db_url)
            log.info("[Runner] DataConnector initialisé avec succès.")
        except Exception as e:
            log.error(f"[Runner] Echec connexion DataConnector: {e}"); sys.exit(1) 

    def load_strategy(self, strategy_name):
        if strategy_name not in STRATEGY_MAP:
            log.error(f"[Runner] Stratégie '{strategy_name}' non trouvée."); sys.exit(1)
        self.strategy_name = strategy_name
        self.strategy_class = STRATEGY_MAP[strategy_name]
        log.info(f"[Runner] Classe Stratégie '{strategy_name}' chargée.")

    def set_params(self, initial_sl, trailing_sl, **kwargs):
        self.params = {'initial_sl_atr': initial_sl, 'trailing_sl_atr': trailing_sl}
        log.info(f"[Runner] Paramètres Stratégie: {self.params}")

    def run_backtest(self, start_date, end_date, initial_capital): # Ajout initial_capital
        if not self.data_connector or not self.strategy_class:
            log.error("[Runner] Setup incomplet."); return None

        log.info(f"--- Lancement Test (In-Sample: {start_date} - {end_date}) pour {self.strategy_name} ---")
        log.info(f"--- Capital Initial: {initial_capital:.2f} USDT ---") # Log du capital
        
        strategy_instance = self.strategy_class(params=self.params)
        
        # V1.3.37: Correction Capital Initial
        portfolio = PortfolioManager(
            strategy=strategy_instance,
            initial_capital=initial_capital # Utilise le capital spécifié
        )

        core = Simulator(
            data_connector=self.data_connector,
            strategy=strategy_instance,
            portfolio=portfolio
        )
        
        try:
            TABLE_NAME = "btc_features" 
            log.info(f"Connexion au 'Feature Store' pour charger l'actif: {TABLE_NAME}...")
            data_1h = self.data_connector.load_features_for_asset(TABLE_NAME, start_date, end_date)
            log.info(f"Connexion au 'Feature Store' pour charger l'actif (Daily): {TABLE_NAME}...")
            data_daily = self.data_connector.load_features_for_asset(TABLE_NAME, start_date, end_date)
            
            if data_1h.empty or data_daily.empty:
                log.error(f"[Runner] Données manquantes '{TABLE_NAME}'. Vérifiez l'ETL."); return None
                
            log.info(f"[Runner] Données chargées '{TABLE_NAME}': {len(data_1h)} L (1H), {len(data_daily)} L (Daily)")
            
        except Exception as e: 
            log.error(f"[Runner] Erreur chargement données: {e}"); return None

        try:
            report = core.run_simulation(data_1h, data_daily, start_date, end_date)
            return report
        except Exception as e:
            log.error(f"[Runner] Erreur durant l'exécution de Simulator: {e}")
            import traceback; traceback.print_exc(); return None

# --- Point d'entrée ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lanceur de Backtest - Projet Arsenal")
    parser.add_argument('--strategy', type=str, required=True, help="Nom de la classe Stratégie")
    parser.add_argument('--start', type=str, required=True, help="Date début (YYYY-MM-DD)")
    parser.add_argument('--end', type=str, required=True, help="Date fin (YYYY-MM-DD)")
    parser.add_argument('--initial_sl', type=float, required=True, help="Stop Loss initial (Ex: 2.5 * ATR)")
    parser.add_argument('--trailing_sl', type=float, required=True, help="Trailing Stop Loss (Ex: 3.0 * ATR)")
    # V1.3.37: Ajout de l'argument capital
    parser.add_argument('--capital', type=float, default=1000.0, help="Capital initial (Ex: 1000.0)")

    args = parser.parse_args()

    runner = BacktestRunner(db_url=DATABASE_URL)
    runner.setup_connector()
    runner.load_strategy(args.strategy)
    runner.set_params(args.initial_sl, args.trailing_sl)

    # V1.3.37: Passe le capital au runner
    report = runner.run_backtest(args.start, args.end, args.capital)

    # V1.3.37: Utilise le titre du rapport généré par PortfolioManager
    if report:
        log.info(f"--- Backtest Terminé: {args.strategy} ({args.start} - {args.end}) ---")
        # Le rapport est déjà affiché par generate_report()
    else:
        log.error("Echec du backtest. Aucun rapport généré.")
