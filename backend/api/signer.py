# pip install --upgrade fpdf2
from django.core.cache import cache
import requests
import os
from time import sleep
import requests
from slth.pdf import PdfSigner


class VidaasPdfSigner(PdfSigner):
    def authorize(self, authorization_code):
        cache.set(self.signer, authorization_code)
    
    def sign_hash(self, hash):
        redirect_url = 'push://http://viddas.com.br'
        code_verifier = 'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstwcM'
        authorization_code = cache.get(self.signer, None)
        if authorization_code:
            print('Using cached authorization token...')
            print(authorization_code)
        else:
            cpf = self.signer.split(':')[-1]
            
            url = 'https://certificado.vidaas.com.br/valid/api/v1/trusted-services/authorizations?client_id={}&code_challenge={}&code_challenge_method=S256&response_type=code&scope=signature_session&login_hint={}&lifetime=900&redirect_uri={}'.format(
                os.environ.get('VIDAAS_API_KEY'), code_verifier, cpf, redirect_url
            )
            response = requests.get(url)
            print(url)
            print(response.status_code, response.text)
            authentication_code = response.text
            url = 'https://certificado.vidaas.com.br/valid/api/v1/trusted-services/authentications?{}'.format(authentication_code)
            print(url)
            for i in range(0, 5):
                print(f'({i}) Waiting sign authorization...')
                sleep(10)
                response = requests.get(url)
                print(response.status_code, response.text)
                if response.status_code == 200:
                    data = response.json()
                    print(data)
                    authorization_code = response.json()['authorizationToken']
                    print(authorization_code)
                    print('Setting authorization code into cache....')
                    cache.set(self.signer, authorization_code, timeout=900)
                    break
        # authorization_code = ''
        if authorization_code:
            url = 'https://certificado.vidaas.com.br/v0/oauth/token'
            client_id = os.environ.get('VIDAAS_API_KEY')
            client_secret = os.environ.get('VIDAAS_API_SEC')
            data = dict(grant_type='authorization_code', code=authorization_code, redirect_uri=redirect_url, code_verifier=code_verifier, client_id=client_id, client_secret=client_secret)
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            response = requests.post(url, headers=headers, data=data).json()
            access_token = response['access_token']
            url = 'https://certificado.vidaas.com.br/valid/api/v1/trusted-services/signatures'
            headers = {'Content-type': 'application/json', 'Authorization': 'Bearer {}'.format(access_token)}
            data = {"hashes": [{"id": self.path, "alias": self.path, "hash": hash, "hash_algorithm": "2.16.840.1.101.3.4.2.1", "signature_format": "CMS"}]}#, "base64_content": base64_content,
            response = requests.post(url, json=data, headers=headers).json()
            return response['signatures'][0]['raw_signature']
        return None


#curl -X POST 'https://verificador.staging.iti.br/report' --header 'Content-Type: multipart/form-data' --form 'report_type="json"' --form 'signature_files[]=@"hello-assinado.pdf"' --form 'detached_files[]=""'
