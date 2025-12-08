from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from account.forms.user_search import UserSearchForm
from account.models.m_user_profile import M_UserProfile
from account.services.user_service import UserService
from core.decorators.logging_sql_queries import logging_sql_queries

process_name = "UserSearchView"


class UserSearchView(LoginRequiredMixin, ListView):
    """
    ユーザー検索画面
    """

    model = M_UserProfile
    template_name = "account/user_search.html"
    context_object_name = "profiles"
    paginate_by = 20  # ページネーション

    @logging_sql_queries(process_name=process_name)
    def get_queryset(self):
        service = UserService()
        
        # フォームを使用して検索パラメータを取得・バリデーション
        form = UserSearchForm(self.request.GET)
        
        if form.is_valid():
            search_word = form.cleaned_data.get("search_word")
            location = form.cleaned_data.get("location")
            skill_tag = form.cleaned_data.get("skill_tag")
        else:
            # バリデーションエラーの場合は空の検索条件
            search_word = None
            location = None
            skill_tag = None

        # サービス層を使用して検索
        return service.search_public_profiles(
            search_word=search_word,
            location=location,
            skill_tag=skill_tag,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # フォームをコンテキストに追加
        form = UserSearchForm(self.request.GET)
        context["form"] = form
        
        # テンプレートで使用するため、検索パラメータをコンテキストに追加
        if form.is_valid():
            context["search_word"] = form.cleaned_data.get("search_word", "")
            context["location"] = form.cleaned_data.get("location", "")
            context["skill_tag"] = form.cleaned_data.get("skill_tag", "")
        else:
            context["search_word"] = ""
            context["location"] = ""
            context["skill_tag"] = ""
            
        return context
