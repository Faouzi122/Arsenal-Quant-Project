# MISSION : PREUVE DE CONCEPT (PoC) SANDWICH ATTACK
Orchestrateur : Barbara Grosz
Exécuteur : 02_Developer_UncleBob

CIBLE : Un contrat AMM standard (type Uniswap V2 Router).
ACTION REQUISE :
1. Écrire le script `infrastructure/rpc_adapter.py` permettant de simuler localement la séquence (Achat Attaquant, Achat Victime, Vente Attaquant) sur un bloc.
2. Utiliser le noyau `core/mev_math.py` pour démontrer la perte exacte de la victime.
3. Respecter la directive "Fabuleux" : Le livrable doit être un rapport terminal (STDOUT) affichant la perte financière nette causée par le MEV en dollars. Ne pas utiliser d'APIs payantes, utiliser des requêtes RPC publiques en lecture seule.
