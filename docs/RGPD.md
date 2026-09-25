# 🛡️ Registre des traitements — Le Fléchoir

> Registre simplifié (modèle de la CNIL) des données personnelles traitées par le site. Il tient avec la [page de confidentialité](../frontend/src/app/privacy/page.tsx) : chaque traitement ici y figure, et inversement. Tout nouveau champ mesuré s'ajoute aux deux ([ADR 0016](adr/0016-mesure-d-usage-sans-cookie.md)).
> Dernière mise à jour : 25 septembre 2026.

## Responsable du traitement

L'éditeur du site, un particulier, à titre non professionnel. Son identité n'est pas publiée (LCEN, art. 6, III, 2) ; contact : `contact@leflechoir.fr`.

## Traitements

| # | Traitement | Personnes | Données | Finalité | Base légale | Durée | Où |
|---|------------|-----------|---------|----------|-------------|-------|----|
| 1 | Comptes | Titulaires d'un compte | Adresse e-mail, mot de passe haché (bcrypt), date de confirmation de l'adresse | Fournir le service : se connecter, retrouver ses données | Contrat (art. 6.1.b) | Tant que le compte existe ; suppression immédiate à la demande ; compte sans connexion depuis 3 ans supprimé, après un e-mail un mois avant | Base PostgreSQL (OVH, France) |
| 2 | Dictionnaires et grilles | Titulaires d'un compte | Mots, définitions, grilles, notes | Conserver le travail de l'utilisateur | Contrat (art. 6.1.b) | Comme le compte | Base PostgreSQL (OVH, France) |
| 3 | Session | Titulaires d'un compte | Cookies de session (JWT), liste des jetons révoqués | Rester connecté, se déconnecter | Contrat ; cookies strictement nécessaires, sans consentement | 7 jours au plus | Navigateur ; base |
| 4 | E-mails du compte | Titulaires d'un compte | Adresse e-mail, lien signé | Confirmer l'adresse, changer un mot de passe oublié | Contrat (art. 6.1.b) | Selon Brevo (journal d'envoi) | Brevo (France) |
| 5 | Protection contre les abus | Tout visiteur | Adresse IP | Limiter le nombre de requêtes | Intérêt légitime (art. 6.1.f) | En mémoire, une heure au plus | Serveur (OVH) |
| 6 | Journaux techniques | Tout visiteur | Adresse IP, date, méthode, chemin sans paramètres, statut, durée, identifiant de requête | Diagnostiquer une panne ou une attaque | Intérêt légitime (art. 6.1.f) | 14 jours (rotation des journaux Docker, #117) | Serveur (OVH) |
| 7 | Rapports d'erreur | Visiteur touché par une erreur | Page ou action en cause, pile d'appel ; ni IP, ni cookie, ni corps de requête | Corriger les pannes | Intérêt légitime (art. 6.1.f) | 90 jours au plus (réglage du projet Sentry) | Sentry (UE) |
| 8 | Sauvegardes | Titulaires d'un compte | Copie chiffrée de la base (traitements 1 à 3) | Restaurer après un incident | Intérêt légitime (art. 6.1.f) | 30 jours | Cloudflare R2 (UE) |
| 9 | Messages de contact | Qui écrit à `contact@` ou `securite@` | Adresse e-mail, message | Répondre, suivre la demande | Intérêt légitime (art. 6.1.f) | Un an après le dernier échange | Cloudflare Email Routing, puis la messagerie de l'éditeur |

Ce qui n'est **pas** traité : les recherches, les grilles générées sans être conservées, toute mesure d'audience (jusqu'à [ADR 0016](adr/0016-mesure-d-usage-sans-cookie.md), qui ajoutera sa ligne ici et dans la page de confidentialité), la publicité.

## Sous-traitants (art. 28)

| Sous-traitant | Rôle | Localisation des données | Garanties |
|---------------|------|--------------------------|-----------|
| OVH SAS | Serveur (VPS), base de données | France | Contrat de sous-traitance (DPA) des conditions générales OVH |
| Cloudflare, Inc. | Pages du site, tunnel vers le serveur, DNS, R2 (sauvegardes), Email Routing | UE et États-Unis | DPA Cloudflare ; certifié Data Privacy Framework ; clauses contractuelles types |
| Brevo (Sendinblue SAS) | Envoi des e-mails du compte | France | DPA Brevo |
| Sentry (Functional Software, Inc.) | Rapports d'erreur | UE (région `de`) | DPA Sentry ; certifié Data Privacy Framework |

La messagerie qui reçoit les messages de contact, derrière Email Routing, est aussi un sous-traitant : la nommer ici et dans la page de confidentialité.

## Droits des personnes

Par `contact@leflechoir.fr`, depuis l'adresse du compte ; réponse sous un mois. Accès, rectification et effacement se font aussi dans l'application (Mon compte, Dictionnaires, Mes grilles). Portabilité : export des grilles (fichier de travail) ; un export complet du compte reste à faire si la demande arrive.

## Sécurité

Voir [SECURITY.md](SECURITY.md) : mots de passe hachés, cookies httpOnly, CSP, base sans port publié, sauvegardes chiffrées (age), accès au serveur par clé.

## À faire avant l'ouverture

- Rotation des journaux Docker à 14 jours (#117).
- Régler la rétention du projet Sentry à 90 jours au plus.
- Suppression des comptes inactifs depuis 3 ans, avec e-mail de prévenance (la date de dernière connexion arrive avec #116).
