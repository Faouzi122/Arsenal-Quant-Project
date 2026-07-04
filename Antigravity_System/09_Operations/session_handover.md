# 📋 SESSION HANDOVER — Arsenal Decision Engine
> Dernière mise à jour : 2026-07-04
> Source de vérité unique pour ré-injection en nouveau chat.

---

## I. ÉTAT DU SYSTÈME (Production)

| Composant | Statut | Localisation |
|-----------|--------|-------------|
| VPS Vultr (Francfort) | ✅ ACTIF 24/7 | `199.247.19.249` |
| L402 Gateway (FastAPI) | ✅ Container Docker `l402_gateway` port 8088 | `/home/faouzi/Antigravity_System/06_Router_MCP/l402_gateway_real.py` |
| Decision Engine | ✅ Container Docker `decision_engine` port 8002 | `/home/faouzi/API_Factory/Sentiment_Alpha_v1/` |
| LNbits (Lightning) | ✅ Container Docker `lnbits_gateway` port 5001 (localhost) | FakeWallet (sandbox) |
| Cloudflare Tunnel | ✅ HTTPS via `api.arsenal-quant.com` | Container `cloudflare_tunnel` |
| Smithery.ai | ✅ Score 86/100, TXT DNS vérifié | `khelifa-faouzi16/arsenal-decision-engine` |
| Glama.ai | ✅ Indexé | `Faouzi122/Arsenal-Quant-Project` |
| GitHub | ✅ Branche `master` synchronisée | `github.com/Faouzi122/Arsenal-Quant-Project` |

## II. ARCHITECTURE LOCALE (Lenovo / Antigravity IDE)

```
~/Antigravity_System/
├── 01_Orchestrator_Grosz/GEMINI.md        ← Constitution (Global Rules v3.0 + Fabuleux + Meta-Audit)
├── 02_Developer_UncleBob/
│   ├── persona.md                          ← Directive Fabuleux injectée
│   └── Doctrines/                          ← SKILL.md, revision-prose.md, auto-evaluation-visuelle.md
├── 04_Strategy_Gerber/                     ← Moteur mathématique IL (Entité pure)
├── 05_Innovation_Ries/ADK_Scout/           ← Agent ADK (adk_mission.txt avec Fabuleux)
├── 06_Router_MCP/l402_gateway_real.py      ← Gateway L402 (Adaptateur)
├── 08_SDK_Wrappers/COOKBOOK.md              ← Guide d'intégration CrewAI/LangChain
├── 09_Operations/
│   ├── META_AUDIT_PROTOCOL.md              ← 10 questions méta-cognitives (disjoncteur N5)
│   ├── weekly_audit_checklist.md           ← Protocole d'audit hebdomadaire Phase 3
│   └── session_handover.md                 ← CE FICHIER
└── scripts/
    ├── monitor_m2m.sh                      ← Dashboard Torvalds (monitoring général)
    ├── hunt_client_zero.sh                 ← Traqueur de premier client réel externe
    ├── evaluate_pool.py                    ← Outil Concierge MVP (audit IL local)
    ├── il_empirical_backtest.py            ← Backtest 30 scénarios (99.08% drawdown reduction)
    └── client_one.py                       ← Démo agent autonome LP
```

## III. DÉCISIONS STRATÉGIQUES ACTÉES

1. **Positionnement :** Middleware d'infrastructure (Niveau 3/5 "vendeur de pioches"), PAS de bot de trading.
2. **Métrique validée :** 99.08% de réduction de Drawdown sur 30 scénarios historiques.
3. **Pivot B2B validé :** Distribution en licence Docker privée (On-Prem) pour les fonds, en plus de l'API L402 publique.
4. **Concierge MVP activé :** Validation manuelle du Product-Market Fit AVANT toute nouvelle ligne de code.
5. **Doctrine Fabuleux :** Intégrée dans Uncle Bob (persona.md), ADK Scout (adk_mission.txt), et NotebookLM.
6. **Disjoncteur méta-cognitif :** Règle injectée dans Section 10 de GEMINI.md → charge `META_AUDIT_PROTOCOL.md` en cas de doute.
7. **Code gelé :** Aucune nouvelle fonctionnalité tant que le PMF n'est pas prouvé.

## IV. MISSION ACTIVE (Phase 3 — Acquisition)

### Seuils de succès (falsifiables)
- **Signal On-Chain :** 1 paiement L402 externe (HTTP 200 + preimage) capturé par `hunt_client_zero.sh`
- **Signal Social :** 3 soumissions manuelles de paramètres de pools + 1 phrase explicite "je paierais pour automatiser ça"
- **En dessous = ÉCHEC → Pivot** (changer le prix, la cible, ou le problème)

### Plan d'acquisition Reddit/Discord (CEO — action humaine)
| Jour | Action |
|------|--------|
| J-0 → J-4 | Créer comptes, commenter, aider, zéro auto-promotion (farming karma > 50) |
| J-5 | Post technique pur + test de visibilité en navigation privée |
| J-6 | Poster le Sniper Pitch corrigé (avec pont CTA vers API L402) |
| Continu | Vérifier `hunt_client_zero.sh` au rallumage du PC |

### Sniper Pitch corrigé (avec pont API)
> "Je développe un moteur d'Oracle déterministe (Arsenal Decision Engine) pour protéger les agents DeFi de l'Impermanent Loss (validé à 99% de drawdown reduction). Normalement, ce moteur tourne en API M2M derrière un paywall Lightning/x402 pour les agents autonomes.
> Mais pour calibrer mon modèle, je propose des exécutions manuelles aujourd'hui. Ne me donnez pas vos clés : envoyez-moi juste les paramètres de votre pool Uniswap (Paire, TVL, APY attendu, ratio actuel) en MP. Je passe ça dans mon moteur local et je vous donne le signal HEDGE/EXECUTE.
> Si l'analyse vous sauve de l'argent et que vous voulez l'automatiser pour votre propre agent/bot, mon endpoint public est ici : https://api.arsenal-quant.com/mcp/audit/latest (150 sats par appel)."

## V. COMMANDES OPÉRATIONNELLES ESSENTIELLES

```bash
# Surveiller le trafic réel externe (Client Zéro)
~/Antigravity_System/scripts/hunt_client_zero.sh

# Évaluer les paramètres d'un client Concierge
python3 ~/Antigravity_System/scripts/evaluate_pool.py <APY> <RATIO_PRIX>

# Monitoring général du gateway
~/Antigravity_System/scripts/monitor_m2m.sh

# Vérifier la santé du VPS
ssh root@199.247.19.249 "free -h && df -h && docker ps"
```

## VI. POUR RÉINJECTER CE CONTEXTE EN NOUVEAU CHAT

Collez ce prompt au début d'une nouvelle session :
> "Tu es l'Orchestrateur Barbara Grosz de l'Antigravity Engine. Voici notre Source de Vérité unique : [coller le contenu de GEMINI.md]. Voici l'état actuel du projet : [coller le contenu de ce fichier session_handover.md]. Confirme la réception et propose la prochaine action."
