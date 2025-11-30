from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.db.models import Q

# --- 共通モジュール ---
from core.consts import LOG_METHOD
from core.decorators import logging_sql_queries
from core.utils.log_helpers import log_output_by_msg_id

UserModel = get_user_model()

"""
カスタムユーザ認証バックエンドクラス
メールアドレスを使用して認証を行う (username/user_idは廃止)
"""


class UserAuthBackend(BaseBackend):

    # ModelBackendは継承しない（ユーザーモデルとフィールド名が大きく異なるため）
    # ModelBackendの user_can_authenticate はBaseBackendにはないので、手動で実装するか
    # または、そのロジックを認証メソッド内に統合する (今回は統合)

    @logging_sql_queries
    # 識別子は常に 'username' として渡されるため、そのまま受け取る
    def authenticate(self, request, username=None, password=None, **kwargs):

        # 1. ログイン試行に使用された識別子 (メールアドレス) を取得
        # identifierは adminサイトから渡される 'username' を使用
        identifier = username

        # identifierがNoneの場合、管理サイトログインではない（カスタムフォームなどの可能性）ため、
        # emailフィールドを直接探すか、単純に None で返す
        if identifier is None:
            # 識別子がない場合は認証をスキップ
            return None

        try:
            # 2. メールアドレスでのみユーザーを検索 (username フィールドのロジックは削除)
            # email フィールドでのみフィルタリング
            user_model_instance = UserModel.objects.get(
                email=identifier,
                # ユーザーが有効な状態（is_active=True）であることを認証時に確認する
                is_active=True,
            )

        except UserModel.DoesNotExist:
            # ユーザーが存在しない場合、または is_active=False の場合
            log_output_by_msg_id(
                log_id="MSGE101",
                params=[identifier, "（パスワードはログに残さない）"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            return None
        except UserModel.MultipleObjectsReturned:
            # 複数のユーザーがヒットした場合 (Meta制約が正しければ起こらない)
            log_output_by_msg_id(
                log_id="MSGE102",
                params=[identifier],
                logger_name=LOG_METHOD.APPLICATION.value,
                exc_info=True,
            )
            return None

        else:
            # 3. パスワードチェックと認証成功
            # パスワードチェックのみに絞り、認証権限チェックを簡略化
            if user_model_instance.check_password(password):
                # 認証成功
                return user_model_instance
            else:
                # パスワードが一致しない場合
                log_output_by_msg_id(
                    log_id="MSGE101",
                    params=[identifier, "（パスワードはログに残さない）"],
                    logger_name=LOG_METHOD.APPLICATION.value,
                )
                return None

    # 必須: 認証成功後にユーザーインスタンスを取得するためのメソッド
    @logging_sql_queries
    def get_user(self, user_id):
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
