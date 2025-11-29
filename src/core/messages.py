MESSAGES = {
    # ----- DEBUG関連ログメッセージ -----
    "MSGD001": "{0}",
    "MSGD002": "{0} 処理時間: {1}",
    # ----- INFO関連ログメッセージ -----
    "MSGI001": "{0}",
    "MSGI002": "サービスが起動されました。",
    "MSGI003": "処理開始します。 処理名: {0} リクエスト内容: {1}",
    # ----- WARNING関連ログメッセージ -----
    "MSGW001": "{0}",
    # ... 他のメッセージ定義
    # ----- ERROR関連ログメッセージ -----
    "MSGE001": "{0}",
    # "MSGE002": "エラーが発生しました。 エラーメッセージ: {0} エラー詳細: {1} レスポンス内容: {2}\n%s",
    # 認証関連のエラーメッセージ
    "MSGE101": "認証処理で予期せぬエラーが発生しました。識別子: {0} 詳細: {1}\n%s",  # 汎用的な認証エラー
    "MSGE102": "データベースに同一識別子のユーザが複数存在します。識別子: {0}\n%s",  # 複数ユーザーヒット
}


def get_message(message_id: str, params: list) -> str:
    """メッセージIDに対応する内容を取得し、パラメータを挿入する"""
    message = MESSAGES.get(message_id, f"ERROR: Message ID {message_id} not found.")
    try:
        return message.format(*params)
    except IndexError:
        return f"ERROR: Message ID {message_id} parameter mismatch."
