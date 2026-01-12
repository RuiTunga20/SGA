
# --- PROGRAMA PARA ESTUDO ---

# 1. Variáveis e Entrada de Dados (Input)
nome_dog = input("Qual o nome do seu cachorro? ")
idade_real = input(f"Quantos anos o {nome_dog} tem? ")

# 2. Conversão de Tipos (Casting)
# O input sempre recebe texto (string), precisamos converter para número (int)
idade_inteira = int(idade_real)

# 3. Operações Matemáticas
idade_humana = idade_inteira * 7

# 4. Estruturas de Decisão (If/Else)
if idade_humana > 60:
    status = "um senhorzinho(a)!"
else:
    status = "muito jovem!"

# 5. Saída de Dados (F-string)
print(f"\nO {nome_dog} tem {idade_humana} anos em 'anos humanos'.")
print(f"Ele(a) é {status}")