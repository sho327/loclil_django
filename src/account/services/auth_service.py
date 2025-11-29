import hashlib
import os
from typing import Any, Dict

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

# Exception
from account.exceptions import (
    AccountLockedException,
    AuthenticationFailedException,
    PasswordResetTokenInvalidException,
    UserNotFoundException,
)

# account/必要なモデルとリポジトリをインポート
from account.models.t_user_token import TokenTypes
from account.repositories.m_user_repository import M_UserRepository
from account.repositories.t_user_token_repository import T_UserTokenRepository
from core.consts import APP_NAME

User = get_user_model()


class AuthService:
    """
    認証（ログイン、ログアウト）、認可、
    およびクレデンシャル管理（パスワードリセット等）を担うサービスクラス
    """

    def __init__(self):
        self.user_repo = M_UserRepository()
        self.token_repo = T_UserTokenRepository()

    # ------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------
    def _send_password_reset_email(self, user: User, token: str):
        """パスワードリセットメール送信の実装"""
        reset_url = f"http://127.0.0.1:8000/account/password-reset/{token}/confirm/"
        subject = f"【{APP_NAME}】パスワード再設定のご案内"
        message = (
            f"{user.display_name} 様\n\n"
            f"パスワード再設定のリクエストを受け付けました。\n"
            f"以下のリンクから新しいパスワードを設定してください（有効期限：1時間）。\n\n"
            f"{reset_url}\n\n"
            f"お心当たりがない場合は、このメールを破棄してください。"
        )
        send_mail(subject, message, settings.EMAIL_FROM, [user.email])

    # ------------------------------------------------------------------
    # ログイン処理 (JWT発行)
    # ------------------------------------------------------------------
    def login(self, email: str, password: str) -> Dict[str, str]:
        """
        メールアドレスとパスワードでログインし、JWTトークンペアを返す。
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
        user = authenticate(email=email, password=password)

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

        # 4. JWTトークンの生成 (SimpleJWT利用)
        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

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

        # 2. リセットトークンの生成 (アクティベーションと同様のロジック)
        raw_token = os.urandom(32).hex()
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expiry_seconds = settings.TOKEN_EXPIRY_SECONDS.get("password_reset")
        expires_at = timezone.now() + timezone.timedelta(hours=expiry_seconds)

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
            type=TokenTypes.PASSWORD_RESET,
            expires_at=expires_at,
        )

        # 5. メール送信
        self._send_password_reset_email(user, raw_token)

        return True

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
            type=TokenTypes.PASSWORD_RESET,
            expires_at__gt=now,
        )

        if not token_instance:
            raise PasswordResetTokenInvalidException()

        user = token_instance.m_user

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

        # ------------------------------------------------------------------
        # 5. 【セキュリティ強化：全デバイスからの強制ログアウト（セッション切断）】
        #    パスワード変更により、不正アクセス者による他のセッション利用を防ぐために行う。
        #    ※ 現在は実装しないが、将来的な拡張ポイントとしてコメントで残す。
        # ------------------------------------------------------------------

        # ▼ 実現方法 1: リフレッシュトークンの削除 (推奨/ソフトコミット)
        #    T_UserTokenにリフレッシュトークンを保存している場合、
        #    そのユーザーIDに紐づく全てのリフレッシュトークンを削除する。
        #    # self.token_repo.invalidate_tokens_by_user(user, TokenTypes.REFRESH)

        # ▼ 実現方法 2: JWTアクセストークンのブラックリスト化 (即時切断/負荷高)
        #    SimpleJWTのブラックリスト機能（通常Redisなどのキャッシュを使用）を利用し、
        #    ユーザーの全JWTを強制的に失効させる。

        # ▼ 実現方法 3: 伝統的なDjangoセッションの削除
        #    django.contrib.sessions の機能を利用し、ユーザーに紐づくDB上の全セッションを削除する。
        #    # from django.contrib.sessions.models import Session
        #    # Session.objects.filter(expire_date__gte=timezone.now(), session_key__in=Session.objects.filter(session_key=user.pk).values_list('session_key', flat=True)).delete()
        # ------------------------------------------------------------------

        return user
