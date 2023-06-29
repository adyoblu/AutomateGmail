import subprocess
import webbrowser
import sys
import os
import platform
from tkinter import *
import customtkinter

def main():
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("dark-blue")
    root = customtkinter.CTk()
    root.title("Meniu")
    # Obține dimensiunile ecranului
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    def button_clicked():
        if platform.system() == 'Windows':
            subprocess.run(['taskkill', '/F', '/IM', 'firefox.exe'])  # Închide Mozilla Firefox pe Windows
            subprocess.run(['taskkill', '/F', '/IM', 'opera.exe'])  # Închide Opera GX pe Windows
        elif platform.system() == 'Linux':
            subprocess.run(['pkill', 'google-chrome'])  # Închide Google Chrome pe Linux
            subprocess.run(['pkill', 'firefox'])
            subprocess.run(['pkill', 'chromium'])
    def exit_button_clicked():
        button_clicked()
        sys.exit()  # Încheie scriptul
    # Calculează poziția x și y pentru a afișa fereastra în mijlocul ecranului
    window_width = 600
    window_height = 200
    x = int((screen_width / 2) - (window_width / 2))
    y = int((screen_height / 2) - (window_height / 2))

    # Setează geometria ferestrei pentru a o afișa în mijlocul ecranului
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def option1_clicked():
        root.withdraw()
        webbrowser.open("http://127.0.0.1:5000", new=0)
        python_executable = sys.executable
        subprocess.run([python_executable, 'today.py'])
        root.deiconify()

    def option2_clicked():
        root.withdraw()
        window_width = 300
        window_height = 200
        x = int((screen_width / 2) - (window_width / 2))
        y = int((screen_height / 2) - (window_height / 2))
        new_window = customtkinter.CTkToplevel(root)
        new_window.title("Căutare subiect")
        new_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        label = customtkinter.CTkLabel(new_window, text="Introduceți un string de căutat în subiecte:")
        label.pack(pady=10)

        entry = customtkinter.CTkEntry(new_window)
        entry.pack(pady=10)

        def search_button_clicked():
            search_string = entry.get()
            new_window.destroy()
            if search_string:
                webbrowser.open("http://127.0.0.1:5000")
                python_executable = sys.executable
                subprocess.run([python_executable, 'search.py', search_string])
            root.deiconify()  # Afișează fereastra principală

        button = customtkinter.CTkButton(new_window, text="OK", command=search_button_clicked)
        button.pack(pady=10)

        new_window.mainloop()  # Afișează fereastra `new_window`


    button_font = ("Roboto", 24)

    option1_button = customtkinter.CTkButton(root, text="1) Afiseaza toate mesajele de astazi(INBOX si SPAM)", command=option1_clicked, font=button_font)
    option1_button.pack(pady=20, padx=10)

    option2_button = customtkinter.CTkButton(root, text="2) Afiseaza mesajele in functie de subiect anume", command=option2_clicked, font=button_font)
    option2_button.pack(pady=12, padx =10)

    exit_button = customtkinter.CTkButton(root, text="3) Ieșire", command=exit_button_clicked, font=button_font)
    exit_button.pack(pady=12, padx = 10)

    root.mainloop()

if __name__ == '__main__':
    main()