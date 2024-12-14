import requests

def enviar_mensagem(telefone, mensagem):
    url = 'https://whatsapp.aplicativo.click/send'
    headers={"Content-Type": "application/json", "Authorization": "Token undefined"}
    telefone = telefone.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
    telefone = '55{}{}@c.us'.format(telefone[0:2], telefone[3:])
    data = {"to": telefone, "message": mensagem}
    response = requests.post(url, headers=headers, json=data)
    response.status_code == 200
