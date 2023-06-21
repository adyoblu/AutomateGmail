from flask import Flask, request, render_template
import pickle
import os.path
from apiclient import errors
import email
import subprocess
import webbrowser
from datetime import datetime
import pytz
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import base64

# autorizatie fara restrictii
SCOPES = ['https://mail.google.com/']

app = Flask(__name__, template_folder='templates')
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

search_string = None

def display_messages_today():
    # Implementați codul pentru a afișa mesajele din inbox de astăzi
    pass

def create_message_backup():
    # Implementați codul pentru a crea un backup pentru mesaje
    pass

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
        list_ids = [] #lista cu id-uri
        search_ids = service.users().messages().list(userId=user_id, q=search_string).execute()
        try:
            ids = search_ids['messages']
        except KeyError:
            print("WARNING: cautarea a returnat 0 rezultate")
            return []

        for msg_id in ids: # iterez prin toate
            list_ids.append(msg_id['id']) # adaug în lista de ID-uri toate ID-urile
        return list_ids

    except errors.HttpError as error:
        print("Eroare: %s") % error


def get_message(service, user_id, msg_id):
    try:
        # message instance
        message = service.users().messages().get(userId=user_id, id=msg_id,format='raw').execute()

        # decode raw in ASCII
        msg_str = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))

        # grab the string from the byte object
        mime_msg = email.message_from_bytes(msg_str)

        # check if the content is multipart (it usually is)
        content_type = mime_msg.get_content_maintype()
        
        # there will usually be 2 parts the first will be the body in text
        # the second will be the text in html
        parts = mime_msg.get_payload()

        # return the encoded text
        #final_content = parts[0].get_payload()
        html_content = parts[0].get_payload(decode=True).decode('utf-8')
        #text_content = html2text.html2text(html_content)
        #final_content = text_content.strip()


        date = mime_msg.get('Date')
        timezone = pytz.timezone("Europe/Bucharest")
        parsed_date = email.utils.parsedate_to_datetime(date)
        datetime_obj = parsed_date.astimezone(timezone)
        formatted_date = datetime_obj.strftime("%Y-%m-%d %H:%M:%S")

        message_data = {
            'date': formatted_date,
            'content': html_content
        }
        return message_data

    except errors.HttpError as error:
        print('An error occured: %s') % error

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


def display_menu():
    print("Meniu:")
    print("1. Afiseaza mesajele de astazi")
    print("2. Afiseaza mesajele in functie de subiect anume")
    print("3. Fa backup mesaje")
    print("0. Ieșire")

def handle_option(option):
    if option == 1:
        os.system('cls')
        print("Ați selectat Opțiunea 1")
        display_messages_today()
        # Adăugați aici codul corespunzător pentru Opțiunea 1
    elif option == 2:
        os.system('cls')
        print("Ați selectat Opțiunea 2")
        search_string = input("Introduceți un string de cautat in subiecte: ")
        print("Ați introdus:", search_string)
        webbrowser.open("http://127.0.0.1:5000", new=0)
        server_process = subprocess.run(['python', 'search.py', search_string])
        
        
        # Adăugați aici codul corespunzător pentru Opțiunea 2
    elif option == 3:
        os.system('cls')
        print("Ați selectat Opțiunea 3")
        # Adăugați aici codul corespunzător pentru Opțiunea 3
    elif option == 0:
        os.system('cls')
        print("La revedere!")
        return False
    else:
        os.system('cls')
        print("Opțiune invalidă. Vă rugăm să selectați o opțiune validă.")
    return True

def main():
    while True:
        os.system('cls')
        display_menu()
        option = int(input("Introduceți opțiunea: "))
        if not handle_option(option):
            break

def run_local_server():
    subprocess.run(['flask', 'run'], check=True)
#display_message()
if __name__ == '__main__':
    main()