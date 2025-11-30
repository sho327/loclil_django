from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class M_UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("email is not found.")
        user = self.model(
            email=self.normalize_email(email),
            **extra_fields,
        )
        user.set_password(password)
        # ユーザーモデルのデフォルト値を明示的に設定（省略されているが安全のため）
        user.is_staff = extra_fields.pop("is_staff", False)
        user.is_active = extra_fields.pop("is_active", False)  # 初期は非アクティブ
        user.is_superuser = extra_fields.pop("is_superuser", False)
        # user.is_email_verified = extra_fields.pop("is_email_verified", False)
        user.status_code = extra_fields.pop("status_code", AccountStatus.ACTIVE)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("email is not found.")
        user = self.model(
            email=self.normalize_email(email),
            **extra_fields,
        )
        user.set_password(password)
        # 管理者権限の設定
        user.is_staff = True
        user.is_active = True
        user.is_superuser = True
        user.status_code = AccountStatus.ACTIVE
        user.save(using=self._db)
        return user


# アカウントステータスコード
# アカウントの論理的なライフサイクル（最終的な利用可否）
# 一時的な認証プロセスではなく、ユーザーの永続的な状態（退会、凍結、ロック）を示す
class AccountStatus(models.IntegerChoices):
    ACTIVE = 10, "アクティブ"
    TEMPORARY_LOCKED = 30, "一時ロック"
    FROZEN = 40, "永続凍結"
    WITHDRAWN = 99, "退会済み"


# ユーザーマスタ
class M_User(AbstractBaseUser, BaseModel, PermissionsMixin):
    """認証とコア情報を保持するモデル (Djangoの認証モデルを継承)"""

    # Consts
    # Fields
    # ID (BIGINT PRIMARY KEY) はDjangoが自動で付与

    # メールアドレス
    email = models.EmailField(
        db_column="email",
        verbose_name="メールアドレス",
        db_comment="メールアドレス",
        max_length=254,  # RFC推奨の長さ設定
        # unique=False,  # 論理削除を考慮し、unique=Trueは外す
    )
    # ステータスコード(認証に必須なためM_Userモデルに配置)
    status_code = models.IntegerField(
        db_column="status_code",
        verbose_name="ステータスコード",
        db_comment="ステータスコード",
        choices=AccountStatus.choices,
        db_default=AccountStatus.ACTIVE,
        default=AccountStatus.ACTIVE,
        db_index=True,
    )
    # ロック解除日時
    locked_until_at = models.DateTimeField(
        db_column="locked_until_at",
        verbose_name="ロック解除日時",
        db_comment="ロック解除日時",
        null=True,
        blank=True,
    )
    # パスワード最終更新日時
    password_updated_at = models.DateTimeField(
        db_column="password_updated_at",
        verbose_name="パスワード更新日時",
        db_comment="パスワード更新日時",
        null=True,
        blank=True,
    )
    # 初回ログインフラグ
    is_first_login = models.BooleanField(
        db_column="is_first_login",
        verbose_name="初回ログインであるかフラグ",
        db_comment="初回ログインであるかフラグ",
        db_default=True,
        default=True,
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
    # 以下Djangoの共通のユーザ認証を扱う上で設定の必須のため追加しておく(継承元/AbstractBaseUserで定義されているので、オーバライドしないと、列順がこの通りにならない)
    # ※パスワード
    password = models.CharField(
        db_column="password",
        verbose_name="パスワード",
        db_comment="パスワード",
        max_length=128,
    )
    # 最終ログイン
    last_login = models.DateTimeField(
        db_column="last_login",
        verbose_name="最終ログイン",
        db_comment="最終ログイン",
        null=True,
        blank=True,
    )
    # 有効フラグ(管理サイトに入れるか、その他Djangoパッケージで有効なユーザかの判定で使用される)
    is_active = models.BooleanField(
        db_column="is_active",
        verbose_name="有効フラグ",
        db_comment="有効フラグ",
        db_default=False,
        default=False,
    )
    # 一般ユーザフラグ(管理サイトに一般ユーザとして入れるか)
    is_staff = models.BooleanField(
        db_column="is_staff",
        verbose_name="一般ユーザフラグ",
        db_comment="一般ユーザフラグ",
        db_default=False,
        default=False,
    )
    # 管理者フラグ(管理サイトに管理者として入れるか)
    is_superuser = models.BooleanField(
        db_column="is_superuser",
        verbose_name="管理者フラグ",
        db_comment="管理者フラグ",
        db_default=False,
        default=False,
    )
    groups = models.ManyToManyField(
        blank=True,
        related_name="user_set",
        related_query_name="user",
        to="auth.Group",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        blank=True,
        related_name="user_set",
        related_query_name="user",
        to="auth.Permission",
        verbose_name="user permissions",
    )

    ### カスタム定義 ###
    # ユーザネームフィールド
    USERNAME_FIELD = "email"
    # REQUIRED_FIELDS = ["user_id"]
    # django-simple-historyを使用
    history = HistoricalRecords()

    # MetaSettings
    class Meta:
        db_table = "m_user"
        db_table_comment = "ユーザーマスタ"
        verbose_name = "ユーザーマスタ"
        verbose_name_plural = "ユーザーマスタ"
        constraints = [
            # アクティブな (is_active=True) かつ 未削除の (deleted_at__isnull=True) ユーザー間でのみ email, user_id がユニーク
            UniqueConstraint(
                fields=["email"],
                condition=Q(is_active=True, deleted_at__isnull=True),
                name="unique_active_email",
            ),
        ]

    def __str__(self):
        return f"{self.email}"
