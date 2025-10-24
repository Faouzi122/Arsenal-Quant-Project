# etl_pipeline_v1.py
# Ingénieur Logiciel, TKR QuantLab
# MISE A NIVEAU V1.1 : Ajout calcul et stockage indicateurs Daily

import logging
import os
import pandas as pd
import pandas_ta as ta
from binance.client import Client
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
import time

# --- Configuration du Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constantes ---
# !! CORRECTION REQUISE !! : Mettez votre VRAI mot de passe ici
DB_PASSWORD = os.getenv("DB_PASSWORD", "sidali122")
DATABASE_URL = f"postgresql://postgres:{DB_PASSWORD}@localhost:5432/postgres"
# !! CORRECTION REQUISE !! : Mettez vos VRAIES clés API Binance ici
BINANCE_API_KEY = "D2i1YHDYhJ5LgND5dxr168Jrzkkp3hhp5jhyQd3uG6owuIJVkrE0mFcmwC6ScvqM"
BINANCE_API_SECRET = "WCUBZpnrZgMIALzHiNhfE1pPBcB9LyJBJppMMvrVNZnnvSfBqKyKkqGJr5Tzt7WR"

WATCHLIST = ["BTCUSDT", "ETHUSDT"] # Actifs à traiter
START_DATE = "2017-01-01" # Date de début pour l'historique

# --- Initialisation ---
try:
    engine = create_engine(DATABASE_URL)
    logging.info("Connexion à la base de données établie.")
except Exception as e:
    logging.error(f"Erreur de connexion à la base de données: {e}")
    exit()

try:
    client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
    logging.info("Connexion à l'API Binance établie.")
    # Test rapide de connexion
    client.ping()
    status = client.get_system_status()
    if status['status'] != 0:
         logging.warning(f"Statut système Binance non normal : {status['msg']}")
except Exception as e:
    logging.error(f"Erreur de connexion à l'API Binance: {e}")
    exit()


def fetch_binance_data(symbol, interval, start_str):
    """Récupère les données OHLCV depuis Binance."""
    logging.info(f"Récupération des données {interval} pour {symbol} depuis {start_str}...")
    try:
        klines = client.get_historical_klines(symbol, interval, start_str)
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        # Conversion et sélection des colonnes
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        logging.info(f"{len(df)} lignes de données {interval} récupérées pour {symbol}.")
        return df[['open', 'high', 'low', 'close', 'volume']]
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des données {interval} pour {symbol}: {e}")
        return pd.DataFrame()

def calculate_features(df, interval_suffix):
    """Calcule les indicateurs techniques."""
    logging.info(f"Calcul des indicateurs {interval_suffix}...")
    try:
        # EMAs H1/H4 (si suffixe h1/h4)
        if interval_suffix in ['h1', 'h4']:
            df[f'ema_200_{interval_suffix}'] = ta.ema(df['close'], length=200)
        if interval_suffix == 'h1': # EMA 34 uniquement en H1
             df[f'ema_34_{interval_suffix}'] = ta.ema(df['close'], length=34)

        # ATR H1 (si suffixe h1) et Daily (si suffixe daily)
        if interval_suffix in ['h1', 'daily']:
            df[f'atr_14_{interval_suffix}'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        # ADX H1 (si suffixe h1)
        if interval_suffix == 'h1':
             adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
             # Vérifier si la colonne existe avant de l'assigner
             if f'ADX_14' in adx_df.columns:
                 df[f'adx_14_{interval_suffix}'] = adx_df[f'ADX_14']
             else:
                 logging.warning(f"Colonne ADX_14 non trouvée dans le résultat de ta.adx pour {interval_suffix}")
                 df[f'adx_14_{interval_suffix}'] = pd.NA # Mettre NA si non trouvée


        # RSI H1 (si suffixe h1)
        if interval_suffix == 'h1':
            df[f'rsi_14_{interval_suffix}'] = ta.rsi(df['close'], length=14)

        # --- AJOUT/MODIFICATION --- : Indicateurs Daily
        if interval_suffix == 'daily':
            # EMAs Daily
            df[f'ema_100_{interval_suffix}'] = ta.ema(df['close'], length=100)
            df[f'ema_200_{interval_suffix}'] = ta.ema(df['close'], length=200)
            # Donchian Channel Daily
            donchian_df = ta.donchian(df['high'], df['low'], lower_length=20, upper_length=20)
            # Renommer explicitement pour correspondre à la stratégie
            # Vérifier si les colonnes existent avant de les assigner
            if f'DCU_20_20' in donchian_df.columns:
                df[f'donchian_high_20_{interval_suffix}'] = donchian_df['DCU_20_20']
            else:
                 logging.warning(f"Colonne DCU_20_20 non trouvée dans le résultat de ta.donchian pour {interval_suffix}")
                 df[f'donchian_high_20_{interval_suffix}'] = pd.NA

        logging.info(f"Indicateurs {interval_suffix} calculés.")
        return df
    except Exception as e:
        logging.error(f"Erreur lors du calcul des indicateurs {interval_suffix}: {e}")
        return df # Retourne le df partiel en cas d'erreur


def create_hypertable(conn, table_name):
    """Crée l'hypertable TimescaleDB si elle n'existe pas."""
    try:
        # Vérifie si c'est déjà une hypertable
        check_sql = text(f"SELECT * FROM timescaledb_information.hypertables WHERE hypertable_name = '{table_name}';")
        result = conn.execute(check_sql).fetchone()

        if result is None:
            logging.info(f"Création de l'hypertable {table_name}...")
            # Commande TimescaleDB pour créer une hypertable partitionnée par 'timestamp'
            # AJOUT : migrate_data=True pour permettre la transformation si table non vide existe
            sql_create_hypertable = text(f"SELECT create_hypertable('{table_name}', 'timestamp', if_not_exists => TRUE, migrate_data => TRUE);")
            conn.execute(sql_create_hypertable)
            logging.info(f"Hypertable {table_name} créée ou déjà existante.")
        else:
             logging.info(f"L'hypertable {table_name} existe déjà.")

    except ProgrammingError as e:
        # Gère le cas où l'extension timescaledb n'est pas activée
        if 'relation "timescaledb_information.hypertables" does not exist' in str(e):
             logging.warning("L'extension TimescaleDB ne semble pas activée. Tentative d'activation...")
             try:
                 conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
                 logging.info("Extension TimescaleDB activée. Relancez le script.")
                 exit() # Arrête pour que l'activation soit prise en compte
             except Exception as activation_error:
                 logging.error(f"Impossible d'activer l'extension TimescaleDB: {activation_error}")
                 raise # Propage l'erreur si l'activation échoue
        else:
            logging.error(f"Erreur SQL lors de la création/vérification de l'hypertable : {e}")
            raise # Propage les autres erreurs SQL


def store_data(df, table_name, engine):
    """Stocke le DataFrame dans la base de données TimescaleDB."""
    logging.info(f"Stockage des données dans la table {table_name}...")
    try:
        # Utilisation d'une transaction pour assurer l'atomicité
        with engine.begin() as conn:
            # Écrit les données dans la table SQL. 'replace' supprime l'ancienne table si elle existe.
            df.to_sql(table_name, conn, if_exists='replace', index=True, chunksize=1000)
            logging.info(f"{len(df)} lignes écrites dans {table_name}.")

            # Crée l'hypertable APRES que la table ait été créée par to_sql
            create_hypertable(conn, table_name)

    except Exception as e:
        logging.error(f"Erreur lors du stockage des données dans {table_name}: {e}")
        # IMPORTANT: Ne pas arrêter le script ici, essayer l'actif suivant
        # raise e # Ne pas propager l'erreur pour continuer avec ETHUSDT par exemple


# --- Processus ETL principal ---
if __name__ == "__main__":
    start_time = time.time()
    for symbol in WATCHLIST:
        logging.info(f"--- Début du traitement pour {symbol} ---")

        # 1. Extraction (Binance)
        df_h1 = fetch_binance_data(symbol, Client.KLINE_INTERVAL_1HOUR, START_DATE)
        df_h4 = fetch_binance_data(symbol, Client.KLINE_INTERVAL_4HOUR, START_DATE)
        # --- AJOUT/MODIFICATION --- : Extraction Daily
        df_daily = fetch_binance_data(symbol, Client.KLINE_INTERVAL_1DAY, START_DATE)

        if df_h1.empty or df_h4.empty or df_daily.empty:
            logging.warning(f"Données manquantes pour {symbol}. Passage au suivant.")
            continue

        # 2. Transformation (Calcul des Indicateurs)
        df_h1 = calculate_features(df_h1, 'h1')
        df_h4 = calculate_features(df_h4, 'h4')
        # --- AJOUT/MODIFICATION --- : Calcul Daily
        df_daily = calculate_features(df_daily, 'daily')

        # 3. Combinaison des DataFrames
        logging.info(f"Combinaison des données H1, H4 et Daily pour {symbol}...")
        # Renommer les colonnes H4 pour éviter les conflits lors de la fusion
        df_h4 = df_h4.rename(columns=lambda x: x if x in ['open', 'high', 'low', 'close', 'volume'] else f"{x}")
        # Fusion H1 et H4: merge_asof pour joindre sur le timestamp le plus proche (précédent ou égal)
        df_merged = pd.merge_asof(df_h1.sort_index(), df_h4.sort_index(), on='timestamp', direction='backward', suffixes=('', '_h4_drop'))
        df_merged.drop(columns=[col for col in df_merged.columns if '_h4_drop' in col], inplace=True)

        # --- AJOUT/MODIFICATION --- : Fusion avec les indicateurs Daily
        daily_indicators = [col for col in df_daily.columns if '_daily' in col]
        df_daily_indicators_only = df_daily[daily_indicators]
        df_final = pd.merge_asof(df_merged.sort_index(), df_daily_indicators_only.sort_index(), on='timestamp', direction='backward')

        df_final.set_index('timestamp', inplace=True) # Assure que timestamp est l'index
        df_final.dropna(inplace=True)

        if df_final.empty:
             logging.warning(f"Le DataFrame final pour {symbol} est vide après fusion/nettoyage. Vérifiez les données/calculs.")
             continue

        logging.info(f"DataFrame final pour {symbol} prêt ({len(df_final)} lignes).")

        # 4. Chargement (TimescaleDB)
        table_name = f"{symbol.lower()}_features"
        store_data(df_final, table_name, engine) # Cette fonction peut échouer si le mdp est faux

        logging.info(f"--- Fin du traitement pour {symbol} ---")

    end_time = time.time()
    logging.info(f"Processus ETL terminé. Durée totale : {end_time - start_time:.2f} secondes.")
