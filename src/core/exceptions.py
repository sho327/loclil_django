"""
フレームワークに依存しない、ビジネスロジックで発生するカスタム例外の基底クラス。
"""


class ApplicationError(Exception):
    """
    全てのカスタムビジネス例外の基底クラス。

    業務ロジックで発生したエラー情報を統一的に保持し、
    プレゼンテーション層での処理を容易にする。
    """

    # --------------------------------------------------
    # 共通属性 (子クラスで上書きされることを想定)
    # --------------------------------------------------
    # ユーザーに見せる、またはログに出力される標準メッセージ
    default_message: str = "予期せぬアプリケーションエラーが発生しました。"

    # 固有のエラーコード (ログやフロントエンドでの分岐に使用)
    message_id: str = "ERR_UNKNOWN"

    def __init__(self, message: str = None, details: dict = None, *args):
        """
        メッセージと詳細データを初期化する。

        Args:
            message (str, optional): エラーに特化したメッセージ (default_messageを上書き)。
            details (dict, optional): エラーに関連する追加情報（例: field_errors, invalid_id）。
        """
        # メッセージを設定: 引数があればそれを使用、なければデフォルトメッセージを使用
        self.message = message if message is not None else self.default_message

        # 追加の詳細データを格納
        # View層でDRF例外に翻訳する際、この details に全ての情報（message_id, message, details）を集約します。
        self.details = details if details is not None else {}

        # Pythonの標準Exceptionコンストラクタを呼び出す
        # 最初の引数は通常のエラーメッセージとして扱われる
        super().__init__(self.message, self.details, *args)

    def __str__(self):
        """例外が文字列として表示される際の形式を定義"""
        # [ERR_ID] メッセージ (詳細データ) の形式で返す
        detail_str = f" (Details: {self.details})" if self.details else ""
        return f"[{self.message_id}] {self.message}{detail_str}"


# --------------------------------------------------
# 共通でよく使われる汎用的なエラーの例
# --------------------------------------------------
class IntegrityError(ApplicationError):
    """データベースの整合性制約違反など、データ層に近いエラー"""

    default_message = "データの一貫性に関する問題が発生しました。"
    message_id = "ERR_DB_001"


class ResourceNotFound(ApplicationError):
    """リソースが存在しない（View層で404に翻訳されることを想定）"""

    default_message = "指定されたリソースが見つかりませんでした。"
    message_id = "ERR_NOT_FOUND"


class PermissionDeniedError(ApplicationError):
    """ユーザーが特定のアクションを実行する権限を持っていない (HTTP 403想定)"""

    default_message = "この操作を実行する権限がありません。"
    message_id = "ERR_AUTH_002"


class DuplicationError(ApplicationError):
    """一意制約が破られた（メールアドレスなどが重複）"""

    default_message = "入力された情報（例：メールアドレス）は既に使用されています。"
    message_id = "ERR_DATA_002"


class ResourceNotFound(ApplicationError):  # 採用されたクラス
    default_message = "指定されたリソースが見つかりませんでした。"
    message_id = "ERR_NOT_FOUND"


class ExternalServiceError(ApplicationError):
    """外部API連携時の失敗"""

    default_message = "外部サービスとの連携中に問題が発生しました。"
    message_id = "ERR_EXTERNAL_001"
