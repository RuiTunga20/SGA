from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import CustomUser, Departamento, Seccoes, Documento, MovimentacaoDocumento, ArmazenamentoDocumento, LocalArmazenamento, TipoDocumento, Administracao

class ModelValidationTests(TestCase):
    def setUp(self):
        # Criar Administração obrigatória
        self.admin = Administracao.objects.create(nome="Admin Teste", tipo_municipio="A")
        
        # Setup básico de Departamentos e Secções COM administração
        self.dept_a = Departamento.objects.create(nome="Departamento A", codigo="DEP-A", administracao=self.admin)
        self.dept_b = Departamento.objects.create(nome="Departamento B", codigo="DEP-B", administracao=self.admin)
        
        self.seccao_a1 = Seccoes.objects.create(nome="Secção A1", departamento=self.dept_a)
        self.seccao_b1 = Seccoes.objects.create(nome="Secção B1", departamento=self.dept_b)
        
        # Tipo de Documento
        self.tipo_doc = TipoDocumento.objects.create(nome="Ofício", prazo_dias=10)

    def test_user_validation(self):
        """Testa validação de consistência entre Departamento e Secção no Usuário"""
        
        # Caso Válido: Secção pertence ao Departamento
        user = CustomUser(
            username="user_valid", 
            departamento=self.dept_a, 
            seccao=self.seccao_a1,
            administracao=self.admin,
            password="password123"
        )
        try:
            user.full_clean()  # Deve passar
        except ValidationError:
            self.fail("CustomUser.full_clean() falhou para dados válidos.")

        # Caso Inválido: Secção NÃO pertence ao Departamento
        user_invalid = CustomUser(
            username="user_invalid", 
            departamento=self.dept_a, 
            seccao=self.seccao_b1,  # Pertence ao Dept B
            administracao=self.admin,
            password="password123"
        )
        with self.assertRaises(ValidationError):
            user_invalid.full_clean()

    def test_movimentacao_validation(self):
        """Testa validação de destino na Movimentação"""
        user = CustomUser.objects.create(username="tester", departamento=self.dept_a, administracao=self.admin, password="password123")
        doc = Documento.objects.create(
            titulo="Doc Teste", 
            tipo_documento=self.tipo_doc,
            departamento_origem=self.dept_a,
            departamento_atual=self.dept_a,
            criado_por=user,
            administracao=self.admin,
            telefone="900000000",
            utente="Tester"
        )

        # Caso Inválido: Encaminhamento sem destino
        mov_sem_destino = MovimentacaoDocumento(
            documento=doc,
            tipo_movimentacao='encaminhamento',
            usuario=user,
            departamento_origem=self.dept_a
        )
        with self.assertRaises(ValidationError):
            mov_sem_destino.full_clean()

        # Caso Inválido: Secção destino não bate com Departamento destino
        mov_inconsistente = MovimentacaoDocumento(
            documento=doc,
            tipo_movimentacao='encaminhamento',
            usuario=user,
            departamento_origem=self.dept_a,
            departamento_destino=self.dept_a,
            seccao_destino=self.seccao_b1 # Pertence ao Dept B
        )
        with self.assertRaises(ValidationError):
            mov_inconsistente.full_clean()

    def test_armazenamento_validation(self):
        """Testa validação de Armazenamento (Local Cadastrado vs Manual)"""
        user = CustomUser.objects.create(username="archivist", departamento=self.dept_a, administracao=self.admin, password="password123")
        doc = Documento.objects.create(
            titulo="Doc Arquivo", 
            tipo_documento=self.tipo_doc,
            departamento_origem=self.dept_a,
            departamento_atual=self.dept_a,
            criado_por=user,
            administracao=self.admin,
            telefone="900000000",
            utente="Tester"
        )
        
        local = LocalArmazenamento.objects.create(
            codigo="EST-01", 
            nome="Estante 1", 
            departamento=self.dept_a
        )

        # Caso Válido: Com local cadastrado
        arm_cadastrado = ArmazenamentoDocumento(
            documento=doc,
            local_armazenamento=local,
            registrado_por=user
        )
        try:
            arm_cadastrado.full_clean()
        except ValidationError:
            self.fail("Armazenamento com local cadastrado deveria ser válido.")

        # Caso Válido: Com local manual
        arm_manual = ArmazenamentoDocumento(
            documento=doc,
            estante="Estante X",
            registrado_por=user
        )
        try:
            arm_manual.full_clean()
        except ValidationError:
            self.fail("Armazenamento com local manual deveria ser válido.")

        # Caso Inválido: Sem nada
        arm_vazio = ArmazenamentoDocumento(
            documento=doc,
            registrado_por=user
        )
        with self.assertRaises(ValidationError):
            arm_vazio.full_clean()

    def test_documento_fixes(self):
        """Testa as correções críticas no modelo Documento"""
        user = CustomUser.objects.create(username="doc_fixer", departamento=self.dept_a, administracao=self.admin, password="password123")
        
        # 1. Teste Telefone Validation (Mais de 9 dígitos)
        doc_invalid_phone = Documento(
            titulo="Doc Phone", 
            tipo_documento=self.tipo_doc,
            departamento_origem=self.dept_a,
            departamento_atual=self.dept_a,
            criado_por=user,
            administracao=self.admin,
            telefone="1234567890", # 10 digits
            utente="Tester"
        )
        with self.assertRaises(ValidationError):
            doc_invalid_phone.full_clean()

        # 1.1 Teste Telefone Validation (Menos de 9 dígitos)
        doc_invalid_phone_short = Documento(
            titulo="Doc Phone Short", 
            tipo_documento=self.tipo_doc,
            departamento_origem=self.dept_a,
            departamento_atual=self.dept_a,
            criado_por=user,
            administracao=self.admin,
            telefone="12345678", # 8 digits
            utente="Tester"
        )
        with self.assertRaises(ValidationError):
            doc_invalid_phone_short.full_clean()
            
        # 2. Teste Protocol Generation (Save)
        doc = Documento.objects.create(
            titulo="Doc Protocol", 
            tipo_documento=self.tipo_doc,
            departamento_origem=self.dept_a,
            departamento_atual=self.dept_a,
            criado_por=user,
            administracao=self.admin,
            telefone="900000000",
            utente="Tester"
        )
        self.assertIsNotNone(doc.numero_protocolo)
        import re
        self.assertTrue(re.match(r'^\d+/\d{4}$', doc.numero_protocolo))
