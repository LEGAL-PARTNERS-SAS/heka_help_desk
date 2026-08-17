from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/token/',         TokenObtainPairView.as_view(),  name='tokenObtain'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(),     name='tokenRefresh'),
    path('api/auth/token/verify/',  TokenVerifyView.as_view(),      name='tokenVerify'),
    path('',          include('apps.core.urls')),
    path('usuarios/', include('apps.users.urls')),
    path('tickets/',  include('apps.tickets.urls')),
    path('panel/',    include('apps.admin_panel.urls')),   # <-- NUEVO
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
