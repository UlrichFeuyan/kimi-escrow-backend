"""
Service d'envoi d'emails professionnel pour Kimi Escrow
"""

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service centralisé pour l'envoi d'emails"""
    
    @staticmethod
    def send_password_reset_email(user, reset_code):
        """
        Envoie un email de réinitialisation de mot de passe avec template HTML
        """
        try:
            # Contexte pour le template
            context = {
                'user': user,
                'reset_code': reset_code,
                'current_year': timezone.now().year,
                'site_name': 'Kimi Escrow',
                'site_url': getattr(settings, 'SITE_URL', 'https://kimi-escrow.com'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@kimi-escrow.com'),
            }
            
            # Rendu du template HTML
            html_content = render_to_string('emails/password_reset.html', context)
            
            # Version texte de l'email (fallback)
            text_content = f"""
Bonjour {user.get_full_name()},

Vous avez demandé la réinitialisation de votre mot de passe sur Kimi Escrow.

Votre code de réinitialisation est : {reset_code}

Ce code expire dans 15 minutes pour votre sécurité.

Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.

Cordialement,
L'équipe Kimi Escrow

---
Cet email a été envoyé depuis une adresse automatisée.
© {timezone.now().year} Kimi Escrow. Tous droits réservés.
            """.strip()
            
            # Création de l'email
            subject = "🔐 Réinitialisation de votre mot de passe - Kimi Escrow"
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kimi-escrow.com')
            to_email = [user.email]
            
            # Email avec contenu HTML et texte
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=to_email,
            )
            
            # Ajout du contenu HTML
            email.attach_alternative(html_content, "text/html")
            
            # Envoi de l'email
            result = email.send(fail_silently=False)
            
            if result:
                logger.info(f"Email de réinitialisation envoyé à {user.email}")
                return True
            else:
                logger.error(f"Échec envoi email de réinitialisation à {user.email}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi email à {user.email}: {e}")
            return False
    
    @staticmethod
    def send_password_changed_notification(user):
        """
        Envoie une notification de changement de mot de passe réussi
        """
        try:
            context = {
                'user': user,
                'current_year': timezone.now().year,
                'site_name': 'Kimi Escrow',
                'timestamp': timezone.now(),
            }
            
            # Version texte simple pour la notification
            text_content = f"""
Bonjour {user.get_full_name()},

Votre mot de passe a été modifié avec succès le {timezone.now().strftime('%d/%m/%Y à %H:%M')}.

Si vous n'êtes pas à l'origine de cette modification, contactez immédiatement notre support.

Cordialement,
L'équipe Kimi Escrow
            """.strip()
            
            subject = "✅ Mot de passe modifié - Kimi Escrow"
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kimi-escrow.com')
            to_email = [user.email]
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=to_email,
            )
            
            result = email.send(fail_silently=False)
            
            if result:
                logger.info(f"Notification de changement de mot de passe envoyée à {user.email}")
                return True
            else:
                logger.error(f"Échec envoi notification à {user.email}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi notification à {user.email}: {e}")
            return False
    
    @staticmethod
    def send_welcome_email(user):
        """
        Envoie un email de bienvenue après inscription
        """
        try:
            text_content = f"""
Bienvenue sur Kimi Escrow !

Bonjour {user.get_full_name()},

Félicitations ! Votre compte a été créé avec succès sur Kimi Escrow.

Prochaines étapes :
1. Vérifiez votre numéro de téléphone
2. Complétez votre profil
3. Soumettez vos documents KYC pour des transactions sécurisées

Notre équipe est là pour vous accompagner 24h/7j.

Cordialement,
L'équipe Kimi Escrow
            """.strip()
            
            subject = "🎉 Bienvenue sur Kimi Escrow !"
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kimi-escrow.com')
            to_email = [user.email]
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=to_email,
            )
            
            result = email.send(fail_silently=False)
            
            if result:
                logger.info(f"Email de bienvenue envoyé à {user.email}")
                return True
            else:
                logger.error(f"Échec envoi email de bienvenue à {user.email}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi email de bienvenue à {user.email}: {e}")
            return False


# Fonction utilitaire pour rétrocompatibilité
def send_notification_email(to_email, subject, message, **kwargs):
    """
    Fonction utilitaire pour l'envoi d'emails simples (rétrocompatibilité)
    """
    try:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kimi-escrow.com')
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=from_email,
            to=[to_email],
        )
        
        result = email.send(fail_silently=False)
        
        if result:
            logger.info(f"Email envoyé à {to_email}: {subject}")
            return True
        else:
            logger.error(f"Échec envoi email à {to_email}")
            return False
            
    except Exception as e:
        logger.error(f"Erreur envoi email à {to_email}: {e}")
        return False
