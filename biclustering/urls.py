from django.urls import path
from . import views

# соединяем веб-адреса, функции рендера и ссылки из темплейтов
urlpatterns = [
    path('', views.main_view, name='main'),
    path('run/', views.run_view, name='run'),
    path('save/', views.save_view, name='save'),
    path('gene_expression/run/<int:num>', views.table, name='table'),
]