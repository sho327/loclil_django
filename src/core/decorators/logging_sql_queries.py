from functools import wraps
from typing import Any, Callable, List, Tuple

from django.db import connection

# --- 共通モジュールの新しいパス ---
from core.consts import LOG_LEVEL, LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id


def logging_sql_queries(func: Callable) -> Callable:
    """
    デコレートされた関数が実行された際に発行されたSQLクエリをキャプチャし、
    ACCESSロガーまたはAPPLICATIONロガーに出力するデコレータ。
    """

    class QueryLogger:
        """
        connection.execute_wrapper に渡され、実行されたクエリを収集するクラス
        """

        def __init__(self):
            # 実行されたSQLクエリとそのパラメータを格納
            self.queries: List[Tuple[str, Any]] = []

        def __call__(
            self, execute: Callable, sql: str, params: Any, many: bool, context: Any
        ) -> Any:
            """クエリ実行時に呼び出されるフック"""
            self.queries.append((sql, params))
            return execute(sql, params, many, context)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = QueryLogger()

        # 1. クエリロガーを接続に設定し、デコレートされた関数を実行
        with connection.execute_wrapper(logger):
            result = func(*args, **kwargs)

        # 2. ロギング処理

        # --- ヘッダーログ出力 ---
        log_output_by_msg_id(
            log_id="MSGI001",
            params=[f"=== Executed SQL in function: {func.__name__} ==="],
            logger_name=LOG_METHOD.APPLICATION.value,
            log_level=LOG_LEVEL.INFO.value,
        )

        # --- クエリとパラメータのログ出力 ---
        for sql, params in logger.queries:
            # SQLとパラメータを結合して出力
            full_sql_message = f"{sql} / Params: {str(params)}"

            log_output_by_msg_id(
                log_id="MSGI001",
                params=[full_sql_message],
                logger_name=LOG_METHOD.APPLICATION.value,
                log_level=LOG_LEVEL.INFO.value,
            )

        return result

    return wrapper
