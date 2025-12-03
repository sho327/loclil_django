from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View


class LogoutView(View):
    """
    ユーザーをログアウトさせ、ログインページにリダイレクトするビュー。
    """

    # ログアウト後のリダイレクト先 (通常はログインページ)
    # reverse_lazy を使うことで、URLがまだ読み込まれていなくても安全に参照できます
    redirect_url = reverse_lazy("account:login")

    def get(self, request):
        # Djangoの組み込み関数でセッションを破棄
        logout(request)

        # リダイレクト
        return redirect(self.redirect_url)

    # ユーザーが誤ってログアウトリンクを画像として貼った場合のセキュリティ対策
    def post(self, request):
        return self.get(request)
