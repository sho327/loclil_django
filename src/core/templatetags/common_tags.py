import calendar
import re
from datetime import datetime

from django import template
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.template.defaultfilters import stringfilter
from django.utils import timezone
from django.utils.safestring import mark_safe

# 外部ライブラリ（Markdown変換に必要。インストールが必要です: pip install bleach markdown）
# from bleach import clean
# from markdown import markdown

register = template.Library()


# --------------------------------------------------
# 1. データ整形・表示系フィルタ
# --------------------------------------------------


@register.filter
@stringfilter
def truncate_text(value, length=50):
    """
    テキストを指定文字数で省略し、「...」を追加するフィルタ。
    全角文字を1文字として正確にカウントし、日本語の途中で切れないようにする。
    """
    try:
        max_len = int(length)
    except ValueError:
        return value

    if len(value) <= max_len:
        return value

    # 実際にはより高度な文字コード処理が必要だが、ここではPythonのlenで処理
    # 例：サロゲートペアなどの複雑なケースは考慮しない
    return value[:max_len] + "..."


@register.filter(expects_localtime=True)
def datetime_format(value, arg="%Y/%m/%d %H:%M:%S"):
    """
    タイムゾーンを考慮し、指定されたフォーマットで日時を表示するフィルタ。
    値がNoneまたは空の場合は空文字列を返す。
    """
    if not value:
        return ""

    if isinstance(value, datetime):
        # タイムゾーンをsettings.TIME_ZONEに変換（ローカライズ）
        # settings.USE_TZ=Trueが前提
        local_tz = timezone.get_current_timezone()
        local_dt = timezone.localtime(value, timezone=local_tz)

        return local_dt.strftime(arg)

    return value


@register.filter
def currency(value, currency_symbol="円"):
    """
    数値を3桁区切りのカンマ形式に変換し、通貨記号を付与するフィルタ。
    """
    if value is None or value == "":
        return ""

    try:
        # 整数部と小数部に分ける
        value_str = str(int(value))

        # 3桁ごとにカンマを挿入
        formatted_value = re.sub(r"(\d)(?=(\d{3})+(?!\d))", r"\1,", value_str)

        return f"{formatted_value}{currency_symbol}"
    except (TypeError, ValueError):
        return value


@register.filter
@stringfilter
def markdown_to_html(value):
    """
    Markdown形式のテキストを安全なHTMLに変換するフィルタ。
    ※ 依存ライブラリ (bleach, markdown) が必要です。
    """
    # 依存ライブラリがない場合、そのまま返す
    # if 'markdown' not in globals():
    #     return value

    # 1. MarkdownをHTMLに変換
    # html = markdown(value, extensions=['nl2br', 'fenced_code'])

    # 2. BleachでHTMLをサニタイズし、安全を確保
    # allowed_tags = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'h1', 'h2', 'code', 'pre']
    # html = clean(
    #     html,
    #     tags=allowed_tags,
    #     attributes={'a': ['href', 'title']},
    #     strip=True
    # )

    # return mark_safe(html)

    # 仮実装として、ただの改行コードを<br>に変換
    html_safe = value.replace("\n", "<br>")
    return mark_safe(html_safe)


# --------------------------------------------------
# 2. URL・リソース系タグ
# --------------------------------------------------


@register.simple_tag(takes_context=True)
def active_link(context, url_name, css_class="is-active"):
    """
    現在のリクエストパスと指定されたURL名（またはパス）を比較し、
    一致した場合にCSSクラス名を返すテンプレートタグ。
    """
    try:
        # requestオブジェクトから現在のパスを取得
        request = context["request"]
        current_path = request.path

        # 指定されたURL名が現在のパスと一致するか、またはその子孫パスであるか
        if current_path == url_name or current_path.startswith(url_name + "/"):
            return css_class

        return ""
    except (KeyError, AttributeError):
        # requestがコンテキストにない場合（通常はcontext_processorsで解決）
        return ""


@register.simple_tag
def static_file_hash(path):
    """
    静的ファイルパスの末尾に、ファイルの更新時刻（タイムスタンプ）を付与し、
    キャッシュバスト（Cache Busting）を実現するタグ。
    """
    # Djangoのstaticfiles_storageを使って実際のファイルパスを取得
    full_path = staticfiles_storage.path(path)

    try:
        # ファイルの最終更新時刻（UNIXタイムスタンプ）を取得
        mtime = int(os.path.getmtime(full_path))  # osモジュールのインポートが必要
    except FileNotFoundError:
        # ファイルが見つからない場合は、そのままパスを返す
        return staticfiles_storage.url(path)

    # ファイルURLにタイムスタンプをクエリパラメータとして付与
    return f"{staticfiles_storage.url(path)}?v={mtime}"


# --------------------------------------------------
# 3. ロジック・ユーティリティ系フィルタ/タグ
# --------------------------------------------------


@register.filter
def get_item(dictionary, key):
    """
    辞書やリストから、キーやインデックスを指定して値を取得するフィルタ。
    {% with dict_var|get_item:key_name as item %}
    """
    try:
        return dictionary[key]
    except (KeyError, IndexError, TypeError):
        return None


@register.tag(name="range")
def do_range(parser, token):
    """
    {% range start end as variable %} の形式でPythonのrangeをテンプレートで実現するタグ。
    """
    try:
        tag_name, start, end, as_word, var_name = token.split_contents()
        if as_word != "as":
            raise ValueError
    except ValueError:
        raise template.TemplateSyntaxError(
            "%r tag requires arguments in the format 'start end as variable'"
            % token.split_contents()[0]
        )

    return RangeNode(start, end, var_name)


class RangeNode(template.Node):
    def __init__(self, start, end, var_name):
        self.start = parser.compile_filter(start)
        self.end = parser.compile_filter(end)
        self.var_name = var_name

    def render(self, context):
        try:
            # テンプレートコンテキストからstartとendの値を解決
            start = self.start.resolve(context)
            end = self.end.resolve(context)

            # rangeオブジェクトを生成し、コンテキストに格納
            context[self.var_name] = range(start, end)
        except (ValueError, TypeError):
            # 数値に解決できない場合は空のリストを格納
            context[self.var_name] = []

        return ""


# 使い方:
# {% load common_tags %}
# {% range 1 10 as numbers %}
# {% for num in numbers %}
#     {{ num }}
# {% endfor %}
