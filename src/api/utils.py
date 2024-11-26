import os
import requests
import re
from .models import Estado, Municipio
        

def buscar_endereco(cep):
    endereco = {}
    if cep:
        dados = requests.get('{}{}'.format(os.environ['CEP_API_URL'], cep.replace('.', '').replace('-', ''))).json()
        sigla, nome, codigo = dados['estado'], dados['estado_info']['nome'], dados['estado_info']['codigo_ibge']
        estado = Estado.objects.get_or_create(sigla=sigla, codigo=codigo, nome=nome)[0]
        nome, codigo = dados['cidade'], dados['cidade_info']['codigo_ibge']
        municipio = Municipio.objects.filter(codigo=codigo).first()
        if municipio is None:
            municipio = Municipio.objects.get_or_create(estado=estado, codigo=codigo, nome=nome)[0]
        endereco.update(bairro=dados['bairro'], logradouro=dados['logradouro'], municipio=municipio)
    return endereco


def normalizar_nome(nome):
    ponto = r'\.'
    ponto_espaco = '. '
    espaco = ' '
    regex_multiplos_espacos = r'\s+'
    regex_numero_romano = r'^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$'

    # colocando espaço após nomes abreviados
    nome = re.sub(ponto, ponto_espaco, nome or '')
    # retirando espaços múltiplos
    nome = re.sub(regex_multiplos_espacos, espaco, nome)
    nome = nome.title()  # alterando os nomes para CamelCase
    partes_nome = nome.split(espaco)  # separando as palavras numa lista
    excecoes = [
        'de',
        'di',
        'do',
        'da',
        'dos',
        'das',
        'dello',
        'della',
        'dalla',
        'dal',
        'del',
        'e',
        'em',
        'na',
        'no',
        'nas',
        'nos',
        'van',
        'von',
        'y',
        'a',
    ]

    resultado = []

    for palavra in partes_nome:
        if palavra.lower() in excecoes:
            resultado.append(palavra.lower())
        elif re.match(regex_numero_romano, palavra.upper()):
            resultado.append(palavra.upper())
        else:
            resultado.append(palavra)

    nome = espaco.join(resultado)
    return nome
