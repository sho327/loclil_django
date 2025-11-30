from django.apps import AppConfig


class AccountConfig(AppConfig):
    # アプリケーションの完全なドット区切りパス
    # プロジェクト名が 'config' だった場合: 'config.[name]'
    name = "account"
    # label = "account"
    # 管理画面での表示名など（任意）
    verbose_name = "アカウント機能"
    # データベースのスケーラビリティを確保するため、BigAutoFieldを明示的に指定
    default_auto_field = "django.db.models.BigAutoField"
    # モデルの定義があるサブモジュールを明示的に指定する
    # Djangoは通常 'account.models' を探すが、サブモジュール分割時は明示的に指定することで確実になる
    # 'account.models' は 'account/models/__init__.py' を指す
    # models_module = "account.models"

    def ready(self):
        """Djangoの起動時にシグナルをインポートして接続する"""
        import account.signals
