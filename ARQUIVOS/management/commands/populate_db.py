"""
Comando para popular a base de dados com departamentos, secções e tipos de documentos.
Estrutura típica de uma Administração Municipal Angolana.

Uso: python manage.py populate_db
"""
from django.core.management.base import BaseCommand
from django.db import connection
from ARQUIVOS.models import Departamento, Seccoes, TipoDocumento


class Command(BaseCommand):
    help = 'Popula a base de dados com departamentos, secções e tipos de documentos iniciais'

    def reset_sequences(self):
        """Reset PostgreSQL sequences to avoid ID conflicts"""
        with connection.cursor() as cursor:
            # Get table names from models (lowercase in PostgreSQL)
            models_to_reset = [
                (TipoDocumento._meta.db_table, 'id'),
                (Departamento._meta.db_table, 'id'),
                (Seccoes._meta.db_table, 'id'),
            ]
            for table, pk in models_to_reset:
                try:
                    seq_name = f"{table}_{pk}_seq"
                    cursor.execute(f'SELECT COALESCE(MAX("{pk}"), 0) + 1 FROM "{table}"')
                    max_id = cursor.fetchone()[0]
                    cursor.execute(f"SELECT setval('{seq_name}', {max_id}, false)")
                    self.stdout.write(f'   ✓ Sequência {seq_name} resetada para {max_id}')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'   ⚠️ Sequência {table}: {e}'))

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('🚀 Iniciando população da base de dados...'))
        
        # Reset sequences to avoid conflicts
        self.reset_sequences()
        
        # Criar Tipos de Documentos
        self.criar_tipos_documentos()
        
        # Criar Departamentos e Secções
        self.criar_departamentos_e_seccoes()
        
        self.stdout.write(self.style.SUCCESS('✅ Base de dados populada com sucesso!'))

    def criar_tipos_documentos(self):
        """Cria os tipos de documentos mais comuns"""
        tipos = [
            {'nome': 'Ofício', 'descricao': 'Comunicação oficial entre órgãos', 'prazo_dias': 15},
            {'nome': 'Requerimento', 'descricao': 'Solicitação formal do cidadão', 'prazo_dias': 30},
            {'nome': 'Carta', 'descricao': 'Correspondência formal', 'prazo_dias': 15},
            {'nome': 'Memorando', 'descricao': 'Comunicação interna rápida', 'prazo_dias': 7},
            {'nome': 'Circular', 'descricao': 'Comunicação para múltiplos destinatários', 'prazo_dias': 10},
            {'nome': 'Relatório', 'descricao': 'Documento de prestação de contas ou análise', 'prazo_dias': 30},
            {'nome': 'Parecer', 'descricao': 'Opinião técnica sobre determinado assunto', 'prazo_dias': 20},
            {'nome': 'Despacho', 'descricao': 'Decisão ou orientação de autoridade', 'prazo_dias': 5},
            {'nome': 'Processo', 'descricao': 'Conjunto de documentos sobre um caso', 'prazo_dias': 60},
            {'nome': 'Certidão', 'descricao': 'Documento que certifica informações', 'prazo_dias': 10},
            {'nome': 'Declaração', 'descricao': 'Documento que declara fatos', 'prazo_dias': 5},
            {'nome': 'Atestado', 'descricao': 'Documento que atesta condição', 'prazo_dias': 5},
            {'nome': 'Contrato', 'descricao': 'Acordo formal entre partes', 'prazo_dias': 45},
            {'nome': 'Edital', 'descricao': 'Documento público de convocação ou aviso', 'prazo_dias': 30},
            {'nome': 'Acta', 'descricao': 'Registro de reunião ou sessão', 'prazo_dias': 10},
            {'nome': 'Nota', 'descricao': 'Comunicação breve e informal', 'prazo_dias': 5},
            {'nome': 'Convite', 'descricao': 'Convocação para evento ou reunião', 'prazo_dias': 7},
            {'nome': 'Petição', 'descricao': 'Pedido formal do cidadão', 'prazo_dias': 30},
            {'nome': 'Recurso', 'descricao': 'Contestação de decisão anterior', 'prazo_dias': 15},
            {'nome': 'Outros', 'descricao': 'Outros tipos de documentos', 'prazo_dias': 30},
        ]
        
        criados = 0
        for tipo in tipos:
            obj, created = TipoDocumento.objects.get_or_create(
                nome=tipo['nome'],
                defaults=tipo
            )
            if created:
                criados += 1
        
        self.stdout.write(f'   📄 Tipos de Documento: {criados} criados')

    def criar_departamentos_e_seccoes(self):
        """Cria a estrutura completa de departamentos e secções"""
        
        # Estrutura: { 'nome_departamento': { 'codigo': 'XXX', 'descricao': '...', 'seccoes': [...] } }
        estrutura = {
            # ========================================
            # GABINETE DO ADMINISTRADOR
            # ========================================
            'Gabinete do Administrador': {
                'codigo': 'GAB-ADM',
                'descricao': 'Gabinete do Administrador Municipal',
                'seccoes': [
                    {'nome': 'Secretariado', 'codigo': 'SEC-GAB', 'descricao': 'Secretariado do Gabinete'},
                    {'nome': 'Assessoria Jurídica', 'codigo': 'AJ-GAB', 'descricao': 'Assessoria Jurídica do Gabinete'},
                    {'nome': 'Protocolo Geral', 'codigo': 'PROT-GAB', 'descricao': 'Protocolo Geral da Administração'},
                    {'nome': 'Comunicação Social', 'codigo': 'COM-GAB', 'descricao': 'Gabinete de Comunicação Social'},
                ]
            },
            
            # ========================================
            # GABINETE DO ADMINISTRADOR ADJUNTO
            # ========================================
            'Gabinete do Administrador Adjunto': {
                'codigo': 'GAB-ADJ',
                'descricao': 'Gabinete do Administrador Municipal Adjunto',
                'seccoes': [
                    {'nome': 'Secretariado Adjunto', 'codigo': 'SEC-ADJ', 'descricao': 'Secretariado do Gabinete Adjunto'},
                ]
            },
            
            # ========================================
            # DIRECÇÃO DE ADMINISTRAÇÃO E FINANÇAS
            # ========================================
            'Direcção de Administração e Finanças': {
                'codigo': 'DAF',
                'descricao': 'Direcção responsável pela gestão administrativa e financeira',
                'seccoes': [
                    {'nome': 'Secção de Recursos Humanos', 'codigo': 'RH', 'descricao': 'Gestão de pessoal e recursos humanos'},
                    {'nome': 'Secção de Contabilidade', 'codigo': 'CONT', 'descricao': 'Gestão contábil e financeira'},
                    {'nome': 'Secção de Tesouraria', 'codigo': 'TES', 'descricao': 'Tesouraria e pagamentos'},
                    {'nome': 'Secção de Património', 'codigo': 'PAT', 'descricao': 'Gestão patrimonial'},
                    {'nome': 'Secção de Aprovisionamento', 'codigo': 'APROV', 'descricao': 'Compras e aprovisionamento'},
                    {'nome': 'Secção de Expediente Geral', 'codigo': 'EXP', 'descricao': 'Expediente e arquivo geral'},
                ]
            },
            
            # ========================================
            # DIRECÇÃO DE PLANEAMENTO E ESTATÍSTICA
            # ========================================
            'Direcção de Planeamento e Estatística': {
                'codigo': 'DPE',
                'descricao': 'Direcção de Planeamento, Orçamento e Estatística',
                'seccoes': [
                    {'nome': 'Secção de Planeamento', 'codigo': 'PLAN', 'descricao': 'Planeamento estratégico e operacional'},
                    {'nome': 'Secção de Orçamento', 'codigo': 'ORC', 'descricao': 'Elaboração e controle orçamental'},
                    {'nome': 'Secção de Estatística', 'codigo': 'EST', 'descricao': 'Estatísticas e indicadores'},
                    {'nome': 'Secção de Projectos', 'codigo': 'PROJ', 'descricao': 'Gestão de projectos'},
                ]
            },
            
            # ========================================
            # DIRECÇÃO DE OBRAS PÚBLICAS E URBANISMO
            # ========================================
            'Direcção de Obras Públicas e Urbanismo': {
                'codigo': 'DOPU',
                'descricao': 'Direcção de Obras Públicas, Urbanismo e Ambiente',
                'seccoes': [
                    {'nome': 'Secção de Obras Públicas', 'codigo': 'OP', 'descricao': 'Fiscalização e acompanhamento de obras'},
                    {'nome': 'Secção de Urbanismo', 'codigo': 'URB', 'descricao': 'Licenciamento urbanístico'},
                    {'nome': 'Secção de Topografia', 'codigo': 'TOP', 'descricao': 'Levantamentos topográficos'},
                    {'nome': 'Secção de Ambiente', 'codigo': 'AMB', 'descricao': 'Gestão ambiental e saneamento'},
                    {'nome': 'Secção de Terras', 'codigo': 'TER', 'descricao': 'Gestão de terras e cadastro'},
                ]
            },
            
            # ========================================
            # DIRECÇÃO DE SAÚDE
            # ========================================
            'Direcção Municipal de Saúde': {
                'codigo': 'DMS',
                'descricao': 'Direcção Municipal de Saúde Pública',
                'seccoes': [
                    {'nome': 'Secção de Programas de Saúde', 'codigo': 'PS', 'descricao': 'Programas de saúde pública'},
                    {'nome': 'Secção de Administração de Saúde', 'codigo': 'AS', 'descricao': 'Administração das unidades de saúde'},
                    {'nome': 'Secção de Medicamentos', 'codigo': 'MED', 'descricao': 'Gestão de medicamentos e insumos'},
                    {'nome': 'Secção de Vigilância Epidemiológica', 'codigo': 'VE', 'descricao': 'Vigilância e controle de doenças'},
                ]
            },
            
            # ========================================
            # DIRECÇÃO DE EDUCAÇÃO
            # ========================================
            'Direcção Municipal de Educação': {
                'codigo': 'DME',
                'descricao': 'Direcção Municipal de Educação',
                'seccoes': [
                    {'nome': 'Secção Pedagógica', 'codigo': 'PED', 'descricao': 'Acompanhamento pedagógico'},
                    {'nome': 'Secção de Estatística Escolar', 'codigo': 'EE', 'descricao': 'Estatísticas educacionais'},
                    {'nome': 'Secção de Recursos Educativos', 'codigo': 'RE', 'descricao': 'Material didáctico e recursos'},
                    {'nome': 'Secção de Inspecção Escolar', 'codigo': 'IE', 'descricao': 'Inspecção e supervisão escolar'},
                ]
            },
            
            # ========================================
            # DIRECÇÃO DE ACÇÃO SOCIAL
            # ========================================
            'Direcção de Acção Social': {
                'codigo': 'DAS',
                'descricao': 'Direcção de Família e Promoção da Mulher',
                'seccoes': [
                    {'nome': 'Secção de Protecção Social', 'codigo': 'PROT', 'descricao': 'Protecção e assistência social'},
                    {'nome': 'Secção de Família', 'codigo': 'FAM', 'descricao': 'Apoio à família'},
                    {'nome': 'Secção da Mulher', 'codigo': 'MUL', 'descricao': 'Promoção da mulher'},
                    {'nome': 'Secção de Reinserção Social', 'codigo': 'RS', 'descricao': 'Reinserção social'},
                ]
            },
            
            # ========================================
            # DIRECÇÃO DE JUVENTUDE E DESPORTOS
            # ========================================
            'Direcção de Juventude e Desportos': {
                'codigo': 'DJD',
                'descricao': 'Direcção de Juventude e Desportos',
                'seccoes': [
                    {'nome': 'Secção de Juventude', 'codigo': 'JUV', 'descricao': 'Programas de juventude'},
                    {'nome': 'Secção de Desportos', 'codigo': 'DES', 'descricao': 'Actividades desportivas'},
                    {'nome': 'Secção de Tempos Livres', 'codigo': 'TL', 'descricao': 'Lazer e tempos livres'},
                ]
            },
            
            # ========================================
            # DIRECÇÃO DE CULTURA E TURISMO
            # ========================================
            'Direcção de Cultura e Turismo': {
                'codigo': 'DCT',
                'descricao': 'Direcção de Cultura, Turismo e Hotelaria',
                'seccoes': [
                    {'nome': 'Secção de Cultura', 'codigo': 'CULT', 'descricao': 'Promoção cultural'},
                    {'nome': 'Secção de Turismo', 'codigo': 'TUR', 'descricao': 'Promoção turística'},
                    {'nome': 'Secção de Património Cultural', 'codigo': 'PC', 'descricao': 'Preservação do património'},
                ]
            },
            
            # ========================================
            # DIRECÇÃO DE AGRICULTURA E DESENVOLVIMENTO RURAL
            # ========================================
            'Direcção de Agricultura e Desenvolvimento Rural': {
                'codigo': 'DADR',
                'descricao': 'Direcção de Agricultura, Pescas e Desenvolvimento Rural',
                'seccoes': [
                    {'nome': 'Secção de Agricultura', 'codigo': 'AGR', 'descricao': 'Apoio à agricultura'},
                    {'nome': 'Secção de Pecuária', 'codigo': 'PEC', 'descricao': 'Apoio à pecuária'},
                    {'nome': 'Secção de Pescas', 'codigo': 'PES', 'descricao': 'Apoio às pescas'},
                    {'nome': 'Secção de Extensão Rural', 'codigo': 'ER', 'descricao': 'Extensão e assistência rural'},
                    {'nome': 'Secção de Florestas', 'codigo': 'FLO', 'descricao': 'Gestão florestal'},
                ]
            },
            
            # ========================================
            # DIRECÇÃO DE COMÉRCIO E INDÚSTRIA
            # ========================================
            'Direcção de Comércio e Indústria': {
                'codigo': 'DCI',
                'descricao': 'Direcção de Comércio, Indústria e Empreendedorismo',
                'seccoes': [
                    {'nome': 'Secção de Comércio', 'codigo': 'COM', 'descricao': 'Licenciamento comercial'},
                    {'nome': 'Secção de Indústria', 'codigo': 'IND', 'descricao': 'Apoio à indústria'},
                    {'nome': 'Secção de Mercados', 'codigo': 'MER', 'descricao': 'Gestão de mercados'},
                    {'nome': 'Secção de Empreendedorismo', 'codigo': 'EMP', 'descricao': 'Apoio ao empreendedorismo'},
                ]
            },
            
            # ========================================
            # DIRECÇÃO DE TRANSPORTES E COMUNICAÇÕES
            # ========================================
            'Direcção de Transportes e Comunicações': {
                'codigo': 'DTC',
                'descricao': 'Direcção de Transportes, Trânsito e Comunicações',
                'seccoes': [
                    {'nome': 'Secção de Transportes', 'codigo': 'TRANS', 'descricao': 'Gestão de transportes públicos'},
                    {'nome': 'Secção de Trânsito', 'codigo': 'TRAN', 'descricao': 'Ordenamento do trânsito'},
                    {'nome': 'Secção de Comunicações', 'codigo': 'COMU', 'descricao': 'Telecomunicações e correios'},
                ]
            },
            
            # ========================================
            # DIRECÇÃO DE ENERGIA E ÁGUAS
            # ========================================
            'Direcção de Energia e Águas': {
                'codigo': 'DEA',
                'descricao': 'Direcção de Energia e Águas',
                'seccoes': [
                    {'nome': 'Secção de Energia', 'codigo': 'ENE', 'descricao': 'Gestão energética'},
                    {'nome': 'Secção de Águas', 'codigo': 'AGU', 'descricao': 'Abastecimento de água'},
                    {'nome': 'Secção de Saneamento', 'codigo': 'SAN', 'descricao': 'Saneamento básico'},
                ]
            },
            
            # ========================================
            # SERVIÇOS DE REGISTO CIVIL
            # ========================================
            'Serviços de Registo Civil': {
                'codigo': 'SRC',
                'descricao': 'Serviços de Registo Civil e Notariado',
                'seccoes': [
                    {'nome': 'Secção de Nascimentos', 'codigo': 'NASC', 'descricao': 'Registo de nascimentos'},
                    {'nome': 'Secção de Casamentos', 'codigo': 'CAS', 'descricao': 'Registo de casamentos'},
                    {'nome': 'Secção de Óbitos', 'codigo': 'OBI', 'descricao': 'Registo de óbitos'},
                    {'nome': 'Secção de Identificação', 'codigo': 'ID', 'descricao': 'Bilhetes de identidade'},
                ]
            },
        }
        
        deps_criados = 0
        secs_criadas = 0
        
        for nome_dep, dados in estrutura.items():
            # Criar Departamento
            departamento, dep_created = Departamento.objects.get_or_create(
                nome=nome_dep,
                codigo=dados['codigo'],
                defaults={
                    'descricao': dados['descricao'],
                    'tipo_municipio': 'A',  # Tipo A por padrão
                    'ativo': True
                }
            )
            if dep_created:
                deps_criados += 1
            
            # Criar Secções do Departamento
            for seccao_data in dados['seccoes']:
                seccao, sec_created = Seccoes.objects.get_or_create(
                    nome=seccao_data['nome'],
                    Departamento=departamento,
                    defaults={
                        'codigo': seccao_data['codigo'],
                        'descricao': seccao_data['descricao'],
                        'ativo': True
                    }
                )
                if sec_created:
                    secs_criadas += 1
        
        self.stdout.write(f'   🏢 Departamentos (Direcções): {deps_criados} criados')
        self.stdout.write(f'   📁 Secções: {secs_criadas} criadas')
