#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arsenal Simulator - Moteur de Backtest V3.7
"""

import pandas as pd
import numpy as np
import logging
from strategies import BaseStrategy, BTCBreakoutStrategy, ETHPullbackH4Strategy, ETHGasFilteredStrategy, SOLIgnitionH4Strategy, SOLIgnitionH4Strategy_V2, Signal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PortfolioManager:
    def __init__(self, initial_capital, risk_per_trade_pct):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.active_trades = {}
        self.trade_history = []
        self.equity_curve = [{'Timestamp': pd.Timestamp('1970-01-01'), 'Equity': initial_capital}]

    def open_trade(self, symbol, data, trade_signal):
        if symbol in self.active_trades: return
        entry_price = data['Close']
        atr = data.get('atr_14_h4', data.get('ATR')) 
        if atr is None or atr == 0: return

        initial_sl_mult = trade_signal.get('initial_sl_atr_mult', 2.0)
        trailing_sl_mult = trade_signal.get('trailing_sl_atr_mult', 4.0)
        initial_sl_price = entry_price - (atr * initial_sl_mult)
        trailing_sl_price = entry_price - (atr * trailing_sl_mult)
        risk_unit = abs(entry_price - initial_sl_price)
        if risk_unit == 0: return
        
        size = (self.current_capital * self.risk_per_trade_pct) / risk_unit
        
        self.active_trades[symbol] = {
            'entry_date': data.name, 'entry_price': entry_price, 'size': size, 'direction': 'LONG',
            'initial_sl': initial_sl_price, 'trailing_sl': trailing_sl_price,
            'initial_sl_atr_mult': initial_sl_mult, 'trailing_sl_atr_mult': trailing_sl_mult,
            'HighestPrice_Close': entry_price, 'MACD_Ligne_Max': data.get('MACD', 0), 
            'previous_macd_histo': data.get('macd_histogram_daily', 0)
        }

    def close_trade(self, symbol, data, exit_type, exit_price=None):
        if symbol not in self.active_trades: return
        trade = self.active_trades.pop(symbol)
        if exit_price is None: exit_price = data['Close']
        if exit_type == 'TSL_EXIT': exit_price = max(trade['initial_sl'], trade['trailing_sl'])
        pnl = (exit_price - trade['entry_price']) * trade['size']
        self.current_capital += pnl
        self.update_equity_curve(data.name)
        self.trade_history.append({
            'symbol': symbol, 'entry_date': trade['entry_date'], 'exit_date': data.name,
            'entry_price': trade['entry_price'], 'exit_price': exit_price, 'pnl': pnl, 'exit_type': exit_type
        })

    def process_market_data(self, symbol, data, strategy):
        if symbol not in self.active_trades: return
        trade = self.active_trades[symbol]
        atr = data.get('atr_14_h4', data.get('ATR'))
        if atr is None: atr = 0
        
        # TSL
        dyn_tsl = data['Close'] - (atr * trade['trailing_sl_atr_mult'])
        if dyn_tsl > trade['trailing_sl']: trade['trailing_sl'] = dyn_tsl
        stop = max(trade['initial_sl'], trade['trailing_sl'])
        
        if data['Low'] <= stop:
            self.close_trade(symbol, data, 'TSL_EXIT')
            return

        # Strategy Exits
        if strategy.CHECK_DIVERGENCE_MACD(data, trade):
            self.close_trade(symbol, data, 'EXIT_DIVERGENCE_MACD')
            return
        if hasattr(strategy, 'CHECK_EXIT_MACD_HISTO'):
             pass 
        
        trade['previous_macd_histo'] = data.get('macd_histogram_daily', 0)

    def handle_signal(self, signal, symbol, data, config):
        if signal == Signal.BUY and symbol not in self.active_trades:
            self.open_trade(symbol, data, config)
        elif signal == Signal.SELL and symbol in self.active_trades:
            self.close_trade(symbol, data, 'EXIT_SIGNAL')

    def update_equity_curve(self, timestamp):
        self.equity_curve.append({'Timestamp': timestamp, 'Equity': self.current_capital})

    def get_results(self, last_data):
        if self.active_trades:
            for s in list(self.active_trades.keys()):
                if s in last_data: self.close_trade(s, last_data[s], 'M2M_CLOSE')
        return pd.DataFrame(self.trade_history), pd.DataFrame(self.equity_curve)

class Results:
    def __init__(self, trades, equity, name):
        self.trades = trades
        self.equity = equity.set_index('Timestamp')
        self.name = name
        self.metrics = self.calc()
    def calc(self):
        m = {'Test': self.name, 'Total Trades': 0, 'Profit Factor': 0, 'Payoff Ratio': 0, 'MDD %': 0}
        if not self.trades.empty:
            wins = self.trades[self.trades['pnl'] > 0]
            loss = self.trades[self.trades['pnl'] <= 0]
            gains = wins['pnl'].sum()
            losses = abs(loss['pnl'].sum())
            pf = gains/losses if losses > 0 else np.inf
            pr = (wins['pnl'].mean()/abs(loss['pnl'].mean())) if len(wins)>0 and len(loss)>0 else 0
            m.update({'Total Trades': len(self.trades), 'Profit Factor': round(pf, 2), 'Payoff Ratio': round(pr, 2)})
        if not self.equity.empty:
            eq = self.equity
            eq['DD'] = eq['Equity'] - eq['Equity'].cummax()
            eq['DD_Pct'] = (eq['DD'] / eq['Equity'].cummax()) * 100
            m['MDD %'] = round(eq['DD_Pct'].min(), 2)
        return m

def run_backtest(data_dict, strategy_class, strategy_config, portfolio_config):
    strategy = strategy_class(**strategy_config)
    pm = PortfolioManager(portfolio_config['initial_capital'], portfolio_config['risk_per_trade_pct'])
    
    df = pd.concat(data_dict.values(), keys=data_dict.keys(), names=['Symbol', 'Timestamp']).sort_index(level='Timestamp')
    last_rows = {s: data_dict[s].iloc[-1] for s in data_dict}
    
    prev_rows = {}
    for (sym, ts), row in df.iterrows():
        if row.isnull().any(): continue
        prev = prev_rows.get(sym, None)
        
        pm.process_market_data(sym, row, strategy)
        sig = strategy.generate_signals(row, prev)
        if sig != Signal.HOLD:
            pm.handle_signal(sig, sym, row, strategy_config)
            
        prev_rows[sym] = row
        
    t, e = pm.get_results(last_rows)
    return Results(t, e, strategy_config.get('name', 'TEST')).metrics
