# Fichier: inspect_columns.py
# Outil de diagnostic pour le Projet Arsenal
# Version: V1.3.29

import sys
import pandas as pd
from sqlalchemy import create_engine, text

# --- CONFIGURATION (Doit correspondre à V1.3.27) ---

# 1. Chaîne de connexion (Utilisateur 'user' et mot de passe V1.3.12)
DATABASE_URL = "postgresql://user:MonNouveauMotDePasseSécurisé123@localhost:5432/arsenal_db"

# 2. Nom de la table à inspecter (Nom réel de l'ETL V1.3.27)
TABLE_NAME = "btc_features"
# 3. Requête SQL pour extraire les données
QUERY = f"SELECT * FROM {TABLE_NAME} LIMIT 5"

# --- EXÉCUTION ---

print(f"--- DIAGNOSTIC SCHÉMA (V1.3.29) ---")
print(f"Inspection de la table: {TABLE_NAME}")

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Test de connexion et exécution
        print("Connexion à la base de données réussie.")
        df = pd.read_sql(text(QUERY), conn)

    if df.empty:
        print(f"ERREUR: La table '{TABLE_NAME}' est vide.")
        sys.exit(1)

    # Affichage des résultats
    print(f"\n[SUCCÈS] {len(df)} lignes chargées.")
    
    print("\n--- NOMS DE COLONNES DISPONIBLES ---")
    print("Copiez ces noms exacts (respect de la casse).")
    print("-" * 30)
    for col in df.columns:
        print(col)
    print("-" * 30)

    print("\n--- APERÇU DES DONNÉES (LIMIT 5) ---")
    print(df.head())
    print("--- FIN DU DIAGNOSTIC ---")


except Exception as e:
    print(f"\nERREUR FATALE LORS DE L'INSPECTION:")
    print(f"Vérifiez DATABASE_URL (V1.3.12) et TABLE_NAME (V1.3.27).")
    print(f"Erreur: {e}")
    sys.exit(1)
