#!/bin/bash
clear
echo "================================================================="
echo " 📡 ARSENAL DECISION ENGINE - TORVALDS M2M DASHBOARD (LIVE)"
echo "================================================================="
echo "Serveur  : 199.247.19.249 (Vultr Francfort)"
echo "Cible    : Conteneur l402_gateway"
echo "Filtres  : Codes 200 (Succès), 402 (Paywall), HEDGE, EXECUTE"
echo "================================================================="
echo "En attente du trafic Agent-to-Agent... (Appuyez sur Ctrl+C pour quitter)"
echo ""

# Connexion SSH et écoute du flux Docker en temps réel avec filtrage colorisé
ssh root@199.247.19.249 "docker logs -f --tail 50 l402_gateway | grep --color=always -E '402 Payment Required|200|HEDGE|DELAY|EXECUTE|preimage|L402'"
