from typing import BinaryIO, Optional

# 役割: Cloudinary/S3など、外部ストレージへのファイルアップロード・削除処理を統一的に扱う。
# 利用例: ユーザーのアバター画像、作品のサムネイル画像の保存/削除。


class FileStorageError(Exception):
    """ファイルストレージ操作に関するカスタムエラー"""

    pass


def upload_file(file_data: BinaryIO, folder_path: str, filename: str) -> Optional[str]:
    """
    ファイルを外部ストレージにアップロードし、公開URLを返す。
    """
    try:
        # --- [TODO] Cloudinary SDKなどを使ったアップロード処理を実装 ---
        print(f"File uploaded to: {folder_path}/{filename}")
        # 成功時はURLを返す
        return f"https://cdn.shelio.com/{folder_path}/{filename}.png"

    except Exception as e:
        # ロギング処理を行う
        raise FileStorageError(f"ファイルのアップロードに失敗しました: {e}")


def delete_file(file_url: str) -> bool:
    """
    公開URLに基づいてファイルを外部ストレージから削除する。
    """
    try:
        # --- [TODO] 外部ストレージの削除処理を実装 ---
        print(f"File deleted: {file_url}")
        return True
    except Exception as e:
        # ロギング処理を行う
        print(f"Storage Deletion Failed: {e}")
        return False
