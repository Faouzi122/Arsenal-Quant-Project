# Fichier: run_optimization.py
# Lanceur d'optimisation paramétrique pour Projet Arsenal
# Version: V1.3.43 (Correction NameError: 'text')

import argparse
import logging
import itertools
import pandas as pd
import time
import sys
import numpy as np
from sqlalchemy import create_engine, text # V1.3.43: Import manquant

# Importations Corrigées
from arsenal_simulator import DataConnector, PortfolioManager, Signal
from strategies import LaVagueDAvalancheStrategy, BTCBreakoutStrategy

# --- CONFIGURATION LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger()

# --- CONFIGURATION CONNEXION DB ---
DATABASE_URL = "postgresql://user:MonNouveauMotDePasseSécurisé123@localhost:5432/arsenal_db"

# --- NOMS DE COLONNES ---
COL_ATR = 'atr_14_h1'

# --- Mappage des stratégies ---
STRATEGY_MAP = {
    "LaVagueDAvalancheStrategy": LaVagueDAvalancheStrategy,
    "BTCBreakoutStrategy": BTCBreakoutStrategy,
}

# --- MOTEUR DE SIMULATION (Interne) ---
class InternalSimulator:
    def __init__(self, data_connector, strategy, portfolio):
        self.data_connector = data_connector
        self.strategy = strategy
        self.portfolio = portfolio

    def _prepare_data(self, data_1h, data_daily, start_date, end_date):
        log.debug("[OptiSim] Préparation et fusion des données...")
        data_1h.index = pd.to_datetime(data_1h.index)
        data_daily.index = pd.to_datetime(data_daily.index)
        data_1h = data_1h.loc[start_date:end_date].copy()
        data_daily = data_daily.loc[start_date:end_date].copy()

        daily_features_resampled = data_daily.resample('1H').ffill()
        merged_df = data_1h.join(daily_features_resampled, how='left', rsuffix='_daily_raw')
        merged_df.ffill(inplace=True); merged_df.bfill(inplace=True)

        if 'close_daily_raw' in merged_df.columns:
             cols_to_rename_h1 = {c: f"{c}_1h" for c in ['close', 'open', 'low', 'high', 'volume'] if c in merged_df.columns}
             merged_df.rename(columns=cols_to_rename_h1, inplace=True)
             cols_to_rename_daily = {f"{c}_daily_raw": c for c in ['close', 'open', 'low', 'high', 'volume'] if f"{c}_daily_raw" in merged_df.columns}
             merged_df.rename(columns=cols_to_rename_daily, inplace=True)

        required_sim_cols = ['open_1h', 'close_1h', 'low_1h', 'high_1h', COL_ATR, 'low']
        if not all(col in merged_df.columns for col in required_sim_cols):
             log.error(f"[OptiSim] FATAL: Colonnes manquantes. Requis: {required_sim_cols}\nDisponibles: {list(merged_df.columns)}")
             return pd.DataFrame()
        log.debug("[OptiSim] Données fusionnées.")
        return merged_df

    def run_simulation(self, data_1h, data_daily, start_date, end_date):
        processed_data = self._prepare_data(data_1h, data_daily, start_date, end_date)
        if processed_data.empty: return {}

        log.debug("[OptiSim] Démarrage boucle de simulation...")
        OPEN_PRICE_COL = 'open_1h'
        ATR_COL = COL_ATR

        if not processed_data.empty:
             first_timestamp = processed_data.index[0]
             self.portfolio.add_equity_point(first_timestamp, self.portfolio.initial_capital)

        for i in range(len(processed_data)):
            current_row = processed_data.iloc[i]
            previous_row = processed_data.iloc[i-1] if i > 0 else None

            try:
                self.portfolio.update_equity(timestamp=current_row.name, current_price=current_row[OPEN_PRICE_COL])
                row_for_exit_check = current_row.copy()
                if 'low_1h' in row_for_exit_check.index:
                     row_for_exit_check.rename({'low_1h':'low'}, inplace=True)
                if 'low' in row_for_exit_check.index:
                     self.portfolio.check_exit_conditions(row_for_exit_check)
                else:
                     log.warning(f"Colonne 'low' manquante pour check_exit_conditions à {current_row.name}. Sortie skip.")

                if previous_row is not None:
                     signal = self.strategy.generate_signal(current_row, previous_row)
                     if signal == Signal.BUY:
                          self.portfolio.execute_entry(
                               timestamp=current_row.name,
                               entry_price=current_row[OPEN_PRICE_COL],
                               current_atr=current_row[ATR_COL]
                          )
            except KeyError as e:
                log.error(f"[OptiSim] FATAL KeyError: {e}. Vérifiez ETL/Mappage."); return {}
            except Exception as e:
                log.error(f"[OptiSim] Erreur Inconnue: {e}"); return {}

        log.debug("[OptiSim] Simulation terminée.")
        report = self.portfolio.generate_report()
        return report

# --- FONCTION POUR LANCER UN BACKTEST UNIQUE ---
def run_single_backtest(db_url, strategy_name, start_date, end_date, initial_capital, params):
    """Exécute un backtest unique avec les paramètres donnés."""
    data_connector = None
    strategy_class = STRATEGY_MAP.get(strategy_name)

    if not strategy_class: log.error(f"Stratégie '{strategy_name}' non trouvée."); return None
    try:
        retries = 3; wait_time = 5
        for attempt in range(retries):
             try:
                  data_connector = DataConnector(db_url)
                  # V1.3.43: 'text' est maintenant importé
                  with data_connector.engine.connect() as conn_test:
                       conn_test.execute(text("SELECT 1"))
                  log.debug(f"Connexion DB réussie (Tentative {attempt+1}/{retries})")
                  break
             except Exception as conn_e:
                  log.warning(f"Echec connexion DB (Tentative {attempt+1}/{retries}): {conn_e}")
                  if attempt < retries - 1: time.sleep(wait_time)
                  else: raise
    except Exception as e: log.error(f"Echec connexion DB final: {e}"); return None

    pm_logger = logging.getLogger('arsenal_simulator')
    original_level = pm_logger.level
    pm_logger.setLevel(logging.WARNING)

    strategy_instance = strategy_class(params=params)
    portfolio = PortfolioManager(strategy=strategy_instance, initial_capital=initial_capital)
    simulator = InternalSimulator(data_connector, strategy_instance, portfolio)

    report = None
    try:
        TABLE_NAME = "btc_features"
        data_1h = data_connector.load_features_for_asset(TABLE_NAME, start_date, end_date)
        data_daily = data_connector.load_features_for_asset(TABLE_NAME, start_date, end_date)

        if data_1h.empty or data_daily.empty:
            log.error(f"Données manquantes '{TABLE_NAME}'."); return None

        report = simulator.run_simulation(data_1h, data_daily, start_date, end_date)
        if report:
             report['initial_sl_atr'] = params['initial_sl_atr']
             report['trailing_sl_atr'] = params['trailing_sl_atr']
    except Exception as e:
        log.error(f"Erreur durant l'exécution du backtest unique: {e}")
        report = None
    finally:
        pm_logger.setLevel(original_level)

    return report

# --- LANCEUR D'OPTIMISATION ---
def run_optimization(strategy_name, start_date, end_date, capital, initial_sl_range, trailing_sl_range):
    """Exécute l'optimisation sur les plages de paramètres."""
    log.info(f"--- DÉMARRAGE OPTIMISATION PARAMÉTRIQUE ---")
    log.info(f"Stratégie: {strategy_name}, Période: {start_date} - {end_date}, Capital: {capital:.2f}")
    log.info(f"Initial SL (ATR): {initial_sl_range}")
    log.info(f"Trailing SL (ATR): {trailing_sl_range}")

    results = []
    param_combinations = list(itertools.product(initial_sl_range, trailing_sl_range))
    total_runs = len(param_combinations)
    log.info(f"Nombre total de combinaisons à tester: {total_runs}")

    start_time = time.time()
    from tqdm import tqdm
    for i, (isl, tsl) in enumerate(tqdm(param_combinations, desc="Optimisation")):
        params = {'initial_sl_atr': isl, 'trailing_sl_atr': tsl}
        report = run_single_backtest(DATABASE_URL, strategy_name, start_date, end_date, capital, params)

        # Gestion améliorée des échecs
        if report:
            expected_keys = ['initial_sl_atr', 'trailing_sl_atr', 'total_trades', 'net_profit_usd', 'net_profit_pct', 'win_rate_pct', 'profit_factor', 'payoff_ratio', 'max_drawdown_pct']
            is_valid_report = all(key in report and report[key] not in ['N/A', 'FAIL', 'INCOMPLETE', np.nan, None] for key in expected_keys)
            if is_valid_report: results.append(report)
            else:
                 log.warning(f"Rapport invalide/incomplet pour ISL={isl}, TSL={tsl}. Marqué comme FAIL.")
                 failed_report = params.copy()
                 failed_report.update({k: report.get(k, 'MISSING') for k in expected_keys if k not in params})
                 for k in expected_keys:
                      if k not in failed_report or failed_report[k] in ['N/A', 'FAIL', 'INCOMPLETE', 'MISSING', np.nan, None]: failed_report[k] = 'FAIL'
                 results.append(failed_report)
        else:
            failed_report = params.copy()
            failed_report.update({k: 'FAIL' for k in ['total_trades', 'net_profit_usd', 'net_profit_pct', 'win_rate_pct', 'profit_factor', 'payoff_ratio', 'max_drawdown_pct']})
            results.append(failed_report)

    end_time = time.time()
    log.info(f"\n--- OPTIMISATION TERMINÉE en {end_time - start_time:.2f} secondes ---")

    # --- AFFICHAGE DU TABLEAU RÉCAPITULATIF ---
    if results:
        results_df = pd.DataFrame(results)
        numeric_cols = ['net_profit_pct', 'max_drawdown_pct', 'profit_factor', 'payoff_ratio', 'win_rate_pct', 'total_trades', 'net_profit_usd']
        for col in numeric_cols:
             if col in results_df.columns: results_df[col] = pd.to_numeric(results_df[col], errors='coerce')
        results_df = results_df.fillna('FAIL') # Remplace NaN et None par 'FAIL'

        cols_order = ['initial_sl_atr', 'trailing_sl_atr', 'net_profit_pct', 'max_drawdown_pct', 'profit_factor', 'payoff_ratio', 'win_rate_pct', 'total_trades', 'net_profit_usd']
        col_names_map = {
             'initial_sl_atr': 'Initial SL (ATR)', 'trailing_sl_atr': 'Trailing SL (ATR)',
             'net_profit_pct': 'Net Profit (%)', 'max_drawdown_pct': 'Max Drawdown (%)',
             'profit_factor': 'Profit Factor', 'payoff_ratio': 'Payoff Ratio',
             'win_rate_pct': 'Win Rate (%)', 'total_trades': 'Total Trades',
             'net_profit_usd': 'Net Profit ($)'
        }
        display_cols = [col for col in cols_order if col in results_df.columns]
        display_df = results_df[display_cols].rename(columns=col_names_map)

        log.info(f"\n--- RAPPORT D'OPTIMISATION PARAMÉTRIQUE ({strategy_name} {start_date} - {end_date}, Capital: {capital:.2f}) ---")
        try:
             # V1.3.42: Suppression de na_rep
             print(display_df.to_markdown(index=False, floatfmt=".2f", numalign="right", stralign="right"))
        except ImportError:
             print(display_df.to_string(index=False, float_format="%.2f", na_rep='FAIL')) # na_rep OK pour to_string
    else: log.error("Aucun résultat d'optimisation généré.")

# --- POINT D'ENTRÉE ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lanceur d'Optimisation Paramétrique - Projet Arsenal")
    parser.add_argument('--strategy', type=str, required=True, help="Nom de la classe Stratégie")
    parser.add_argument('--start', type=str, required=True, help="Date début (YYYY-MM-DD)")
    parser.add_argument('--end', type=str, required=True, help="Date fin (YYYY-MM-DD)")
    parser.add_argument('--capital', type=float, default=1000.0, help="Capital initial (Ex: 1000.0)")
    parser.add_argument('--initial_sl_range', type=float, nargs='+', required=True, help="Plage Initial SL ATR (Ex: 2.0 2.5 3.0)")
    parser.add_argument('--trailing_sl_range', type=float, nargs='+', required=True, help="Plage Trailing SL ATR (Ex: 3.0 4.0 5.0)")

    args = parser.parse_args()
    if not args.initial_sl_range or not args.trailing_sl_range: log.error("Plages SL vides."); sys.exit(1)

    run_optimization(
        strategy_name=args.strategy, start_date=args.start, end_date=args.end,
        capital=args.capital, initial_sl_range=args.initial_sl_range,
        trailing_sl_range=args.trailing_sl_range
    )
