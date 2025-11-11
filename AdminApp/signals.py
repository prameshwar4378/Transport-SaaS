# Add this in signals.py or at the bottom of models.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Company, CompanySettings

@receiver(post_save, sender=Company)
def create_company_settings(sender, instance, created, **kwargs):
    if created:
        CompanySettings.objects.get_or_create(company=instance)

@receiver(post_save, sender=Company)
def save_company_settings(sender, instance, **kwargs):
    instance.settings.save()