from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

# --- 共通モジュール ---
from core.consts import LOG_LEVEL, LOG_METHOD
from core.decorators import logging_sql_queries
from core.utils.log_helpers import log_output_by_msg_id

UserModel = get_user_model()

"""
カスタムユーザ認証バックエンドクラス
メールアドレスまたはユーザー名を使用して認証を行う
"""


class UserAuthBackend(ModelBackend):
    # ModelBackendのメソッドをオーバーライド
    @logging_sql_queries
    def authenticate(self, request, email=None, password=None, **kwargs):

        # 1. ログイン試行に使用された識別子 (email/username) を取得
        identifier = email
        if identifier is None:
            # admin管理サイトや他のフォームからのログイン対策として、username フィールドもチェック
            identifier = kwargs.get("username")

        if identifier is None:
            return None  # 識別子がない場合は認証をスキップ

        try:
            # 2. メールアドレスまたはユーザー名でユーザーを検索
            # 独自のUserModelで username フィールドが使用されている場合は、Qオブジェクトで検索条件を結合
            user_model_queryset = UserModel.objects.filter(
                Q(email=identifier) | Q(username=identifier)
            )

            # 3. ユーザーインスタンスを取得
            user_model_instance = user_model_queryset.get()

        except UserModel.DoesNotExist:
            # ユーザーが存在しない場合
            log_output_by_msg_id(
                log_id="MSGE101",
                params=[identifier, "（パスワードはログに残さない）"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            return None
        except UserModel.MultipleObjectsReturned:
            # 複数のユーザーがヒットした場合 (通常あってはならない)
            # エラーログを出力し、認証を拒否
            log_output_by_msg_id(
                log_id="MSGE102",
                # ログに出力するパラメータは識別子のみ
                params=[identifier],
                logger_name=LOG_METHOD.APPLICATION.value,
                # MultipleObjectsReturnedはシステムエラーなのでTracebackは不要だが、
                # 念のためexc_info=Trueを維持
                exc_info=True,
            )
            return None

        else:
            # 4. パスワードチェックと認証権限チェック
            if user_model_instance.check_password(
                password
            ) and self.user_can_authenticate(user_model_instance):
                return user_model_instance
            else:
                log_output_by_msg_id(
                    log_id="MSGE101",
                    params=[identifier, "（パスワードはログに残さない）"],
                    logger_name=LOG_METHOD.APPLICATION.value,
                )
                return None
