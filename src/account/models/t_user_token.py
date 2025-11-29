from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class TokenTypes(models.TextChoices):
    ACTIVATION = "AC", "アカウント有効化"
    PASSWORD_RESET = "PR", "パスワードリセット"
    EMAIL_CHANGE = "EC", "メールアドレス変更確認"


# ユーザ発行トークントラン
class T_UserToken(BaseModel):
    # Fields
    # ID (BIGINT PRIMARY KEY) はDjangoが自動で付与
    # ユーザマスタ
    m_user = models.ForeignKey(
        "account.M_User",
        db_column="m_user_id",
        verbose_name="ユーザマスタ",
        db_comment="ユーザマスタ",
        on_delete=models.CASCADE,
        # 逆参照名を定義(例: m_user_instance.user_tokens/通常参照はt_user_token_instance.m_user(_id)で取得可能)
        related_name="user_tokens",
    )
    # トークン種別
    token_type = models.CharField(
        db_column="token_type",
        verbose_name="トークン種別",
        db_comment="トークン種別",
        max_length=2,
        choices=TokenTypes.choices,
    )
    # トークンハッシュ（SHA256など）
    token_hash = models.CharField(
        db_column="token_hash",
        verbose_name="トークンハッシュ（SHA256など）",
        db_comment="トークンハッシュ（SHA256など）",
        max_length=64,
        db_index=True,
        unique=True,
    )
    # トークン有効期限
    expired_at = models.DateTimeField(
        db_column="expired_at",
        verbose_name="トークン有効期限",
        db_comment="トークン有効期限",
        db_index=True,
    )
    # トークン無効化日時
    revoked_at = models.DateTimeField(
        db_column="revoked_at",
        verbose_name="トークン無効化日時",
        db_comment="トークン無効化日時",
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
        db_table = "t_user_token"
        db_table_comment = "ユーザ発行トークントラン"
        verbose_name = "ユーザ発行トークントラン"
        verbose_name_plural = "ユーザ発行トークントラン"

    def __str__(self):
        return f"{self.m_user}/{self.token_hash[:10]}..."
