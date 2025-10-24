# Fichier: arsenal_simulator.py
# Composants principaux du simulateur pour Projet Arsenal
# Version: V1.3.37.A (Rapport de Performance Complet et Final)

import logging
import enum
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
import numpy as np

# --- CONFIGURATION LOGGING ---
log = logging.getLogger(__name__)

# --- ÉNUMÉRATIONS ---
class Signal(enum.Enum):
    HOLD = 0
    BUY = 1
    SELL = 2

class SystemState(enum.Enum):
    FLAT = 0
    IN_LONG = 1
    IN_SHORT = 2

# --- DATA CONNECTOR ---
class DataConnector:
    """Gère la connexion et l'extraction des données depuis le Feature Store."""
    def __init__(self, db_uri):
        self.db_uri = db_uri
        self.engine = None
        try:
            self.engine = create_engine(self.db_uri)
            with self.engine.connect() as conn:
                log.info("DataConnector initialisé. Connexion testée au Feature Store.")
        except Exception as e:
            log.error(f"Échec de l'initialisation du DataConnector: {e}")
            raise

    def load_features_for_asset(self, table_name, start_date, end_date):
        """Charge les données depuis la table spécifiée pour la période donnée."""
        log.info(f"Connexion au 'Feature Store' pour charger l'actif: {table_name}...")
        query = text(f"""
        SELECT * FROM {table_name}
        WHERE timestamp >= :start AND timestamp <= :end
        ORDER BY timestamp ASC;
        """)
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params={'start': start_date, 'end': end_date}, index_col='timestamp')
                log.info(f"{len(df)} lignes de features chargées depuis {table_name}.")
                df.index = pd.to_datetime(df.index)
                return df
        except ProgrammingError as pe:
            log.error(f"Erreur SQL (Table '{table_name}' existe?): {pe}")
            return pd.DataFrame()
        except Exception as e:
            log.error(f"Erreur lors du chargement des données: {e}")
            return pd.DataFrame()

# --- BASE STRATEGY ---
class BaseStrategy:
    """Classe de base pour les stratégies."""
    def __init__(self, initial_sl_atr=None, trailing_sl_atr=None):
        self.initial_sl_atr = initial_sl_atr
        self.trailing_sl_atr = trailing_sl_atr

        sl_ok = isinstance(initial_sl_atr, (int, float)) and initial_sl_atr > 0
        tsl_ok = isinstance(trailing_sl_atr, (int, float)) and trailing_sl_atr > 0

        if not sl_ok or not tsl_ok:
             log.warning(f"BaseStrategy __init__: Paramètres SL/TSL invalides. SL: {initial_sl_atr}, TSL: {trailing_sl_atr}")
             self.initial_sl_atr = 2.0
             self.trailing_sl_atr = 2.5
             log.warning(f"Utilisation des SL/TSL par défaut: {self.initial_sl_atr} / {self.trailing_sl_atr}")

        log.info(f"BaseStrategy __init__ complet. InitialSL: {self.initial_sl_atr}, TrailingSL: {self.trailing_sl_atr}")

    def generate_signal(self, row, previous_row):
        raise NotImplementedError("La méthode generate_signal doit être définie.")

# --- PORTFOLIO MANAGER (V1.3.37: Rapport Amélioré) ---
class PortfolioManager:
    """Gère l'état du portefeuille, les positions, les SL/TP et la performance."""
    def __init__(self, strategy, initial_capital=1000.0, commission_pct=0.001): # Default capital changed
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.equity = initial_capital
        self.cash = initial_capital
        self.commission_pct = commission_pct

        self.state = SystemState.FLAT
        self.current_position_size = 0.0
        self.entry_price = 0.0
        self.entry_timestamp = None
        self.stop_loss_price = 0.0
        self.trailing_stop_loss_price = 0.0
        self.highest_price_since_entry = 0.0
        self.current_atr_at_entry = None

        self.trade_log = []
        self.equity_curve = []

        log.info(f"PortfolioManager initialisé. Capital: ${self.equity:.2f}")

    def add_equity_point(self, timestamp, equity_value):
         """Ajoute un point à la courbe d'équité en évitant les doublons."""
         # Gère le cas où l'equity curve est vide ou si le timestamp est nouveau
         if not self.equity_curve or timestamp > self.equity_curve[-1][0]:
              self.equity_curve.append((timestamp, equity_value))
         # Met à jour la dernière valeur si le timestamp est le même (ex: sortie et update dans la même barre)
         elif self.equity_curve and timestamp == self.equity_curve[-1][0]:
              self.equity_curve[-1] = (timestamp, equity_value)


    def update_equity(self, timestamp, current_price):
        """Met à jour la valeur du portefeuille basée sur le prix actuel."""
        # Initialisation de l'equity curve au premier appel
        if not self.equity_curve:
             # Utilise le timestamp actuel comme point de départ si la liste est vide
             self.add_equity_point(timestamp, self.initial_capital)

        current_value = 0.0
        if self.state == SystemState.IN_LONG:
            current_value = self.current_position_size * current_price
            self.equity = self.cash + current_value
        else: # FLAT
            self.equity = self.cash

        self.add_equity_point(timestamp, self.equity)

        # Mise à jour pour le Trailing Stop
        if self.state == SystemState.IN_LONG:
             if current_price > self.highest_price_since_entry:
                  self.highest_price_since_entry = current_price
                  if self.strategy.trailing_sl_atr is not None and self.current_atr_at_entry is not None and self.current_atr_at_entry > 0:
                       tsl_level = self.highest_price_since_entry - (self.strategy.trailing_sl_atr * self.current_atr_at_entry)
                       self.trailing_stop_loss_price = max(self.trailing_stop_loss_price, tsl_level)

    def check_exit_conditions(self, row):
        """Vérifie si le Stop Loss ou le Trailing Stop Loss est touché."""
        if self.state != SystemState.IN_LONG:
            return

        # Utilise le 'low' de la bougie H1 (renommée par _prepare_data)
        current_low = row['low']
        current_timestamp = row.name

        # Vérification Stop Loss Initial
        if current_low <= self.stop_loss_price:
            self.execute_exit(current_timestamp, self.stop_loss_price, "Stop Loss")
            return

        # Vérification Trailing Stop Loss
        if current_low <= self.trailing_stop_loss_price:
            self.execute_exit(current_timestamp, self.trailing_stop_loss_price, "Trailing SL")
            return


    def execute_entry(self, timestamp, entry_price, current_atr):
        """Exécute un signal d'entrée LONG (Risque 1% du capital)."""
        if self.state != SystemState.FLAT:
            return

        if current_atr is None or pd.isna(current_atr) or current_atr <= 0:
             log.warning(f"{timestamp} | ATR invalide ({current_atr}). Entrée annulée.")
             return

        stop_loss_distance = self.strategy.initial_sl_atr * current_atr
        self.stop_loss_price = entry_price - stop_loss_distance

        if stop_loss_distance <= 0:
             log.warning(f"{timestamp} | Distance SL invalide ({stop_loss_distance}). Entrée annulée.")
             return

        risk_per_trade = self.equity * 0.01 # Risque 1% de l'équité ACTUELLE
        position_size_asset = risk_per_trade / stop_loss_distance

        cost = position_size_asset * entry_price
        commission = cost * self.commission_pct

        # SECURITÉ CRITIQUE: Vérification de la Marge (Confirmé par l'Architecte)
        if cost + commission > self.cash:
            log.warning(f"{timestamp} | Capital insuffisant pour entrer. Requis: {cost+commission:.2f}, Dispo: {self.cash:.2f}")
            # Réduire la taille pour utiliser 99% du cash
            position_size_asset = (self.cash * 0.99) / (entry_price * (1 + self.commission_pct))
            cost = position_size_asset * entry_price
            commission = cost * self.commission_pct
            if position_size_asset <= 0:
                log.error(f"{timestamp} | Cash trop faible ({self.cash:.2f}) pour entrer.")
                return

        # Exécution
        self.state = SystemState.IN_LONG
        self.current_position_size = position_size_asset
        self.entry_price = entry_price
        self.entry_timestamp = timestamp
        self.cash -= (cost + commission)

        self.highest_price_since_entry = entry_price
        self.current_atr_at_entry = current_atr
        if self.strategy.trailing_sl_atr is not None:
             self.trailing_stop_loss_price = entry_price - (self.strategy.trailing_sl_atr * current_atr)
        else:
             self.trailing_stop_loss_price = -np.inf

        log.info(f"{timestamp} | BUY | Price: {entry_price:.2f} | Size: {position_size_asset:.4f} | Entry. SL set: {self.stop_loss_price:.2f}")
        self.log_trade(timestamp, "BUY_ENTRY", entry_price, position_size_asset, "Signal Strategy", 0.0)

    def execute_exit(self, timestamp, exit_price, reason):
        """Exécute une sortie de position LONG."""
        if self.state != SystemState.IN_LONG:
            return

        revenue = self.current_position_size * exit_price
        entry_cost = self.current_position_size * self.entry_price
        commission_entry = entry_cost * self.commission_pct
        commission_exit = revenue * self.commission_pct

        pnl = revenue - entry_cost - commission_entry - commission_exit

        self.cash += (revenue - commission_exit)
        self.equity = self.cash # L'équité est égale au cash quand on est FLAT
        self.add_equity_point(timestamp, self.equity) # Enregistrer l'équité après sortie

        log.info(f"{timestamp} | SELL | Price: {exit_price:.2f} | Size: {self.current_position_size:.4f} | Exit ({reason}). PnL: ${pnl:.2f}. Equity: ${self.equity:.2f}")
        self.log_trade(timestamp, "SELL_EXIT", exit_price, self.current_position_size, reason, pnl)

        # Réinitialisation
        self.state = SystemState.FLAT
        self.current_position_size = 0.0
        self.entry_price = 0.0
        self.entry_timestamp = None
        self.stop_loss_price = 0.0
        self.trailing_stop_loss_price = 0.0
        self.highest_price_since_entry = 0.0
        self.current_atr_at_entry = None


    def log_trade(self, timestamp, type, price, size, reason, pnl):
        """Enregistre un trade dans le journal avec PnL."""
        self.trade_log.append({
            'timestamp': timestamp,
            'type': type,
            'price': price,
            'size': size,
            'reason': reason,
            'pnl': pnl,
            'equity': self.equity
        })

    def generate_report(self):
        """Génère un rapport de performance complet (V1.3.37)."""
        if not self.trade_log:
            log.warning("Aucun trade n'a été exécuté.")
            return {
                'total_trades': 0.0, 'net_profit_usd': 0.0, 'net_profit_pct': 0.0,
                'win_rate_pct': 'N/A', 'profit_factor': 'N/A',
                'payoff_ratio': 'N/A', 'max_drawdown_pct': 0.0,
            }

        trades_df = pd.DataFrame(self.trade_log)
        exits = trades_df[trades_df['type'] == 'SELL_EXIT'].copy()

        total_trades = len(exits)

        # --- Initialisation des métriques ---
        net_profit_usd = 0.0
        net_profit_pct = 0.0
        win_rate_pct = 0.0
        profit_factor = 0.0
        payoff_ratio = 0.0
        max_drawdown_pct = 0.0

        if total_trades > 0:
            # --- Calculs Métriques ---
            net_profit_usd = exits['pnl'].sum()
            final_equity = self.equity_curve[-1][1] if self.equity_curve else self.initial_capital
            net_profit_pct = ((final_equity / self.initial_capital) - 1) * 100

            winning_trades = exits[exits['pnl'] > 0]
            losing_trades = exits[exits['pnl'] <= 0]

            win_rate_pct = (len(winning_trades) / total_trades) * 100

            gross_profit = winning_trades['pnl'].sum()
            gross_loss = abs(losing_trades['pnl'].sum())

            profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

            avg_gain = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
            avg_loss = abs(losing_trades['pnl'].mean()) if len(losing_trades) > 0 else 0

            payoff_ratio = avg_gain / avg_loss if avg_loss > 0 else np.inf

            # Max Drawdown (calcul final)
            if self.equity_curve:
                 equity_curve_df = pd.DataFrame(self.equity_curve, columns=['timestamp', 'equity']).set_index('timestamp')['equity']
                 if not equity_curve_df.empty:
                      rolling_max = equity_curve_df.cummax()
                      drawdown = (equity_curve_df - rolling_max) / rolling_max
                      drawdown.replace([np.inf, -np.inf], np.nan, inplace=True)
                      max_drawdown_pct = abs(drawdown.min()) * 100 if pd.notna(drawdown.min()) else 0.0
                 else: max_drawdown_pct = 0.0
            else: max_drawdown_pct = 0.0


        # --- Formatage du Rapport ---
        report = {
            'total_trades': float(total_trades),
            'net_profit_usd': f"{net_profit_usd:.2f}",
            'net_profit_pct': f"{net_profit_pct:.2f}",
            'win_rate_pct': f"{win_rate_pct:.2f}",
            'profit_factor': f"{profit_factor:.2f}" if profit_factor != np.inf else "Inf",
            'payoff_ratio': f"{payoff_ratio:.2f}" if payoff_ratio != np.inf else "Inf",
            'max_drawdown_pct': f"{max_drawdown_pct:.2f}",
        }
        self.print_report_table(report)
        return report

    def print_report_table(self, report, title="--- RAPPORT DE PERFORMANCE ---"):
         log.info(title)
         log.info(f"{'Metric':<20} | {'Value':<10}")
         log.info("-" * 33)
         for key, value in report.items():
              metric_name = key.replace('_', ' ').title().replace('Pct', '(%)').replace('Usd', '($)')
              log.info(f"{metric_name:<20} | {value:<10}")
         log.info("-" * 33)
