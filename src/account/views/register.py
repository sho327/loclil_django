from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from account.forms.signup import SignupForm
from account.services.auth_service import AuthService
from core.consts import LOG_METHOD
from core.decorators.logging_sql_queries import logging_sql_queries
from core.exceptions import DuplicationError, ExternalServiceError, IntegrityError
from core.utils.log_helpers import log_output_by_msg_id

process_name = "RegisterView"

class RegisterView(FormView):
    form_class = SignupForm
    template_name = "account/register.html"
    success_url = reverse_lazy("account:register_pending")

    # SQLログデコレータを適用
    @logging_sql_queries(process_name=process_name)
    def form_valid(self, form: SignupForm) -> HttpResponseRedirect:

        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        display_name = form.cleaned_data.get("display_name")

        auth_service = AuthService()

        try:
            # 1. サービスを介してユーザーを作成・保存
            auth_service.register_new_user(
                email=email, 
                password=password, 
                display_name=display_name, 
                process_name=process_name,
            )

            # 2. 成功後のリダイレクト
            return redirect(self.get_success_url())

        except DuplicationError as e:
            # ログ出力: メールアドレス重複を記録
            log_output_by_msg_id(
                log_id="MSGE301",
                params=[email, e.message_id],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            # 例外クラスで定義されたメッセージを使用
            form.add_error(None, e.message)
            return self.form_invalid(form)

        except IntegrityError as e:
            # ログ出力: データベース整合性エラーを記録
            log_output_by_msg_id(
                log_id="MSGE302",
                params=[email, e.message_id, str(e.details)],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            # 例外クラスで定義されたメッセージを使用
            form.add_error(None, e.message)
            return self.form_invalid(form)

        except ExternalServiceError as e:
            # ログ出力: 外部サービスエラーを記録
            log_output_by_msg_id(
                log_id="MSGE303",
                params=[email, e.message_id],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            # 例外クラスで定義されたメッセージを使用
            form.add_error(None, e.message)
            return self.form_invalid(form)

        except Exception as e:
            # ログ出力: 予期せぬエラーを記録（スタックトレースを含む）
            error_detail = f"新規登録処理中にエラーが発生しました。メールアドレス: {email} エラー: {str(e)}"
            log_output_by_msg_id(
                log_id="MSGE002",
                params=[error_detail],
                logger_name=LOG_METHOD.APPLICATION.value,
                exc_info=True,  # 予測不可能なエラーのためスタックトレースを含める
            )
            form.add_error(None, "予期せぬエラーが発生しました。")
            return self.form_invalid(form)
