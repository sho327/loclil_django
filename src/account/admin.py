from django.contrib import admin

from account.models import M_User, M_UserProfile, T_LoginHisory, T_UserToken

admin.site.register(M_User)
admin.site.register(M_UserProfile)
admin.site.register(T_LoginHisory)
admin.site.register(T_UserToken)
