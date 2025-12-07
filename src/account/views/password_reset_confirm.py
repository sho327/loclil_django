from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView

from account.exceptions import PasswordResetTokenInvalidException
from account.forms.password_reset_confirm import PasswordResetConfirmForm
from account.services.auth_service import AuthService
from core.consts import LOG_METHOD
from core.exceptions import IntegrityError
from core.utils.log_helpers import log_output_by_msg_id
from core.decorators.logging_sql_queries import logging_sql_queries

process_name = "PasswordResetConfirmView"

# パスワードリセット確認＆実行ビュー(トークン検証とパスワード設定)
class PasswordResetConfirmView(FormView):
    template_name = "account/password_reset_confirm.html"
    form_class = PasswordResetConfirmForm
    # 成功後はログイン画面へリダイレクト
    success_url = reverse_lazy("account:login")

    def dispatch(self, request, *args, **kwargs):
        # URLからトークンを取得し、このビューインスタンスに保存
        self.token_value = kwargs.get("token_value")
        return super().dispatch(request, *args, **kwargs)

    @logging_sql_queries(process_name=process_name)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # テンプレートにトークンを渡す（例: フォームのhiddenフィールドなど）
        context["token_value"] = self.token_value
        return context

    @logging_sql_queries(process_name=process_name)
    def form_valid(self, form):
        new_password = form.cleaned_data["new_password1"]
        auth_service = AuthService()

        try:
            # サービス層でトークン検証とパスワード更新を実行
            user = auth_service.reset_password(
                raw_token_value=self.token_value,
                new_password=new_password,
                process_name=process_name,
            )

            # 成功メッセージを設定し、ログイン画面へリダイレクト
            # messages.success(
            #     self.request,
            #     "パスワードが正常にリセットされました。新しいパスワードでログインしてください。",
            # )
            return super().form_valid(form)

        except PasswordResetTokenInvalidException as e:
            # ログ出力: トークン無効を記録
            log_output_by_msg_id(
                log_id="MSGE601",
                params=[
                    self.token_value[:8] + "...",
                    e.message_id,
                ],  # トークンの一部のみ記録（セキュリティのため）
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            # 例外クラスで定義されたメッセージを使用
            form.add_error(None, e.message)

            # エラー発生時はリセット要求画面に戻す
            return redirect(reverse("account:password_reset_request"))

        except IntegrityError as e:
            # ログ出力: データベース整合性エラーを記録
            user_id = str(user.pk) if "user" in locals() else "unknown"
            log_output_by_msg_id(
                log_id="MSGE602",
                params=[user_id, e.message_id, str(e.details)],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            # 例外クラスで定義されたメッセージを使用
            form.add_error(None, e.message)
            return redirect(reverse("account:login"))  # またはエラー画面へリダイレクト

        except Exception as e:
            # ログ出力: 予期せぬエラーを記録（スタックトレースを含む）
            error_detail = f"パスワードリセット実行処理中にエラーが発生しました。トークン: {self.token_value[:8]}... エラー: {str(e)}"
            log_output_by_msg_id(
                log_id="MSGE002",
                params=[error_detail],
                logger_name=LOG_METHOD.APPLICATION.value,
                exc_info=True,  # 予測不可能なエラーのためスタックトレースを含める
            )
            form.add_error(None, "予期せぬエラーが発生しました。")
            return redirect(reverse("account:login"))  # 安全のためログイン画面に戻す
