"""
Script para popular as 326 Administrações Municipais conforme o 
Decreto Presidencial n.º 270/24 de 29 de novembro.

Estrutura Orgânica:
- Tipo A: 46 Municípios (centros urbanos de maior densidade)
- Tipo B: 38 Municípios (nível intermédio de desenvolvimento)
- Tipo C: 50 Municípios (unidades em consolidação)
- Tipo D: 58 Municípios (localidades rurais)
- Tipo E: 134 Municípios (localidades mais rurais/recentemente elevadas)
Total: 326 Administrações
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SGA.settings')
django.setup()

from ARQUIVOS.models import Administracao

# =============================================================================
# TODAS AS 326 ADMINISTRAÇÕES MUNICIPAIS
# Decreto Presidencial n.º 270/24 de 29 de novembro
# =============================================================================

ADMINISTRACOES = {
    # =========================================================================
    # TIPO A - 46 Municípios (Centros urbanos de maior densidade)
    # =========================================================================
    'A': {
        'Bengo': ['Dande'],
        'Benguela': ['Benguela', 'Lobito', 'Catumbela', 'Cubal'],
        'Bié': ['Andulo', 'Cuito'],
        'Cabinda': ['Cabinda'],
        'Cuando': ['Mavinga'],
        'Cuanza-Norte': ['Cazengo', 'Cambambe'],
        'Cuanza-Sul': ['Gabela', 'Sumbe'],
        'Cubango': ['Menongue'],
        'Cunene': ['Cuanhama'],
        'Huambo': ['Bailundo', 'Caála', 'Huambo'],
        'Huíla': ['Lubango', 'Matala'],
        'Icolo e Bengo': ['Catete', 'Calumbo'],
        'Luanda': [
            'Sequele', 'Cacuaco', 'Cazenga', 'Kilamba Kiaxi', 'Ingombota',
            'Viana', 'Talatona', 'Maianga', 'Rangel', 'Samba', 'Sambizanga',
            'Hoji ya Henda', 'Kilamba', 'Belas', 'Camama'
        ],
        'Lunda-Norte': ['Dundo'],
        'Lunda-Sul': ['Saurimo'],
        'Malanje': ['Malanje'],
        'Moxico Leste': ['Cazombo'],
        'Moxico': ['Luena'],
        'Namibe': ['Moçamedes'],
        'Uíge': ['Uige'],
        'Zaire': ['Mbanza Kongo', 'Soyo'],
    },
    
    # =========================================================================
    # TIPO B - 38 Municípios (Nível intermédio de desenvolvimento)
    # =========================================================================
    'B': {
        'Bengo': ['Ambriz', 'Barra do Dande', 'Nambuangongo', 'Panguila'],
        'Benguela': ['Baía Farta', 'Ganda', 'Navegantes'],
        'Bié': ['Camacupa', 'Nharea', 'Chinguar'],
        'Cabinda': ['Cacongo'],
        'Cuanza-Sul': ['Porto Amboím', 'Quibala', 'Seles', 'Waku Kungo', 'Gangula'],
        'Cubango': ['Cuchi'],
        'Cunene': ['Namacunde', 'Ombadja'],
        'Huíla': ['Caconda', 'Caluquembe', 'Chibia', 'Humpata'],
        'Icolo e Bengo': ['Bom Jesus'],
        'Luanda': ['Mulenvos'],
        'Lunda-Norte': ['Chitato', 'Cuango', 'Lucapa', 'Mussungue', 'Cafunfo'],
        'Lunda-Sul': ['Muconda', 'Cassengo'],
        'Malanje': ['Calandula', 'Cacuso'],
        'Moxico Leste': ['Luau'],
        'Namibe': ['Tombwa'],
        'Uíge': ['Maquela do Zombo', 'Negage'],
    },
    
    # =========================================================================
    # TIPO C - 50 Municípios (Unidades em consolidação)
    # =========================================================================
    'C': {
        'Bengo': ['Quibaxe', 'Muxaluando'],
        'Benguela': ['Balombo', 'Bocoio'],
        'Bié': ['Chitembo', 'Catabola', 'Cunhinga', 'Cuemba', 'Calucinga'],
        'Cabinda': ['Buco Zau', 'Liambo'],
        'Cuando': ['Cuito Cuanavale'],
        'Cuanza-Norte': ['Golungo Alto', 'Ambaca'],
        'Cuanza-Sul': ['Calulo', 'Cassongue', 'Mussende', 'Ebo', 'Condé'],
        'Cubango': ['Caiundo', 'Savate'],
        'Cunene': ['Cahama'],
        'Huambo': ['Cachiungo', 'Chicala Choloanga', 'Londuimbali', 'Mungo'],
        'Huíla': ['Cacula', 'Chicomba', 'Jamba Mineira', 'Quipungo', 'Hoque', 'Palanca'],
        'Icolo e Bengo': ['Quiçama', 'Cabo Ledo'],
        'Luanda': ['Mussulo'],
        'Lunda-Norte': ['Cambulo'],
        'Lunda-Sul': ['Cacolo', 'Dala', 'Muangueji'],
        'Moxico': ['Lumbala Nguimbo'],
        'Malanje': ['Cangandala', 'Cambundi Catembo'],
        'Namibe': ['Bibala', 'Sacomar'],
        'Uíge': ['Damba', 'Cangola', 'Bembe'],
        'Zaire': ['Luvo', 'Nóqui', 'Nzeto'],
    },
    
    # =========================================================================
    # TIPO D - 58 Municípios (Localidades rurais)
    # =========================================================================
    'D': {
        'Bengo': ['Bula Atumba', 'Pango Aluquém'],
        'Benguela': ['Chongorói', 'Caimbambo'],
        'Cabinda': ['Belize', 'Ngoio'],
        'Cuanza-Norte': ['Banga', 'Bolongongo', 'Lucala', 'Quiculungo', 'Samba Cajú'],
        'Cuanza-Sul': ['Conda', 'Quilenda', 'Boa Entrada'],
        'Cubango': ['Calai', 'Cuangar', 'Nancova', 'Cutato'],
        'Cunene': ['Curoca', 'Cuvelai'],
        'Huambo': ['Chinjenje', 'Ecunha', 'Ucuma', 'Longonjo', 'Alto Hama', 'Cuima'],
        'Huíla': ['Chipindo', 'Cuvango', 'Gambos', 'Quilengues'],
        'Lunda-Norte': ['Capenda Camulemba', 'Caungula', 'Cuilo', 'Lóvua', 'Lubalo', 'Xá Muteba'],
        'Malanje': ['Cahombo', 'Kiwaba Nzoji', 'Kunda dya Baze', 'Quela'],
        'Moxico': ['Camanongue', 'Cangamba', 'Léua', 'Cameia'],
        'Moxico Leste': ['Luacano'],
        'Namibe': ['Camucuio', 'Virei', 'Cacimbas'],
        'Uíge': ['Ambuíla', 'Dange Quitexe', 'Milunga', 'Mucaba', 'Sanza Pombo', 'Puri', 'Quimbele', 'Songo'],
        'Zaire': ['Cuimba', 'Tomboco'],
    },
    
    # =========================================================================
    # TIPO E - 134 Municípios (Localidades mais rurais/recentemente elevadas)
    # =========================================================================
    'E': {
        'Bengo': ['Piri', 'Quicunzo', 'Úcua'],
        'Benguela': [
            'Biópio', 'Bolonguera', 'Catengue', 'Chila', 'Chicuma', 'Iambala',
            'Babaera', 'Canhamela', 'Chindumbo', 'Egito Praia', 'Dombe Grande', 'Capupa'
        ],
        'Bié': [
            'Chicala', 'Chipeta', 'Luando', 'Ringoma', 'Umpulo',
            'Cambândua', 'Lúbia', 'Mumbué', 'Belo Horizonte'
        ],
        'Cabinda': ['Massabi', 'Miconje', 'Necuto', 'Tando Zinze'],
        'Cuando': ['Dirico', 'Rivungo', 'Luiana', 'Mucusso', 'Xipundo', 'Dima', 'Luengue'],
        'Cuanza-Norte': [
            'Ngonguembo', 'Aldeia Nova', 'Caculo Cabaça', 'Cerca',
            'Luinga', 'Massangano', 'Tango', 'Terreiro'
        ],
        'Cuanza-Sul': [
            'Pambangala', 'Amboiva', 'Lonhe', 'Munenga', 'Quissongo',
            'Quenha', 'Quirimbo', 'Sanga', 'Gungo'
        ],
        'Cubango': ['Chinguanja', 'Mavengue', 'Longa', 'Chissuata'],
        'Cunene': ['Mupa', 'Naulila', 'Cafima', 'Mucope', 'Nehone', 'Chitado', 'Chiéde'],
        'Huambo': ['Bimbe', 'Chilata', 'Galanga', 'Sambo'],
        'Huíla': [
            'Capunda Cavilongo', 'Dongo', 'Galangue', 'Capelongo',
            'Chituto', 'Viti Vivali', 'Chicungo'
        ],
        'Icolo e Bengo': ['Cabiri'],
        'Lunda-Norte': [
            'Cassanje Calucala', 'Luangue', 'Xá Cassau', 'Luremo', 'Camaxilo', 'Canzar'
        ],
        'Lunda-Sul': [
            'Alto Chicapa', 'Cazage', 'Chiluage', 'Luma Cassai',
            'Muriege', 'Sombo', 'Xassengue', 'Cassai - Sul'
        ],
        'Malanje': [
            'Massango', 'Marimba', 'Quirima', 'Caculama', 'Luquembo',
            'Cambo Suinginge', 'Cateco Cangola', 'Mbanji ya Ngola', 'Muquixe',
            'Pungu a Ndongo', 'Ngola Luiji', 'Quihuhu', 'Quitapa', 'Xandel',
            'Capunda', 'Cuale', 'Milando', 'Quêssua'
        ],
        'Moxico': [
            'Alto Cuito', 'Cangumbe', 'Chiúme', 'Lucusse', 'Lutembo',
            'Lutuai', 'Ninda', 'Lago Dilolo', 'Nana Candundo'
        ],
        'Moxico Leste': ['Caianda', 'Macondo', 'Lóvua do Zambeze'],
        'Namibe': ['Iona', 'Lucira', 'Nova Esperança'],
        'Uíge': [
            'Bungo', 'Lucunga', 'Quipedro', 'Vista Alegre',
            'Alto Zaza', 'Nsosso', 'Sacandica', 'Massau'
        ],
        'Zaire': ['Lufico', 'Quêlo', 'Quindeje', 'Serra de Canda'],
    },
}


def popular_administracoes():
    """Popula todas as 326 administrações com tipo e província."""
    criadas = 0
    atualizadas = 0
    
    totais_por_tipo = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0}
    
    for tipo, provincias in ADMINISTRACOES.items():
        for provincia, municipios in provincias.items():
            for municipio in municipios:
                obj, created = Administracao.objects.update_or_create(
                    nome=municipio,
                    defaults={
                        'tipo_municipio': tipo,
                        'provincia': provincia,
                    }
                )
                totais_por_tipo[tipo] += 1
                
                if created:
                    criadas += 1
                    print(f"[+] Criada: {municipio} - Tipo {tipo} - {provincia}")
                else:
                    atualizadas += 1
                    print(f"[=] Atualizada: {municipio} - Tipo {tipo} - {provincia}")
    
    print(f"\n{'='*60}")
    print(f"RESUMO - Decreto Presidencial n.º 270/24 de 29 de novembro")
    print(f"{'='*60}")
    print(f"  Tipo A (Centros urbanos):            {totais_por_tipo['A']:>3} municípios")
    print(f"  Tipo B (Nível intermédio):           {totais_por_tipo['B']:>3} municípios")
    print(f"  Tipo C (Em consolidação):            {totais_por_tipo['C']:>3} municípios")
    print(f"  Tipo D (Localidades rurais):         {totais_por_tipo['D']:>3} municípios")
    print(f"  Tipo E (Mais rurais/recentes):       {totais_por_tipo['E']:>3} municípios")
    print(f"{'='*60}")
    print(f"  TOTAL: {sum(totais_por_tipo.values())} administrações")
    print(f"{'='*60}")
    print(f"\n  Administrações criadas:    {criadas}")
    print(f"  Administrações atualizadas: {atualizadas}")
    print(f"  Total processado:          {criadas + atualizadas}")


if __name__ == '__main__':
    print("="*60)
    print("POPULAR ADMINISTRAÇÕES MUNICIPAIS DE ANGOLA")
    print("Decreto Presidencial n.º 270/24 de 29 de novembro")
    print("="*60)
    popular_administracoes()
    print("\n✅ Concluído!")
