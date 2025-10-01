# WebWatcher – Cahier des charges

## 1. Présentation du projet

- **Nom du projet** : WebWatcher
- **Type** : Outil de veille thématique et notifications multi-canaux
- **Porteur du projet** : Maxime G. Martin (Clower)

### 🎯 But

Concevoir un outil de veille dynamique permettant de :

1. Centraliser l’information en provenance de sources multiples (RSS, sites, plateformes d’offres).
2. La filtrer automatiquement selon des mots-clés et thématiques.
3. Alerter l’utilisateur via des notifications instantanées (Telegram) ou un digest email quotidien (Brevo).

L’objectif principal est le gain de temps et l’efficacité : permettre à l’utilisateur de commenter, interagir, postuler ou créer du contenu à partir de l’actualité sans perdre des heures à surveiller manuellement chaque site.

---

## 2. Intentions & vision

### Intentions

- Créer un radar personnel qui fait gagner du temps.
- Rester sobre, éco-conçu, accessible.
- Éviter la complexité d’un SaaS géant → commencer par un MVP interne utilisable par une seule personne, extensible ensuite.

### Vision

- **Court terme** : outil interne minimal, utilisé en ligne de commande + notifications.
- **Moyen terme** : interface simple (Nuxt) permettant de configurer ses feeds et visualiser les résultats.
- **Long terme** : solution SaaS légère pour freelances, agences et assos (modèle freemium + plans payants).

---

## 3. Cibles

### 🎯 Public principal

- Freelances (devs, designers, consultants) → prospection, veille techno.
- Agences à impact → surveiller concurrents, appels à projets, tendances.
- Associations/ONG → suivi de l’actualité, financements, appels d’offres.

### 📊 Positionnement

- **Accessibilité** : outil léger, abordable (voire gratuit en interne).
- **Différenciation** : sobriété, simplicité, rapidité d’exécution.
- **Prix cible (si SaaS)** : 10–30 €/mois.

---

## 4. Design

### 🧑‍🎨 Principes directeurs

- Sobre et élégant : interface minimaliste, pas de surcharges graphiques.
- Éco-conception :
  - Design low-impact (polices systèmes, peu de couleurs, sobriété visuelle).
  - Optimisation des poids (images WebP/AVIF, lazy-loading).
- Accessibilité : contrastes AA/AAA, navigation clavier, support dark mode.
- UX friendly : navigation intuitive, actions rapides, responsive (mobile first).

### 🎨 Identité visuelle

- **Palette** : neutres clairs/foncés + violet `#9C6BFF` (identité Clower).
- **Typo** : polices système (éco et rapides), modernité avec possibilité d’un ajout de variable font unique.
- **Composants** : cartes, badges, boutons minimalistes (arrondis doux, ombres discrètes).

---

## 5. Architecture technique

### ⚙️ Structure monorepo

```
webwatcher/
├── apps/
│   ├── frontend/   → Nuxt 3 + Tailwind v4 (UI/dashboard)
│   └── backend/    → FastAPI (API scraping, hooks, notifs)
├── packages/
│   └── ui/         → Design system DIY (tokens + composants)
├── infra/
│   ├── nginx/      → Reverse proxy + headers sécurité
│   ├── docker-compose.yml → profils dev/prod
│   └── Makefile    → raccourcis build/run
└── .env.{dev,prod} → gestion des secrets
```

### 🖥️ Frontend (Nuxt 3 + Tailwind v4)

- Affichage des items filtrés (type « inbox de veille »).
- CRUD futur pour gérer feeds et topics.
- Intégration design system DIY (tokens CSS).
- Performances : SSR, SWR, caching, images optimisées.

### 🔐 Backend (FastAPI)

- Endpoints : `/api/health`, `/api/hook/run` (déclencheurs sécurisés).
- Intégration runners de scraping (RSS, sites custom).
- Notifications via API Telegram + Brevo.
- Persistance SQLite (MVP) → PostgreSQL (V1 SaaS).
- Sécurité : CORS restrictif, secret API, rate-limit.

### 🌐 Infra (Docker + Nginx)

- Deux profils distincts : Dev (hot reload, volumes montés) et Prod (images optimisées).
- Nginx en prod : TLS (Let’s Encrypt), HSTS, CSP stricte, cache statique.
- Cron hôte : déclenchement éco-sobre (pas de conteneur qui tourne inutilement).

---

## 6. Fonctionnalités prévues

### MVP (Étape 1)

- Ingestion RSS/Atom.
- Scoring thématique (`topics.yaml`).
- Notifs Telegram (instant) + Digest email (Brevo).
- Stockage SQLite.

### V1 (Étape 2)

- Multi-utilisateurs, authentification.
- Dashboard UI (inbox de veille).
- CRUD Feeds/Topics via interface.
- Plans freemium (Stripe).

### V1.5 (Étape 3)

- Résumés automatiques IA.
- Suggestions de posts LinkedIn.
- Intégrations API (Reddit, HN, WTTJ, MakeSense).
- Collaboration (partage de veille).

---

## 7. Exigences de sécurité

- HTTPS obligatoire (TLS).
- Headers sécurité (CSP, HSTS, X-Frame-Options, `nosniff`).
- Stockage des secrets en `.env` non versionné.
- Limitation des dépendances (images `alpine`/`slim`).
- Rate limiting API.
- Authentification JWT (V1).

---

## 8. Planning indicatif

- **Semaine 1–2** : MVP interne.
- **Semaine 3–6** : V1 SaaS (multi-user + dashboard).
- **Semaine 7–10** : V1.5 Premium (IA + intégrations).

---

## ✅ Conclusion

WebWatcher est conçu comme un radar de veille sobre et intelligent, d’abord pour un usage interne (gain de temps personnel), avec un potentiel d’évolution vers un SaaS niche destiné aux freelances, agences et associations à impact. Sa force : simplicité, accessibilité, éco-conception et orientation UX, là où les outils existants sont souvent complexes, chers et lourds.

---

## 9. Implémentation du MVP

L’implémentation initiale se trouve dans `apps/backend` et fournit l’ingestion RSS, le scoring thématique et les notifications Telegram/Brevo décrits dans le cahier des charges.

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Configurer ensuite un fichier `.env` (un exemple est fourni dans `.env.dev`).

### Commandes utiles

```bash
python -m apps.backend.app.cli initdb   # Initialise la base SQLite
python -m apps.backend.app.cli ingest   # Lance l’ingestion + notifications Telegram
python -m apps.backend.app.cli digest   # Génère un digest email Brevo
uvicorn apps.backend.app.main:app --reload
```

### Configuration

- `config/topics.yaml` : règles de scoring et mots-clés.
- `config/feeds.yaml` : flux surveillés.
- Variables d’environnement `WEBWATCHER_*` pour les secrets (Telegram, Brevo, etc.).

### Tests

```bash
pytest
```

