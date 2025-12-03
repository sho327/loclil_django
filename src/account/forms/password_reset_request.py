from django import forms


# パスワードリセット要求フォーム (メールアドレス入力)
class PasswordResetRequestForm(forms.Form):
    """パスワードリセットのためにメールアドレスを入力するフォーム"""

    email = forms.EmailField(
        label="ご登録のメールアドレス",
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "placeholder": "メールアドレス",
                "class": "input input-bordered w-full",
            }
        ),
    )
