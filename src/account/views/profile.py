from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from account.exceptions import ProfileNotFoundException
from account.services.user_service import UserService
from core.consts import LOG_METHOD
from core.decorators.logging_sql_queries import logging_sql_queries
from core.utils.log_helpers import log_output_by_msg_id

process_name = "ProfileView"


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    プロフィール表示画面（自分自身のプロフィール）
    """

    template_name = "account/profile.html"

    @logging_sql_queries(process_name=process_name)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        service = UserService()

        try:
            # サービス層を使用してプロフィールを取得
            profile = service.get_user_profile(user)
            context["profile"] = profile
            context["skill_tags"] = service.parse_skill_tags(profile)
        except ProfileNotFoundException as e:
            # ログ出力: プロフィール未作成エラーを記録
            log_output_by_msg_id(
                log_id="MSGE901",
                params=[str(user.pk), e.message_id],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            context["profile"] = None
            context["skill_tags"] = []
            messages.warning(self.request, "プロフィールが作成されていません。")
        except Exception as e:
            # ログ出力: 予期せぬエラーを記録
            error_detail = f"プロフィール取得中にエラーが発生しました。ユーザーID: {user.pk} エラー: {str(e)}"
            log_output_by_msg_id(
                log_id="MSGE002",
                params=[error_detail],
                logger_name=LOG_METHOD.APPLICATION.value,
                exc_info=True,
            )
            context["profile"] = None
            context["skill_tags"] = []
            messages.error(self.request, "プロフィールの取得中にエラーが発生しました。")

        context["user"] = user
        return context
