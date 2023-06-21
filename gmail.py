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