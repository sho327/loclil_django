# 🛠️ ユーザー属性に基づく Site 切り替えミドルウェア

**目標:** ログインしているユーザーが特定の条件（例: **スタッフ**または**管理者**）を満たした場合に、`settings.SITE_ID` の設定を一時的に上書きし、メール送信やリンク生成時に**ステージング環境**のドメイン（例: ID=3）を参照するようにする。

## 1\. 📂 設定の準備 (`settings.py` と DB)

まず、切り替えたい Site ID を `settings.py` に定義し、データベースにその Site 情報を登録します。

### A. `settings.py` の定義

```python
# settings.py

# デフォルトのプロダクションサイト
SITE_ID = 1

# スタッフや開発者が参照すべきステージングサイトID
# (DBのdjango_siteテーブルにID=3として登録されていることを想定)
STAGING_SITE_ID = 3

# Siteフレームワークとカスタムミドルウェアの追加
INSTALLED_APPS = [
    # ...
    'django.contrib.sites',
    # ...
]

MIDDLEWARE = [
    # ... 他のミドルウェア ...
    # 'django.contrib.sites.middleware.CurrentSiteMiddleware',
    # ↑これは標準的なドメインベース切り替え用。代わりにカスタムミドルウェアを使う。
    'core.middleware.UserSiteSwitcherMiddleware', # ← ここにカスタムミドルウェアを追加
    # ...
]
```

### B. データベースの確認

管理画面 (`/admin/sites/site/`) で以下の Site レコードが存在することを確認します。

| ID    | Domain           | Name             |
| :---- | :--------------- | :--------------- |
| **1** | `shelio.com`     | 本番環境         |
| **3** | `stg.shelio.com` | ステージング環境 |

---

## 2\. 📝 カスタムミドルウェアの実装

`core/middleware.py` に、リクエストの処理開始時にユーザーの情報をチェックし、`settings` を上書きするミドルウェアを作成します。

```python
# core/middleware.py

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin

User = get_user_model()

class UserSiteSwitcherMiddleware(MiddlewareMixin):
    """
    ログインユーザーの属性に応じて、参照する SITE_ID を動的に切り替えるミドルウェア。
    """

    def process_request(self, request):
        # ユーザー認証情報がロードされた後（SessionMiddleware, AuthenticationMiddlewareの後）に実行
        # 認証済みユーザーがいる場合に処理を実行
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user

            # 1. ユーザー属性による切り替えロジック
            # 例: スタッフ権限を持つユーザーは、常にステージング環境のSiteを参照する
            if user.is_staff or user.is_superuser:
                # settings.pyで定義したステージングIDを取得
                target_site_id = getattr(settings, 'STAGING_SITE_ID', None)

                if target_site_id:
                    # ⭐ settingsを一時的に上書きし、SiteフレームワークがID=3を参照するように強制する
                    settings.SITE_ID = target_site_id

            # 2. その他の動的な切り替えロジックの例
            # elif user.email.endswith('@partner.com'):
            #     settings.SITE_ID = settings.PARTNER_SITE_ID

            # ロジックが適用されなかった場合、settings.pyで定義されたデフォルト値 (SITE_ID=1) がそのまま使用される
```

---

## 3\. ⚙️ 効果とコードへの影響

このミドルウェアが動作することで、以下の効果が得られます。

### A. サービス層への影響

`UserService` など、リクエストオブジェクトを持たないサービス層のコードでも、**スタッフがログインしている間**は、自動的にステージングドメインを参照するようになります。

```python
# account/services.py (メール送信処理内)

from django.contrib.sites.models import Site
from django.conf import settings # SITE_IDを上書きされたsettingsを参照

def send_activation_email(...):
    # ミドルウェアにより settings.SITE_ID が上書きされている可能性がある
    current_site = Site.objects.get_current()
    domain = current_site.domain

    # ユーザーがスタッフでログインしている場合: domainは "stg.shelio.com" になる
    # 一般ユーザーの場合: domainは "shelio.com" になる
    # ...
```

### B. テンプレートへの影響

カスタムタグやテンプレートフィルタ、または `Site` に依存する組み込み機能も影響を受け、参照するドメインが切り替わります。

- **利点:** テスト目的でスタッフが本番環境で操作を行う際、間違って本番ドメインのリンクをメールに含めるのを防ぐことができます。

### ⚠️ 注意点

- **ミドルウェアの順序:** このミドルウェアは、`SessionMiddleware` および `AuthenticationMiddleware` の**後**に配置し、`request.user` がロードされた後に実行されるようにしてください。
- **グローバルな上書き:** `settings.SITE_ID` の上書きは**スレッドローカル**で処理されますが、設定はグローバルなものであるため、予期せぬ副作用がないか注意深くテストする必要があります。
