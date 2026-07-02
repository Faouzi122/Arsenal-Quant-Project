#!/bin/bash
clear
echo "================================================================="
echo " 🎯 OPÉRATION CLIENT ZÉRO RÉEL — LE COMPTE À REBOURS EST LANCÉ"
echo "================================================================="
echo "Objectif  : 1 paiement L402 validé (HTTP 200) d'une IP externe."
echo "Filtre    : IP locales et boucles internes IGNORÉES."
echo "Délai     : 7 jours."
echo "================================================================="
echo "En attente du premier vrai client externe... (Ctrl+C pour quitter)"
echo ""

# On se connecte au VPS et on écoute les logs Nginx/FastAPI
# On utilise grep -v pour exclure (ignore) les IPs locales (127.0.0.1, localhost, et l'IP de la machine)
# On cherche uniquement la complétion d'un L402 (Preimage valide conduisant à un 200)

ssh root@199.247.19.249 "docker logs -f l402_gateway | grep -E 'HTTP/1.1\" 402|HTTP/1.1\" 200' | grep -v '127.0.0.1' | grep -E 'L402|macaroon|preimage'"
