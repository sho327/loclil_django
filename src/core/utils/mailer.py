from typing import List

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

# 役割: アカウント有効化、通知など、システムからユーザーへのメール送信処理を抽象化する。
# 利用例: 新規登録時のアカウント有効化メール、パスワードリセットメールの送信。


class EmailSendingError(Exception):
    """メール送信に関するカスタムエラー"""

    pass


def send_templated_email(
    subject: str, recipient_list: List[str], template_name: str, context: dict
) -> bool:
    """
    テンプレートを使ってメールを作成し、送信する。
    """
    if not recipient_list:
        return False

    # テンプレートをレンダリングして本文を生成 (例: 'emails/activation_email.html')
    html_message = render_to_string(template_name, context)

    try:
        send_mail(
            subject=subject,
            message="",  # HTMLメールなのでmessageは空
            from_email=settings.EMAIL_FROM,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        print(f"Email sent successfully to: {', '.join(recipient_list)}")
        return True

    except Exception as e:
        # ロギング処理を行う
        raise EmailSendingError(f"メールの送信中にエラーが発生しました: {e}")
