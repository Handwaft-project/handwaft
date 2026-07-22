import customtkinter as ctk
import subprocess
from tkinter import filedialog

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def launch_handwaft():
    subprocess.Popen(["py", "main.py"])

def launch_dj_mode():
    file_path = filedialog.askopenfilename(
        title="Choose a song",
        filetypes=[("Audio files", "*.wav")]
    )
    if file_path:
        subprocess.Popen(["py", "dj_mode.py", file_path])

root = ctk.CTk()
root.title("Handwaft")
root.geometry("450x350")

title_label = ctk.CTkLabel(root, text="Handwaft", font=("Arial", 32, "bold"))
title_label.pack(pady=40)

subtitle_label = ctk.CTkLabel(root, text="Choose a mode to begin", font=("Arial", 14), text_color="gray")
subtitle_label.pack(pady=(0, 30))

handwaft_button = ctk.CTkButton(root, text="🎵 Handwaft Mode (make music)",
                                  font=("Arial", 16), height=50,
                                  command=launch_handwaft)
handwaft_button.pack(pady=10, padx=40, fill="x")

dj_button = ctk.CTkButton(root, text="🎧 DJ Mode (play & remix songs)",
                            font=("Arial", 16), height=50,
                            command=launch_dj_mode)
dj_button.pack(pady=10, padx=40, fill="x")

root.mainloop()