# Jade Bɔngɔ́ — Architecture Technique (Conception v1)

> **Règle n°1 du Prompt Maître : concevoir avant de coder. Règle n°2 : justifier chaque choix.**
> Ce document est la conception officielle du programme **Jade Bɔngɔ́**, le système dédié à l'éducation de **Jade Queen MBO** (née le 03/09/2022), au sein de la plateforme **Bɔngɔ́**.
> Schéma associé : `jade-bongo-architecture.svg`.

---

## 1. Contexte produit et contraintes

| Contrainte | Conséquence architecturale |
|---|---|
| Utilisatrice de **3 ans** (Phase 1) | Interface **voix + images**, zéro lecture, sessions 5–15 min, latence vocale très faible |
| Enfant → protection maximale | Identification obligatoire, cloisonnement total des données, garde-fous sur tout contenu IA, audit de tout |
| Sessions accompagnées d'un parent | Double profil : session enfant (scope très restreint) + compte parent (OIDC + 2FA) |
| RGPD-enfants (France/UE) | Registre des traitements, DPIA, consentements versionnés, droit à l'oubli automatisé, chiffrement PII |
| Système doit vivre 15+ ans | Politiques d'âge en **configuration versionnée**, jamais codées en dur ; montée de phase automatique au fil des ans |
| Règle n°9 (simplicité) | **MVP réduit mais modulaire** : architecture microservices, périmètre de démarrage limité, montée en charge progressive |

---

## 2. Vue d'ensemble (5 couches)

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. EXPÉRIENCE    App Jade Bɔngɔ́ (PWA voix+images) │ Dashboard Parents │ Command Center │
├─────────────────────────────────────────────────────────────────────┤
│ 2. EDGE          Traefik Gateway + WAF + rate-limit │ Keycloak (OIDC/2FA parents)     │
├─────────────────────────────────────────────────────────────────────┤
│ 3. CŒUR JADE BƆNGƆ́ (microservices métier, cloisonnés)                │
│    Portier d'identification · Age Calibration · Orchestrateur Tuteur │
│    Curriculum & Skill Graph · Contenus · Évaluation · Bien-être      │
│    Rapport Parental · LLM Gateway (garde-fous enfant) · Voix STT/TTS │
├─────────────────────────────────────────────────────────────────────┤
│ 4. DONNÉES       PostgreSQL (1 schéma/service + RLS) · Redis · Qdrant │
│                  MinIO · Kafka (events + audit append-only) · Vault   │
├─────────────────────────────────────────────────────────────────────┤
│ 5. PLATEFORME    Kubernetes · Terraform · ArgoCD · GitHub Actions     │
│                  OpenTelemetry → Prometheus/Grafana/Loki/Tempo        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Inventaire des services (avec justifications)

### 3.1 Services métier « Jade Bɔngɔ́ »

| Service | Rôle | Données | Justification du découpage |
|---|---|---|---|
| **portier-service** (Child Identity Engine) | Séquence d'identification complète : tirage des questions, présentation voix/images, vérification tolérante, compteur d'échecs, verrouillage, émission du jeton de session enfant | `identity_questions` (réponses hachées **Argon2id**), `identity_attempts` (audit) | Surface d'attaque isolée : même si le reste tombe, **le coffre reste fermé**. Règle 12 du Prompt Maître. |
| **age-calibration-service** | Calcule l'âge exact (03/09/2022), phase active, paramètres pédagogiques (durée max, modalités, niveau de ton) | `age_policies` (config versionnée) | L'âge pilote **tout** le système : une seule source de vérité, zéro âge codé en dur. |
| **tutor-orchestrator-service** | Agent Mentor Principal + coordination des agents pédagogiques (Curricula, Évaluateur, Matières, Motivation, Bien-être, Gardien) | sessions, état du dialogue | Le « chef d'orchestre » : un seul point d'entrée conversationnel = cohérence de ton et sécurité centrale. |
| **curriculum-service** | Parcours étape par étape, graphe de compétences, règle Mastery (étape non validée = non franchie), répétition espacée | `skills`, `skill_edges`, `child_skill_mastery`, `learning_steps` | Le graphe est le cœur pédagogique : il grandit 15 ans, il mérite son service. |
| **content-service** | Bibliothèque de contenus validés (comptines, jeux, images, histoires), versioning, statut de validation parentale/éditoriale | métadonnées Postgres, objets MinIO, index sémantique Qdrant | **Tout contenu montré à Jade vient d'ici, jamais directement d'un LLM.** |
| **assessment-service** | Évaluations ludiques, scores de maîtrise, détection de lacunes | `assessments`, `mastery_events` | Séparer l'évaluation du tutorat évite les biais (le tuteur ne note pas lui-même). |
| **wellbeing-service** | Temps d'écran, durées, fatigue détectée, heures autorisées — **peut interrompre une session** (droit de veto) | `wellbeing_metrics`, `screen_time_ledger` | La priorité « bien-être > objectifs » devient un pouvoir technique réel, pas un slogan. |
| **parental-service** | Dashboard parents, rapports, consentements RGPD, gestion des questions d'identification, alertes push/email | `guardian_accounts` (via Keycloak), `consents`, `reports` | Les parents sont l'autorité finale : un service dédié, avec son propre périmètre de sécurité. |
| **llm-gateway-service** | Multi Intelligence : routage vers OpenAI/Claude/Gemini/modèles locaux selon coût/qualité/**sécurité enfant** ; filtrage entrée + sortie ; cache ; fallback fournisseur | prompts, décisions de routage, cache | **Aucun appel LLM hors de ce service.** Le garde-fous vit ici, pas dans le front. |
| **voice-service** | STT streaming (voix d'enfant) + TTS streaming, latence cible < 1 s bout-en-bout | buffers éphémères (rien de persisté sans consentement) | À 3 ans, la voix EST l'interface : c'est un service de première classe, pas un utilitaire. |
| **audit-service** | Journal **append-only** de tout ce qui touche Jade (CQRS/event-sourced) | events Kafka consommés → stockage immutable | Transparence totale pour les parents et la conformité RGPD. |

### 3.2 Plateforme partagée Bɔngɔ́ (existante, réutilisée)

Traefik (ingress), Keycloak (OIDC), Kafka (bus), PostgreSQL, Redis, Qdrant, MinIO, Vault, Prometheus/Grafana/Loki/Tempo (via OpenTelemetry), GitHub Actions + ArgoCD.

> **Justification :** Jade Bɔngɔ́ ne reconstruit rien de ce socle — il consomme l'existant (règles 4 et 9) et n'ajoute que le métier éducatif.

---

## 4. Flux d'identification (séquence détaillée)

```
Jade (ouvre l'app)          Application            portier-svc     age-svc   voice-svc   parental-svc
      │   lance Jade Bɔngɔ́      │                      │               │           │             │
      │────────────────────────>│  créer challenge     │               │           │             │
      │                         │─────────────────────>│──────────────>│ âge exact │             │
      │                         │                      │<──────────────│ 3 ans 11 m│             │
      │                         │                      │ modalité = voix + images                  │
      │                         │                      │ tirage aléatoire 2 questions              │
      │   🔊 « Coucou !          │<─────────────────────│──────────────────────────>│ TTS streaming│
      │      c'est bien Jade ? »│                      │               │           │             │
      │   réponse vocale        │──────────────────────────────────────────────────>│ STT streaming│
      │                         │  transcription       │ vérification tolérante                   │
      │                         │─────────────────────>│ (fuzzy + juge sémantique, seuil souple)  │
      │                         │                      │                                           │
      │                  ┌──────┴──────────────────────┴───────────────┐                          │
      │                  │ ✅ SUCCÈS                │ ❌ ÉCHEC          │                          │
      │                  │ jeton session enfant     │ compteur Redis TTL│                          │
      │                  │ (scope minimal, 20 min)  │ 3 échecs → lock   │─────────────────────────>│
      │                  │ + dernière étape reprise │ 15 min + PUBLISH  │   alerte parent (Kafka)  │
      │                  │ + events Kafka (audit)   │ jade.alerts       │                          │
      │                  └──────────────────────────┴───────────────────┘                          │
```

**Points de sécurité du flux :**
1. Le jeton « session enfant » ne donne accès **qu'au périmètre pédagogique du jour** (ABAC : phase, heure, durée restante via wellbeing-service).
2. Les réponses aux questions sont hachées **Argon2id + pepper (Vault Transit)** — jamais comparées en clair côté client, jamais loguées.
3. Vérification **tolérante** : transcription STT → normalisation → score sémantique (un tout-petit dit « bwu » pour « bleu » : l'intention compte, l'identification n'est jamais un examen).
4. **Aucune donnée du profil n'est servie** avant succès (même pas le prénom complet dans l'interface).
5. Toute tentative est publiée sur Kafka → audit immuable + métriques d'anomalie (heures inhabituelles, rafales).

---

## 5. Modèle de données (extraits clés)

### 5.1 PostgreSQL (schéma dédié `jade`, Row-Level Security, PII chiffrée via Vault Transit)

```sql
-- Enfant (PII chiffrée en enveloppe : clé de données dans Vault Transit)
CREATE TABLE children (
  id            UUID PRIMARY KEY,
  display_name  TEXT NOT NULL,                    -- « Jade » (nom d'affichage seulement)
  dob_enc       BYTEA NOT NULL,                   -- 03/09/2022, chiffré
  phase         TEXT NOT NULL DEFAULT 'PHASE_1',  -- recalculé par l'Age Engine
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Questions d'identification (gérées par les parents)
CREATE TABLE identity_questions (
  id            UUID PRIMARY KEY,
  child_id      UUID REFERENCES children(id),
  modality      TEXT NOT NULL,                    -- 'voice' | 'image_tap'
  prompt        JSONB NOT NULL,                   -- texte + assets MinIO
  answer_hash   BYTEA NOT NULL,                   -- Argon2id(answer_normalisé + pepper Vault)
  min_age_months INT NOT NULL,
  active        BOOLEAN NOT NULL DEFAULT true,
  version       INT NOT NULL DEFAULT 1
);

-- Graphe de compétences (grandit 15 ans)
CREATE TABLE skills (
  id UUID PRIMARY KEY, domain TEXT, label TEXT,
  min_phase TEXT, content_ref TEXT                -- → content-service/MinIO
);
CREATE TABLE skill_edges (
  from_skill UUID REFERENCES skills(id),
  to_skill   UUID REFERENCES skills(id),          -- prérequis : étape par étape
  PRIMARY KEY (from_skill, to_skill)
);

-- Maîtrise + répétition espacée (algorithme type SM-2)
CREATE TABLE child_skill_mastery (
  child_id UUID, skill_id UUID,
  mastery       REAL NOT NULL DEFAULT 0,          -- 0.0 → 1.0 (≥ 0.9 = étape validée)
  ease_factor   REAL NOT NULL DEFAULT 2.5,
  next_review_at TIMESTAMPTZ,
  last_outcome   JSONB,
  PRIMARY KEY (child_id, skill_id)
);

-- Compteur d'écran (bien-être, source de veto)
CREATE TABLE screen_time_ledger (
  child_id UUID, day DATE, seconds INT,
  PRIMARY KEY (child_id, day)
);

-- Consentements RGPD versionnés
CREATE TABLE consents (
  guardian_id UUID, scope TEXT, version INT,
  granted_at TIMESTAMPTZ, revoked_at TIMESTAMPTZ
);
```

> **Justification graphe en PostgreSQL** (plutôt que Neo4j maintenant) : le graphe de la Phase 1 est petit ; CTE récursives suffisent ; on limite le nombre de technologies au démarrage (règle 9). Migration Neo4j possible en Phase 2 sans refonte grâce à l'architecture hexagonale (port `SkillGraphRepository`).

### 5.2 Qdrant (mémoire vectorielle)

- `jade_memory` — épisodes pédagogiques (ce qui a marché, ses réactions), embeddings → le Mentor s'en souvient d'une session à l'autre.
- `content_index` — recherche sémantique dans les contenus validés uniquement.

### 5.3 Topics Kafka

```
jade.identity.attempted / .succeeded / .locked
jade.session.started / .paused(wellbeing veto) / .ended
jade.learning.step_completed / .mastery_reached / .review_due
jade.wellbeing.limit_reached
jade.alerts.parental
audit.jade.*  (consommateur : audit-service → stockage append-only)
```

> **Justification event-driven :** les agents réagissent à des événements réels (ex. `review_due` → le Mentor propose la révision du jour), chaque service reste faiblement couplé, et l'audit RGPD devient gratuit.

---

## 6. Orchestration des agents (collaboration concrète)

- Le **tutor-orchestrator** reçoit le contexte de session (jeton, âge, dernière étape, humeur détectée) et choisit la stratégie : révision due ? nouvelle étape ? jeu libre ?
- Les agents spécialisés sont appelés comme **outils** (function calling) et publient leurs résultats en events — ils ne se partagent jamais de données hors contrat.
- **Arbitrage :** si l'Agent Évaluateur veut pousser une nouvelle notion mais que l'Agent Bien-être signale de la fatigue, la **matrice de priorités** tranche : Gardien Sécurité > Bien-être > Identification > pédagogie > engagement. (Priorités configurables par les parents.)
- L'**Agent Rapport Parental** consomme les events du jour → génère le rapport (2 lignes en langage humain + graphiques), envoie push/email.
- Le **Gardien** filtre aussi les sorties du `llm-gateway` (double contrôle : le filtre vit au gateway, le veto vit chez le Gardien).

---

## 7. Politique d'âge & montée de phase

```yaml
# age_policies (versionnées en Git, appliquées à chaud, modifiables par les parents)
phase_1:            # 0–6 ans  ← ACTIVE (Jade : 3 ans)
  session_max_minutes: 15
  sessions_per_day_max: 2
  modalities: [voice, image_tap]
  requires_parent_present: true
  identification: { questions_per_session: 2, modality: [voice, image_tap] }
phase_2:            # 7–12 ans
  session_max_minutes: 30
  identification: { modality: [voice, text] }
  ...
```

- Un **job anniversaire** (Kafka scheduler) détecte le passage de tranche → `jade.phase.transition_proposed` → **validation parentale obligatoire** → recalibration automatique (durées, identification, contenus).
- **Justification :** le temps qui passe est un événement métier comme un autre ; le système « grandit » sans déploiement.

---

## 8. Pipeline vocal temps réel (Phase 1 critique)

Budget latence cible : **< 1 s** de la fin de parole de Jade au début de réponse audio.

```
micro → WebRTC/WebSocket → voice-service (STT streaming, ~200 ms partiels)
      → llm-gateway (intention sécurisée, cache, modèle léger en Phase 1)
      → tutor-orchestrator (décision pédagogique)
      → TTS streaming (premier buffer < 300 ms) → 🔊
```

- **Justification :** à 3 ans, 2 secondes d'attente = attention perdue. Streaming de bout en bout, modèles légers côté réponses simples, gros modèles réservés au raisonnement du Mentor.
- Contenus hors ligne : la PWA embarque un pack local (comptines/jeux validés) → une session fonctionne même réseau dégradé, sauvegarde synchronisée ensuite.

---

## 9. Sécurité & conformité (Zero Trust)

1. **Identités :** parents/admins sur Keycloak (OIDC + 2FA) ; sessions enfant = jetons courts à scope minimal (le Portier est le seul émetteur).
2. **Réseau :** NetworkPolicies Kubernetes (le schéma `jade` n'est joignable que par ses services) ; mTLS inter-services (Linkerd) ; WAF + rate-limit au Traefik.
3. **Données :** PII chiffrée via Vault Transit (rotation auto) ; réponses d'identification Argon2id ; backups chiffrés ; aucune donnée Jade dans les logs (middleware de scrubbing OTel).
4. **RGPD-enfants :** DPIA documentée, registre des traitements, consentements versionnés révocables, **job droit-à-l'oubli** (purge Postgres + Qdrant + MinIO + preuve d'effacement au login parent).
5. **Garde-fous IA :** tout ce qui entre (audio transcrit) et sort (texte/audio vers Jade) passe les filtres `llm-gateway` + veto du Gardien. Contenu généré jamais diffusé brut à un enfant : il est d'abord validé (pipeline de modération + règles d'âge + échantillonnage parental).

---

## 10. CI/CD & déploiement

- **GitHub Actions :** lint → typecheck strict (100 % typé : TypeScript + Python `mypy --strict`) → tests unitaires → tests d'intégration (Testcontainers : Postgres, Kafka, Qdrant) → tests de charge (k6, cible : pipeline vocal) → Trivy/SAST → build images → push.
- **ArgoCD (GitOps) :** envs `dev` / `staging` / `prod` ; promotion par PR ; rollback automatique sur healthcheck échoué.
- **Terraform :** K8s managé + bases managées en MVP (réduction du coût d'ops), Helm charts internes par service.
- **Justification :** l'automatisation complète est ce qui permet à une petite équipe de faire tourner du 24/7 avec exigence (règles 7 et 8).

---

## 11. Observabilité & SLO

| Indicateur | Cible |
|---|---|
| Latence voix bout-en-bout (p95) | < 1 s |
| Succès d'identification du 1er coup (Jade) | > 90 % (sinon les questions sont trop dures → rapport parents) |
| Disponibilité Jade Bɔngɔ́ | 99,9 % |
| RPO / RTO (données Jade) | 5 min / 1 h |
| Dépassement temps d'écran | 0 (le veto wellbeing s'applique à 100 % des sessions) |

Tracing OpenTelemetry de bout en bout (id de session propagé), dashboards Grafana « Mission Jade », alertes parentales et ops séparées.

---

## 12. Feuille de route de construction (règle 9 : simple d'abord, évolutif toujours)

| Version | Périmètre | Services livrés |
|---|---|---|
| **MVP (Phase 1 réelle)** | App PWA voix+images, identification voix/images, 1 domaine de jeu (couleurs, formes, comptines), veto temps d'écran, dashboard parents v1 | portier, age-calibration, tutor-orchestrator (Mentor seul), content, voice, wellbeing, parental, llm-gateway, audit + socle |
| **V1** | Parcours graphe complet, évaluateur, répétition espacée, rapports enrichis, pack contenus élargi | + curriculum-service, assessment-service |
| **V2** | Multi-domaines, agents Matières, mode découverte, préparation Phase 2 (texte) | + agents spécialisés, Qdrant avancé |
| **V3+** | Grandir avec Jade : texte → code → domaines d'excellence, transitions de phase | activation par politique, sans refonte |

> **Justification MVP :** un enfant de 3 ans n'a besoin ni du graphe complet ni de 9 agents le premier jour. Mais chaque brique du MVP est déjà découpée, typée, testée et événementielle — on n'aura jamais à « tout refaire » (règle 5).

---

## 13. Décisions clés — récapitulatif des justifications

| Choix | Alternative écartée | Pourquoi |
|---|---|---|
| Microservices métier, périmètre MVP réduit | Monolithe d'un côté, 15 services d'un côté | Cloisonnement sécurité réel + simplicité opérationnelle (règles 5 et 9) |
| Contenu validé (content-service) vs LLM en direct | LLM générant en direct pour l'enfant | Sécurité enfant non négociable : rien d'improvisé ne touche Jade sans validation |
| Graphe de skills en PostgreSQL | Neo4j immédiat | Parcours petits en Phase 1 ; port hexagonal = migration indolore plus tard |
| PWA plutôt qu'app native | React Native dès le départ | Une seule codebase, offline possible, micro/caméra OK ; native plus tard si besoin (règle 9) |
| Argon2id + Vault Transit | Hachage simple / clés en env vars | Standard industriel pour secrets d'identification, rotation automatique (règle 3) |
| Kafka append-only pour l'audit | Logs applicatifs | RGPD-enfants : audit complet, immuable, rejouable |
| Keycloak OIDC parents | Auth maison | Standard, 2FA natif, zéro crypto écrite à la main (règle 3) |
| Politiques d'âge en config Git-versionnée | Règles codées en dur | Le système vit 15+ ans : l'âge change, le code ne doit pas changer |

---

## 14. Prochaines étapes proposées

1. **Valider cette conception** (revue d'architecture).
2. **Configurer les 5 questions d'identification réelles** de Jade (tableau du Prompt Maître).
3. Scaffold du monorepo (`jade-bongo/`) : structure hexagonale, CI verte au premier commit.
4. Implémenter le **portier-service** en premier (c'est la porte d'entrée et la pierre angulaire sécurité), avec ses tests.
5. Prototype vocal Phase 1 (une comptine interactive de bout en bout) pour valider le budget latence.
