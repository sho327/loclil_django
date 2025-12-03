from django import forms
from django.conf import settings


class PasswordResetConfirmForm(forms.Form):
    """トークン検証後、新しいパスワードを設定するフォーム"""

    # settings.MIN_PASSWORD_LENGTH を使用する場合
    MIN_LENGTH = getattr(settings, "MIN_PASSWORD_LENGTH", 8)

    new_password1 = forms.CharField(
        label="新しいパスワード",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": f"新しいパスワード ({MIN_LENGTH}文字以上)",
                "class": "input input-bordered w-full",
            }
        ),
        strip=False,
        min_length=MIN_LENGTH,
    )
    new_password2 = forms.CharField(
        label="新しいパスワード（確認）",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "確認のため再入力",
                "class": "input input-bordered w-full",
            }
        ),
        strip=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("new_password1")
        password_confirm = cleaned_data.get("new_password2")

        if password and password_confirm and password != password_confirm:
            # フォームレベルのエラーを発生させる
            raise forms.ValidationError(
                "パスワードが一致しません。", code="password_mismatch"
            )

        return cleaned_data
