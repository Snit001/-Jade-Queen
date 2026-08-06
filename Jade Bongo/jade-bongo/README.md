# ⭐ Jade Bɔngɔ́

**Le programme d'éducation dédié à Jade Queen MBO** (née le 03/09/2022) — au sein de la plateforme **Bɔngɔ́**.
Construit selon le *Prompt Maître* et le document `ARCHITECTURE_JADE_BONGO.md`.

> Mission : instruire, former et éduquer Jade — étape par étape, à son rythme,
> en sécurité maximale — pour en faire **une élite de demain**.

---

## 🧩 Ce qui est implémenté (tout fonctionne)

| Domaine | Détail |
|---|---|
| 🔐 **Portier d'identification** | Questions secrètes (voix + images), tirage aléatoire, vérification tolérante (variantes + validation parentale), réponses **hachées PBKDF2**, verrouillage après 3 échecs + alerte parents, déverrouillage parent |
| 📅 **Age Calibration** | Âge exact calculé en continu (03/09/2022), 4 phases de vie, politiques par âge (durées, modalités, identification) — jamais d'âge en dur |
| 🎓 **Parcours étape par étape** | Graphe de compétences (couleurs → animaux → formes → nombres → comptine), Mastery Learning (≥ 90 % pour valider), **répétition espacée SM-2** (révisions planifiées) |
| ⏱ **Veto bien-être** | Durée max/session (15 min Phase 1) coupée automatiquement par le système, limite de sessions/jour, compteur d'écran |
| 👨‍👩‍👧 **Dashboard Parents** | Vue complète : progression, écran, alertes, **CRUD des questions d'identification**, **politiques d'âge** (durées, sessions/jour), **consentements RGPD** (révoquer « éducation » bloque tout), audit complet |
| 🖥 **Command Center** | Cockpit temps réel « Mission Jade » : KPIs, graphe de compétences, journal des identifications, services, bien-être |
| 🛡 **LLM Gateway** | Point unique des appels IA, garde-fous enfant, mode local à contenus validés (connecteurs OpenAI/Claude/Gemini à brancher) |
| 🧾 **Audit append-only** | Chaque interaction tracée, visible par les parents, jamais de réponse en clair dans les logs |
| 🎙 **Voix** | TTS + STT navigateur (Web Speech API, français), repli « validation par un adulte » |

## 🚀 Lancement

**Méthode express (recommandée) — une seule commande :**

```bash
./start.sh                    # installe les dépendances si besoin + démarre sur le port 8030
PORT=9000 ./start.sh          # autre port
JADE_PARENT_PIN=secret ./start.sh   # PIN parent personnalisé
```

Le script crée un environnement isolé (`.venv`) au premier lancement sur une
machine vierge, détecte si le serveur tourne déjà, et affiche toutes les URL.

**Méthode manuelle :**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8030
```

| Interface | URL | Accès |
|---|---|---|
| 🎮 App de Jade | `http://localhost:8000/` | identification par questions |
| 👨‍👩‍👧 Espace Parents | `http://localhost:8000/parent.html` | PIN parent |
| 🖥 Command Center | `http://localhost:8000/command.html` | PIN parent |

**PIN parent par défaut : `0000`** — à changer impérativement : variable `JADE_PARENT_PIN`.

## ⚙ Configuration (variables d'environnement)

| Variable | Défaut | Rôle |
|---|---|---|
| `JADE_PARENT_PIN` | `0000` | Code d'accès parents (**à changer**) |
| `JADE_PEPPER` | `dev-…` | Poivre serveur pour le hachage (**secret en prod**) |
| `JADE_DB_PATH` | `backend/jade.db` | Chemin de la base SQLite |
| `JADE_LOCK_MAX_FAILURES` | `3` | Échecs avant verrouillage |
| `JADE_LOCK_MINUTES` | `15` | Durée du verrou |

## 🔑 Parcours d'utilisation

1. **Configurer les vraies questions de Jade** : Espace Parents → « Questions d'identification » (les 5 questions par défaut sont des placeholders).
2. Jade ouvre l'app → répond aux questions (voix ou images) → sa leçon du jour se lance.
3. Le veto bien-être termine la session à 15 min, en douceur.
4. Les parents suivent tout : progression, alertes, audit — et gardent l'autorité finale.

## 🧪 Tests

```bash
cd backend && python -m pytest -q
```
Couverture : âge exact & phases, hachage/tolérance, parcours complet, verrous,
déverrouillage parent, CRUD questions, politiques, consentements RGPD, graphe +
SM-2, veto/limite journalière, audit, command center, contrôle d'accès.

## 🐳 Docker

```bash
docker build -t jade-bongo .
docker run -p 8000:8000 -e JADE_PARENT_PIN=secret jade-bongo
```

## 🗺 Correspondance architecture → production

Ce livrable est le **MVP intégré complet** : tous les services de
l'architecture existent en modules Python, sur une base SQLite embarquée.
La cible production (cf. `ARCHITECTURE_JADE_BONGO.md`) remplace les adapters :
PostgreSQL + RLS (schéma fourni), Kafka pour les événements d'audit, Keycloak
OIDC + 2FA pour les parents, Argon2id + Vault Transit, Qdrant pour la mémoire
vectorielle, Kubernetes/ArgoCD pour le déploiement — **sans refonte métier**
(services découplés, ports/adapters).
