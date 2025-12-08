from typing import overload, Optional

from django.db.models import QuerySet, Q

from account.models import M_UserProfile
from core.repositories import BaseRepository

M_UserProfileQuerySet = QuerySet[M_UserProfile]


class M_UserProfileRepository(BaseRepository):
    """
    ユーザプロフィールマスタ(M_UserProfile)モデル専用のリポジトリクラス。

    データ永続化層へのアクセスを抽象化し、ビジネスロジックから分離する役割を担う。
    論理削除の考慮や基本的なCRUD操作はBaseRepositoryに委譲し、本クラスではユーザー固有の検索条件を定義する。
    """

    # 必須：対象モデルを設定 (BaseRepositoryの初期化で使用される)
    model: M_UserProfile = M_UserProfile

    # ------------------------------------------------------------------
    # BaseRepositoryから継承される主なメソッド群
    # ------------------------------------------------------------------
    # 【内部QuerySet】
    # * _get_alive_queryset()      # 論理削除されていないレコードのベースQuerySet
    # * _get_deleted_queryset()    # 論理削除されたレコードのベースQuerySet
    # * _get_all_queryset()        # 論理削除済みを含む全てのレコードのベースQuerySet

    # 【主キー検索】
    # * get_alive_by_pk(pk)        # 主キーで「生存している」（論理削除されていない）レコードを取得
    # * get_deleted_by_pk(pk)      # 主キーで「論理削除された」レコードのみを取得
    # * get_all_by_pk(pk)          # 主キーで、論理削除の状態を問わず存在するレコードを取得

    # 【単一取得（条件検索）】
    # * get_alive_one_or_none(**kwargs)  # 論理削除されていないレコードから、条件で1件取得
    # * get_deleted_one_or_none(**kwargs)# 論理削除されたレコードから、条件で1件取得
    # * get_all_one_or_none(**kwargs)    # 論理削除の状態を問わず存在するレコードから、条件で1件取得

    # 【全件検索】
    # * get_alive_records()        # 全ての「生存している」（論理削除されていない）レコードを取得
    # * get_deleted_records()      # 全ての「論理削除された」レコードのみを取得
    # * get_all_records()          # 全ての論理削除の状態を問わず存在するレコードを取得

    # 【データ操作】
    # * create(**kwargs)           # レコードの作成
    # * update(instance, **kwargs) # レコードの更新
    # * soft_delete(instance)      # レコードの論理削除 (deleted_atを設定)
    # * hard_delete(instance)      # レコードの物理削除
    # * restore(instance)          # レコードの復元 (deleted_atをNULLに)

    # ------------------------------------------------------------------
    # 共通で追加されるメソッドの型付けだけ行う
    # ------------------------------------------------------------------
    # 【主キー検索】
    # @overload
    # def get_alive_by_pk(self, pk: int) -> M_UserProfile | None: ...
    # @overload
    # def get_deleted_by_pk(self, pk: int) -> M_UserProfile | None: ...
    # @overload
    # def get_all_by_pk(self, pk: int) -> M_UserProfile | None: ...

    # 【単一取得（条件検索）】
    # @overload
    # def get_alive_one_or_none(self, **kwargs) -> M_UserProfile | None: ...
    # @overload
    # def get_deleted_one_or_none(self, **kwargs) -> M_UserProfile | None: ...
    # @overload
    # def get_all_one_or_none(self, **kwargs) -> M_UserProfile | None: ...

    # 【全件検索】
    # @overload
    # def get_alive_records(self) -> M_UserProfileQuerySet: ...
    # @overload
    # def get_deleted_records(self) -> M_UserProfileQuerySet: ...
    # @overload
    # def get_all_records(self) -> M_UserProfileQuerySet: ...

    # ------------------------------------------------------------------
    # モデルに対する固有のデータ取得処理
    # ------------------------------------------------------------------
    def find_public_profiles(
        self,
        search_word: Optional[str] = None,
        location: Optional[str] = None,
        skill_tag: Optional[str] = None,
    ) -> M_UserProfileQuerySet:
        """
        公開プロフィールを検索する

        Args:
            search_word: 表示名またはスキルタグで検索するキーワード
            location: 所在地で検索するキーワード
            skill_tag: スキルタグで検索するキーワード

        Returns:
            検索条件に合致するプロフィールのQuerySet
        """
        queryset = self._get_alive_queryset().filter(is_public=True).select_related("m_user")

        # 検索条件を組み立て
        if search_word:
            queryset = queryset.filter(
                Q(display_name__icontains=search_word)
                | Q(skill_tags_raw__icontains=search_word)
            )

        if location:
            queryset = queryset.filter(location__icontains=location)

        if skill_tag:
            queryset = queryset.filter(skill_tags_raw__icontains=skill_tag)

        return queryset.order_by("-created_at")
