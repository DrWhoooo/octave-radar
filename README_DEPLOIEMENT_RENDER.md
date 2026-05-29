# Octave Radar - Déploiement GitLab + Render

## Objectif

CRM en ligne + imports LinkedIn + actualités ciblées, sans GitHub Actions.

## 1. Créer le dépôt GitLab

1. Va sur GitLab.
2. Crée un nouveau projet privé : `octave-radar`.
3. Upload tous les fichiers du pack à la racine du dépôt.

## 2. Supabase

Dans Supabase SQL Editor, lance :

```txt
sql/001_bootstrap.sql
```

## 3. Render

1. Crée un compte Render.
2. New → Blueprint.
3. Connecte le dépôt GitLab.
4. Render lit `render.yaml`.
5. Renseigne les secrets :
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`

Le Blueprint crée :
- un Web Service Streamlit `octave-radar-crm`
- un Cron Job `octave-radar-linkedin-import`
- un Cron Job `octave-radar-targeted-news`

## 4. Validation

Dans le CRM, onglet Debug :
- staging total
- staging promoted
- contacts linkedin_file
- programs detail

## 5. Règles de sécurité

- Pas de GitHub Actions.
- Pas de scraping LinkedIn direct.
- LinkedIn = fichier/export → staging → promotion.
- Web news = seulement comptes ciblés.
