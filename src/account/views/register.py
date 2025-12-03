from django.contrib.auth import login
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

# サインアップフォームをインポート
from account.forms.signup import SignupForm

# AuthServiceとカスタム例外をインポート
from account.services.user_service import UserService
from core.decorators.logging_sql_queries import logging_sql_queries

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

        user_service = UserService()

        try:
            # 1. サービスを介してユーザーを作成・保存
            user_service.register_new_user(
                email=email, password=password, display_name=display_name
            )

            # 2. 成功後のリダイレクト
            return redirect(self.get_success_url())

        except Exception as e:
            # サービス層で発生した予期せぬエラーをキャッチし、フォームエラーとして表示
            form.add_error(None, str(e))
            return self.form_invalid(form)
