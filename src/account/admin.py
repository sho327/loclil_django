from django.contrib import admin

from .models.m_user import M_User

# from .models.T_USER_HISTORY import T_USER_HISTORY
# from .models.T_USER_STATUS import T_USER_STATUS

admin.site.register(M_User)
# admin.site.register(T_USER_HISTORY)
# admin.site.register(T_USER_STATUS)
