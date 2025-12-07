from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from account.models.m_user_profile import M_UserProfile
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
        queryset = super().get_queryset().filter(is_public=True)  # 公開ユーザーのみ
        query = self.request.GET.get("q")

        if query:
            # 表示名または技術タグで部分一致検索 (スペース区切りでAND検索も可能にするならロジック追加が必要だが、まずはシンプルに)
            queryset = queryset.filter(
                Q(display_name__icontains=query) | Q(skill_tags_raw__icontains=query)
            )
        
        # 結果をランダムまたは更新順などで表示（ここでは作成順の逆＝新しい順）
        return queryset.select_related("m_user").order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        return context
