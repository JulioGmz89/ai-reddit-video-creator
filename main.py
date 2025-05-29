# main.py

import customtkinter
from reddit_scraper import get_post_details

# Apariencia de la GUI
customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # --- Configuración de la Ventana Principal ---
        self.title("AI Reddit Story Video Creator")
        self.geometry("800x600")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Frame de Entrada ---
        self.input_frame = customtkinter.CTkFrame(self)
        self.input_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.input_frame.grid_columnconfigure(1, weight=1)

        self.reddit_url_label = customtkinter.CTkLabel(self.input_frame, text="URL de Reddit:")
        self.reddit_url_label.grid(row=0, column=0, padx=10, pady=10)

        self.reddit_url_entry = customtkinter.CTkEntry(self.input_frame, placeholder_text="Pega aquí la URL de un post de Reddit...")
        self.reddit_url_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.reddit_fetch_button = customtkinter.CTkButton(self.input_frame, text="Obtener Historia", command=self.fetch_reddit_post)
        self.reddit_fetch_button.grid(row=0, column=2, padx=10, pady=10)

        # --- Frame de Salida (donde se muestra la historia) ---
        self.story_frame = customtkinter.CTkFrame(self)
        self.story_frame.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self.story_frame.grid_columnconfigure(0, weight=1)
        self.story_frame.grid_rowconfigure(0, weight=1)

        self.story_textbox = customtkinter.CTkTextbox(self.story_frame, wrap="word", font=("Arial", 14))
        self.story_textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.story_textbox.insert("1.0", "Aquí aparecerá la historia de Reddit...")

    def fetch_reddit_post(self):
        """Función que se ejecuta al presionar el botón 'Obtener Historia'."""
        url = self.reddit_url_entry.get()
        if not url:
            self.story_textbox.delete("1.0", "end")
            self.story_textbox.insert("1.0", "Error: Por favor, introduce una URL de Reddit válida.")
            return

        # Mostramos un mensaje de carga en la GUI
        self.story_textbox.delete("1.0", "end")
        self.story_textbox.insert("1.0", "Obteniendo post de Reddit, por favor espera...")
        self.update_idletasks() # Forzamos la actualización de la GUI

        # Llamamos a nuestra función de scraping
        title, body = get_post_details(url)
        full_story = f"{title}\n\n{body}"

        # Mostramos el resultado final
        self.story_textbox.delete("1.0", "end")
        self.story_textbox.insert("1.0", full_story)


if __name__ == "__main__":
    app = App()
    app.mainloop()