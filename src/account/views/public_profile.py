from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView
from django.http import Http404

from account.exceptions import ProfileNotFoundException, ProfileAccessDeniedException
from account.models.m_user_profile import M_UserProfile
from account.services.user_service import UserService
from core.consts import LOG_METHOD
from core.decorators.logging_sql_queries import logging_sql_queries
from core.utils.log_helpers import log_output_by_msg_id

process_name = "PublicProfileView"


class PublicProfileView(LoginRequiredMixin, DetailView):
    """
    公開プロフィール詳細画面
    """

    model = M_UserProfile
    template_name = "account/public_profile.html"
    context_object_name = "profile"

    @logging_sql_queries(process_name=process_name)
    def get_object(self, queryset=None):
        service = UserService()
        profile_id = self.kwargs.get("pk")

        try:
            profile = service.get_public_profile(
                profile_id=profile_id, requesting_user=self.request.user
            )
            return profile
        except ProfileNotFoundException as e:
            # ログ出力: プロフィール未発見エラーを記録
            log_output_by_msg_id(
                log_id="MSGE902",
                params=[str(profile_id), e.message_id],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            raise Http404("プロフィールが見つかりません。")
        except ProfileAccessDeniedException as e:
            # ログ出力: アクセス拒否エラーを記録
            log_output_by_msg_id(
                log_id="MSGE903",
                params=[str(profile_id), str(self.request.user.pk), e.message_id],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            raise Http404("このユーザーのプロフィールは非公開です。")
        except Exception as e:
            # ログ出力: 予期せぬエラーを記録
            error_detail = f"公開プロフィール取得中にエラーが発生しました。プロフィールID: {profile_id} エラー: {str(e)}"
            log_output_by_msg_id(
                log_id="MSGE002",
                params=[error_detail],
                logger_name=LOG_METHOD.APPLICATION.value,
                exc_info=True,
            )
            raise Http404("プロフィールの取得中にエラーが発生しました。")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = UserService()
        profile = self.object

        # サービス層を使用してスキルタグをパース
        context["skill_tags"] = service.parse_skill_tags(profile)

        return context
