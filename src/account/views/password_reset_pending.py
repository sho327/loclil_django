from django.views.generic import TemplateView


# パスワードリセット完了(実行待ち)ビュー
class PasswordResetPendingView(TemplateView):
    # このビューは、メールが送信されたことだけを通知するシンプルな画面
    template_name = "account/password_reset_pending.html"
