# urls.py
from django.urls import path, include
from django.contrib.auth import views as auth_views
from ARQUIVOS import views
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings
from django.urls import re_path
from django.views.static import serve

app_name = 'documentos'

urlpatterns = [
    # Dashboard
    path('Painel-Control/', admin.site.urls),

    # Autenticação
    path('', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Documentos
    path('Painel/', views.dashboard, name='Painel'),
    path('documentos/', views.listar_documentos, name='listar_documentos'),
    path('documentos/criar/', views.criar_documento, name='criar_documento'),
    path('documentos/Editar/<id>', views.Editar_documento, name='editar_documento'),
    path('documentos/arquivo-morto/', views.arquivo_morto, name='arquivo_morto'),
    path('documentos/<documento_id>/', views.encaminhar_documento, name='Encaminhar'),
    path('documentos/listar', views.listar_documentos, name='listar_documento'),
    path('movimento/listar', views.listar_movimentações, name='listar_movimento'),
    path('documentos/detalhe/<documento_id>', views.detalhe_documento, name='detalhe_documento'),
    path('movimentacao/<int:movimentacao_id>/confirmar/', views.confirmar_recebimento, name='confirmar_recebimento'),
    path('api/verificar-notificacoes/', views.verificar_notificacoes, name='verificar_notificacoes'),
    path('api/lista-pendencias-parcial/', views.listar_pendencias_parcial,name='lista_pendencias_parcial'),

                  # Em ARQUIVOS/urls.py
path('notificacoes/marcar-como-lidas/', views.marcar_notificacoes_como_lidas, name='marcar_notificacoes_lidas'),

    # Pendências
    path('pendencias/', views.pendencias, name='pendencias'),
    
    # Relatórios
    path('relatorios/', views.relatorios, name='relatorios'),
    #path('relatorios/exportar/', views.exportar_relatorio, name='exportar_relatorio'),
    
    # AJAX
    path('ajax/load-departamentos/', views.load_departamentos, name='ajax_load_departamentos'),
    path('ajax/load-seccoes/', views.load_seccoes, name='ajax_load_seccoes'),
    path('ajax/busca/', views.busca_ajax, name='busca_ajax'),
#    path('ajax/confirmar-recebimento/', views.confirmar_recebimento_ajax, name='confirmar_recebimento_ajax'),

    # Armazenamento de Documentos
    path('documentos/<int:documento_id>/armazenamento/', views.registrar_armazenamento, name='registrar_armazenamento'),
    path('armazenamentos/', views.listar_armazenamentos, name='listar_armazenamentos'),
    path('documentos/<int:documento_id>/armazenamentos/', views.listar_armazenamentos, name='historico_armazenamento'),

    # Gestão de Usuários (admin_sistema)
    path('administracao/usuarios/', views.gestao_usuarios, name='gestao_usuarios'),
    path('ajax/seccoes-departamento/', views.ajax_seccoes_departamento, name='ajax_seccoes_departamento'),

]

# Servir arquivos media e static
# Nota: Habilitado manualmente para funcionar na porta 8000 mesmo com DEBUG=False
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]