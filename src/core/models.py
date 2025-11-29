from django.db import models


class BaseModel(models.Model):
    # created_by = models.CharField(db_column='created_by', verbose_name='作成者', db_comment='作成者', max_length=32, null=True, blank=True)
    created_by = models.DecimalField(
        db_column="created_by",
        verbose_name="作成者/id",
        db_comment="作成者/id",
        decimal_places=0,
        max_digits=20,
        null=True,
    )
    # auto_now_add はインスタンスの作成(DBにINSERT)する度に更新
    # created_at = models.DateTimeField(db_column='created_at', verbose_name='作成日時', db_comment='作成日時', auto_now_add=True, null=True, blank=True)
    created_at = models.DateTimeField(
        db_column="created_at",
        verbose_name="作成日時",
        db_comment="作成日時",
        null=True,
        blank=True,
    )
    created_method = models.CharField(
        db_column="created_method",
        verbose_name="作成処理",
        db_comment="作成処理",
        max_length=128,
        null=True,
        blank=True,
    )
    # updated_by = models.CharField(db_column='updated_by', verbose_name='更新者', db_comment='更新者', max_length=32, null=True, blank=True)
    updated_by = models.DecimalField(
        db_column="updated_by",
        verbose_name="更新者/id",
        db_comment="更新者/id",
        decimal_places=0,
        max_digits=20,
        null=True,
    )
    # auto_now=Trueの場合はモデルインスタンスを保存する度に現在の時間で更新
    # updated_at = models.DateTimeField(db_column='updated_at', verbose_name='更新日時', db_comment='更新日時', auto_now=True, null=True, blank=True)
    updated_at = models.DateTimeField(
        db_column="updated_at",
        verbose_name="更新日時",
        db_comment="更新日時",
        null=True,
        blank=True,
    )
    updated_method = models.CharField(
        db_column="updated_method",
        verbose_name="更新処理",
        db_comment="更新処理",
        max_length=128,
        null=True,
        blank=True,
    )
    deleted_at = models.DateTimeField(
        db_column="deleted_at",
        verbose_name="削除日時",
        db_comment="削除日時",
        null=True,
        blank=True,
        db_default=None,
        default=None,
    )

    class Meta:
        abstract = True
