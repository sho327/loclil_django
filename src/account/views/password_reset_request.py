from audioop import reverse

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from account.forms.password_reset_request import PasswordResetRequestForm
from account.services.auth_service import AuthService
from core.consts import LOG_METHOD
from core.exceptions import ExternalServiceError, IntegrityError
from core.utils.log_helpers import log_output_by_msg_id
from core.decorators.logging_sql_queries import logging_sql_queries

process_name = "PasswordResetRequestView"

# パスワードリセット要求ビュー (メールアドレス入力)
class PasswordResetRequestView(FormView):
    template_name = "account/password_reset_request.html"
    form_class = PasswordResetRequestForm
    success_url = reverse_lazy("account:password_reset_pending")

    @logging_sql_queries(process_name=process_name)
    def form_valid(self, form):
        email = form.cleaned_data["email"]
        auth_service = AuthService()

        try:
            # サービスに処理を委譲。ユーザーの有無にかかわらず成功を返す（列挙攻撃対策）。
            auth_service.request_password_reset(
                email=email, 
                process_name=process_name
            )

            # 成功メッセージを設定（ユーザーがメールをチェックすべきことを通知）
            # messages.info(self.request, "パスワード再設定用のメールを送信しました。")

            return super().form_valid(form)

        except IntegrityError as e:
            # ログ出力: データベース整合性エラーを記録
            log_output_by_msg_id(
                log_id="MSGE501",
                params=[email, e.message_id, str(e.details)],
                logger_name=LOG_METHOD.APPLICATION.value,
                # exc_info=Trueを削除（予測可能なエラーのため）
            )
            # 例外クラスで定義されたメッセージを使用
            form.add_error(None, e.message)
            return redirect(
                reverse("account:login")
            )  # ユーザーを安全な場所へリダイレクト

        except ExternalServiceError as e:
            # ログ出力: 外部サービスエラーを記録
            log_output_by_msg_id(
                log_id="MSGE502",
                params=[email, e.message_id],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            # 例外クラスで定義されたメッセージを使用
            form.add_error(None, e.message)
            return redirect(reverse("account:login"))

        except Exception as e:
            # ログ出力: 予期せぬエラーを記録（スタックトレースを含む）
            error_detail = f"パスワードリセット要求処理中にエラーが発生しました。メールアドレス: {email} エラー: {str(e)}"
            log_output_by_msg_id(
                log_id="MSGE002",
                params=[error_detail],
                logger_name=LOG_METHOD.APPLICATION.value,
                exc_info=True,  # 予測不可能なエラーのためスタックトレースを含める
            )
            # 予期せぬ全てのエラー
            form.add_error(None, "予期せぬエラーが発生しました。")
            return redirect(reverse("account:login"))
