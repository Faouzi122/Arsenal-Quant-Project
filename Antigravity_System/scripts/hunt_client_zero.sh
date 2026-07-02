#!/bin/bash
clear
echo "================================================================="
echo " 🎯 OPÉRATION CLIENT ZÉRO RÉEL — LE COMPTE À REBOURS EST LANCÉ"
echo "================================================================="
echo "Objectif  : 1 paiement L402 validé (HTTP 200) d'une IP externe."
echo "Filtres   : Ignorer les IP locales et les requêtes mal formées."
echo "================================================================="
echo "En attente du premier vrai client externe... (Ctrl+C pour quitter)"
echo ""

ssh root@199.247.19.249 "docker logs -f l402_gateway 2>&1 | grep -v 'Invalid HTTP request' | grep -v 'SyntaxError' | grep -E 'HTTP/1.1\" 402|HTTP/1.1\" 200' | grep -v '127.0.0.1' | grep -E 'L402|macaroon|preimage'"
