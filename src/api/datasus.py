# -*- coding: utf-8 -*-
import os
import xmltodict
import requests, json
from suds.sax.text import Raw

DATASUS_USER = os.environ.get('DATASUS_USER')
DATASUS_PASSWORD = os.environ.get('DATASUS_PASSWORD')
url = "https://servicos.saude.gov.br/cadsus/PDQSupplier"
headers = {"content-type": "application/soap+xml"}


def __get_element_dict_or_list(data, key, index=0):
    try:
        return data.get(key, None)
    except Exception as e:
        return data[index].get(key, None)

def __extract_data(data_soap):
    dados_paciente = \
    data_soap['soap:Envelope']['S:Body']['PRPA_IN201306UV02']['controlActProcess']['subject']['registrationEvent'][
        'subject1']['patient']['patientPerson']
    dados_paciente = json.loads(json.dumps(dados_paciente))
    parsed_data = dict()

    parsed_data['nome'] = __get_element_dict_or_list(dados_paciente['name'], 'given')

    data_nasc = dados_paciente['birthTime']['@value']
    if data_nasc:
        parsed_data['data_nascimento'] = '{}-{}-{}'.format(data_nasc[0:4], data_nasc[4:6], data_nasc[6:8])

    parsed_data['sexo'] = dados_paciente['administrativeGenderCode']['@code']

    if 'addr' in dados_paciente:
        parsed_data['logradouro'] = __get_element_dict_or_list(dados_paciente['addr'], 'streetName')
        parsed_data['bairro'] = __get_element_dict_or_list(dados_paciente['addr'], 'additionalLocator')
        parsed_data['codigo_mun'] = __get_element_dict_or_list(dados_paciente['addr'], 'city')
        if __get_element_dict_or_list(dados_paciente['addr'], 'postalCode'):
            parsed_data['cep'] = __get_element_dict_or_list(dados_paciente['addr'], 'postalCode')

        if __get_element_dict_or_list(dados_paciente['addr'], 'houseNumber'):
            parsed_data['numero'] = __get_element_dict_or_list(dados_paciente['addr'], 'houseNumber')

    if dados_paciente.get('telecom', None):
        telefone = __get_element_dict_or_list(dados_paciente['telecom'], '@value', 1)

        if telefone:
            try:
                parsed_data['telefone'] = '({}){}-{}'.format(telefone.split('-')[1], telefone.split('-')[2][0:4],
                                                             telefone.split('-')[2][4:])
            except Exception as e:
                parsed_data['telefone'] = None

    try:
        parsed_data['cns'] = dados_paciente['asOtherIDs'][0]['id'][0]['@extension']
    except Exception as e:
        parsed_data['cns'] = None

    return parsed_data


def busca_por_cpf(cpf):
    if not cpf or not DATASUS_USER:
        return {}
    body = Raw(
        '''
            <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:urn="urn:ihe:iti:xds-b:2007" xmlns:urn1="urn:oasis:names:tc:ebxml-regrep:xsd:lcm:3.0" xmlns:urn2="urn:oasis:names:tc:ebxml-regrep:xsd:rim:3.0" xmlns:urn3="urn:ihe:iti:xds-b:2007">
                <soap:Header>
                    <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
                    <wsse:UsernameToken wsu:Id="Id-0001334008436683-000000002c4a1908-1" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
                        <wsse:Username>{}</wsse:Username>
                        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">{}</wsse:Password>
                    </wsse:UsernameToken>
                    </wsse:Security>
                </soap:Header>
                <soap:Body>
                    <PRPA_IN201305UV02 xsi:schemaLocation="urn:hl7-org:v3 ./schema/HL7V3/NE2008/multicacheschemas/PRPA_IN201305UV02.xsd" ITSVersion="XML_1.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="urn:hl7-org:v3">
                    <id root="2.16.840.1.113883.4.714" extension="123456"/>
                    <creationTime value="20070428150301"/>
                    <interactionId root="2.16.840.1.113883.1.6" extension="PRPA_IN201305UV02"/>
                    <processingCode code="T"/>
                    <processingModeCode code="T"/>
                    <acceptAckCode code="AL"/>
                    <receiver typeCode="RCV">
                        <device classCode="DEV" determinerCode="INSTANCE">
                            <id root="2.16.840.1.113883.3.72.6.5.100.85"/>
                        </device>
                    </receiver>
                    <sender typeCode="SND">
                        <device classCode="DEV" determinerCode="INSTANCE">
                            <id root="2.16.840.1.113883.3.72.6.2"/>
                            <name>[SYSTEMCODE]</name>
                        </device>
                    </sender>
                    <controlActProcess classCode="CACT" moodCode="EVN">
                        <code code="PRPA_TE201305UV02" codeSystem="2.16.840.1.113883.1.6"/>
                        <queryByParameter>
                            <queryId root="1.2.840.114350.1.13.28.1.18.5.999" extension="1840997084"/>
                            <statusCode code="new"/>
                            <responseModalityCode code="R"/>
                            <responsePriorityCode code="I"/>
                            <parameterList>
                                <livingSubjectId>
                                <value root="2.16.840.1.113883.13.237" extension="{}"/>
                                <semanticsText>LivingSubject.id</semanticsText>
                                </livingSubjectId>
                            </parameterList>
                        </queryByParameter>
                    </controlActProcess>
                    </PRPA_IN201305UV02>
                </soap:Body>
            </soap:Envelope>
        '''.format(DATASUS_USER, DATASUS_PASSWORD, cpf))

    try:
        response = requests.post(url, data=body, headers=headers, verify=False)
    except Exception as e:
        return {}

    if response.status_code == 200:
        data_soap = xmltodict.parse(response.content)  # OrderedDict
        if list(data_soap['soap:Envelope']['S:Body'].items()):
            return __extract_data(data_soap)

    return {}
