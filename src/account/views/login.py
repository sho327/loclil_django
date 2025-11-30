from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy


# 標準の LoginView を継承してカスタム設定を行う
class CustomLoginView(LoginView):
    # テンプレートファイルへのパスを指定します
    template_name = "account/login.html"

    # ログイン成功後にリダイレクトするURLを設定
    # reverse_lazy を使うことで、設定ファイルがロードされる前にURL参照が行われるのを防ぎます
    success_url = reverse_lazy(
        "home"
    )  # 'home'はあなたが定義するトップページのURL名に置き換えてください

    # ログインフォームとして使用するクラスを指定することもできますが、
    # ユーザーモデルに email を使用している場合、標準の AuthenticationForm で問題ありません。
    # form_class = AuthenticationForm # デフォルト
