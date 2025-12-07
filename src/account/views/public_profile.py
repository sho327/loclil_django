from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView
from django.http import Http404

from account.models.m_user_profile import M_UserProfile
from core.decorators.logging_sql_queries import logging_sql_queries

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
        profile = super().get_object(queryset)
        
        # 非公開プロフィール、または自分自身でない場合は404 (自分自身はProfileViewで見る想定だが、アクセスできても良い)
        if not profile.is_public and profile.m_user != self.request.user:
             raise Http404("このユーザーのプロフィールは非公開です。")
             
        return profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.object

        # 技術タグをリストに変換
        if profile.skill_tags_raw:
            skill_tags = [
                tag.strip()
                for tag in profile.skill_tags_raw.split(",")
                if tag.strip()
            ]
            context["skill_tags"] = skill_tags
        else:
            context["skill_tags"] = []
            
        return context
