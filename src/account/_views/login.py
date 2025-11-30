from datetime import datetime

from django.db import transaction
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import APIException
from rest_framework.response import Response

# from models import V_USER
from account.models import M_User
from core import consts, modules
from core.auth_scheme.user_auth_backend import UserAuthBackend
from core.decorators import logging_sql_queries
from core.exceptions.custom_exceptions import InternalServerError, UnauthorizedError
from core.message import MessageDefinition as md

from ..serializer.login import LoginSerializer

# , UnauthorizedError


kino_id = "login"


# ユーザ状態管理トランへの更新後、エラーでロールバックされないように独自でトランザクションを切る
# @method_decorator(transaction.non_atomic_requests, name='dispatch')
class LoginViewSet(viewsets.ModelViewSet):
    """
    ログイン処理APIクラス
    Create
        Date: 2025/11/18
        Author: Kato Shogo
    """

    serializer_class = LoginSerializer
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
            Date: 2025/11/18
            Author: Kato Shogo
        """
        try:
            return self.login(request, *args, **kwargs)
        except APIException:
            # APIException関連はカスタムエラー処理が設定されている為そのまま親へスローする
            raise
        except Exception as e:
            # その他想定外エラーの場合もAPIエラーとする
            raise InternalServerError() from e

    @logging_sql_queries
    def login(self, request, *args, **kwargs):
        """
        ログインを行う
        ※ POSTメソッドでリクエストを受け入れるため、あえてcreateメソッド利用する(データ登録は行わない)
        Args:
            request:  HTTPリクエスト
            *args:    引数
            **kwargs: キーワード引数
        Method: POST
        Create
            Date: 2024/11/04
            Author: Kato Shogo
        """
        # 処理開始ログ出力(アプリケーションログ)
        modules.LogOutput.log_output(
            consts.LOG_LEVEL.INFO.value,
            md.get_message("MSGI003", [kino_id, str(request.data)]),
        )

        # リクエストパラメータの取得
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            self.email = serializer.validated_data.get("email", "")
            self.password = serializer.validated_data.get("password", "")
        else:
            # パラメータのバリデーションエラーログ出力(アプリケーションログ)
            modules.LogOutput.log_output(
                consts.LOG_LEVEL.INFO.value,
                md.get_message(
                    "MSGE001", [f"request parameter error: {serializer.errors}"]
                ),
            )
            raise InternalServerError()

        # 1. ユーザ認証処理(ユーザマスタに対する存在チェック)
        user_auth_backend = UserAuthBackend()
        request_user: M_User | None = user_auth_backend.authenticate(
            request, email=self.email, password=self.password
        )
        # ユーザマスタが存在しないか
        if request_user is None:
            # エラーログ出力(アプリケーションログ)
            # 一致するユーザが存在しませんでした。 メールアドレス:{0} パスワード:{1}
            modules.LogOutput.log_output(
                consts.LOG_LEVEL.ERROR.value,
                md.get_message("MSGE101", [self.email, self.password]),
            )
            raise UnauthorizedError()

        # SQL実行/SELECTログ出力(アプリケーションログ)
        # modules.LogOutput.log_output(consts.LOG_LEVEL.INFO.value, md.get_message('MSGI005', ['Exists取得(M_UserStatus):' + str(m_user_status_queryset.query)]))

        # 2. ユーザ状態管理マスタのチェック(アカウント状態/ロック中かのチェック)
        m_user_status_queryset = request_user.m_user_status_set.filter(
            m_user=request_user,
            is_account_lock=False,
        )
        # SQL実行/SELECTログ出力(アプリケーションログ)
        # modules.LogOutput.log_output(consts.LOG_LEVEL.INFO.value, md.get_message('MSGI005', ['Exists取得(M_UserStatus):' + str(m_user_status_queryset.query)]))
        # ユーザ状態管理マスタが存在しないか
        if not m_user_status_queryset.exists():
            return None

        response_param = {
            "email": (
                "" if request_user is None else request_user.email
            ),  # ログインメールアドレス
            "executeAt": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
        }
        # 処理終了ログ出力(アプリケーションログ)
        modules.LogOutput.log_output(
            consts.LOG_LEVEL.INFO.value,
            md.get_message("MSGI004", [kino_id, str(request.data)]),
        )
        return Response(response_param)
        # # 1. ユーザIDを基にユーザマスタビューへの存在チェック
        # if not cq_V_USER.exists_v_user(self.user_id):
        #     # ユーザが存在しない場合はエラーログを出力する
        #     cm.writeLog(const.LOG_TYPE['ERROR'], md.get_message('MSGW001', [f'v_user is not exists. user_id: {self.user_id}']))
        #     # ユーザマスタが存在しない場合
        #     raise UnauthorizedError()

        # # 2. ユーザー情報の取得(ビル取得の判定に使用する情報をユーザマスタビューより取得する)
        # current_user_instance =  self.get_user()
        # if current_user_instance is None:
        #     # ユーザIDに一致するユーザマスタビューが存在しない/SQLエラーの場合エラーとする
        #     # エラーログ出力(アプリケーションログ)
        #     cm.writeLog(const.LOG_TYPE['ERROR'], md.get_message('MSGE001', [f'No V_USER matching instance existed. user_id: {self.user_id}']))
        #     raise UnauthorizedError()

        # szk_kbn = current_user_instance.get('SZK_KBN')
        # ten_cd = current_user_instance.get('TEN_CD')

        # # 3. テナントユーザの場合、テナント自体の適用期間/削除フラグを基に存在チェックを行う
        # # テナントの場合
        # if szk_kbn == const.SZK_KBN['TENANT']:
        #     # ユーザのテナントCDに紐づくテナントの存在チェック
        #     if not cq_V_TEN.exists_v_ten(ten_cd, True):
        #         # テナントCDに一致するテナントデータが存在しない場合/SQLエラーの場合エラーとする
        #         cm.writeLog(const.LOG_TYPE['ERROR'], md.get_message('MSGW001', [f'v_ten is not exists. user_id: {self.user_id} ten_cd: {ten_cd}']))
        #         # テナントデータが存在しない場合
        #         raise UnauthorizedError()

        # # 上記以外(デベロッパー以外の想定外区分)の場合
        # elif szk_kbn not in const.DEVELOPER_SZK_KBN_LIST:
        #     # 想定外の所属区分が設定されていた場合エラーとする
        #     # エラーログ出力(アプリケーションログ)
        #     cm.writeLog(const.LOG_TYPE['ERROR'], md.get_message('MSGE001', [f'szk_kbn must be 1 ... 3. user_id: {self.user_id}']))
        #     # 想定外の所属区分が設定されている場合
        #     raise UnauthorizedError()

        # # 4. ユーザIDを基にアカウントロック管理トランを確認し、アカウントがロック中の場合
        # if cq_T_ACCOUNT_LOCK.exists_t_account_lock(self.user_id, const.ACCOUNT_LOCK_FLG['LOCK']):
        #     # アカウントロック中の場合はwarningログを出力する
        #     cm.writeLog(const.LOG_TYPE['WARNING'], md.get_message('MSGW001', [f'account_lock_flg is already locked. user_id: {self.user_id}']))
        #     # ログイン試行回数カウント判定(+試行回数上限のチェック)
        #     self.t_account_lock_update(serializer, self.user_id, self.user_id, False)
        #     raise UnauthorizedError()

        # # 5. ユーザ存在チェック(ユーザーマスタビューに対しユーザーID、パスワードにて照合を行う)
        # if not cq_V_USER.exists_v_user(self.user_id, self.encrypt_password):
        #     # アカウントロック中の場合はwarningログを出力する
        #     cm.writeLog(const.LOG_TYPE['WARNING'], md.get_message('MSGW001', [f'v_user is not exists. user_id: {self.user_id} password: {self.password}']))
        #     # ログイン試行回数カウント判定(+試行回数上限のチェック)
        #     self.t_account_lock_update(serializer, self.user_id, self.user_id, False)
        #     raise UnauthorizedError()

        # # ビルコード(2024/09-改修予定)※所属区分によって紐づけ/テナントマスタより(メイン)ビルの情報を取得し返す
        # # 6. ビル取得処理
        # # デベロッパーの場合：ユーザビル紐づけマスタよりメインビルフラグが"1"のビルCDを取得する
        # # テナントの場合：テナントマスタよりビルCDを取得する
        # bil_cd = '1' # 現状は「1」固定

        # # 7. ログイン完了によるログイン試行回数の初期化処理
        # # ログイン試行回数の初期化
        # self.t_account_lock_update(serializer, self.user_id, self.user_id, True)

        response_param = {
            "email": (
                "" if request_user is None else request_user.EMAIL
            ),  # ログインメールアドレス
            "executeAt": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
        }

        # 処理終了ログ出力(アプリケーションログ)
        lo.log_output(
            const.LOG_LEVEL.INFO.value,
            md.get_message("MSGI004", [kino_id, str(response_param)]),
        )
        return Response(response_param)

    # def get_user(self):
    #     """
    #     ユーザ情報(所属区分/テナントCD/パスワード発行日時)を取得する
    #     Returns:
    #         szk_kbn: 所属区分
    #     Author: Nakamura Tomohisa

    #     """
    #     queryset_user_szk_kbn = (
    #         V_USER.objects.filter(USER_ID=self.user_id, DLT_FLG=const.DEL_FLG['NON_DELETE'])
    #         .values('SZK_KBN', 'TEN_CD')
    #         .distinct()
    #     )

    #     # SQL実行/SELECTログ出力(アプリケーションログ)
    #     cm.writeLog(const.LOG_TYPE['INFO'], md.get_message('MSGI005', [str(queryset_user_szk_kbn.query)]))

    #     if queryset_user_szk_kbn.count() == 0:
    #         return None

    #     return queryset_user_szk_kbn.first()

    # def t_account_lock_update(self, serializer: LoginSerializer, target_user_id, user_id, isInit: bool = False):
    #     """
    #     アカウントロック管理トランへのデータ登録/更新を行う
    #     isInit
    #         Trueの場合：ログイン試行回数の初期化
    #         Falseの場合：ログイン試行回数カウント(+アカウントロック)
    #     Returns:
    #         -
    #     Author: Kato Shogo
    #     """
    #     # 1. アカウントロック管理トランの取得(0件取得の場合はNone/2件以上取得はExceptionをスローさせる)
    #     t_account_lock_instance = cq_T_ACCOUNT_LOCK.get_t_account_lock_instance_first(target_user_id)

    #     # 2. isInitによる分岐
    #     if isInit: # ログイン試行回数の初期化の場合
    #         # アカウントロック管理トランの取得状況による分岐
    #         if t_account_lock_instance is None: # アカウントロック管理トラン未作成の場合
    #             with transaction.atomic():
    #                 serializer.create_T_ACCOUNT_LOCK(
    #                     target_user_id=target_user_id,
    #                     login_attempts=0,
    #                     account_lock_flg=const.ACCOUNT_LOCK_FLG["NON_LOCK"],
    #                     user_id=user_id,
    #                     kino_id=kino_id,
    #                 )
    #         else: # インスタンスが存在する場合
    #             account_lock_flg = t_account_lock_instance.ACCOUNT_LOCK_FLG
    #             if account_lock_flg == const.ACCOUNT_LOCK_FLG["NON_LOCK"]:
    #                 with transaction.atomic():
    #                     t_account_lock_instance.LOGIN_ATTEMPTS = 0 # ログイン試行回数のみ初期化を行う
    #                     serializer.update_T_ACCOUNT_LOCK(
    #                         instance=t_account_lock_instance,
    #                         user_id=user_id,
    #                         kino_id=kino_id,
    #                     )
    #             else:
    #                 # アカウントロックがかけられている場合(※想定外エラー※)
    #                 # エラーログ出力(アプリケーションログ)
    #                 cm.writeLog(const.LOG_TYPE['ERROR'], md.get_message('MSGE001', [f'account_lock_flg is already locked. user_id: {self.user_id}']))
    #                 raise InternalServerError()

    #     else: # ログイン試行回数カウント(+アカウントロック)の場合
    #         # ログイン最大許容失敗数の取得
    #         cd_kbn_dtl_link_instance = cq_M_CKBN_DTL_LINK.get_cd_kbn_dtl_link_instance(const.MAX_LOGIN_COUNT_KNR_CD, const.MAX_LOGIN_COUNT_CD_KBN)
    #         if cd_kbn_dtl_link_instance is None:
    #             # コード区分情報の取得に失敗した場合はエラーとする
    #             # エラーログ出力(アプリケーションログ)
    #             cm.writeLog(const.LOG_TYPE['ERROR'], md.get_message('MSGE017', [const.MAX_LOGIN_COUNT_KNR_CD, const.MAX_LOGIN_COUNT_CD_KBN]))
    #             raise InternalServerError()

    #         max_login_count = cd_kbn_dtl_link_instance.CD_KBN_NAME

    #         # アカウントロック管理トランの取得状況による分岐
    #         if t_account_lock_instance is None: # アカウントロック管理トラン未作成の場合
    #             with transaction.atomic():
    #                 serializer.create_T_ACCOUNT_LOCK(
    #                     target_user_id=target_user_id,
    #                     login_attempts=1,
    #                     account_lock_flg=const.ACCOUNT_LOCK_FLG["LOCK"] if int(max_login_count) < 1 else const.ACCOUNT_LOCK_FLG["NON_LOCK"],
    #                     user_id=user_id,
    #                     kino_id=kino_id,
    #                 )

    #         else: # インスタンスが存在する場合
    #             account_lock_flg = t_account_lock_instance.ACCOUNT_LOCK_FLG
    #             next_login_attempts = t_account_lock_instance.LOGIN_ATTEMPTS + 1
    #             if account_lock_flg == const.ACCOUNT_LOCK_FLG["NON_LOCK"]:
    #                 with transaction.atomic():
    #                     t_account_lock_instance.LOGIN_ATTEMPTS = next_login_attempts # ログイン試行回数のカウント
    #                     if int(max_login_count) < next_login_attempts:
    #                         t_account_lock_instance.ACCOUNT_LOCK_FLG = const.ACCOUNT_LOCK_FLG["LOCK"] # アカウントロックを掛ける
    #                     serializer.update_T_ACCOUNT_LOCK(
    #                         instance=t_account_lock_instance,
    #                         user_id=user_id,
    #                         kino_id=kino_id,
    #                     )
    #             else:
    #                 with transaction.atomic():
    #                     # 試行回数のみ更新を行う
    #                     t_account_lock_instance.LOGIN_ATTEMPTS = next_login_attempts # ログイン試行回数のカウント
    #                     serializer.update_T_ACCOUNT_LOCK(
    #                         instance=t_account_lock_instance,
    #                         user_id=user_id,
    #                         kino_id=kino_id,
    #                     )
