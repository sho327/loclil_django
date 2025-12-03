import hashlib
import os
from typing import Any, Dict

from django.conf import settings
from django.contrib.auth import get_user_model

# 必要なDjango標準認証関数をインポート
# import django.contrib.auth.login はビュー層で行うため、ここでは不要
# セッション管理のためにSessionモデルをインポート（強制ログアウト用）
from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.db import IntegrityError as DjangoIntegrityError
from django.db import transaction
from django.utils import timezone

# Exception
from account.exceptions import (
    AccountLockedException,
    AuthenticationFailedException,
    PasswordResetTokenInvalidException,
)

# account/必要なモデルとリポジトリをインポート
from account.models.t_user_token import TokenTypes
from account.repositories.m_user_profile_repository import M_UserProfileRepository
from account.repositories.m_user_repository import M_UserRepository
from account.repositories.t_user_token_repository import T_UserTokenRepository
from core.auth_scheme.user_auth_backend import UserAuthBackend
from core.consts import APP_NAME
from core.exceptions import ExternalServiceError, IntegrityError  # コア例外をインポート

# from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class AuthService:
    """
    認証（ログイン、ログアウト）、認可、
    およびクレデンシャル管理（パスワードリセット等）を担うサービスクラス
    """

    def __init__(self):
        self.user_auth_backend = UserAuthBackend()
        self.user_repo = M_UserRepository()
        self.profile_repo = M_UserProfileRepository()
        self.token_repo = T_UserTokenRepository()

    # ------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------
    def _send_password_reset_email(self, user: User, token: str):
        """パスワードリセットメール送信の実装"""
        m_user_profile_instance = self.profile_repo.get_alive_one_or_none(
            m_user=user.pk
        )
        reset_url = f"http://localhost:8000/account/password_reset_confirm/{token}/"
        subject = f"【{APP_NAME}】パスワード再設定のご案内"
        message = (
            f"{m_user_profile_instance.display_name} 様\n\n"
            f"パスワード再設定のリクエストを受け付けました。\n"
            f"以下のリンクから新しいパスワードを設定してください（有効期限：1時間）。\n\n"
            f"{reset_url}\n\n"
            f"お心当たりがない場合は、このメールを破棄してください。"
        )
        try:
            send_mail(subject, message, settings.EMAIL_FROM, [user.email])
        except Exception as e:
            # send_mailはSMTP接続失敗など、様々なエラーを投げる可能性がある
            raise ExternalServiceError(
                message="パスワードリセットメールの送信に失敗しました。",
                details={"recipient": user.email, "internal_error": str(e)},
            )

    def _force_logout_all_sessions(self, user: User):
        """
        指定されたユーザーに関連付けられている全ての既存のセッションを強制的に無効化する。
        """
        # Djangoのセッションストアから、現在アクティブなセッションを全て取得
        sessions = Session.objects.filter(expire_date__gte=timezone.now())

        # ユーザーIDに紐づくセッションキーを特定し、削除
        for session in sessions:
            session_data = session.get_decoded()
            # セッションデータ内の認証ユーザーIDが一致するかチェック
            if str(session_data.get("_auth_user_id")) == str(user.pk):
                session.delete()

    # ------------------------------------------------------------------
    # ログイン処理
    # ------------------------------------------------------------------
    def login(self, email: str, password: str) -> User:
        """
        メールアドレスとパスワードで認証済みユーザーインスタンスを返す。
        ビュー層でこのユーザーを使い、セッションを確立する必要がある。
        Args:
            email (str): メールアドレス
            password (str): パスワード
        Returns:
            Dict[str, str]: {"access": "...", "refresh": "..."}
        Raises:
            AuthenticationFailedException: 認証失敗
            AccountLockedException: アカウントが無効（is_active=False）
        """
        # 1. Django標準のauthenticateを使って認証
        # (内部でcheck_passwordが行われる)
        user = self.user_auth_backend.authenticate(
            None, username=email, password=password
        )

        if user is None:
            # ユーザーが存在しないか、パスワードが不一致
            # セキュリティのため、どちらが間違っているかは教えない
            raise AuthenticationFailedException()

        # 2. アカウント状態のチェック (is_active)
        if not user.is_active:
            # 凍結、ロック、または退会済み
            raise AccountLockedException()

        # 3. 最終ログイン日時の更新
        # update_last_login(None, user) # Django標準関数を使う場合
        # またはリポジトリ経由で更新
        self.user_repo.update(user, last_login=timezone.now())

        return user  # 認証済みユーザーを返却

    # ------------------------------------------------------------------
    # パスワードリセット要求 (メール送信)
    # ------------------------------------------------------------------
    @transaction.atomic
    def request_password_reset(self, email: str) -> bool:
        """
        パスワードリセットメールを送信する。
        セキュリティ上の理由から、ユーザーが存在しなくてもエラーにはせずTrueを返す（列挙攻撃対策）。
        """
        # 1. ユーザー検索
        user = self.user_repo.get_alive_one_or_none(email=email)

        # ユーザーが存在しない、またはアクティブでない場合は何もしないが、
        # 攻撃者に悟られないよう正常終了を装う
        if not user or not user.is_active:
            return True

        try:
            # 2. リセットトークンの生成 (アクティベーションと同様のロジック)
            raw_token = os.urandom(32).hex()
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            expiry_seconds = settings.TOKEN_EXPIRY_SECONDS.get("password_reset")
            expired_at = timezone.now() + timezone.timedelta(hours=expiry_seconds)

            # 3. 既存のリセットトークンがあれば無効化する（オプション）
            # 【セキュリティ/利便性のトレードオフ】
            # 既存のトークンを無効化することで、ユーザーが誤って何度もリクエストした際に
            # どのメール（どのトークン）が有効か迷うのを防げる。
            # ただし、悪意のあるユーザーが連続リクエストで正規ユーザーの有効トークンを無効化する
            # Denial of Service (DoS) 攻撃の可能性もある。今回はコメントアウト。
            # # self.token_repo.invalidate_tokens_by_user(user, TokenTypes.PASSWORD_RESET)

            # 4. トークン保存
            self.token_repo.create(
                m_user=user,
                token_hash=token_hash,
                token_type=TokenTypes.PASSWORD_RESET,
                expired_at=expired_at,
            )

            # 5. メール送信
            self._send_password_reset_email(user, raw_token)

            return True

        except DjangoIntegrityError as e:
            # トークン保存時に発生しうるDBレベルのエラー（例: 外部キー制約）
            # DuplicationErrorはトークンでは考えにくいが、IntegrityErrorとして捕捉
            # ログ記録推奨
            raise IntegrityError(
                message="リセットトークン生成中にデータベース整合性エラーが発生しました。",
                details={"internal_message": str(e)},
            )
        except ExternalServiceError:
            # メール送信失敗の例外をそのまま View へ再送出
            raise
        except Exception as e:
            # その他の予期せぬエラー（DB接続エラーなど）
            # ログ記録推奨
            raise IntegrityError(
                message="リセット要求処理中に予期せぬエラーが発生しました。",
                details={"internal_message": str(e)},
            )

    # ------------------------------------------------------------------
    # パスワードリセット実行
    # ------------------------------------------------------------------
    @transaction.atomic
    def reset_password(self, raw_token: str, new_password: str) -> User:
        """
        トークンを検証し、パスワードを更新する。
        """
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        now = timezone.now()

        # 1. トークン検証
        token_instance = self.token_repo.get_alive_one_or_none(
            token_hash=token_hash,
            token_type=TokenTypes.PASSWORD_RESET,
            expired_at__gt=now,
        )

        if not token_instance:
            raise PasswordResetTokenInvalidException()

        user = token_instance.m_user

        try:
            # 2. パスワード更新 (ハッシュ化はset_passwordが担う)
            user.set_password(new_password)

            # 3. 情報更新 (パスワード更新日時など)
            self.user_repo.update(
                user,
                password=user.password,  # set_passwordでハッシュ化された値が入っている
                password_updated_at=now,
            )

            # 4. 使用済みトークンを無効化
            self.token_repo.soft_delete(token_instance)

            # 5. 【セキュリティ強化：全デバイスからの強制ログアウト（セッション切断）】
            # セッション認証に基づき、全セッションを削除する
            # SessionモデルにはUserへの直接的なリレーションがないため、セッションデータを解析して削除
            self._force_logout_all_sessions(user)

            return user

        except DjangoIntegrityError as e:
            # パスワード更新時のDBレベルのエラー（外部キーなど）
            # ログ記録推奨
            raise IntegrityError(
                message="パスワード更新中にデータベース整合性エラーが発生しました。",
                details={"internal_message": str(e)},
            )
        except Exception as e:
            # その他の予期せぬエラー（DB接続エラーなど）
            # ログ記録推奨
            raise IntegrityError(
                message="パスワードリセット処理中に予期せぬエラーが発生しました。",
                details={"internal_message": str(e)},
            )
