from django.contrib import admin
from django.urls import include, path

# from account.urls import router as account_router

urlpatterns = [
    path("admin/", admin.site.urls),
    # path("account/", include(account_router.urls)),
    # path(f'{BASE_API_PATH}/token/', include('apps.token.urls')),
    # path(f'{BASE_API_PATH}/auth/', include(auth_router.urls)),
]
