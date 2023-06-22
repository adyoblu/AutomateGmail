from flask import Flask, request, jsonify, render_template
import pickle
import os.path
from apiclient import errors
import email
from datetime import datetime
import pytz
import sys
import quopri
from email.header import decode_header
import signal
import os
from googleapiclient import errors
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import base64

# autorizatie fara restrictii
SCOPES = ['https://mail.google.com/']

app = Flask(__name__, template_folder='templates')

search_string = sys.argv[1]

@app.route('/close-server', methods=['POST'])
def close_server():
    os.kill(os.getpid(), signal.SIGINT)
    return jsonify

@app.route('/')
def display_message():
    service = get_service()

    # Definiți ID-ul utilizatorului (adresa de e-mail)
    user_id = 'me'
    # Definiți șirul de căutare pentru mesaje
    #search_string = 'simplu'  # înlocuiți cu căutarea dorită

    # Apelați funcția search_message pentru a obține lista de ID-uri ale mesajelor căutate
    message_ids = search_message(service, user_id, search_string)
    if not message_ids:
        return "Nu s-au găsit mesaje conform căutării."
    

    message_content_list = []
    # Iterați prin fiecare ID de mesaj și obțineți conținutul mesajelor
    for msg_id in message_ids :
        message_content = get_message(service, user_id, msg_id)
        message_content['id'] = msg_id
        print(message_content)
        message_content_list.append(message_content)
    
    print(message_content_list)
    return render_template('messages.html', messages=message_content_list)


def search_message(service, user_id, search_string):
    try:
        list_ids = []  # lista cu id-uri
        search_ids = service.users().messages().list(userId=user_id, q=search_string).execute()
        try:
            ids = search_ids['messages']
        except KeyError:
            print("Atenție: Căutarea nu a returnat niciun rezultat.")
            return []

        for msg_id in ids:  # iterez prin toate
            message = service.users().messages().get(userId=user_id, id=msg_id['id']).execute()
            subject = None
            headers = message['payload'].get('headers')
            if headers:
                for header in headers:
                    if header['name'].lower() == 'subject':
                        subject = header['value']
                        break
            if subject is not None and search_string.lower() in subject.lower():
                list_ids.append(msg_id['id'])  # adaug în lista de ID-uri toate ID-urile

        return list_ids

    except errors.HttpError as error:
        print("Eroare: %s" % error)

def get_message(service, user_id, msg_id):
    try:
        message = service.users().messages().get(userId=user_id, id=msg_id, format='raw').execute()
        raw_data = message['raw']
        msg_str = base64.urlsafe_b64decode(raw_data).decode('utf-8')
        mime_msg = email.message_from_string(msg_str)

        sender = mime_msg['From']
        recipient = mime_msg['To']
        subject = mime_msg['Subject']
        if subject is not None:
            subject = decode_header(subject)[0][0]
            subject = quopri.decodestring(subject).decode('utf-8', errors='replace')

        html_content = None
        for part in mime_msg.walk():
            if part.get_content_type() == 'text/html':
                html_content = part.get_payload(decode=True).decode('utf-8', errors='replace')
                break

        date = mime_msg.get('Date')
        timezone = pytz.timezone("Europe/Bucharest")
        parsed_date = email.utils.parsedate_to_datetime(date)
        datetime_obj = parsed_date.astimezone(timezone)
        formatted_date = datetime_obj.strftime("%Y-%m-%d %H:%M:%S")

        message_data = {
            'sender': sender,
            'recipient': recipient,
            'subject': subject,
            'date': formatted_date,
            'content': html_content
        }

        return message_data

    except errors.HttpError as error:
        print('A apărut o eroare: %s') % error


#return va fi <googleapiclient.discovery.Resource at 0x284631d0790>
def get_service():
    creds = None
    # token.pickle salveaza accesul user-ului the user access, refresh_token si este generat automat 
    # cand e autorizata aplicatia de user
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # Daca credentialele nu sunt valide, user-ul se logheaza
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Salvez credentiale pentru data viitoare
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    return service

if __name__ == '__main__':
    app.run(debug=True)