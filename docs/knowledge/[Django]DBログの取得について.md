📘 Django / DRF の SQL ログをまとめて取得する方法まとめ

---

📝 結論

Django の SQL を確実に取得したいなら、connection.execute_wrapper() を利用するのが最適。
ViewSet の create / update / list などで動いた SQL をすべてキャプチャできる。

---

🔥 1. QueryLogger — SQL を貯めるロガー

```python
from django.db import connection

class QueryLogger:
def **init**(self):
self.queries = []

    def __call__(self, execute, sql, params, many, context):
        self.queries.append({"sql": sql, "params": params})
        return execute(sql, params, many, context)
```

---

🔥 2. record_sql — 任意の関数を丸ごと SQL ロギングするデコレータ

あなたが以前使っていた record_sql 関数も整理してまとめました。

✔ record_sql（デコレータ形式）

```python
def record_sql(func):
from django.db import connection

    class QueryLogger:
        def __init__(self):
            self.queries = []

        def __call__(self, execute, sql, params, many, context):
            self.queries.append((sql, params))
            return execute(sql, params, many, context)

    def wrapper(*args, **kwargs):
        logger = QueryLogger()
        with connection.execute_wrapper(logger):
            result = func(*args, **kwargs)

        print("=== Executed SQL ===")
        for sql, params in logger.queries:
            print(sql, params)

        return result

    return wrapper
```

使い方：

```python
@record_sql
def some_process():
User.objects.get(id=1)
Project.objects.filter(status=1).first()
```

→ 関数中の SQL がすべて出力される。

---

🔥 3. ViewSet の create() を囲んで SQL を取る方法

```python
class UserViewSet(ModelViewSet):

    def create(self, request, *args, **kwargs):
        logger = QueryLogger()
        with connection.execute_wrapper(logger):
            response = super().create(request, *args, **kwargs)

        print("========== SQL LOG ==========")
        for q in logger.queries:
            print(q["sql"], q["params"])

        return response
```

✔ これで捕捉できるもの
• serializer.is_valid() 内の SELECT
• serializer.save() の INSERT / UPDATE
• 外部キーチェックの SELECT
• signals の SQL
• create 内の ORM すべて

---

🔥 4. すべての ViewSet に SQL ログを自動適用する Mixin

```python
class SQLLogMixin:
def \_log_sql(self, func, *args, \*\*kwargs):
logger = QueryLogger()
with connection.execute_wrapper(logger):
response = func(*args, \*\*kwargs)

        print(f"========== SQL LOG for {func.__name__} ==========")
        for q in logger.queries:
            print(q["sql"], q["params"])

        return response

    def create(self, request, *args, **kwargs):
        return self._log_sql(super().create, request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return self._log_sql(super().update, request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        return self._log_sql(super().list, request, *args, **kwargs)
```

利用例：

```python
class UserViewSet(SQLLogMixin, ModelViewSet):
queryset = User.objects.all()
serializer_class = UserSerializer
```

---

🧪 5. 「first() の時の SQL」について

✔ SQL 文を見たい（実行前）

```python
qs = instance.m_user_status_set.order_by("id")[:1]
print(qs.query)
```

→ 0 件でも安全に SQL 表示。

✔ 実行された SQL を見たい

```python
with connection.execute_wrapper(logger):
result = qs.first()
```

→ 0 件でも None になるだけで SQL は確実にキャプチャ。

---

⚠️ 6. 捕捉できない部分（注意点）

場所 SQL 捕捉？ 理由
ViewSet 内（create/update/list） ✔ その中で wrapper が生きている
serializer / signals ✔ create() 内で動く
認証処理 (Authentication classes) ✗ ViewSet より前で実行される
Middleware ✗ ViewSet の外側

→ 認証や middleware の SQL を取りたい時は、
そちら側でも execute_wrapper を使う必要がある。

---

📌 まとめ

目的 ベストな方法
関数単位で SQL をまとめて取りたい record_sql デコレータ
ViewSet の SQL を全部捕捉したい execute_wrapper() で create/update/list を囲む
全 ViewSet に適用したい SQLLogMixin
実行された SQL を確実にキャプチャしたい execute_wrapper
実行前の SQL 文を見たい qs.query

---
