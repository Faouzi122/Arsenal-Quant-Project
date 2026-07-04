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
├── 07_Backtest_Engine/                      ← Backtest empirique sur données réelles
│   ├── fetch_real_data.py                   ← Fetcher Binance API (0 dépendance)
│   ├── run_empirical_backtest.py            ← Validateur R_net sur 180j ETH/USDC
│   └── data/                                ← CSV réels + rapports JSON
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
2. **PIVOT R_NET (2026-07-04) :** L'ancien oracle HEDGE/EXECUTE (seuil 1.5×) a échoué sur données réelles (0% de précision à 35% APY / 30j). Pivot vers un évaluateur R_net pur. L'engine ne dicte plus l'action — il délivre l'intelligence mathématique.
3. **Métriques validées (données réelles, 180j ETH/USDC Binance) :**
   - Breakeven corridor → 100% de fiabilité (si le ratio reste dans le corridor, R_net est positif)
   - Mid-checkpoint predictive accuracy : 82-97% selon les scénarios
   - Exécution : ~310ms pour 1,350 positions simulées, O(N), 0 dépendances
4. **Pivot B2B validé :** Distribution en licence Docker privée (On-Prem) pour les fonds, en plus de l'API L402 publique.
5. **Doctrine Fabuleux :** Intégrée dans Uncle Bob (persona.md), ADK Scout (adk_mission.txt), et NotebookLM.
6. **Disjoncteur méta-cognitif :** Règle injectée dans Section 10 de GEMINI.md → charge `META_AUDIT_PROTOCOL.md` en cas de doute.
7. **Proposition de valeur v2 :** "Étant donné votre pool, voici votre R_net exact, votre niveau de risque, et votre corridor de breakeven. Vous décidez." L'agent client garde le contrôle.

## IV. MISSION ACTIVE (Phase 4 — R_net Infrastructure)

### Seuils de succès (falsifiables)
- **Signal On-Chain :** 1 paiement L402 externe (HTTP 200 + preimage) capturé par `hunt_client_zero.sh`
- **Signal Technique :** 1 agent externe consomme le JSON R_net et intègre le corridor dans sa logique
- **En dessous = ÉCHEC → Pivot** (changer le prix, la cible, ou le problème)

### Plan de distribution M2M (Infrastructure Provider)
| Phase | Action |
|-------|--------|
| ✅ FAIT | Backtest empirique sur 180j de données réelles ETH/USDC |
| ✅ FAIT | Refactorisation evaluate_pool.py → évaluateur R_net pur |
| EN COURS | Mise à jour de la gateway L402 (output JSON R_net) |
| SUIVANT | Mise à jour README.md + registres MCP (Smithery, Glama) |
| SUIVANT | Publication GitHub Gist avec rapport de backtest réel |
| Continu | Vérifier `hunt_client_zero.sh` au rallumage du PC |

## V. COMMANDES OPÉRATIONNELLES ESSENTIELLES

```bash
# Surveiller le trafic réel externe (Client Zéro)
~/Antigravity_System/scripts/hunt_client_zero.sh

# Évaluer les paramètres d'une position LP (R_net evaluator v2)
python3 ~/Antigravity_System/scripts/evaluate_pool.py <APY> <RATIO_PRIX> [JOURS]
# Exemple: python3 ~/Antigravity_System/scripts/evaluate_pool.py 0.20 0.85 30

# Lancer le backtest empirique sur données réelles
python3 ~/Antigravity_System/07_Backtest_Engine/run_empirical_backtest.py

# Récupérer les dernières données de marché (Binance, 0 dépendance)
python3 ~/Antigravity_System/07_Backtest_Engine/fetch_real_data.py 180

# Monitoring général du gateway
~/Antigravity_System/scripts/monitor_m2m.sh

# Vérifier la santé du VPS
ssh root@199.247.19.249 "free -h && df -h && docker ps"
```

## VI. POUR RÉINJECTER CE CONTEXTE EN NOUVEAU CHAT

Collez ce prompt au début d'une nouvelle session :
> "Tu es l'Orchestrateur Barbara Grosz de l'Antigravity Engine. Voici notre Source de Vérité unique : [coller le contenu de GEMINI.md]. Voici l'état actuel du projet : [coller le contenu de ce fichier session_handover.md]. Confirme la réception et propose la prochaine action."
