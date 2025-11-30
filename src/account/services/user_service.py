import hashlib
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from account.exceptions import (
    TokenExpiredOrNotFoundException,
    UserAlreadyActiveException,
)

# account/必要なモデルとリポジトリをインポート
from account.models.t_user_token import TokenTypes
from account.repositories.m_user_profile_repository import M_UserProfileRepository
from account.repositories.m_user_repository import M_UserRepository
from account.repositories.t_user_token_repository import T_UserTokenRepository
from core.consts import APP_NAME

User = get_user_model()


class UserService:
    """
    ユーザーのライフサイクル（作成、有効化、更新、退会）に関する
    ビジネスロジックを担うクラス
    """

    def __init__(self):
        # 必要なRepositoryを依存性注入
        self.user_repo = M_UserRepository()
        self.profile_repo = M_UserProfileRepository()
        self.token_repo = T_UserTokenRepository()

    # ------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------
    def send_activation_email(self, m_user_instance: User, token_value: str):
        """
        アクティベーションメールの送信処理 (Siteフレームワーク使用例)
        """

        # 1. Siteフレームワークからドメインを取得
        current_site = Site.objects.get_current()
        domain = current_site.domain

        # 2. Viewからスキーム（http/https）を取得し View から渡すのがベストですが、
        #    Siteフレームワーク内で完結させるため、ここでは強制的に https とする
        scheme = "https" if not settings.DEBUG else "http"

        # 3. URLパターン名からパスを逆引き (例: /account/user/token/activation/)
        path = reverse("account:activate", kwargs={"token_value": token_value})

        # 4. 絶対URLを構築
        activation_url = f"{scheme}://{domain}{path}"

        # メール本文に利用
        subject = f"【{APP_NAME}】仮登録完了のお知らせ"
        message = f"{APP_NAME}にご登録いただきありがとうございます。次のリンクをクリックしてアカウントを有効化してください。\n {activation_url}"
        from_email = settings.EMAIL_FROM
        recipient_list = [
            m_user_instance.email,
        ]
        send_mail(subject, message, from_email, recipient_list)
        return True

    # ------------------------------------------------------------------
    # ユーザ新規登録処理
    # ------------------------------------------------------------------
    @transaction.atomic
    def register_new_user(self, email: str, password: str, display_name: str) -> User:
        """
        ユーザー新規作成時に必要な一連の処理を実行
        Args:
            email (str): ユーザーのメールアドレス
            password (str): パスワード（ハッシュ化される）
            display_name (str, optional): プロフィール表示名
        Returns:
            User: 作成されたユーザーインスタンス
        """
        # 1. M_Userの作成 (User.objects.create_userはリポジトリのメソッド経由で呼ぶ)
        m_user_instance = self.user_repo.create_user_with_password(
            email=email, password=password
        )

        # M_UserProfileがシグナルで作成された後、display_nameを更新
        # (シグナルが動かないことは起こり得ないので冗長となる存在しないかのチェックは行わない)
        if display_name:
            # M_UserProfileのリポジトリを使用して更新
            # M_UserとM_UserProfileは1:1のため、M_UserインスタンスからM_UserProfileを取得し更新
            m_user_profile_instance = self.profile_repo.get_by_user_id(
                m_user_instance.pk
            )
            if m_user_profile_instance:
                # profile_repoのupdateメソッドを使用
                self.profile_repo.update(
                    m_user_profile_instance, display_name=display_name
                )

        # 2. T_UserToken(アクティベーション)レコードの作成
        raw_token_value = os.urandom(32).hex()
        token_hash = hashlib.sha256(raw_token_value.encode()).hexdigest()
        expiry_seconds = settings.TOKEN_EXPIRY_SECONDS.get("activation")
        expires_at = timezone.now() + timezone.timedelta(hours=expiry_seconds)

        # T_UserTokenRepositoryのcreateメソッドを使用
        self.token_repo.create(
            m_user=m_user_instance,
            token_hash=token_hash,
            type=TokenTypes.ACTIVATION,
            expires_at=expires_at,
        )

        # 3. アクティベーションメールの送信
        self.send_activation_email(m_user_instance, raw_token_value)
        return m_user_instance

    # ------------------------------------------------------------------
    # ユーザアクティベーション処理
    # ------------------------------------------------------------------
    @transaction.atomic
    def activate_user(self, raw_token_value: str) -> User:
        """
        アクティベーションリンクに含まれる生トークンを使用してユーザーを有効化する。
        Args:
            raw_token_value (str): URLから取得した生トークン値
        Returns:
            User: 有効化されたユーザーインスタンス
        Raises:
            TokenExpiredOrNotFoundException: トークンが見つからないか、期限切れの場合
            UserAlreadyActiveException: ユーザーが既に有効な場合
        """
        # 1. 生トークンをDBに保存されている形式（ハッシュ値）に変換
        token_hash = hashlib.sha256(raw_token_value.encode()).hexdigest()
        now = timezone.now()

        # 2. トークンを検索（ハッシュ値、種別、未期限切れ、未削除を条件とする）
        token_instance = self.token_repo.get_alive_one_or_none(
            token_hash=token_hash,
            type=TokenTypes.ACTIVATION,
            expires_at__gt=now,  # 現在時刻より期限が未来であること
        )

        if not token_instance:
            # トークンが存在しない、または期限切れ
            raise TokenExpiredOrNotFoundException(
                "有効なアクティベーション・トークンが見つかりません。"
            )

        m_user_instance = token_instance.m_user

        # 3. ユーザーの状態チェック
        if m_user_instance.is_active:
            # トークンが見つかったがユーザーは既にアクティブ
            # この場合も、セキュリティのため使用済みトークンとして無効化する
            self.token_repo.soft_delete(token_instance)
            raise UserAlreadyActiveException("アカウントは既に有効化されています。")

        # 4. ユーザーをシステム的にログイン可能(アクティブ)にする
        # user_repoのupdateメソッドを使用し、is_activeを更新
        updated_user = self.user_repo.update(
            m_user_instance,
            is_active=True,
        )

        # 5. 使用済みのトークンを無効化（論理削除）
        self.token_repo.soft_delete(token_instance)

        return updated_user
