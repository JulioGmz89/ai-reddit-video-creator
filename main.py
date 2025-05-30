# main.py
import customtkinter
from customtkinter import filedialog # Importar filedialog
from reddit_scraper import get_post_details
import tts_kokoro_module 
import ai_story_generator 
import video_processor # <--- IMPORTAR EL NUEVO MÓDULO
import os 
import traceback

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Reddit Story Video Creator")
        self.geometry("800x850") # Aumentamos altura para nuevos controles

        # Variables para rutas de archivos
        self.generated_audio_path = None
        self.background_video_path = None

        # Configuración del Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # input_frame (Reddit URL)
        self.grid_rowconfigure(1, weight=0)  # ai_story_config_frame
        self.grid_rowconfigure(2, weight=0)  # tts_config_frame
        self.grid_rowconfigure(3, weight=1)  # story_frame (Textbox) - ESTE SE EXPANDE
        self.grid_rowconfigure(4, weight=0)  # video_processing_frame
        self.grid_rowconfigure(5, weight=0)  # status_frame

        # --- Frame de Entrada (URL de Reddit) ---
        # (Sin cambios, solo verifica que el grid row=0 sea correcto)
        self.input_frame = customtkinter.CTkFrame(self)
        self.input_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.input_frame.grid_columnconfigure(1, weight=1)
        self.reddit_url_label = customtkinter.CTkLabel(self.input_frame, text="URL de Reddit:")
        self.reddit_url_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.reddit_url_entry = customtkinter.CTkEntry(self.input_frame, placeholder_text="Pega aquí la URL de un post de Reddit...")
        self.reddit_url_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.reddit_fetch_button = customtkinter.CTkButton(self.input_frame, text="Obtener Historia", command=self.fetch_reddit_post)
        self.reddit_fetch_button.grid(row=0, column=2, padx=10, pady=10)

        # --- Frame de Configuración de Historia IA ---
        # (Sin cambios, solo verifica que el grid row=1 sea correcto)
        self.ai_story_config_frame = customtkinter.CTkFrame(self)
        self.ai_story_config_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.ai_story_config_frame.grid_columnconfigure(1, weight=1)
        self.ai_subject_label = customtkinter.CTkLabel(self.ai_story_config_frame, text="Tema Historia IA (Inglés):")
        self.ai_subject_label.grid(row=0, column=0, padx=(10,0), pady=5, sticky="w")
        self.ai_subject_entry = customtkinter.CTkEntry(self.ai_story_config_frame, placeholder_text="Ej: alien encounter, haunted house")
        self.ai_subject_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        self.ai_style_label = customtkinter.CTkLabel(self.ai_story_config_frame, text="Estilo Historia IA (Inglés):")
        self.ai_style_label.grid(row=1, column=0, padx=(10,0), pady=5, sticky="w")
        self.ai_style_entry = customtkinter.CTkEntry(self.ai_story_config_frame, placeholder_text="Ej: r/nosleep, comedy, mystery")
        self.ai_style_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        self.ai_max_tokens_label = customtkinter.CTkLabel(self.ai_story_config_frame, text="Tokens Máx. IA:")
        self.ai_max_tokens_label.grid(row=2, column=0, padx=(10,0), pady=5, sticky="w")
        self.max_tokens_options = ["200", "300", "400", "500"]
        self.ai_max_tokens_menu_var = customtkinter.StringVar(value=self.max_tokens_options[1])
        self.ai_max_tokens_menu = customtkinter.CTkOptionMenu(
            self.ai_story_config_frame, values=self.max_tokens_options, variable=self.ai_max_tokens_menu_var)
        self.ai_max_tokens_menu.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.generate_ai_story_button = customtkinter.CTkButton(
            self.ai_story_config_frame, text="Generar Historia con IA", command=self.process_ai_story_generation)
        self.generate_ai_story_button.grid(row=2, column=2, padx=10, pady=5, sticky="e")

        # --- Frame de Configuración TTS ---
        # (Sin cambios, solo verifica que el grid row=2 sea correcto)
        self.tts_config_frame = customtkinter.CTkFrame(self)
        self.tts_config_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.tts_config_frame.grid_columnconfigure(1, weight=1)
        self.tts_voice_label = customtkinter.CTkLabel(self.tts_config_frame, text="Voz TTS:")
        self.tts_voice_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.available_voices_map = tts_kokoro_module.list_english_voices_for_pip_package()
        self.voice_friendly_names = list(self.available_voices_map.keys())
        self.selected_voice_technical_name = None
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
            self.tts_config_frame, values=self.voice_friendly_names,
            variable=self.tts_voice_menu_var, command=self.update_selected_voice_technical_name)
        self.tts_voice_menu.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        if not self.can_generate_audio: self.tts_voice_menu.configure(state="disabled")
        self.generate_audio_button = customtkinter.CTkButton(
            self.tts_config_frame, text="Generar Audio de Historia", command=self.process_text_to_speech)
        self.generate_audio_button.grid(row=0, column=2, padx=10, pady=10)
        if not self.can_generate_audio: self.generate_audio_button.configure(state="disabled")

        # --- Frame de Salida (donde se muestra la historia) ---
        # (Verifica que el grid row=3 sea correcto)
        self.story_frame = customtkinter.CTkFrame(self)
        self.story_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        self.story_frame.grid_columnconfigure(0, weight=1)
        self.story_frame.grid_rowconfigure(0, weight=1)
        self.story_textbox = customtkinter.CTkTextbox(self.story_frame, wrap="word", font=("Arial", 14))
        self.story_textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.story_textbox.insert("1.0", "Aquí aparecerá la historia de Reddit o el texto que ingreses...")
        
        # --- NUEVO: Frame de Procesamiento de Video ---
        self.video_processing_frame = customtkinter.CTkFrame(self)
        self.video_processing_frame.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        self.video_processing_frame.grid_columnconfigure(1, weight=1) # Para que la etiqueta del path se expanda

        self.select_video_button = customtkinter.CTkButton(
            self.video_processing_frame,
            text="Seleccionar Video de Fondo (.mp4)",
            command=self.select_background_video
        )
        self.select_video_button.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.selected_video_label = customtkinter.CTkLabel(self.video_processing_frame, text="Video no seleccionado")
        self.selected_video_label.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        self.generate_final_video_button = customtkinter.CTkButton(
            self.video_processing_frame,
            text="Generar Video Final Narrado",
            command=self.process_final_video_generation
        )
        self.generate_final_video_button.grid(row=0, column=2, padx=10, pady=10, sticky="e")


        # --- Frame de Estado/Salida --- 
        # (Verifica que el grid row=5 sea correcto)
        self.status_frame = customtkinter.CTkFrame(self)
        self.status_frame.grid(row=5, column=0, padx=10, pady=(5,10), sticky="ew")
        self.status_label = customtkinter.CTkLabel(self.status_frame, text="Estado: Listo")
        self.status_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

    # --- Métodos existentes (update_selected_voice_technical_name, fetch_reddit_post, process_ai_story_generation) ---
    # (Sin cambios significativos, solo asegúrate de que son consistentes)
    def update_selected_voice_technical_name(self, selected_friendly_name: str):
        if self.can_generate_audio:
            self.selected_voice_technical_name = self.available_voices_map.get(selected_friendly_name)
            self.status_label.configure(text=f"Voz seleccionada: {selected_friendly_name}")

    def fetch_reddit_post(self): # (Sin cambios)
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
        if "Error" in title or "no encontrado" in title : 
            full_story = f"{title}\n\n{body}" 
            self.status_label.configure(text="Error al obtener historia de Reddit o post no textual.")
        else:
            full_story = f"{title}\n\n{body}"
            self.status_label.configure(text="Historia de Reddit cargada.")
        self.story_textbox.insert("1.0", full_story)

    def process_ai_story_generation(self): # (Sin cambios)
        subject = self.ai_subject_entry.get().strip()
        style = self.ai_style_entry.get().strip()
        if not subject or not style:
            self.status_label.configure(text="Error IA: Ingresa Tema y Estilo (en Inglés).")
            return
        try:
            max_tokens = int(self.ai_max_tokens_menu_var.get())
        except ValueError:
            self.status_label.configure(text="Error IA: Número de tokens inválido.")
            return
        self.status_label.configure(text="IA está generando historia en INGLÉS... Esto puede tardar.")
        self.story_textbox.delete("1.0", "end")
        self.story_textbox.insert("1.0", "Generando historia con IA, por favor espera...")
        self.update_idletasks() 
        try:
            generated_story = ai_story_generator.generate_story(subject, style, max_tokens)
            self.story_textbox.delete("1.0", "end")
            self.story_textbox.insert("1.0", generated_story) 
            if "Error:" in generated_story: 
                 self.status_label.configure(text="IA: Hubo un error al generar la historia (ver texto).")
            else:
                self.status_label.configure(text="IA: ¡Historia en INGLÉS generada!")
        except Exception as e:
            self.story_textbox.delete("1.0", "end")
            self.story_textbox.insert("1.0", f"Ocurrió un error crítico al generar la historia con IA:\n{e}")
            self.status_label.configure(text="IA: Error crítico durante la generación.")
            traceback.print_exc()
            
    def process_text_to_speech(self):
        # ... (como estaba, solo asegúrate que el texto que toma sea de la historia actual en el textbox)
        if not self.can_generate_audio or not self.selected_voice_technical_name:
            self.status_label.configure(text="Error: No hay una voz TTS válida seleccionada o disponible.")
            return

        story_text = self.story_textbox.get("1.0", "end-1c").strip() 
        # Chequeos de texto vacío o placeholder
        placeholders = ["Aquí aparecerá la historia de Reddit o el texto que ingreses...", "Cargando...", "Generando historia con IA, por favor espera...\n\n(La GUI puede congelarse durante este proceso si el modelo es pesado o es la primera carga)."]
        if not story_text or story_text in placeholders:
            self.status_label.configure(text="Error: No hay texto válido en la historia para convertir a voz.")
            return
        
        selected_friendly_name = self.tts_voice_menu_var.get()
        self.status_label.configure(text=f"Generando audio con voz '{selected_friendly_name}'... Por favor espera.")
        self.update_idletasks()

        output_audio_filename = "historia_narrada.wav" 
        
        success = tts_kokoro_module.generate_speech_with_voice_name(
            story_text,
            self.selected_voice_technical_name, 
            output_audio_filename 
        )

        if success:
            self.generated_audio_path = os.path.abspath(output_audio_filename) # Guardar ruta completa
            self.status_label.configure(text=f"¡Audio generado! Guardado en: {self.generated_audio_path}")
        else:
            self.generated_audio_path = None # Resetear si falla
            self.status_label.configure(text="Error al generar el audio. Revisa la consola.")
            
    # --- NUEVOS MÉTODOS para Procesamiento de Video ---
    def select_background_video(self):
        """Abre un diálogo para seleccionar un archivo de video."""
        filetypes = (("Archivos MP4", "*.mp4"), ("Todos los archivos", "*.*"))
        filepath = filedialog.askopenfilename(title="Selecciona un video de fondo", filetypes=filetypes)
        if filepath:
            self.background_video_path = filepath
            # Mostrar solo el nombre del archivo para no saturar la GUI
            filename = os.path.basename(filepath) 
            self.selected_video_label.configure(text=filename)
            self.status_label.configure(text=f"Video de fondo seleccionado: {filename}")
        else:
            self.background_video_path = None
            self.selected_video_label.configure(text="Video no seleccionado")
            # self.status_label.configure(text="Selección de video cancelada.")


    def process_final_video_generation(self):
        """Genera el video final combinando el audio narrado y el video de fondo."""
        if not self.generated_audio_path or not os.path.exists(self.generated_audio_path):
            self.status_label.configure(text="Error: Primero genera el audio de la historia.")
            return
        
        if not self.background_video_path or not os.path.exists(self.background_video_path):
            self.status_label.configure(text="Error: Primero selecciona un video de fondo.")
            return

        self.status_label.configure(text="Generando video final... Esto puede tardar mucho tiempo.")
        self.update_idletasks() # Forzar actualización de la GUI

        output_final_video_filename = "video_final_narrado.mp4"
        # output_final_video_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_final_video_filename)
        # Por simplicidad, guardar en el directorio de trabajo actual.

        success = video_processor.create_narrated_video(
            self.background_video_path,
            self.generated_audio_path,
            output_final_video_filename # Guarda en el directorio actual
        )

        if success:
            full_path = os.path.abspath(output_final_video_filename)
            self.status_label.configure(text=f"¡Video final generado! Guardado en: {full_path}")
        else:
            self.status_label.configure(text="Error al generar el video final. Revisa la consola.")    

if __name__ == "__main__":
    # No es necesario llamar a _initialize_model aquí si se maneja dentro de generate_story
    app = App()
    app.mainloop()