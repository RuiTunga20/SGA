from django.core.management.base import BaseCommand
from ARQUIVOS.models import Administracao

class Command(BaseCommand):
    help = 'Popula a base de dados com todas as administrações municipais de Angola (164 Municípios)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Iniciando o cadastro das 164 Administrações...'))

        municipios = [
            # --- PROVÍNCIA DO BENGO (6) ---
            ("Dande (Caxito)", "B", "Bengo"),
            ("Ambriz", "C", "Bengo"),
            ("Bula Atumba", "D", "Bengo"),
            ("Dembos", "C", "Bengo"),
            ("Nambuangongo", "D", "Bengo"),
            ("Pango Aluquém", "D", "Bengo"),

            # --- PROVÍNCIA DE BENGUELA (10) ---
            ("Benguela", "A", "Benguela"),
            ("Lobito", "A", "Benguela"),
            ("Catumbela", "B", "Benguela"),
            ("Baía Farta", "B", "Benguela"),
            ("Balombo", "C", "Benguela"),
            ("Bocoio", "C", "Benguela"),
            ("Caimbambo", "C", "Benguela"),
            ("Chongoroi", "D", "Benguela"),
            ("Cubal", "C", "Benguela"),
            ("Ganda", "C", "Benguela"),

            # --- PROVÍNCIA DO BIÉ (9) ---
            ("Kuito", "B", "Bié"),
            ("Andulo", "C", "Bié"),
            ("Camacupa", "C", "Bié"),
            ("Catabola", "C", "Bié"),
            ("Chinguar", "C", "Bié"),
            ("Chitembo", "D", "Bié"),
            ("Cuemba", "D", "Bié"),
            ("Cunhinga", "D", "Bié"),
            ("Nharea", "D", "Bié"),

            # --- PROVÍNCIA DE CABINDA (4) ---
            ("Cabinda", "A", "Cabinda"),
            ("Cacongo", "C", "Cabinda"),
            ("Buco-Zau", "C", "Cabinda"),
            ("Belize", "D", "Cabinda"),

            # --- PROVÍNCIA DO CUANDO CUBANGO (9) ---
            ("Menongue", "B", "Cuando Cubango"),
            ("Calai", "C", "Cuando Cubango"),
            ("Cuangar", "C", "Cuando Cubango"),
            ("Cuchi", "D", "Cuando Cubango"),
            ("Cuito Cuanavale", "C", "Cuando Cubango"),
            ("Dirico", "D", "Cuando Cubango"),
            ("Mavinga", "D", "Cuando Cubango"),
            ("Nancova", "D", "Cuando Cubango"),
            ("Rivungo", "D", "Cuando Cubango"),

            # --- PROVÍNCIA DO CUANZA NORTE (10) ---
            ("Cazengo (Ndalatando)", "B", "Cuanza Norte"),
            ("Ambaca", "C", "Cuanza Norte"),
            ("Banga", "D", "Cuanza Norte"),
            ("Bolongongo", "D", "Cuanza Norte"),
            ("Cambambe", "C", "Cuanza Norte"),
            ("Golungo Alto", "C", "Cuanza Norte"),
            ("Gonguembo", "D", "Cuanza Norte"),
            ("Lucala", "C", "Cuanza Norte"),
            ("Quiculungo", "D", "Cuanza Norte"),
            ("Samba Cajú", "C", "Cuanza Norte"),

            # --- PROVÍNCIA DO CUANZA SUL (12) ---
            ("Sumbe", "B", "Cuanza Sul"),
            ("Porto Amboim", "B", "Cuanza Sul"),
            ("Amboim", "C", "Cuanza Sul"),
            ("Cassongue", "C", "Cuanza Sul"),
            ("Cela (Waku Kungo)", "B", "Cuanza Sul"), # Centro importante
            ("Conda", "D", "Cuanza Sul"),
            ("Ebo", "D", "Cuanza Sul"),
            ("Libolo", "C", "Cuanza Sul"),
            ("Mussende", "C", "Cuanza Sul"),
            ("Quibala", "C", "Cuanza Sul"),
            ("Quilenda", "D", "Cuanza Sul"),
            ("Seles", "C", "Cuanza Sul"),

            # --- PROVÍNCIA DO CUNENE (6) ---
            ("Cuanhama (Ondjiva)", "B", "Cunene"),
            ("Cahama", "C", "Cunene"),
            ("Cuvelai", "D", "Cunene"),
            ("Namacunde", "C", "Cunene"),
            ("Ombadja", "C", "Cunene"),
            ("Curoca", "D", "Cunene"),

            # --- PROVÍNCIA DO HUAMBO (11) ---
            ("Huambo", "A", "Huambo"),
            ("Bailundo", "B", "Huambo"), # Histórico/População
            ("Caála", "B", "Huambo"), # Proximidade capital
            ("Cachiungo", "C", "Huambo"),
            ("Chicala-Choloanga", "C", "Huambo"),
            ("Chinjenje", "D", "Huambo"),
            ("Ecunha", "C", "Huambo"),
            ("Londuimbali", "C", "Huambo"),
            ("Longonjo", "C", "Huambo"),
            ("Mungo", "D", "Huambo"),
            ("Ucuma", "C", "Huambo"),

            # --- PROVÍNCIA DA HUÍLA (14) ---
            ("Lubango", "A", "Huíla"),
            ("Caconda", "C", "Huíla"),
            ("Cacula", "C", "Huíla"),
            ("Caluquembe", "C", "Huíla"),
            ("Chiange", "D", "Huíla"),
            ("Chibia", "C", "Huíla"),
            ("Chicomba", "D", "Huíla"),
            ("Chipindo", "D", "Huíla"),
            ("Cuvango", "C", "Huíla"),
            ("Humpata", "C", "Huíla"),
            ("Jamba", "C", "Huíla"),
            ("Matala", "B", "Huíla"), # Polo forte
            ("Quilengues", "C", "Huíla"),
            ("Quipungo", "C", "Huíla"),

            # --- PROVÍNCIA DE LUANDA (9) ---
            ("Luanda", "A", "Luanda"),
            ("Belas", "A", "Luanda"),
            ("Cacuaco", "A", "Luanda"),
            ("Cazenga", "A", "Luanda"),
            ("Ícolo e Bengo", "C", "Luanda"),
            ("Kilamba Kiaxi", "A", "Luanda"),
            ("Quiçama", "D", "Luanda"), # Área rural extensa
            ("Talatona", "A", "Luanda"),
            ("Viana", "A", "Luanda"),

            # --- PROVÍNCIA DA LUNDA NORTE (10) ---
            ("Chitato (Dundo)", "B", "Lunda Norte"),
            ("Cambulo", "C", "Lunda Norte"),
            ("Capenda-Camulemba", "D", "Lunda Norte"),
            ("Caungula", "C", "Lunda Norte"),
            ("Cuango", "C", "Lunda Norte"),
            ("Cuilo", "C", "Lunda Norte"),
            ("Lóvua", "D", "Lunda Norte"),
            ("Lubalo", "D", "Lunda Norte"),
            ("Lucapa", "C", "Lunda Norte"),
            ("Xá-Muteba", "C", "Lunda Norte"),

            # --- PROVÍNCIA DA LUNDA SUL (4) ---
            ("Saurimo", "B", "Lunda Sul"),
            ("Cacolo", "D", "Lunda Sul"),
            ("Dala", "D", "Lunda Sul"),
            ("Muconda", "C", "Lunda Sul"),

            # --- PROVÍNCIA DE MALANJE (14) ---
            ("Malanje", "B", "Malanje"),
            ("Cacuso", "C", "Malanje"),
            ("Calandula", "C", "Malanje"),
            ("Cambundi-Catembo", "D", "Malanje"),
            ("Cangandala", "C", "Malanje"),
            ("Caombo", "D", "Malanje"),
            ("Cuaba Nzogo", "D", "Malanje"),
            ("Cunda-Dia-Baze", "D", "Malanje"),
            ("Luquembo", "D", "Malanje"),
            ("Marimba", "D", "Malanje"),
            ("Massango", "D", "Malanje"),
            ("Mucari", "C", "Malanje"),
            ("Quela", "D", "Malanje"),
            ("Quirima", "D", "Malanje"),

            # --- PROVÍNCIA DO MOXICO (9) ---
            ("Moxico (Luena)", "B", "Moxico"),
            ("Alto Zambeze", "D", "Moxico"),
            ("Bundas", "D", "Moxico"),
            ("Camanongue", "C", "Moxico"),
            ("Léua", "C", "Moxico"),
            ("Luacano", "D", "Moxico"),
            ("Luau", "C", "Moxico"), # Fronteira importante
            ("Luchazes", "D", "Moxico"),
            ("Cameia", "D", "Moxico"),

            # --- PROVÍNCIA DO NAMIBE (5) ---
            ("Moçâmedes", "B", "Namibe"),
            ("Bibala", "C", "Namibe"),
            ("Camacuio", "D", "Namibe"),
            ("Tômbwa", "C", "Namibe"),
            ("Virei", "D", "Namibe"),

            # --- PROVÍNCIA DO UÍGE (16) ---
            ("Uíge", "B", "Uíge"),
            ("Alto Cauale", "D", "Uíge"),
            ("Ambuíla", "D", "Uíge"),
            ("Bembe", "D", "Uíge"),
            ("Buengas", "D", "Uíge"),
            ("Bungo", "C", "Uíge"),
            ("Damba", "C", "Uíge"),
            ("Maquela do Zombo", "C", "Uíge"),
            ("Milunga", "D", "Uíge"),
            ("Mucaba", "D", "Uíge"),
            ("Negage", "C", "Uíge"),
            ("Puri", "D", "Uíge"),
            ("Quimbele", "D", "Uíge"),
            ("Quitexe", "C", "Uíge"),
            ("Sanza Pombo", "C", "Uíge"),
            ("Songo", "C", "Uíge"),

            # --- PROVÍNCIA DO ZAIRE (6) ---
            ("Mbanza Kongo", "B", "Zaire"),
            ("Soyo", "A", "Zaire"), # Económico Petróleo
            ("Cuimba", "D", "Zaire"),
            ("Nóqui", "D", "Zaire"),
            ("Nzeto", "C", "Zaire"),
            ("Tomboco", "C", "Zaire"),
        ]

        count_criados = 0
        count_existentes = 0

        for nome, tipo, provincia in municipios:
            # Usa o nome formatado para evitar conflitos
            nome_completo = f"Administração Municipal de {nome}"
            
            # Tenta buscar ou criar
            obj, created = Administracao.objects.get_or_create(
                nome=nome_completo,
                defaults={
                    'tipo_municipio': tipo,
                    'provincia': provincia
                }
            )

            if created:
                count_criados += 1
                self.stdout.write(self.style.SUCCESS(f'Criado: {nome} [{tipo}] - {provincia}'))
            else:
                # Se já existe, atualiza o tipo e a província caso tenham mudado
                mudou = False
                if obj.tipo_municipio != tipo:
                    obj.tipo_municipio = tipo
                    mudou = True
                if hasattr(obj, 'provincia') and obj.provincia != provincia:
                    obj.provincia = provincia
                    mudou = True
                
                if mudou:
                    obj.save()
                    self.stdout.write(self.style.WARNING(f'Atualizado: {nome}'))
                
                count_existentes += 1

        self.stdout.write(self.style.SUCCESS(f'\nCONCLUSÃO:'))
        self.stdout.write(f'Novos Municípios cadastrados: {count_criados}')
        self.stdout.write(f'Municípios já existentes: {count_existentes}')
        self.stdout.write(f'Total processado: {count_criados + count_existentes}')
