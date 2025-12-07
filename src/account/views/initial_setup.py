from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from account.forms.initial_setup import InitialSetupForm
from account.services.user_service import UserService
from core.consts import LOG_METHOD
from core.exceptions import ExternalServiceError, IntegrityError
from core.utils.log_helpers import log_output_by_msg_id
from core.decorators.logging_sql_queries import logging_sql_queries

process_name = "InitialSetupView"

class InitialSetupView(LoginRequiredMixin, FormView):
    template_name = "account/initial_setup.html"
    form_class = InitialSetupForm
    success_url = reverse_lazy("dashboard:dashboard")
    user_service = UserService()

    # 1. アクセス制御 (変更なし)
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_first_login:
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    # 2. フォームの初期値設定 (GET)
    def get_initial(self):
        """
        ユーザープロフィールに存在する display_name を取得してフォームに渡す。
        """
        initial = super().get_initial()
        user = self.request.user

        if user.is_authenticated:
            try:
                profile = user.user_profile
                initial["display_name"] = profile.display_name
                initial["is_public"] = profile.is_public
                initial["is_email_notify_enabled"] = profile.is_email_notify_enabled
            except Exception:
                pass

        return initial

    # 3. フォームのインスタンス化をオーバーライド (userインスタンスを渡すため)
    @logging_sql_queries(process_name=process_name)
    def get_form(self, form_class=None):
        form_class = form_class or self.get_form_class()
        # フォームに user インスタンスを渡す
        return form_class(user=self.request.user, **self.get_form_kwargs())

    # 4. POST処理
    @logging_sql_queries(process_name=process_name)
    def form_valid(self, form):
        data = form.cleaned_data
        icon_file = self.request.FILES.get("icon", None)
        icon_clear = data.get("icon_clear", False)
        is_email_notify_enabled = data.get("is_email_notify_enabled", False)
        user_id = str(self.request.user.pk)

        try:
            # サービス層を呼び出し、DB更新とフラグ更新を一括実行
            self.user_service.initial_setup(
                user=self.request.user,
                display_name=data["display_name"],
                is_public=data.get("is_public", False),
                is_email_notify_enabled=is_email_notify_enabled,
                process_name=process_name,
                icon_file=icon_file,
                icon_clear=icon_clear,
            )

            messages.success(self.request, "初期設定が完了しました！")
            return super().form_valid(form)

        except IntegrityError as e:
            # ログ出力: データベース整合性エラーを記録
            # データベースエラーは予測困難な場合があるため、スタックトレースも含める
            log_output_by_msg_id(
                log_id="MSGE801",
                params=[user_id, e.message_id, str(e.details)],
                logger_name=LOG_METHOD.APPLICATION.value,
                exc_info=True,  # スタックトレースを含める（データベースエラーは原因特定が困難な場合があるため）
            )
            # 例外クラスで定義されたメッセージを使用
            form.add_error(
                None,
                e.message,
            )
            return self.form_invalid(form)

        except ExternalServiceError as e:
            # ログ出力: 外部サービスエラーを記録
            log_output_by_msg_id(
                log_id="MSGE802",
                params=[user_id, e.message_id],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            # 例外クラスで定義されたメッセージを使用
            form.add_error(
                "icon",
                e.message,
            )
            return self.form_invalid(form)

        except Exception as e:
            # ログ出力: 予期せぬエラーを記録（スタックトレースを含む）
            error_detail = f"初期設定処理中にエラーが発生しました。ユーザーID: {user_id} エラー: {str(e)}"
            log_output_by_msg_id(
                log_id="MSGE002",
                params=[error_detail],
                logger_name=LOG_METHOD.APPLICATION.value,
                exc_info=True,  # 予測不可能なエラーのためスタックトレースを含める
            )
            form.add_error(None, "予期せぬシステムエラーが発生しました。")
            return self.form_invalid(form)
