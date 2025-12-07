from datetime import datetime, timedelta

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from account.models import M_User, M_UserProfile


@receiver(post_save, sender=M_User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Userモデルが保存された後（post_save）、
    かつインスタンスが新規作成された場合（created=True）にM_UserProfileを自動作成する。
    """
    if created:
        # UserProfileを作成し、Userインスタンスと紐付ける
        # display_nameなどのフィールドには、初期値を設定
        M_UserProfile.objects.create(
            m_user=instance,
            display_name=(
                instance.email.split("@")[0] if instance.email else "新規ユーザー"
            ),
            created_by=instance,
            updated_by=instance,
            created_method="Signal:create_user_profile",
            updated_method="Signal:create_user_profile",
        )
