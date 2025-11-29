import datetime as dt
from datetime import datetime
from typing import Optional

from django.utils import timezone

# 役割: 日付/時刻、タイムゾーン、文字列変換処理を担う。
# 　　  DBのUTC時刻とユーザー表示のJST時刻の相互変換、表示フォーマット調整。

# Djangoの設定からタイムゾーンを取得する前提
SITE_TIMEZONE = timezone.get_current_timezone()


def convert_to_jst(pDate: datetime) -> Optional[datetime]:
    """
    NaiveなDatetimeをJST (Aware) に変換する。
    """
    if pDate is None:
        return None

    # Naiveな日時として扱い、SITE_TIMEZONE (JST) にローカライズ
    if pDate.tzinfo is None or pDate.tzinfo.utcoffset(pDate) is None:
        pDate = timezone.make_aware(pDate, SITE_TIMEZONE)

    return pDate.astimezone(SITE_TIMEZONE)


def convert_to_utc(pDate: datetime) -> Optional[datetime]:
    """
    JST/AwareなDatetimeをUTC (Aware) に変換する。
    DB保存時など、標準のUTC時刻に戻す際に使用。
    """
    if pDate is None:
        return None

    # Naiveな場合はJSTとして認識させる
    if pDate.tzinfo is None or pDate.tzinfo.utcoffset(pDate) is None:
        pDate = timezone.make_aware(pDate, SITE_TIMEZONE)

    return pDate.astimezone(dt.timezone.utc)


def str_to_date(
    target_string: str,
    target_format: str = "%Y/%m/%d %H:%M:%S",
    timezone_name: str = "",
) -> Optional[datetime]:
    """
    日付文字列からdatetime型へのフォーマット変換。必要に応じてJST/UTCに変換する。
    ※timezone変数名を 'timezone_name' に変更しました。
    """
    if target_string is None or target_string == "":
        return None

    return_date = datetime.strptime(target_string, target_format)

    if timezone_name.lower() == "jst":
        # JSTとしてローカライズ
        return_date = timezone.make_aware(return_date, SITE_TIMEZONE)
    elif timezone_name.lower() == "utc":
        # UTCとしてローカライズ
        return_date = timezone.make_aware(return_date, dt.timezone.utc)

    return return_date


def date_to_str(
    target_date: datetime,
    target_format: str = "%Y/%m/%d %H:%M:%S",
    timezone_name: str = "",
) -> str:
    """
    date/datetime型から日付文字列へのフォーマット変換。
    ※timezone変数名を 'timezone_name' に変更しました。
    """
    if target_date is None:
        return ""

    # タイムゾーンの調整
    if timezone_name.lower() == "jst":
        target_date = convert_to_jst(target_date)
    elif timezone_name.lower() == "utc":
        target_date = convert_to_utc(target_date)

    # 調整後の日付を文字列に変換
    if target_date is None:
        return ""

    return target_date.strftime(target_format)


def get_time_ago_string(dt_obj: Optional[datetime]) -> str:
    """
    現在時刻から指定された時刻がどれだけ前かを計算し、文字列で返す。（例: '5分前', '2日前'）
    ※引数名を 'dt_obj' に変更しました。
    """
    if dt_obj is None:
        return "しばらく前"

    # Awareな datetimeに変換 (UTC or JST)
    if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
        dt_obj = timezone.make_aware(dt_obj, timezone.utc)

    now = timezone.now()
    delta = now - dt_obj

    if delta < dt.timedelta(minutes=1):
        return "たった今"
    elif delta < dt.timedelta(hours=1):
        minutes = int(delta.total_seconds() // 60)
        return f"{minutes}分前"
    elif delta < dt.timedelta(days=1):
        hours = int(delta.total_seconds() // 3600)
        return f"{hours}時間前"
    elif delta < dt.timedelta(days=30):
        days = delta.days
        return f"{days}日前"
    else:
        # 30日以上前はJSTで通常の日付表示
        # ※ここでは date_to_str 関数を使用
        return date_to_str(dt_obj, target_format="%Y/%m/%d", timezone_name="jst")
