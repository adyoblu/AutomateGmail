import PySimpleGUI as sg
import os.path
import subprocess
import webbrowser

def display_menu():
    layout = [
        [sg.Button("1) Afiseaza toate mesajele de astazi(INBOX si SPAM)", key='option1')],
        [sg.Button("2) Afiseaza mesajele in functie de subiect anume", key='option2')],
        [sg.Button("4) Ieșire", key='option0')]
    ]
    
    return sg.Window("Meniu", layout, finalize=True)

def main():
    window = display_menu()

    while True:
        event, _ = window.read()
        if event == sg.WINDOW_CLOSED or event == 'option0':
            break
        elif event == 'option1':
            os.system('cls')
            window.hide()
            layout = [
                [sg.Text(f"Ați selectat Opțiunea 1")]
            ]
            option1_window = sg.Window("Opțiunea selectată", layout, finalize=True)
            option1_window.close()
            webbrowser.open("http://127.0.0.1:5000", new=0)
            subprocess.run(['python', 'today.py'])
            window.un_hide()
            
        elif event == 'option2':
            os.system('cls')
            window.hide()
            layout = [
                [sg.Text(f"Ați selectat Opțiunea 2")],
                [sg.Text("Introduceți un string de căutat în subiecte: "), sg.InputText(key='search_string')],
                [sg.Button("OK", key='ok')]
            ]
            option2_window = sg.Window("Opțiunea selectată", layout, finalize=True)
            
            while True:
                event, values = option2_window.read()
                
                if event == sg.WINDOW_CLOSED or event == 'ok':
                    break
            
            option2_window.close()
            search_string = values['search_string']
            webbrowser.open("http://127.0.0.1:5000", new=0)
            subprocess.run(['python', 'search.py', search_string])
            window.un_hide()

    window.close()

if __name__ == '__main__':
    main()
