from django.db import models

from core.models import BaseModel


class failureReasons(models.TextChoices):
    PASSWORD_MISMATCH = "PASSWORD_MISMATCH", "パスワード不一致"
    LOCKED = "LOCKED", "アカウントロック中"
    # MFA_FAILED = "MFA_FAILED", "2段階認証失敗"


class T_LoginHisory(BaseModel):
    # Consts
    # Fields
    # ID (BIGINT PRIMARY KEY) はDjangoが自動で付与

    # ユーザマスタ（ユーザー退会後も履歴を残すためSET_NULL）
    m_user = models.ForeignKey(
        "account.M_User",
        db_column="m_user_id",
        verbose_name="ユーザマスタ",
        db_comment="ユーザマスタ",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        # 逆参照名を定義(例: m_user_instance.login_histories/通常参照はt_login_history_instance.m_user(_id)で取得可能)
        related_name="login_histories",
    )
    # ログイン実行時の入力値（メールアドレス/ユーザーID）
    login_identifier = models.CharField(
        max_length=255,
        verbose_name="ログイン試行識別子",
        db_comment="ログイン試行識別子",
    )
    # 成功フラグ
    is_successful = models.BooleanField(
        verbose_name="成功フラグ", db_comment="成功フラグ", db_index=True
    )
    # ログイン失敗理由コード
    failure_reason = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="ログイン失敗理由コード",
        db_comment="ログイン失敗理由コード",
        choices=failureReasons.choices,
    )
    # IPアドレス
    ip_address = models.CharField(
        max_length=45,
        null=True,
        blank=True,
        verbose_name="IPアドレス",
        db_comment="IPアドレス",
        help_text="クライアントのIPアドレス",
    )
    # クライアント情報
    user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name="ユーザーエージェント",
        help_text="クライアントのブラウザ/OS情報",
        db_comment="ユーザーエージェント",
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

    # テーブル名
    class Meta:
        db_table = "t_login_history"
        db_table_comment = "ログイン履歴トラン"
        verbose_name = "ログイン履歴トラン"
        verbose_name_plural = "ログイン履歴トラン"
        # ログイン試行が多い場合、created_atとis_successfulで複合インデックスを貼ると効率が良い
        # indexes = [models.Index(fields=['created_at', 'is_successful'])]

    def __str__(self):
        return f"{self.m_user_id if self.m_user_id.user_id else '未認証'} - {self.created_at}"
