"""
Script para analisar e verificar todas as URLs do projeto.
Gera um relatório 'relatorio_urls.md' com os resultados.
"""
import os
import django
import sys
from django.urls import URLPattern, URLResolver
from django.test import Client
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SGA.settings')
django.setup()

# Adicionar 'testserver' aos hosts permitidos para o Client de teste
settings.ALLOWED_HOSTS += ['testserver']

def extract_urls(urlpatterns, prefix=''):
    """
    Extrai recursivamente todas as URLs de uma lista de urlpatterns.
    Retorna uma lista de tuplas (url_pattern_string, name, callback).
    """
    urls = []
    for pattern in urlpatterns:
        if isinstance(pattern, URLPattern):
            # É uma URL final
            full_pattern = prefix + str(pattern.pattern)
            urls.append((full_pattern, pattern.name, pattern.callback))
        elif isinstance(pattern, URLResolver):
            # É um include ou namespace
            new_prefix = prefix + str(pattern.pattern)
            urls.extend(extract_urls(pattern.url_patterns, new_prefix))
    return urls

def analyze_urls():
    print("🔍 Iniciando análise de URLs...")
    
    # Obter URL conf raiz
    urlconf = __import__(settings.ROOT_URLCONF, {}, {}, ['urlpatterns'])
    all_urls = extract_urls(urlconf.urlpatterns)
    
    print(f"📋 Total de padrões de URL encontrados: {len(all_urls)}")
    
    client = Client()
    results = []
    
    for url_pattern, name, callback in all_urls:
        # Limpar regex para tentar fazer uma requisição (muito simplificado)
        # Remove ^ e $
        clean_url = url_pattern.lstrip('^').rstrip('$')
        
        # Verificar se tem parâmetros (ex: <int:pk>, (?P<id>...))
        has_params = '<' in clean_url or '(?P' in clean_url
        
        status = "N/A"
        code = 0
        note = ""
        
        if not has_params:
            try:
                # Tentar acessar a URL
                response = client.get('/' + clean_url)
                code = response.status_code
                
                if 200 <= code < 300:
                    status = "✅ Funcional"
                elif 300 <= code < 400:
                    status = "🔄 Redirecionamento"
                elif code == 403:
                    status = "🔒 Proibido (Auth OK)"
                elif code == 404:
                    status = "❌ Não Encontrado"
                    note = "Pode ser erro ou rota inexistente"
                elif code >= 500:
                    status = "🔥 Erro de Servidor"
                    note = "Erro interno no código"
                else:
                    status = f"⚠️ Código {code}"
                    
            except Exception as e:
                status = "💥 Exceção"
                note = str(e)
        else:
            status = "❓ Requer Parâmetros"
            note = "Não testado automaticamente"
            
        results.append({
            'pattern': url_pattern,
            'clean_url': clean_url if not has_params else "N/A",
            'name': name,
            'status': status,
            'code': code,
            'note': note
        })
        
    # Gerar Relatório
    report_path = 'relatorio_urls.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Relatório de Análise de URLs\n\n")
        f.write(f"**Total de URLs:** {len(all_urls)}\n\n")
        
        f.write("| Status | URL Pattern | Nome | Código | Nota |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        
        for r in results:
            # Escapar pipes para markdown
            pattern = r['pattern'].replace('|', '\|')
            note = r['note'].replace('|', '\|')
            f.write(f"| {r['status']} | `{pattern}` | {r['name']} | {r['code'] if r['code'] else '-'} | {note} |\n")
            
    print(f"\n📄 Relatório gerado em: {os.path.abspath(report_path)}")
    print("✅ Análise concluída!")

if __name__ == '__main__':
    analyze_urls()
