from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, Departamento, TipoDocumento, Documento,
    MovimentacaoDocumento, Anexo, ConfiguracaoSistema, Notificacao, Seccoes,
    LocalArmazenamento, ArmazenamentoDocumento, Administracao
)

@admin.register(Administracao)
class AdministracaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo_municipio',)
    search_fields = ('nome', 'tipo_municipio')
    list_filter = ('tipo_municipio',)

# Customização da administração de usuários
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'nivel_acesso', 'departamento', 'seccao', 'administracao', 'is_staff', 'is_active')
    list_filter = ('nivel_acesso', 'is_staff', 'is_superuser', 'departamento', 'administracao')
    fieldsets = UserAdmin.fieldsets + (
        ('Hierarquia', {'fields': ('departamento', 'seccao', 'administracao')}),
        ('Outros', {'fields': ('nivel_acesso', 'telefone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Hierarquia', {'fields': ('departamento', 'seccao', 'administracao')}),
        ('Outros', {'fields': ('nivel_acesso', 'telefone')}),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    
    # Autocomplete para campos ForeignKey
    autocomplete_fields = ['departamento', 'seccao', 'administracao']


@admin.register(Seccoes)
class SeccoesAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'get_departamento_nome', 'get_tipo', 'responsavel', 'ativo')
    search_fields = ('id', 'nome', 'departamento__nome', 'codigo')
    list_filter = ('ativo', 'departamento__tipo_municipio', 'departamento')
    
    # Autocomplete para campos ForeignKey
    autocomplete_fields = ['departamento', 'responsavel']

    def get_departamento_nome(self, obj):
        return obj.departamento.nome
    get_departamento_nome.short_description = 'Departamento'

    def get_tipo(self, obj):
        return obj.departamento.get_tipo_municipio_display()
    get_tipo.short_description = 'Tipo de Município'


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'codigo', 'nome', 'tipo_municipio', 'responsavel', 'ativo')
    search_fields = ('id', 'nome', 'codigo')
    list_filter = ('ativo', 'tipo_municipio')
    ordering = ('tipo_municipio', 'nome')
    
    # Autocomplete para campos ForeignKey
    autocomplete_fields = ['responsavel']


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'prazo_dias', 'ativo')
    search_fields = ('nome', 'descricao')
    list_filter = ('ativo',)


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ('numero_protocolo', 'titulo', 'status', 'prioridade', 'departamento_atual', 'data_criacao')
    list_filter = ('status', 'prioridade', 'tipo_documento', 'departamento_atual')
    search_fields = ('numero_protocolo', 'titulo', 'tags', 'utente', 'conteudo')
    readonly_fields = ('numero_protocolo', 'data_criacao')
    
    # Autocomplete para campos ForeignKey
    autocomplete_fields = ['tipo_documento', 'departamento_origem', 'departamento_atual', 'seccao_atual', 'criado_por', 'responsavel_atual']


@admin.register(MovimentacaoDocumento)
class MovimentacaoDocumentoAdmin(admin.ModelAdmin):
    list_display = ('documento', 'tipo_movimentacao', 'departamento_origem', 'departamento_destino', 'data_movimentacao', 'usuario')
    list_filter = ('tipo_movimentacao', 'data_movimentacao', 'confirmado_recebimento')
    search_fields = ('documento__numero_protocolo', 'documento__titulo', 'usuario__username', 'observacoes', 'despacho')
    
    # Autocomplete para campos ForeignKey
    autocomplete_fields = ['documento', 'departamento_origem', 'departamento_destino', 'seccao_origem', 'seccao_destino', 'usuario', 'usuario_confirmacao']


@admin.register(Anexo)
class AnexoAdmin(admin.ModelAdmin):
    list_display = ('documento', 'nome', 'usuario_upload', 'data_upload')
    search_fields = ('nome', 'descricao', 'documento__numero_protocolo')
    
    # Autocomplete para campos ForeignKey
    autocomplete_fields = ['documento', 'usuario_upload']


@admin.register(ConfiguracaoSistema)
class ConfiguracaoSistemaAdmin(admin.ModelAdmin):
    list_display = ('chave', 'valor', 'ativo')
    search_fields = ('chave', 'valor', 'descricao')
    list_filter = ('ativo',)


@admin.register(Notificacao)
class NotificaAdmin(admin.ModelAdmin):
    list_display = ('mensagem', 'usuario', 'link', 'lida', 'data_criacao')
    search_fields = ('link', 'mensagem', 'usuario__username')
    list_filter = ('lida', 'data_criacao')
    
    # Autocomplete para campos ForeignKey
    autocomplete_fields = ['usuario']


# ========================================
# ADMINISTRAÇÃO DE ARMAZENAMENTO
# ========================================

@admin.register(LocalArmazenamento)
class LocalArmazenamentoAdmin(admin.ModelAdmin):
    """Administração de Locais de Armazenamento"""
    list_display = (
        'codigo', 'nome', 'tipo', 'local_pai', 'departamento',
        'documentos_armazenados_count', 'capacidade_maxima', 'ativo'
    )
    list_filter = ('tipo', 'ativo', 'departamento', 'seccao')
    search_fields = ('codigo', 'nome', 'descricao')
    ordering = ('departamento', 'tipo', 'codigo')
    
    # Autocomplete para campos ForeignKey
    autocomplete_fields = ['local_pai', 'departamento', 'seccao']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('codigo', 'nome', 'tipo', 'descricao')
        }),
        ('Hierarquia', {
            'fields': ('local_pai',),
            'description': 'Selecione o local pai se este for uma subdivisão (ex: prateleira dentro de estante)'
        }),
        ('Localização Física', {
            'fields': ('departamento', 'seccao'),
        }),
        ('Capacidade', {
            'fields': ('capacidade_maxima',),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('ativo',),
        }),
    )

    def documentos_armazenados_count(self, obj):
        return obj.documentos_armazenados_count
    documentos_armazenados_count.short_description = 'Documentos'


@admin.register(ArmazenamentoDocumento)
class ArmazenamentoDocumentoAdmin(admin.ModelAdmin):
    """Administração de registros de armazenamento de documentos"""
    list_display = (
        'documento', 'get_localizacao', 'registrado_por',
        'data_armazenamento', 'ativo'
    )
    list_filter = ('ativo', 'data_armazenamento', 'local_armazenamento__departamento')
    search_fields = (
        'documento__numero_protocolo', 'documento__titulo',
        'estante', 'prateleira', 'dossie', 'caixa',
        'local_armazenamento__codigo'
    )
    ordering = ('-data_armazenamento',)
    readonly_fields = ('data_armazenamento', 'data_retirada')
    
    # Autocomplete para campos ForeignKey
    autocomplete_fields = ['documento', 'local_armazenamento', 'registrado_por', 'retirado_por', 'movimentacao_origem']
    
    fieldsets = (
        ('Documento', {
            'fields': ('documento', 'movimentacao_origem')
        }),
        ('Local Cadastrado', {
            'fields': ('local_armazenamento',),
            'description': 'Selecione um local previamente cadastrado no sistema'
        }),
        ('Localização Manual', {
            'fields': ('estante', 'prateleira', 'dossie', 'caixa', 'posicao'),
            'classes': ('collapse',),
            'description': 'Use estes campos se o local não está cadastrado no sistema'
        }),
        ('Registro', {
            'fields': ('registrado_por', 'data_armazenamento', 'observacoes')
        }),
        ('Retirada', {
            'fields': ('ativo', 'data_retirada', 'retirado_por', 'motivo_movimentacao'),
            'classes': ('collapse',),
        }),
    )

    def get_localizacao(self, obj):
        return obj.localizacao_completa
    get_localizacao.short_description = 'Localização'
