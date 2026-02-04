from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, Departamento, TipoDocumento, Documento,
    MovimentacaoDocumento, Anexo, ConfiguracaoSistema, Notificacao, Seccoes,
    LocalArmazenamento, ArmazenamentoDocumento, Administracao, GovernoProvincial, AdministracaoMunicipal
)


# ========================================
# MIXIN PARA ISOLAMENTO MULTI-TENANT
# ========================================

class AdminMultiTenantMixin:
    """
    Mixin para filtrar registros por administração do usuário logado.
    Superusuários e admin_sistema podem ver tudo.
    """
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        # Superusuários veem tudo
        if request.user.is_superuser:
            return qs
        
        # admin_sistema também vê tudo
        if getattr(request.user, 'nivel_acesso', None) == 'admin_sistema':
            return qs
        
        # Usuários normais veem apenas dados da sua administração
        user_admin = getattr(request.user, 'administracao', None)
        if user_admin:
            # Tenta filtrar pelo campo 'administracao' diretamente
            if hasattr(qs.model, 'administracao'):
                return qs.filter(administracao=user_admin)
            # Para modelos relacionados (ex: Notificacao -> usuario -> administracao)
            elif hasattr(qs.model, 'usuario'):
                return qs.filter(usuario__administracao=user_admin)
        
        return qs
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filtra dropdowns de ForeignKey por administração."""
        user_admin = getattr(request.user, 'administracao', None)
        
        if not request.user.is_superuser and user_admin:
            # Filtrar departamentos
            if db_field.name == 'departamento' or db_field.name in ['departamento_origem', 'departamento_atual', 'departamento_destino']:
                kwargs['queryset'] = Departamento.objects.filter(administracao=user_admin)
            # Filtrar secções
            elif db_field.name == 'seccao' or db_field.name in ['seccao_origem', 'seccao_destino', 'seccao_atual']:
                kwargs['queryset'] = Seccoes.objects.filter(departamento__administracao=user_admin)
            # Filtrar usuários
            elif db_field.name in ['usuario', 'criado_por', 'responsavel_atual', 'registrado_por', 'retirado_por', 'usuario_confirmacao']:
                kwargs['queryset'] = CustomUser.objects.filter(administracao=user_admin)
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Administracao)
class AdministracaoAdmin(admin.ModelAdmin):
    # Mantemos este registro GENÉRICO para que o 'autocomplete_fields' funcione
    # em outros models (Usuario, Departamento) que têm FK para Administracao.
    list_display = ('nome', 'tipo_municipio', 'provincia')
    search_fields = ('nome', 'provincia')
    list_filter = ('tipo_municipio', 'provincia')
    ordering = ('provincia', 'nome')
    
    def has_module_permission(self, request):
        # Esconde do menu principal para não confundir,
        # MAS mantém registrado para o autocomplete funcionar!
        return False
        
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('nome')

@admin.register(GovernoProvincial)
class GovernoProvincialAdmin(admin.ModelAdmin):
    list_display = ('nome', 'provincia', 'get_total_departamentos', 'get_total_seccoes')
    search_fields = ('nome', 'provincia')
    list_filter = ('provincia',)
    ordering = ('provincia', 'nome')
    exclude = ('tipo_municipio',)
    
    def get_total_departamentos(self, obj):
        return Departamento.objects.filter(administracao=obj).count()
    get_total_departamentos.short_description = 'Gabinetes/Direções'

    def get_total_seccoes(self, obj):
        return Seccoes.objects.filter(departamento__administracao=obj).count()
    get_total_seccoes.short_description = 'Departamentos/Secções'
    
    def save_model(self, request, obj, form, change):
        obj.tipo_municipio = 'G' # Garante tipo G
        super().save_model(request, obj, form, change)

@admin.register(AdministracaoMunicipal)
class AdministracaoMunicipalAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo_municipio', 'provincia', 'get_total_departamentos', 'get_total_seccoes')
    search_fields = ('nome', 'provincia')
    list_filter = ('tipo_municipio', 'provincia')
    ordering = ('provincia', 'nome')
    
    def get_total_departamentos(self, obj):
        return Departamento.objects.filter(administracao=obj).count()
    get_total_departamentos.short_description = 'Departamentos'

    def get_total_seccoes(self, obj):
        return Seccoes.objects.filter(departamento__administracao=obj).count()
    get_total_seccoes.short_description = 'Secções'

# Mantemos a administração genérica escondida ou apenas para superusers se necessário, 
# mas por enquanto vamos remover o registro duplicado da genérica para limpar a view.
# @admin.register(Administracao) -> REMOVIDO EM FAVOR DOS PROXIES

# Customização da administração de usuários
@admin.register(CustomUser)
class CustomUserAdmin(AdminMultiTenantMixin, UserAdmin):
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
class SeccoesAdmin(AdminMultiTenantMixin, admin.ModelAdmin):
    list_display = ('id', 'nome', 'get_departamento_nome', 'get_tipo', 'responsavel', 'ativo')
    search_fields = ('id', 'nome', 'departamento__nome', 'codigo')
    list_filter = ('ativo', 'departamento__tipo_municipio','departamento__administracao')
    
    # Autocomplete para campos ForeignKey
    autocomplete_fields = ['departamento', 'responsavel']

    def get_departamento_nome(self, obj):
        return obj.departamento.nome
    get_departamento_nome.short_description = 'Departamento'

    def get_tipo(self, obj):
        return obj.departamento.get_tipo_municipio_display()
    get_tipo.short_description = 'Tipo de Município'


@admin.register(Departamento)
class DepartamentoAdmin(AdminMultiTenantMixin, admin.ModelAdmin):
    list_display = ('nome', 'administracao', 'tipo_municipio', 'get_total_seccoes', 'responsavel', 'ativo')
    search_fields = ('nome', 'codigo', 'administracao__nome')
    list_filter = ('ativo', 'tipo_municipio', 'administracao__provincia')
    ordering = ('administracao', 'nome')
    
    # Autocomplete para campos ForeignKey
    autocomplete_fields = ['responsavel', 'administracao']

    def get_total_seccoes(self, obj):
        return obj.seccoes_count
    get_total_seccoes.short_description = 'Secções'
    get_total_seccoes.admin_order_field = 'seccoes_count'

    def get_queryset(self, request):
        """Otimiza a query com anotações de contagem"""
        from django.db.models import Count
        qs = super().get_queryset(request)
        return qs.annotate(
            seccoes_count=Count('seccoes')
        )


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'prazo_dias', 'ativo')
    search_fields = ('nome', 'descricao')
    list_filter = ('ativo',)


@admin.register(Documento)
class DocumentoAdmin(AdminMultiTenantMixin, admin.ModelAdmin):
    list_display = ('numero_protocolo', 'titulo', 'status', 'prioridade', 'departamento_atual', 'data_criacao')
    list_filter = ('status', 'prioridade', 'tipo_documento', 'departamento_atual')
    search_fields = ('numero_protocolo', 'titulo', 'tags', 'utente', 'conteudo')
    readonly_fields = ('numero_protocolo', 'data_criacao')
    
    # Autocomplete para campos ForeignKey
    autocomplete_fields = ['tipo_documento', 'departamento_origem', 'departamento_atual', 'seccao_atual', 'criado_por', 'responsavel_atual']


@admin.register(MovimentacaoDocumento)
class MovimentacaoDocumentoAdmin(AdminMultiTenantMixin, admin.ModelAdmin):
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
