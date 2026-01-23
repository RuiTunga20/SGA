from django.test import TestCase
from django.core.exceptions import ValidationError
from ARQUIVOS.models import Administracao, Departamento, CustomUser, Documento, TipoDocumento, MovimentacaoDocumento, Seccoes, Notificacao

class IsolamentoTestCase(TestCase):
    def setUp(self):
        # Tipo Documento
        self.tipo_doc = TipoDocumento.objects.create(nome="Ofício", prazo_dias=10)

        # Admin A (Uíge)
        self.admin_a = Administracao.objects.create(nome="Uíge", tipo_municipio="A")
        self.dept_a = Departamento.objects.create(nome="Finanças Uíge", administracao=self.admin_a, tipo_municipio="A")
        self.seccao_a = Seccoes.objects.create(nome="Secção Finanças A", departamento=self.dept_a)
        self.user_a = CustomUser.objects.create_user(
            username="user_a", password="password", administracao=self.admin_a, departamento=self.dept_a
        )

        # Admin B (Benguela)
        self.admin_b = Administracao.objects.create(nome="Benguela", tipo_municipio="B")
        self.dept_b = Departamento.objects.create(nome="RH Benguela", administracao=self.admin_b, tipo_municipio="B")
        self.seccao_b = Seccoes.objects.create(nome="Secção RH B", departamento=self.dept_b)
        self.user_b = CustomUser.objects.create_user(
            username="user_b", password="password", administracao=self.admin_b, departamento=self.dept_b
        )

    def test_usuario_nao_ve_outra_administracao(self):
        """Testa se usuário A não vê usuário B"""
        users_visible_to_a = CustomUser.objects.da_mesma_administracao(self.user_a)
        self.assertIn(self.user_a, users_visible_to_a)
        self.assertNotIn(self.user_b, users_visible_to_a)

    def test_departamento_isolado(self):
        """Testa se usuário A não vê departamento B"""
        depts_visible_to_a = Departamento.objects.para_administracao(self.user_a.administracao)
        self.assertIn(self.dept_a, depts_visible_to_a)
        self.assertNotIn(self.dept_b, depts_visible_to_a)

    def test_criacao_usuario_invalido(self):
        """Testa se impede criar usuário com departamento de outra administração"""
        user_invalido = CustomUser(
            username="user_fail", 
            administracao=self.admin_a, 
            departamento=self.dept_b  # Depto da Admin B
        )
        # A validação do clean() deve falhar
        with self.assertRaises(ValidationError):
            user_invalido.full_clean()

    def test_documento_isolado(self):
        """Testa se usuário A não vê documento B"""
        doc_a = Documento.objects.create(
            titulo="Doc A", 
            departamento_origem=self.dept_a, 
            departamento_atual=self.dept_a,
            criado_por=self.user_a,
            tipo_documento=self.tipo_doc,
            administracao=self.admin_a
        )
        doc_b = Documento.objects.create(
            titulo="Doc B", 
            departamento_origem=self.dept_b, 
            departamento_atual=self.dept_b,
            criado_por=self.user_b,
            tipo_documento=self.tipo_doc,
            administracao=self.admin_b
        )

        docs_visible_to_a = Documento.objects.para_usuario(self.user_a)
        self.assertIn(doc_a, docs_visible_to_a)
        self.assertNotIn(doc_b, docs_visible_to_a)

    def test_documento_generico_isolado(self):
        """Testa se documentos em departamentos genéricos não vazam para outras administrações."""
        dept_saude_a = Departamento.objects.create(nome="Saúde", tipo_municipio="A", administracao=self.admin_a)
        dept_saude_b = Departamento.objects.create(nome="Saúde", tipo_municipio="B", administracao=self.admin_b)

        doc_saude_a = Documento.objects.create(
            titulo="Relatório Saúde Uíge",
            departamento_origem=dept_saude_a,
            departamento_atual=dept_saude_a,
            criado_por=self.user_a,
            tipo_documento=self.tipo_doc,
            administracao=self.admin_a
        )

        docs_visible_to_b = Documento.objects.para_usuario(self.user_b)
        self.assertNotIn(doc_saude_a, docs_visible_to_b)

    # ===== NOVOS TESTES DE ISOLAMENTO =====

    def test_movimentacao_cross_admin_bloqueada(self):
        """Testa se movimentação para departamento de outra administração é bloqueada."""
        doc_a = Documento.objects.create(
            titulo="Doc para encaminhar",
            departamento_origem=self.dept_a,
            departamento_atual=self.dept_a,
            criado_por=self.user_a,
            tipo_documento=self.tipo_doc,
            administracao=self.admin_a
        )

        mov_cross_admin = MovimentacaoDocumento(
            documento=doc_a,
            tipo_movimentacao='encaminhamento',
            usuario=self.user_a,
            departamento_origem=self.dept_a,
            departamento_destino=self.dept_b  # Dept de outra admin!
        )
        
        with self.assertRaises(ValidationError):
            mov_cross_admin.full_clean()

    def test_seccao_herda_administracao(self):
        """Testa se Seccao.administracao herda corretamente do departamento."""
        self.assertEqual(self.seccao_a.administracao, self.admin_a)
        self.assertEqual(self.seccao_b.administracao, self.admin_b)

    def test_usuario_dept_admin_consistencia(self):
        """Testa se usuário não pode ter departamento de administração diferente."""
        # Criar dept da admin_a mas tentar associar a user da admin_b
        user_inconsistente = CustomUser(
            username="inconsistente",
            administracao=self.admin_b,
            departamento=self.dept_a  # Dept é da admin_a!
        )
        
        with self.assertRaises(ValidationError):
            user_inconsistente.full_clean()

    def test_notificacao_pertence_usuario_correto(self):
        """Testa se notificação é criada para usuário da mesma administração."""
        notif = Notificacao.objects.create(
            usuario=self.user_a,
            mensagem="Teste de notificação",
            link="/test/"
        )
        
        # Notificação deve pertencer ao user_a
        self.assertEqual(notif.usuario.administracao, self.admin_a)
        
        # Verificar que não aparece para user_b via filtro
        notificacoes_b = Notificacao.objects.filter(usuario__administracao=self.admin_b)
        self.assertNotIn(notif, notificacoes_b)
