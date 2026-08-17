from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('',                                views.ticketListView,          name='list'),
    path('nuevo/',                          views.ticketCreateView,        name='create'),
    path('<int:pk>/',                       views.ticketDetailView,        name='detail'),
    path('<int:pk>/editar/',                views.ticketUpdateView,        name='update'),
    path('<int:pk>/comentar/',              views.ticketAddCommentView,    name='add_comment'),
    path('api/categorias/<int:area_id>/',   views.categoriasPorAreaView,   name='categorias_por_area'),
    path('notificaciones/',                 views.notificacionesView,      name='notificaciones'),
    path('notificaciones/count/',           views.notificacionesCountView, name='notificaciones_count'),
]
