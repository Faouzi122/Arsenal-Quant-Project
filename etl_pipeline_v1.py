# Fichier: etl_pipeline_v1.py
# Pipeline ETL pour le Projet Arsenal
# Version: V1.3.33 (Correction SyntaxError try/except)

import argparse
import logging
import sys
import ccxt
import pandas as pd
import pandas_ta as ta
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
import time

# --- CONFIGURATION LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger()

# --- CONFIGURATION CONNEXION DB (V1.3.26) ---
DATABASE_URL = "postgresql://user:MonNouveauMotDePasseSécurisé123@localhost:5432/arsenal_db"

# --- CONFIGURATION CCXT ---
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'
    }
})

# --- FONCTIONS UTILES ---

def fetch_ohlcv(symbol, timeframe='1h', since=None, limit=1000):
    """Récupère les données OHLCV depuis l'exchange."""
    try:
        base_symbol = symbol.split('_')[0].upper()
        if len(symbol.split('_')) > 1:
             quote = symbol.split('_')[1].upper()
             ccxt_symbol = f"{base_symbol}/{quote}"
        else:
             if 'USDT' in base_symbol:
                 ccxt_symbol = base_symbol.replace('USDT', '/USDT')
             else:
                 ccxt_symbol = f"{base_symbol}/USDT"

        log.info(f"Normalisation symbole: {symbol} -> {ccxt_symbol}")

        if exchange.has['fetchOHLCV']:
            all_ohlcv = []
            current_since = since or exchange.parse8601('2020-01-01T00:00:00Z')
            
            while True:
                 ohlcv = exchange.fetch_ohlcv(ccxt_symbol, timeframe, current_since, limit)
                 if len(ohlcv) == 0:
                     break
                 all_ohlcv.extend(ohlcv)
                 current_since = ohlcv[-1][0] + exchange.parse_timeframe(timeframe) * 1000 
                 time.sleep(exchange.rateLimit / 1000)

            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df[~df.index.duplicated(keep='first')]
            log.info(f"{len(df)} bougies {timeframe} extraites pour {ccxt_symbol}.")
            return df
        else:
            log.error(f"L'exchange ne supporte pas fetchOHLCV.")
            return pd.DataFrame()

    except Exception as e:
        log.error(f"Erreur lors de l'extraction des données pour {symbol}: {e}")
        return pd.DataFrame()


def calculate_features(df):
    """Calcule les indicateurs techniques requis."""
    log.info("Début du calcul des features...")
    if df.empty:
        return df

    # --- Indicateurs H1 ---
    df.ta.ema(length=200, append=True, col_names=('ema_200_h1'))
    df.ta.ema(length=34, append=True, col_names=('ema_34_h1'))
    df.ta.atr(length=14, append=True, col_names=('atr_14_h1'))
    df.ta.adx(length=14, append=True, col_names=('adx_14_h1', 'dmp_14_h1', 'dmn_14_h1'))
    df.ta.rsi(length=14, append=True, col_names=('rsi_14_h1'))
    
    # --- Indicateurs Daily (V1.3.32) ---
    log.info("Calcul des indicateurs Daily...")
    df_daily = df.resample('D').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    
    df_daily.ta.ema(length=100, append=True, col_names=('ema_100_daily'))
    df_daily.ta.ema(length=200, append=True, col_names=('ema_200_daily'))
    
    donchian_daily = df_daily.ta.donchian(length=20) 
    if donchian_daily is not None and not donchian_daily.empty:
         df_daily['donchian_high_20_daily'] = donchian_daily.iloc[:, 1] 
    else:
         df_daily['donchian_high_20_daily'] = pd.NA
         
    df_daily.ta.atr(length=14, append=True, col_names=('atr_14_daily')) 
    
    daily_features = df_daily[['ema_100_daily', 'ema_200_daily', 'donchian_high_20_daily', 'atr_14_daily']]
    
    daily_features.index = daily_features.index + pd.Timedelta(days=1) 
    df = df.join(daily_features.resample('H').ffill())

    log.info("Calcul des features terminé.")
    
    df.dropna(inplace=True)
    return df

def load_to_db(df, table_name, engine):
    """Charge le DataFrame dans la base de données TimescaleDB."""
    if df.empty:
        log.warning(f"DataFrame vide pour {table_name}. Chargement annulé.")
        return

    log.info(f"Début du chargement dans la table {table_name}...")
    try:
        df.to_sql(table_name, engine, if_exists='replace', index=True, chunksize=1000)
        
        is_hypertable = False
        with engine.connect() as connection:
            is_hypertable_check = text(f"SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_name = '{table_name}'")
            result = connection.execute(is_hypertable_check)
            is_hypertable = result.fetchone() is not None

        if not is_hypertable:
            log.info(f"Transformation de {table_name} en hypertable...")
            with engine.connect() as connection:
                connection.execute(text("COMMIT")) 
                try:
                    connection.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
                    connection.execute(text("COMMIT"))
                except ProgrammingError as pe:
                    log.warning(f"Erreur lors de l'activation de l'extension (peut être normal): {pe}")
                    connection.execute(text("ROLLBACK")) 
                    connection.execute(text("COMMIT")) 
                try:
                    query_hypertable = text(f"SELECT create_hypertable('{table_name}', 'timestamp');")
                    connection.execute(query_hypertable)
                    connection.execute(text("COMMIT"))
                    log.info("Transformation réussie.")
                except Exception as hyper_e:
                     log.error(f"Échec de la transformation en hypertable: {hyper_e}")
                     connection.execute(text("ROLLBACK"))
                     connection.execute(text("COMMIT"))

        log.info(f"Chargement de {len(df)} lignes dans {table_name} terminé.")

    except Exception as e:
        log.error(f"Erreur lors du chargement dans la base de données: {e}")


# --- PIPELINE PRINCIPAL ---

def run_pipeline(symbols):
    """Exécute le pipeline ETL complet."""
    log.info("--- DÉMARRAGE DU PIPELINE ETL DU PROJET ARSENAL (V1.3.33) ---")
    
    engine = None # Initialisation
    try:
        engine = create_engine(DATABASE_URL)
        # V1.3.33: Test de connexion AVEC gestion d'erreur
        with engine.connect() as conn:
            log.info("Connexion à la base de données réussie.")
    except Exception as e: # V1.3.33: Bloc except ajouté
        log.error(f"ÉCHEC CRITIQUE: Impossible de se connecter à la base de données: {e}")
        sys.exit(1)

    for symbol_input in symbols:
        # Corrige le nom pour correspondre à l'usage (btc_usdt_1h -> btc)
        base_symbol_name = symbol_input.split('_')[0] 
        log.info(f"--- Traitement du symbole : {base_symbol_name.upper()} ---")

        # 1. Extraction (Timeframe H1)
        df_h1 = fetch_ohlcv(symbol_input, timeframe='1h')
        if df_h1.empty:
            log.warning(f"Aucune donnée extraite pour {symbol_input}. Passage au suivant.")
            continue
            
        # 2. Transformation (Features H1 + Daily)
        df_features = calculate_features(df_h1)

        # 3. Chargement (Nom de table V1.3.35: btc_features)
        table_name = f"{base_symbol_name.lower()}_features" 
        load_to_db(df_features, table_name, engine)

        log.info(f"--- Symbole {base_symbol_name.upper()} traité avec succès. ---")

    log.info("--- PIPELINE ETL TERMINÉ ---")


# --- POINT D'ENTRÉE ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline ETL pour Projet Arsenal")
    parser.add_argument('--symbol', type=str, nargs='+', required=True, 
                        help="Symbole(s) à traiter (ex: btc_usdt_1h eth_usdt_1d).")
    
    args = parser.parse_args()
    
    run_pipeline(args.symbol)
