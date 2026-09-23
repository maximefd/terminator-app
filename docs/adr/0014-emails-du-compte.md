# 0014 — E-mails du compte : liens signés, SMTP, confirmation non bloquante

- Statut : acceptée
- Date : 2026-09-23

## Contexte

- Un utilisateur qui oublie son mot de passe perd son compte : rien ne permet de le changer. [SECURITY.md](../SECURITY.md) le notait comme limite « avant ouverture à d'autres utilisateurs ».
- Rien ne prouve non plus qu'une adresse appartient à celui qui l'a saisie : on peut créer un compte au nom d'une adresse qui n'est pas la sienne.
- L'[ADR 0013](0013-cible-hebergement-production.md) prévoit un prestataire d'e-mails (Brevo, offre gratuite) pour la production. Il ne doit rien coûter en développement, et rien ne doit partir par erreur depuis un poste de dev.

## Décision

1. **Des liens signés et datés, pas de table.** Le lien porte l'identifiant du compte, signé avec `SECRET_KEY` (itsdangerous), avec un sel propre à chaque usage : un lien de confirmation ne peut pas servir à changer un mot de passe. Voir `backend/account_links.py`.
   - **Mot de passe** : valable **une heure** et **une seule fois**. Le lien porte une empreinte du hash du mot de passe actuel ; dès que le mot de passe change, l'empreinte ne correspond plus.
   - **Confirmation d'adresse** : valable **7 jours**, et seulement pour l'adresse qu'il nomme.
2. **La confirmation n'est pas bloquante.** Un compte non confirmé fonctionne normalement ; « Mon compte » le signale et permet de redemander le lien. Changer son mot de passe par e-mail confirme aussi l'adresse. Colonne `user.email_verified_at` (migration `0005`) : les comptes existants ne sont pas confirmés.
3. **« Mot de passe oublié » ne révèle rien** : même réponse que le compte existe ou non, et que l'envoi réussisse ou non. L'inscription révèle déjà qu'une adresse est prise (409, limite acceptée dans SECURITY.md), mais cette route-ci n'en rajoute pas.
4. **Un envoi par SMTP, choisi par `MAIL_BACKEND`** (`backend/mailer.py`) :
   - `console`, par défaut : le message est écrit dans le journal, rien ne part. C'est le mode des tests unitaires ;
   - `smtp` : en développement, **Mailpit** dans docker compose (http://localhost:8025) capture tout et n'envoie rien ; en production, le relais SMTP du prestataire. Pas de SDK propre au prestataire : on en change en changeant quatre variables ;
   - `memory` : pour les tests.
5. **Limites de débit** : 5 envois par heure et par adresse IP (mot de passe oublié, lien redemandé), sinon l'API sert à arroser une boîte de réception. L'usage d'un lien suit la limite de la connexion.

## Conséquences

- Nouvelles routes : `POST /api/auth/password/forgot`, `/password/reset`, `/email/verify`, `/email/resend`. Nouveaux écrans : `/forgot-password`, `/reset-password`, `/verify-email`, et l'état de l'adresse dans « Mon compte ».
- `SECRET_KEY` signe désormais ces liens : la changer invalide tous les liens en cours, ce qui est sans gravité (on en redemande un).
- En production, `MAIL_BACKEND=console` écrirait les liens de mot de passe dans le journal : qui le lit pourrait prendre un compte. L'API l'y signale au démarrage, et la checklist de [SECURITY.md](../SECURITY.md) exige SMTP.
- Les parcours end-to-end lisent les e-mails dans Mailpit, service du job de CI : le lien reçu est vraiment celui qu'on ouvre.
- Pas de révocation des sessions ouvertes quand le mot de passe change : les jetons restent valables jusqu'à leur expiration (7 jours au plus). Limite déjà connue, traitée avec les cookies httpOnly (#28).
