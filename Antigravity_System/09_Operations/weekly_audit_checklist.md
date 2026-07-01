# 📋 Arsenal Decision Engine — Protocole d'Audit Hebdomadaire (Phase 3)

Ce protocole définit la routine d'observation asynchrone pour piloter l'infrastructure en production sans altérer le code source (Application du principe Lean Startup).

---

## 📡 Étape 1 : Inspection du Trafic M2M (L402 Gateway)
Lancez le **Torvalds Dashboard** local pendant 5 minutes :
```bash
~/Antigravity_System/scripts/monitor_m2m.sh
```
**Indicateurs à surveiller :**
* **Taux de conversion des paiements :** Vérifier que les requêtes `402 Payment Required` sont suivies de `200 OK` (settlement réussi).
* **Signaux générés :** Vérifier l'occurrence des signaux `HEDGE` ou `EXECUTE` transmis aux agents.

---

## 💰 Étape 2 : Audit de la Trésorerie (LNbits)
Connectez-vous à votre interface administrative LNbits pour vérifier le solde accumulé :
* **Vérification du solde :** Quantité de Satoshis encaissés.
* **Volume de transactions :** Nombre de micropaiements réglés par les agents externes.
* **Frais de routage :** Évaluer l'efficacité économique face aux coûts fixes du VPS ($/mois).

---

## ⚡ Étape 3 : Santé Système (VPS Vultr)
Exécutez une connexion SSH rapide pour valider les ressources physiques :
```bash
ssh root@199.247.19.249 "free -h && df -h && docker ps"
```
**Critères de santé :**
* **Consommation RAM :** Consommation stable (inférieure à 1 Go grâce à la structure $\mathcal{O}(1)$).
* **Espace disque :** S'assurer que les logs Docker ne s'accumulent pas de manière critique.
* **Statut des conteneurs :** `l402_gateway` et `tunnel` doivent afficher un statut `Up`.

---

## 🔍 Étape 4 : Veille Concurrentielle et Visibilité AEO
Vérifiez l'état d'indexation du serveur MCP sur les registres :
* **Smithery.ai :** S'assurer que la note reste stable (> 80/100).
* **Glama.ai :** Valider l'état du serveur et sa découvrabilité par les LLMs.
* **GitHub :** Suivre les clones, stars ou éventuelles issues levées sur le Cookbook d'intégration.
