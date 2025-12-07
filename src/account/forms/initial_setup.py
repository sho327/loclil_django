from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

# from account.models import M_UserProfile # ユニークチェックなしのためインポートは不要

User = get_user_model()


class InitialSetupForm(forms.Form):
    """
    初回設定時に必須/推奨される項目のみを扱うフォーム。
    """

    # 必須項目
    display_name = forms.CharField(
        label="表示名",
        max_length=64,
        required=True,
        help_text="コミュニティ内であなたを識別するために使用されます。必須です。",
    )

    # 推奨項目 (オプションとして扱う)
    icon = forms.ImageField(
        label="ユーザーアイコン",
        required=False,
        help_text="プロフィールアイコン画像をアップロードしてください。",
    )

    icon_clear = forms.BooleanField(
        required=False, widget=forms.HiddenInput, initial=False
    )

    is_public = forms.BooleanField(
        label="プロフィールを一般公開する",
        required=False,
        initial=True,
        help_text="チェックを外すと、プロフィールはログインユーザーにのみ表示されます。",
    )

    # 🚨 修正箇所: モデル名 (is_email_notify_enabled) に合わせる 🚨
    is_email_notify_enabled = forms.BooleanField(
        label="メール通知を一括で受け取る",
        required=False,
        initial=True,
        help_text="すべてのメール通知の有効/無効を一括で設定します。",
    )

    # -------------------------------------------------------------
    # 初期値設定用のフック (ビューで利用)
    # -------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    # -------------------------------------------------------------
    # クリーンメソッド
    # -------------------------------------------------------------
    def clean_display_name(self):
        display_name = self.cleaned_data.get("display_name")

        if not display_name:
            raise ValidationError("表示名は必須です。", code="required")

        return display_name
