from django.apps import AppConfig


class AccountConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "account"

    def ready(self):
        """Djangoの起動時にシグナルをインポートして接続する"""
        import account.signals
