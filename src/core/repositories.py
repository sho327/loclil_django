from django.db.models import Model, QuerySet
from django.utils import timezone


class BaseRepository:
    """全てのモデルで共通のCRUD/論理削除ロジックを提供する基底クラス"""

    model: type[Model] = None

    def __init__(self):
        if self.model is None:
            raise NotImplementedError(
                "BaseRepositoryを継承する際は、model属性を設定してください。"
            )

    # ------------------------------------------------------------------
    # 内部メソッド: QuerySetのベースを定義
    # ------------------------------------------------------------------

    def _get_alive_queryset(self) -> QuerySet:
        """論理削除されていないレコードのみを取得するQuerySet (内部利用)"""
        return self.model.objects.filter(deleted_at__isnull=True)

    def _get_deleted_queryset(self) -> QuerySet:
        """論理削除されたレコードのみを取得するQuerySet (内部利用)"""
        return self.model.objects.filter(deleted_at__isnull=False)

    def _get_all_queryset(self) -> QuerySet:
        """論理削除済みを含む全てのレコードを取得するQuerySet (内部利用)"""
        return self.model.objects.all()

    # ------------------------------------------------------------------
    # 外部公開メソッド: 主キー検索
    # ------------------------------------------------------------------

    def get_alive_by_pk(self, pk: int) -> Model | None:
        """主キーで生存している（論理削除されていない）レコードを取得"""
        try:
            # 論理削除されていないことを確認
            return self._get_alive_queryset().get(pk=pk)
        except self.model.DoesNotExist:
            return None

    def get_deleted_by_pk(self, pk: int) -> Model | None:
        """主キーで論理削除されたレコードのみを取得"""
        try:
            # 論理削除フラグが立っていることを確認
            return self._get_deleted_queryset().get(pk=pk)
        except self.model.DoesNotExist:
            return None

    def get_all_by_pk(self, pk: int) -> Model | None:  # ★ 新規追加
        """主キーで、論理削除の状態を問わず存在するレコードを取得"""
        try:
            # フィルタリングなしのQuerySetで検索
            return self._get_all_queryset().get(pk=pk)
        except self.model.DoesNotExist:
            return None

    # ------------------------------------------------------------------
    # 外部公開メソッド: 単一取得（条件検索）
    # ------------------------------------------------------------------

    def get_alive_one_or_none(self, **kwargs) -> Model | None:
        """論理削除されていないレコードから、条件で1件取得"""
        try:
            # 論理削除されていないQuerySetをベースにgetを呼び出す
            return self._get_alive_queryset().get(**kwargs)
        except self.model.DoesNotExist:
            return None

    def get_deleted_one_or_none(self, **kwargs) -> Model | None:
        """論理削除されたレコードから、条件で1件取得"""
        try:
            # 論理削除フラグが立っているQuerySetをベースにgetを呼び出す
            return self._get_deleted_queryset().get(**kwargs)
        except self.model.DoesNotExist:
            return None

    def get_all_one_or_none(self, **kwargs) -> Model | None:
        """論理削除の状態を問わず存在するレコードから、条件で1件取得"""
        try:
            # フィルタリングなしのQuerySetをベースにgetを呼び出す
            return self._get_all_queryset().get(**kwargs)
        except self.model.DoesNotExist:
            return None

    # ------------------------------------------------------------------
    # 外部公開メソッド: 全件検索
    # ------------------------------------------------------------------

    def get_alive_records(self) -> QuerySet:
        """全てのアクティブ（論理削除されていない）なレコードを取得"""
        return self._get_alive_queryset().all()

    def get_deleted_records(self) -> QuerySet:
        """論理削除された（deleted_at IS NOT NULL）レコードのみを全て取得する。"""
        return self._get_deleted_queryset().all()

    def get_all_records(self) -> QuerySet:
        """全ての論理削除の状態を問わず存在するレコードを取得"""
        return self._get_all_queryset().all()

    # ------------------------------------------------------------------
    # 外部公開メソッド: データ操作
    # ------------------------------------------------------------------

    def create(self, **kwargs) -> Model:
        """レコードの作成"""
        # 単純なModel Managerのcreateをラップ
        return self.model.objects.create(**kwargs)

    def update(self, instance: Model, **kwargs) -> Model:
        """レコードの更新"""
        # 既存のインスタンスの属性を更新し、save()を呼び出す
        for key, value in kwargs.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    def soft_delete(self, instance: Model):
        """レコードの論理削除 (deleted_atを設定)"""
        if hasattr(instance, "deleted_at"):
            instance.deleted_at = timezone.now()
            instance.save(update_fields=["deleted_at"])

    def hard_delete(self, instance: Model):
        """レコードの物理削除"""
        instance.delete()

    def restore(self, instance: Model):
        """レコードの復元 (deleted_atをNULLに)"""
        if hasattr(instance, "deleted_at"):
            instance.deleted_at = None
            instance.save(update_fields=["deleted_at"])
