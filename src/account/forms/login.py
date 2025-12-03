from django import forms
from django.contrib.auth.forms import AuthenticationForm as DjangoAuthenticationForm


class AuthenticationForm(DjangoAuthenticationForm):
    """
    ログイン状態を記憶するチェックボックスを追加した認証フォーム
    """

    # AuthenticationFormは汎用的なフォーム(最大文字数やEmailでのチェックはオーバーライドすべき)
    # ユーザーモデルの email フィールドの max_length に合わせる (例: 254)
    username = forms.EmailField(
        label="メールアドレス",
        max_length=254,
        widget=forms.TextInput(attrs={"autofocus": True}),
    )

    # パスワードの max_length は通常 128 に合わせる (ハッシュ値の長さ)
    password = forms.CharField(
        label="パスワード",
        strip=False,
        max_length=128,
        widget=forms.PasswordInput,
    )

    remember_me = forms.BooleanField(
        required=False,  # チェックしなくても良い
        label="ログイン状態を維持する",
        widget=forms.CheckboxInput(attrs={"class": "checkbox checkbox-primary"}),
    )

    # 標準フォームのフィールド（username, password）は継承されるが、
    # DoS対策で最大文字数は弾けるようにする

    # 標準の認証ロジックを含む clean() メソッドを無効化する
    def clean(self):
        # 親クラスの clean() を呼び出しません。
        # 必要なフィールドのデータ（username, password）は self.cleaned_data に格納済みです。

        # フィールド固有のエラーチェックは既にフォームによって行われているため、
        # ここでは何もしません。認証はビューの form_valid() に任せます。

        # ユーザーオブジェクトをキャッシュするフィールドをクリアする (念のため)
        self.user_cache = None

        return self.cleaned_data
