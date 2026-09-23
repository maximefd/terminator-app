# DANS backend/mailer.py
"""
E-mails transactionnels : confirmer son adresse, changer un mot de passe oublié
([ADR 0014](../docs/adr/0014-emails-du-compte.md)).

`MAIL_BACKEND` choisit comment un message part :
- « console » (défaut) : il est écrit dans le journal de l'API, rien n'est envoyé. En production, un lien
  de mot de passe lisible dans un journal serait une faille : l'API l'y signale au démarrage ;
- « smtp » : un serveur SMTP — Mailpit en développement (docker compose, http://localhost:8025), le relais du
  prestataire en production ;
- « memory » : gardé dans `app.extensions["sent_emails"]`, pour les tests.
"""

import logging
import smtplib
from email.message import EmailMessage

from flask import current_app

MAIL_BACKENDS = ("console", "smtp", "memory")


def send_email(to: str, subject: str, body: str) -> bool:
    """Envoie un message texte. Renvoie False si l'envoi échoue : l'appelant décide quoi en dire."""
    config = current_app.config
    message = EmailMessage()
    message["From"] = config["MAIL_FROM"]
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    backend = config["MAIL_BACKEND"]
    try:
        if backend == "memory":
            current_app.extensions.setdefault("sent_emails", []).append(message)
        elif backend == "smtp":
            with smtplib.SMTP(config["SMTP_HOST"], config["SMTP_PORT"], timeout=10) as smtp:
                if config["SMTP_STARTTLS"]:
                    smtp.starttls()
                if config["SMTP_USER"]:
                    smtp.login(config["SMTP_USER"], config["SMTP_PASSWORD"])
                smtp.send_message(message)
        else:
            logging.info("E-mail non envoyé (MAIL_BACKEND=console) — à %s, « %s » :\n%s", to, subject, body)
        return True
    except (OSError, smtplib.SMTPException):
        # Le détail (serveur injoignable, identifiants refusés) reste dans le journal
        logging.exception("Envoi de l'e-mail « %s » impossible", subject)
        return False
