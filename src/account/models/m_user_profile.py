from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


# ユーザプロフィールマスタ
class M_UserProfile(BaseModel):
    # Consts
    # Fields
    # ID (BIGINT PRIMARY KEY) はDjangoが自動で付与

    # ユーザマスタ
    m_user = models.OneToOneField(
        "account.M_User",
        db_column="m_user_id",
        verbose_name="ユーザマスタ",
        db_comment="ユーザマスタ",
        on_delete=models.CASCADE,
        primary_key=True,
        # 逆参照名を定義(例: m_user_instance.user_profile/通常参照はm_user_profile_instance.m_user(_id)で取得可能)
        related_name="user_profile",
    )
    # 表示名
    display_name = models.CharField(
        db_column="display_name",
        verbose_name="表示名",
        db_comment="表示名",
        max_length=64,
        null=True,
        blank=True,
    )
    # --- 各テーブル共通(AbstractBaseModelは列順が変わってしまうので使用しない) ---
    created_by = models.DecimalField(
        db_column="created_by",
        verbose_name="作成者/id",
        db_comment="作成者/id",
        decimal_places=0,
        max_digits=20,
        null=True,
    )
    created_at = models.DateTimeField(
        db_column="created_at",
        verbose_name="作成日時",
        db_comment="作成日時",
        null=True,
        blank=True,
    )
    created_method = models.CharField(
        db_column="created_method",
        verbose_name="作成処理",
        db_comment="作成処理",
        max_length=128,
        null=True,
        blank=True,
    )
    updated_by = models.DecimalField(
        db_column="updated_by",
        verbose_name="更新者/id",
        db_comment="更新者/id",
        decimal_places=0,
        max_digits=20,
        null=True,
    )
    updated_at = models.DateTimeField(
        db_column="updated_at",
        verbose_name="更新日時",
        db_comment="更新日時",
        null=True,
        blank=True,
    )
    updated_method = models.CharField(
        db_column="updated_method",
        verbose_name="更新処理",
        db_comment="更新処理",
        max_length=128,
        null=True,
        blank=True,
    )
    deleted_at = models.DateTimeField(
        db_column="deleted_at",
        verbose_name="削除日時",
        db_comment="削除日時",
        null=True,
        blank=True,
        db_default=None,
        default=None,
    )
    # --- 各テーブル共通 ---

    # django-simple-historyを使用
    history = HistoricalRecords()

    # テーブル名
    class Meta:
        db_table = "m_user_profile"
        db_table_comment = "ユーザプロフィールマスタ"
        verbose_name = "ユーザプロフィールマスタ"
        verbose_name_plural = "ユーザプロフィールマスタ"

    def __str__(self):
        return f"{self.m_user}"
