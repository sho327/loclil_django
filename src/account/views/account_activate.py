from datetime import datetime

from django.middleware.csrf import get_token
from lib import consts, modules
from rest_framework import viewsets
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from core.exceptions.custom_exceptions import InternalServerError
from core.message import MessageDefinition as md
from core.modules.format_changer import FormatChanger as fc

kino_id = "account-activate"


class AccountActivateViewSet(viewsets.ModelViewSet):
    """
    アカウント有効化APIのViewクラス
    Create
        Date: 2025/11/17
        Author: Kato Shogo
    """

    http_method_names = ["post"]

    def create(self, request, *args, **kwargs):
        """
        POSTリクエストを受け付ける。
        Method: POST
        Args:
            request:  HTTPリクエスト
            *args:    引数
            **kwargs: キーワード引数
        Returns:
            Response: HTTPレスポンス
        Raises:
            InternalServerError: 想定外エラー
        Create
            Date: 2025/11/17
            Author: Kato Shogo
        """
        try:
            return self.account_activate(request, *args, **kwargs)
        except APIException:
            # APIException関連はカスタムエラー処理が設定されている為そのまま親へスローする
            raise
        except Exception as e:
            # その他想定外エラーの場合もAPIエラーとする
            raise InternalServerError() from e

    def account_activate(self, request, *args, **kwargs):
        """
        対象アカウントを有効化する
        ※POSTメソッドでリクエストを受け入れるため、あえてcreateメソッド利用する(データ登録は行わない)
        Args:
            request:  HTTPリクエスト
            *args:    引数
            **kwargs: キーワード引数
        Method: POST
        Create
            Date: 2025/11/17
            Author: Kato Shogo
        """
        # 処理開始ログ出力(アプリケーションログ)
        modules.LogOutput.log_output(
            consts.LOG_LEVEL.INFO.value,
            md.get_message("MSGI003", [kino_id, str(request.data)]),
        )
        # 現在日時
        date_now: datetime = modules.FormatChanger.convert_to_jst(datetime.now())
        # CSRF Tokenの取得
        csrf_token = get_token(request)
        response_param = {
            "csrfToken": csrf_token,
            "executeAt": date_now.strftime("%Y/%m/%d %H:%M:%S"),
        }
        # 処理終了ログ出力(アプリケーションログ)
        modules.LogOutput.log_output(
            consts.LOG_LEVEL.INFO.value,
            md.get_message("MSGI004", [kino_id, str(response_param)]),
        )
        return Response(response_param)
