from django.db import migrations

def create_generic_departments(apps, schema_editor):
    Departamento = apps.get_model('ARQUIVOS', 'Departamento')
    
    # Departamentos Genéricos para Tipo A
    depts_tipo_a = [
        'Direção de Finanças',
        'Direção de Recursos Humanos',
        'Direção de Administração',
        'Direção de Saúde',
        'Direção de Educação',
    ]
    
    for nome in depts_tipo_a:
        Departamento.objects.get_or_create(
            nome=nome,
            tipo_municipio='A',
            administracao=None, # Genérico
            defaults={'descricao': f'Departamento genérico de {nome} para municípios Tipo A'}
        )

    # Adicionar outros tipos se necessário...

class Migration(migrations.Migration):

    dependencies = [
        ('ARQUIVOS', '0034_alter_customuser_managers_departamento_administracao'), # Depende da última migration
    ]

    operations = [
        migrations.RunPython(create_generic_departments),
    ]
