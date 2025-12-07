import hashlib
import os

# 必要なDjango標準のインポート
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import IntegrityError as DjangoIntegrityError
from django.db import transaction
from django.utils import timezone

from account.exceptions import (
    AccountLockedException,
    AuthenticationFailedException,
    PasswordResetTokenInvalidException,
    TokenExpiredOrNotFoundException,
    UserAlreadyActiveException,
)
from account.models.t_user_token import TokenTypes
from account.repositories.m_user_profile_repository import M_UserProfileRepository
from account.repositories.m_user_repository import M_UserRepository
from account.repositories.t_user_token_repository import T_UserTokenRepository
from core.auth_scheme.user_auth_backend import UserAuthBackend
from core.consts import LOG_METHOD
from core.exceptions import DuplicationError, ExternalServiceError, IntegrityError
from core.services.notification_service import NotificationService
from core.utils.common import generate_secure_token

User = get_user_model()


class AuthService:
    """
    認証（ログイン、ログアウト）、認可、
    およびクレデンシャル管理（パスワードリセット等）を担うサービスクラス
    【責務：ユーザー状態と資格情報の管理。外部通信は委譲する】
    """

    def __init__(self):
        self.user_auth_backend = UserAuthBackend()
        self.user_repo = M_UserRepository()
        self.profile_repo = M_UserProfileRepository()
        self.token_repo = T_UserTokenRepository()
        self.notification_service = NotificationService()

    # ------------------------------------------------------------------
    # Helper Methods (AuthService固有のヘルパーのみ残す)
    # ------------------------------------------------------------------
    def _force_logout_all_sessions(self, user: User):
        """
        指定されたユーザーに関連付けられている全ての既存のセッションを強制的に無効化する。
        """
        sessions = Session.objects.filter(expire_date__gte=timezone.now())

        for session in sessions:
            session_data = session.get_decoded()
            if str(session_data.get("_auth_user_id")) == str(user.pk):
                session.delete()

    # ------------------------------------------------------------------
    # ログイン処理
    # ------------------------------------------------------------------
    def login(self, email: str, password: str, process_name: str) -> User:
        """
        メールアドレスとパスワードで認証済みユーザーインスタンスを返す。
        """
        user = self.user_auth_backend.authenticate(
            None, username=email, password=password
        )

        if user is None:
            raise AuthenticationFailedException()

        if not user.is_active:
            raise AccountLockedException()

        self.user_repo.update(
            user, 
            last_login=timezone.now(), 
            updated_by=user, 
            updated_method=process_name
        )

        return user

    # ------------------------------------------------------------------
    # ユーザ新規登録処理
    # ------------------------------------------------------------------
    @transaction.atomic
    def register_new_user(self, email: str, password: str, display_name: str, process_name: str) -> User:
        """
        ユーザー新規作成時に必要な一連の処理を実行
        """
        try:
            # 1. M_Userの作成
            m_user_instance = self.user_repo.create_user_with_password(
                email=email, password=password
            )

            # M_UserProfileの更新
            if display_name:
                m_user_profile_instance = self.profile_repo.get_alive_one_or_none(
                    m_user=m_user_instance.pk
                )
                if m_user_profile_instance:
                    self.profile_repo.update(
                        m_user_profile_instance, 
                        display_name=display_name,
                        updated_by=m_user_instance,
                        updated_method=process_name
                    )

            # 2. T_UserToken(アクティベーション)レコードの作成
            raw_token_value = generate_secure_token(32)  # 32バイト = 64文字の16進数
            token_hash = hashlib.sha256(raw_token_value.encode()).hexdigest()
            expiry_seconds = settings.TOKEN_EXPIRY_SECONDS.get("activation")
            expired_at = timezone.now() + timezone.timedelta(hours=expiry_seconds)

            self.token_repo.create(
                m_user=m_user_instance,
                token_hash=token_hash,
                token_type=TokenTypes.ACTIVATION,
                expired_at=expired_at,
                created_by=m_user_instance,
                updated_by=m_user_instance,
                created_method=process_name,
                updated_method=process_name,
            )

            self.notification_service.send_activation_email(
                m_user_instance, raw_token_value
            )
            return m_user_instance

        except DjangoIntegrityError as e:
            if "UNIQUE constraint" in str(e) or "duplicate key" in str(e):
                raise DuplicationError(details={"field": "email"})
            raise IntegrityError(details={"db_error": str(e)})

        except ExternalServiceError:
            raise

        except Exception as e:
            # サービス層ではログ出力せず、例外を投げるだけ（ビュー層でログ出力）
            raise IntegrityError(
                message="登録処理中に予期せぬエラーが発生しました。",
                details={"internal_message": str(e)},
            )

    # ------------------------------------------------------------------
    # ユーザアクティベーション処理
    # ------------------------------------------------------------------
    @transaction.atomic
    def activate_user(self, raw_token_value: str, process_name: str) -> User:
        """
        アクティベーションリンクに含まれる生トークンを使用してユーザーを有効化する。
        """
        token_hash = hashlib.sha256(raw_token_value.encode()).hexdigest()
        now = timezone.now()

        token_instance = self.token_repo.get_alive_one_or_none(
            token_hash=token_hash,
            token_type=TokenTypes.ACTIVATION,
            expired_at__gt=now,
        )

        if not token_instance:
            # 例外クラスのデフォルトメッセージを使用
            raise TokenExpiredOrNotFoundException()

        m_user_instance = token_instance.m_user

        if m_user_instance.is_active:
            self.token_repo.soft_delete(
                instance=token_instance, 
                user=m_user_instance, 
                process_name=process_name,
            )
            # 例外クラスのデフォルトメッセージを使用
            raise UserAlreadyActiveException()

        updated_user = self.user_repo.update(
            m_user_instance,
            is_active=True,
            updated_by=m_user_instance,
            updated_method=process_name,
        )

        self.token_repo.soft_delete(
            instance=token_instance, 
            user=m_user_instance, 
            process_name=process_name,
        )

        return updated_user

    # ------------------------------------------------------------------
    # パスワードリセット要求 (メール送信)
    # ------------------------------------------------------------------
    @transaction.atomic
    def request_password_reset(self, email: str, process_name: str) -> bool:
        """
        パスワードリセットメールを送信する。
        """
        user = self.user_repo.get_alive_one_or_none(email=email)

        if not user or not user.is_active:
            return True

        try:
            # 2. リセットトークンの生成
            raw_token = generate_secure_token(32)  # 32バイト = 64文字の16進数
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            expiry_seconds = settings.TOKEN_EXPIRY_SECONDS.get("password_reset")
            expired_at = timezone.now() + timezone.timedelta(hours=expiry_seconds)

            # 3. トークン保存
            self.token_repo.create(
                m_user=user,
                token_hash=token_hash,
                token_type=TokenTypes.PASSWORD_RESET,
                expired_at=expired_at,
                created_by=user,
                updated_by=user,
                created_method=process_name,
                updated_method=process_name,
            )

            # 4. プロフィールから表示名を取得
            m_user_profile_instance = self.profile_repo.get_alive_one_or_none(
                m_user=user.pk
            )
            # NotificationServiceに渡すために表示名を取得
            display_name = (
                m_user_profile_instance.display_name
                if m_user_profile_instance
                else "お客様"
            )

            self.notification_service.send_password_reset_email(
                user=user,
                display_name=display_name,
                raw_token=raw_token,
            )

            return True

        except DjangoIntegrityError as e:
            raise IntegrityError(
                message="リセットトークン生成中にデータベース整合性エラーが発生しました。",
                details={"internal_message": str(e)},
            )
        except ExternalServiceError:
            raise
        except Exception as e:
            raise IntegrityError(
                message="リセット要求処理中に予期せぬエラーが発生しました。",
                details={"internal_message": str(e)},
            )

    # ------------------------------------------------------------------
    # パスワードリセット実行
    # ------------------------------------------------------------------
    @transaction.atomic
    def reset_password(self, raw_token: str, new_password: str, process_name: str) -> User:
        """
        トークンを検証し、パスワードを更新する。
        """
        # raw_tokenをハッシュ化して使用（バグ修正）
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        now = timezone.now()

        token_instance = self.token_repo.get_alive_one_or_none(
            token_hash=token_hash,
            token_type=TokenTypes.PASSWORD_RESET,
            expired_at__gt=now,
        )

        if not token_instance:
            raise PasswordResetTokenInvalidException()

        user = token_instance.m_user

        try:
            user.set_password(new_password)

            self.user_repo.update(
                user,
                password=user.password,
                password_updated_at=now,
                updated_by=user,
                updated_method=process_name,
            )

            self.token_repo.soft_delete(
                instance=token_instance,
                user=user,
                process_name=process_name,
            )
            self._force_logout_all_sessions(user)

            return user

        except DjangoIntegrityError as e:
            raise IntegrityError(
                message="パスワード更新中にデータベース整合性エラーが発生しました。",
                details={"internal_message": str(e)},
            )
        except Exception as e:
            raise IntegrityError(
                message="パスワードリセット処理中に予期せぬエラーが発生しました。",
                details={"internal_message": str(e)},
            )
