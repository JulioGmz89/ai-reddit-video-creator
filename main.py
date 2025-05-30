# main.py

import customtkinter
from reddit_scraper import get_post_details
import tts_kokoro_module # Importamos nuestro módulo TTS
import os # Para manejar rutas de archivos

# Apariencia de la GUI (como antes)
customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # --- Configuración de la Ventana Principal ---
        self.title("AI Reddit Story Video Creator")
        self.geometry("800x650") # Aumentamos un poco la altura para nuevos widgets

        self.grid_columnconfigure(0, weight=1)
        # Necesitamos configurar el peso de las filas que se expandirán
        # La fila 2 (story_frame) será la que más se expanda
        self.grid_rowconfigure(0, weight=0) # input_frame
        self.grid_rowconfigure(1, weight=0) # tts_config_frame
        self.grid_rowconfigure(2, weight=1) # story_frame
        self.grid_rowconfigure(3, weight=0) # status_frame


        # --- Frame de Entrada (URL de Reddit) ---
        self.input_frame = customtkinter.CTkFrame(self)
        self.input_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.input_frame.grid_columnconfigure(1, weight=1) # Hacer que el entry se expanda

        self.reddit_url_label = customtkinter.CTkLabel(self.input_frame, text="URL de Reddit:")
        self.reddit_url_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.reddit_url_entry = customtkinter.CTkEntry(self.input_frame, placeholder_text="Pega aquí la URL de un post de Reddit...")
        self.reddit_url_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.reddit_fetch_button = customtkinter.CTkButton(self.input_frame, text="Obtener Historia", command=self.fetch_reddit_post)
        self.reddit_fetch_button.grid(row=0, column=2, padx=10, pady=10)

        # --- Frame de Configuración TTS ---
        self.tts_config_frame = customtkinter.CTkFrame(self)
        self.tts_config_frame.grid(row=1, column=0, padx=10, pady=(5,5), sticky="ew")
        self.tts_config_frame.grid_columnconfigure(1, weight=1) # Para que el OptionMenu se expanda si es necesario

        self.tts_voice_label = customtkinter.CTkLabel(self.tts_config_frame, text="Voz TTS:")
        self.tts_voice_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Cargar voces disponibles desde el módulo TTS
        self.available_voices_map = tts_kokoro_module.list_english_voices_for_pip_package()
        self.voice_friendly_names = list(self.available_voices_map.keys())
        
        self.selected_voice_technical_name = None # Variable para guardar el nombre técnico
        default_voice_friendly = ""

        if not self.voice_friendly_names:
            self.voice_friendly_names = ["No hay voces disponibles"]
            default_voice_friendly = self.voice_friendly_names[0]
            self.can_generate_audio = False
        else:
            default_voice_friendly = self.voice_friendly_names[0]
            self.selected_voice_technical_name = self.available_voices_map[default_voice_friendly]
            self.can_generate_audio = True
            
        self.tts_voice_menu_var = customtkinter.StringVar(value=default_voice_friendly)
        self.tts_voice_menu = customtkinter.CTkOptionMenu(
            self.tts_config_frame, 
            values=self.voice_friendly_names,
            variable=self.tts_voice_menu_var,
            command=self.update_selected_voice_technical_name # Llama a esta función cuando cambia la selección
        )
        self.tts_voice_menu.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        if not self.can_generate_audio:
            self.tts_voice_menu.configure(state="disabled")

        self.generate_audio_button = customtkinter.CTkButton(
            self.tts_config_frame, 
            text="Generar Audio de Historia", 
            command=self.process_text_to_speech
        )
        self.generate_audio_button.grid(row=0, column=2, padx=10, pady=10)
        if not self.can_generate_audio:
             self.generate_audio_button.configure(state="disabled")


        # --- Frame de Salida (donde se muestra la historia) ---
        self.story_frame = customtkinter.CTkFrame(self)
        self.story_frame.grid(row=2, column=0, padx=10, pady=(5, 5), sticky="nsew")
        self.story_frame.grid_columnconfigure(0, weight=1) # Para que el textbox se expanda horizontalmente
        self.story_frame.grid_rowconfigure(0, weight=1) # Para que el textbox se expanda verticalmente

        self.story_textbox = customtkinter.CTkTextbox(self.story_frame, wrap="word", font=("Arial", 14))
        self.story_textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.story_textbox.insert("1.0", "Aquí aparecerá la historia de Reddit o el texto que ingreses...")
        
        # --- Frame de Estado/Salida ---
        self.status_frame = customtkinter.CTkFrame(self)
        self.status_frame.grid(row=3, column=0, padx=10, pady=(5,10), sticky="ew")
        self.status_label = customtkinter.CTkLabel(self.status_frame, text="Estado: Listo")
        self.status_label.grid(row=0, column=0, padx=10, pady=10, sticky="w") # sticky w para alinear a la izquierda
        
    def update_selected_voice_technical_name(self, selected_friendly_name: str):
        """Actualiza el nombre técnico de la voz cuando el usuario la cambia en el menú."""
        if self.can_generate_audio:
            self.selected_voice_technical_name = self.available_voices_map.get(selected_friendly_name)
            # print(f"Voz TTS seleccionada: {selected_friendly_name} (Nombre técnico: {self.selected_voice_technical_name})")
            self.status_label.configure(text=f"Voz seleccionada: {selected_friendly_name}")


    def fetch_reddit_post(self):
        url = self.reddit_url_entry.get()
        if not url:
            self.story_textbox.delete("1.0", "end")
            self.story_textbox.insert("1.0", "Error: Por favor, introduce una URL de Reddit válida.")
            self.status_label.configure(text="Error: URL de Reddit vacía.")
            return

        self.status_label.configure(text="Obteniendo post de Reddit...")
        self.story_textbox.delete("1.0", "end")
        self.story_textbox.insert("1.0", "Cargando...")
        self.update_idletasks() 

        title, body = get_post_details(url)
        
        self.story_textbox.delete("1.0", "end")
        if title == "Título no encontrado." and body == "Cuerpo del post no encontrado.":
            full_story = "No se pudo obtener el contenido del post de Reddit. Verifica la URL y tu conexión."
            self.status_label.configure(text="Error al obtener historia de Reddit.")
        else:
            full_story = f"{title}\n\n{body}"
            self.status_label.configure(text="Historia de Reddit cargada.")
        
        self.story_textbox.insert("1.0", full_story)

    def process_text_to_speech(self):
        if not self.can_generate_audio or not self.selected_voice_technical_name:
            self.status_label.configure(text="Error: No hay una voz TTS válida seleccionada o disponible.")
            return

        story_text = self.story_textbox.get("1.0", "end-1c").strip() 
        if not story_text or story_text == "Aquí aparecerá la historia de Reddit o el texto que ingreses..." or story_text == "Cargando...":
            self.status_label.configure(text="Error: No hay texto en la historia para convertir a voz.")
            return
        
        selected_friendly_name = self.tts_voice_menu_var.get()
        self.status_label.configure(text=f"Generando audio con voz '{selected_friendly_name}'... Por favor espera.")
        self.update_idletasks()

        output_audio_filename = "historia_narrada.wav" 
        
        success = tts_kokoro_module.generate_speech_with_voice_name(
            story_text,
            self.selected_voice_technical_name, # Usamos el nombre técnico guardado
            output_audio_filename 
        )

        if success:
            # os.path.abspath para obtener la ruta completa del archivo generado
            full_path = os.path.abspath(output_audio_filename)
            self.status_label.configure(text=f"¡Audio generado! Guardado en: {full_path}")
        else:
            self.status_label.configure(text="Error al generar el audio. Revisa la consola para más detalles.")


if __name__ == "__main__":
    app = App()
    app.mainloop()