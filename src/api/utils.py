import os
import requests
import re
from datetime import datetime
from .datasus import busca_por_cpf
from .models import Estado, Municipio


def buscar_pessoafisica(cpf):
    dados = busca_por_cpf(cpf.replace('.', '').replace('-', ''))
    if dados:
        nome = dados['nome']
        data_nascimento = dados['data_nascimento'] #datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').strftime('%d/%m/%Y')
        sexo = dict(M='Masculino', F='Feminino')[dados['sexo']]
        cep = dados['cep']
        if cep:
            cep = '{}.{}-{}'.format(cep[0:2], cep[2:5], cep[5:])
        endereco = dados['logradouro']
        numero = dados['numero']
        return dict(nome=nome, data_nascimento=data_nascimento, sexo=sexo, cep=cep, endereco=endereco, numero=numero)
    return {}

def buscar_endereco(cep):
    endereco = {}
    if cep:
        cep = cep.replace('.', '').replace('-', '')
        url = os.environ['CEP_API_URL'].format(cep)
        response = requests.get(url)
        if response.status_code == 200:
            dados = response.json()
            if 'uf' in dados:
                sigla, nome, codigo = dados['uf'], dados['estado'], dados['ibge'][0:2]
                estado = Estado.objects.get_or_create(sigla=sigla, defaults=dict(codigo=codigo, nome=nome))[0]
                nome, codigo = dados['localidade'], dados['ibge']
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
