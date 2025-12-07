from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from account.exceptions import (
    TokenExpiredOrNotFoundException,
    UserAlreadyActiveException,
)
from account.services.auth_service import AuthService
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.decorators.logging_sql_queries import logging_sql_queries

process_name = "ActivateUserView"

class ActivateUserView(View):
    """
    メールに記載されたトークンを使ってユーザーアカウントを有効化する。
    """

    @logging_sql_queries(process_name=process_name)
    def get(self, request, token_value):
        auth_service = AuthService()

        try:
            # サービス層でアカウントを有効化
            user = auth_service.activate_user(
                raw_token_value=token_value, 
                process_name=process_name,
            )

            # 成功: ユーザーを強制的にログインさせる (UX向上のためオプション)
            login(self.request, user)

            # 成功画面へリダイレクト
            return redirect(reverse("dashboard:dashboard"))

        except TokenExpiredOrNotFoundException as e:
            # ログ出力: トークン無効を記録
            log_output_by_msg_id(
                log_id="MSGE401",
                params=[
                    token_value[:8] + "...",
                    e.message_id,
                ],  # トークンの一部のみ記録（セキュリティのため）
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            # 例外クラスで定義されたメッセージを使用
            context = {
                "error_title": "無効なリンク",
                "error_message": e.message,
                "can_retry": True,
            }
            return render(
                request, "account/activate_user_failed.html", context, status=400
            )

        except UserAlreadyActiveException as e:
            # ログ出力: 既に有効化済みを記録
            log_output_by_msg_id(
                log_id="MSGE402",
                params=[
                    str(user.pk) if "user" in locals() else "unknown",
                    e.message_id,
                ],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            # 例外クラスで定義されたメッセージを使用
            context = {
                "message_title": "既に有効化済み",
                "message_body": e.message,
            }
            # 既にログイン済みの可能性もあるため、200 OK でメッセージを返す
            return render(
                request, "account/activate_user_success.html", context, status=200
            )

        except Exception as e:
            # ログ出力: 予期せぬエラーを記録（スタックトレースを含む）
            error_detail = f"アクティベーション処理中にエラーが発生しました。トークン: {token_value[:8]}... エラー: {str(e)}"
            log_output_by_msg_id(
                log_id="MSGE002",
                params=[error_detail],
                logger_name=LOG_METHOD.APPLICATION.value,
                exc_info=True,  # 予測不可能なエラーのためスタックトレースを含める
            )
            # その他のシステムエラー
            context = {
                "error_title": "システムエラー",
                "error_message": "アカウントの有効化中に予期せぬエラーが発生しました。",
                "can_retry": False,
            }
            return render(
                request, "account/activate_user_failed.html", context, status=500
            )
