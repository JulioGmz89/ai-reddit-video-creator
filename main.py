# main.py
import customtkinter
from customtkinter import filedialog
from reddit_scraper import get_post_details
import tts_kokoro_module 
import ai_story_generator 
import video_processor 
import srt_generator 
import os 
import traceback

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Reddit Story Video Creator")
        self.geometry("800x1000") 

        self.generated_audio_path = None
        self.background_video_path = None
        self.narrated_video_path = None 
        self.generated_srt_path = None  

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=1) # story_frame se expandirá
        self.grid_rowconfigure(4, weight=0)
        self.grid_rowconfigure(5, weight=0)
        self.grid_rowconfigure(6, weight=0) 
        self.grid_rowconfigure(7, weight=0) 

        # --- Frame de Entrada (URL de Reddit) ---
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
        self.story_frame = customtkinter.CTkFrame(self)
        self.story_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        self.story_frame.grid_columnconfigure(0, weight=1)
        self.story_frame.grid_rowconfigure(0, weight=1)
        self.story_textbox = customtkinter.CTkTextbox(self.story_frame, wrap="word", font=("Arial", 14))
        self.story_textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.story_textbox.insert("1.0", "Aquí aparecerá la historia de Reddit o el texto que ingreses...")

        # --- Frame de Procesamiento de Video ---
        self.video_processing_frame = customtkinter.CTkFrame(self)
        self.video_processing_frame.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        self.video_processing_frame.grid_columnconfigure(1, weight=1) 
        self.select_video_button = customtkinter.CTkButton(
            self.video_processing_frame, text="Seleccionar Video de Fondo (.mp4)", command=self.select_background_video)
        self.select_video_button.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.selected_video_label = customtkinter.CTkLabel(self.video_processing_frame, text="Video no seleccionado")
        self.selected_video_label.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.generate_final_video_button = customtkinter.CTkButton(
            self.video_processing_frame, text="Generar Video Final Narrado", command=self.process_final_video_generation)
        self.generate_final_video_button.grid(row=0, column=2, padx=10, pady=10, sticky="e")

        # --- Frame de Configuración de SRT ---
        self.srt_config_frame = customtkinter.CTkFrame(self)
        self.srt_config_frame.grid(row=5, column=0, padx=10, pady=5, sticky="ew")
        self.srt_config_frame.grid_columnconfigure(1, weight=0) # Para que el OptionMenu no se estire demasiado

        self.srt_max_words_label = customtkinter.CTkLabel(self.srt_config_frame, text="Palabras Máx./Segmento SRT:")
        self.srt_max_words_label.grid(row=0, column=0, padx=(10,0), pady=5, sticky="w")
        self.srt_max_words_options = ["Whisper (Defecto)", "1", "2", "3", "4", "5", "6", "7"]
        self.srt_max_words_var = customtkinter.StringVar(value="3") 
        self.srt_max_words_menu = customtkinter.CTkOptionMenu(
            self.srt_config_frame, values=self.srt_max_words_options, variable=self.srt_max_words_var)
        self.srt_max_words_menu.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self.generate_srt_button = customtkinter.CTkButton(
            self.srt_config_frame, text="1. Generar Archivo .SRT", command=self.process_srt_generation)
        self.generate_srt_button.grid(row=0, column=2, padx=10, pady=5, sticky="e")

        # --- Frame de Estilo de Subtítulos ---
        self.subtitle_style_frame = customtkinter.CTkFrame(self)
        self.subtitle_style_frame.grid(row=6, column=0, padx=10, pady=5, sticky="ew")
        # Configurar columnas para un layout ordenado (label, control, label, control)
        self.subtitle_style_frame.grid_columnconfigure(0, weight=0) # Label
        self.subtitle_style_frame.grid_columnconfigure(1, weight=1) # Control
        self.subtitle_style_frame.grid_columnconfigure(2, weight=0) # Label
        self.subtitle_style_frame.grid_columnconfigure(3, weight=1) # Control
        self.subtitle_style_frame.grid_columnconfigure(4, weight=0) # Botón (no se expande)


        # Fila 1 de Estilos: Fuente y Tamaño
        self.subtitle_font_label = customtkinter.CTkLabel(self.subtitle_style_frame, text="Fuente Sub:")
        self.subtitle_font_label.grid(row=0, column=0, padx=(10,0), pady=5, sticky="w")
        self.subtitle_font_options = ["Arial", "Verdana", "Times New Roman", "Impact", "Courier New"]
        self.subtitle_font_var = customtkinter.StringVar(value="Arial")
        self.subtitle_font_menu = customtkinter.CTkOptionMenu(self.subtitle_style_frame, values=self.subtitle_font_options, variable=self.subtitle_font_var)
        self.subtitle_font_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.subtitle_fontsize_label = customtkinter.CTkLabel(self.subtitle_style_frame, text="Tamaño:")
        self.subtitle_fontsize_label.grid(row=0, column=2, padx=(10,0), pady=5, sticky="w")
        self.subtitle_fontsize_options = ["24", "28", "32", "36", "40", "48", "52"]
        self.subtitle_fontsize_var = customtkinter.StringVar(value="36") # Tamaño un poco más grande por defecto
        self.subtitle_fontsize_menu = customtkinter.CTkOptionMenu(self.subtitle_style_frame, values=self.subtitle_fontsize_options, variable=self.subtitle_fontsize_var)
        self.subtitle_fontsize_menu.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        
        # Fila 2 de Estilos: Color Texto y Posición
        self.subtitle_color_label = customtkinter.CTkLabel(self.subtitle_style_frame, text="Color Texto:")
        self.subtitle_color_label.grid(row=1, column=0, padx=(10,0), pady=5, sticky="w")
        self.subtitle_color_entry = customtkinter.CTkEntry(self.subtitle_style_frame, placeholder_text="white, yellow, #FFFF00")
        self.subtitle_color_entry.insert(0, "yellow") # Amarillo con borde negro suele ser visible
        self.subtitle_color_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.subtitle_pos_label = customtkinter.CTkLabel(self.subtitle_style_frame, text="Posición:")
        self.subtitle_pos_label.grid(row=1, column=2, padx=(10,0), pady=5, sticky="w")
        self.subtitle_pos_options = ["Abajo", "Centro", "Arriba"]
        self.subtitle_pos_var = customtkinter.StringVar(value="Abajo")
        self.subtitle_pos_menu = customtkinter.CTkOptionMenu(self.subtitle_style_frame, values=self.subtitle_pos_options, variable=self.subtitle_pos_var)
        self.subtitle_pos_menu.grid(row=1, column=3, padx=5, pady=5, sticky="ew")

        # Fila 3 de Estilos: Color Borde y Ancho Borde
        self.subtitle_strokecolor_label = customtkinter.CTkLabel(self.subtitle_style_frame, text="Color Borde:")
        self.subtitle_strokecolor_label.grid(row=2, column=0, padx=(10,0), pady=5, sticky="w")
        self.subtitle_strokecolor_entry = customtkinter.CTkEntry(self.subtitle_style_frame, placeholder_text="black, transparent")
        self.subtitle_strokecolor_entry.insert(0, "black")
        self.subtitle_strokecolor_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        self.subtitle_strokewidth_label = customtkinter.CTkLabel(self.subtitle_style_frame, text="Ancho Borde:")
        self.subtitle_strokewidth_label.grid(row=2, column=2, padx=(10,0), pady=5, sticky="w")
        self.subtitle_strokewidth_options = ["0", "0.5", "1", "1.5", "2", "2.5", "3"]
        self.subtitle_strokewidth_var = customtkinter.StringVar(value="1.5")
        self.subtitle_strokewidth_menu = customtkinter.CTkOptionMenu(self.subtitle_style_frame, values=self.subtitle_strokewidth_options, variable=self.subtitle_strokewidth_var)
        self.subtitle_strokewidth_menu.grid(row=2, column=3, padx=5, pady=5, sticky="ew")
        
        # Fila 4 Fondo y Botón para Grabar Subtítulos
        self.subtitle_bgcolor_label = customtkinter.CTkLabel(self.subtitle_style_frame, text="Color Fondo Sub:")
        self.subtitle_bgcolor_label.grid(row=3, column=0, padx=(10,0), pady=5, sticky="w")
        self.subtitle_bgcolor_entry = customtkinter.CTkEntry(self.subtitle_style_frame, placeholder_text="transparent, rgba(0,0,0,0.5)")
        self.subtitle_bgcolor_entry.insert(0, "rgba(0,0,0,0.4)") # Semitransparente por defecto
        self.subtitle_bgcolor_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        self.burn_subtitles_button = customtkinter.CTkButton(
            self.subtitle_style_frame,
            text="2. Grabar Subtítulos en Video Final",
            command=self.process_burn_subtitles
        )
        self.burn_subtitles_button.grid(row=3, column=2, columnspan=2, padx=10, pady=10, sticky="ew")


        # --- Frame de Estado/Salida --- 
        self.status_frame = customtkinter.CTkFrame(self) 
        self.status_frame.grid(row=7, column=0, padx=10, pady=(5,10), sticky="ew") # Ahora en row=7
        self.status_label = customtkinter.CTkLabel(self.status_frame, text="Estado: Listo. ¡Bienvenido!")
        self.status_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

    # --- MÉTODOS ---
    def update_selected_voice_technical_name(self, selected_friendly_name: str): #OK
        if self.can_generate_audio:
            self.selected_voice_technical_name = self.available_voices_map.get(selected_friendly_name)
            self.status_label.configure(text=f"Voz seleccionada: {selected_friendly_name}")

    def fetch_reddit_post(self): #OK
        url = self.reddit_url_entry.get()
        if not url:
            self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", "Error: URL de Reddit vacía.")
            self.status_label.configure(text="Error: URL de Reddit vacía.")
            return
        self.status_label.configure(text="Obteniendo post de Reddit..."); self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", "Cargando..."); self.update_idletasks() 
        title, body = get_post_details(url)
        self.story_textbox.delete("1.0", "end")
        if "Error" in title or "no encontrado" in title or (title == "Título no encontrado." and body == "Cuerpo del post no encontrado.") : 
            full_story = f"{title}\n\n{body}" 
            self.status_label.configure(text="Error al obtener historia de Reddit o post no textual.")
        else:
            full_story = f"{title}\n\n{body}"; self.status_label.configure(text="Historia de Reddit cargada.")
        self.story_textbox.insert("1.0", full_story)

    def process_ai_story_generation(self): #OK
        subject = self.ai_subject_entry.get().strip(); style = self.ai_style_entry.get().strip()
        if not subject or not style: self.status_label.configure(text="Error IA: Ingresa Tema y Estilo (en Inglés)."); return
        try: max_tokens = int(self.ai_max_tokens_menu_var.get())
        except ValueError: self.status_label.configure(text="Error IA: Número de tokens inválido."); return
        self.status_label.configure(text="IA está generando historia en INGLÉS... Esto puede tardar."); self.update_idletasks()
        self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", "Generando historia con IA (Gemma 2B)..."); self.update_idletasks() 
        try:
            generated_story = ai_story_generator.generate_story(subject, style, max_tokens)
            self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", generated_story) 
            if "Error:" in generated_story: self.status_label.configure(text="IA: Hubo un error (ver texto).")
            else: self.status_label.configure(text="IA: ¡Historia en INGLÉS generada!")
        except Exception as e:
            self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", f"Error crítico IA:\n{e}"); self.status_label.configure(text="IA: Error crítico.")
            traceback.print_exc()
            
    def process_text_to_speech(self): #OK
        if not self.can_generate_audio or not self.selected_voice_technical_name: self.status_label.configure(text="Error: No hay voz TTS válida."); return
        story_text = self.story_textbox.get("1.0", "end-1c").strip() 
        placeholders = ["Aquí aparecerá la historia de Reddit o el texto que ingreses...", "Cargando...", "Generando historia con IA (Gemma 2B)..."]
        is_placeholder = any(story_text.startswith(p_start) for p_start in placeholders)
        if not story_text or is_placeholder: self.status_label.configure(text="Error: No hay texto válido para TTS."); return
        
        selected_friendly_name = self.tts_voice_menu_var.get()
        self.status_label.configure(text=f"Generando audio con '{selected_friendly_name}'..."); self.update_idletasks()
        output_audio_filename = "historia_narrada.wav" 
        success = tts_kokoro_module.generate_speech_with_voice_name(story_text, self.selected_voice_technical_name, output_audio_filename)
        if success:
            self.generated_audio_path = os.path.abspath(output_audio_filename) 
            self.status_label.configure(text=f"¡Audio generado!: {self.generated_audio_path}")
        else:
            self.generated_audio_path = None; self.status_label.configure(text="Error al generar audio.")

    def select_background_video(self): #OK
        filetypes = (("Archivos de Video", "*.mp4 *.mov *.avi *.mkv"),("Todos los archivos", "*.*")) # Más tipos
        filepath = filedialog.askopenfilename(title="Selecciona un video de fondo", filetypes=filetypes)
        if filepath:
            self.background_video_path = filepath; filename = os.path.basename(filepath) 
            self.selected_video_label.configure(text=filename)
            self.status_label.configure(text=f"Video de fondo: {filename}")
        else:
            self.background_video_path = None; self.selected_video_label.configure(text="Video no seleccionado")

    def process_final_video_generation(self): #OK
        if not self.generated_audio_path or not os.path.exists(self.generated_audio_path): self.status_label.configure(text="Error: Primero genera el audio."); return
        if not self.background_video_path or not os.path.exists(self.background_video_path): self.status_label.configure(text="Error: Primero selecciona un video de fondo."); return
        
        self.status_label.configure(text="Generando video narrado... Puede tardar."); self.update_idletasks()
        output_final_video_filename = "video_final_narrado.mp4"
        success = video_processor.create_narrated_video(self.background_video_path, self.generated_audio_path, output_final_video_filename)
        if success:
            self.narrated_video_path = os.path.abspath(output_final_video_filename) 
            self.status_label.configure(text=f"¡Video narrado generado!: {self.narrated_video_path}")
        else:
            self.narrated_video_path = None
            self.status_label.configure(text="Error al generar video narrado.")

    def process_srt_generation(self): #OK
        if not self.generated_audio_path or not os.path.exists(self.generated_audio_path): self.status_label.configure(text="Error SRT: Primero genera el audio."); return
        
        max_words_str = self.srt_max_words_var.get()
        max_words_value = None 
        if max_words_str.isdigit(): max_words_value = int(max_words_str)
        elif max_words_str != "Whisper (Defecto)": self.status_label.configure(text="Error SRT: 'Palabras Máx.' inválido."); return
        
        self.status_label.configure(text="SRT: Generando subtítulos... Puede tardar."); self.update_idletasks()
        audio_basename = os.path.splitext(os.path.basename(self.generated_audio_path))[0]
        output_srt_filename = f"{audio_basename}.srt" # ej. historia_narrada.srt
        
        success = srt_generator.create_srt_file(
            self.generated_audio_path, output_srt_filename,
            model_size="base.en", language="en", # Podrían ser configurables en el futuro
            max_words_per_segment=max_words_value)
        if success:
            self.generated_srt_path = os.path.abspath(output_srt_filename) 
            self.status_label.configure(text=f"¡SRT generado!: {self.generated_srt_path}")
        else:
            self.generated_srt_path = None
            self.status_label.configure(text="Error al generar SRT.")
            
    def process_burn_subtitles(self): #OK
        """Recoge opciones de estilo y llama a grabar subtítulos en el video."""
        if not self.narrated_video_path or not os.path.exists(self.narrated_video_path):
            self.status_label.configure(text="Error Sub Burn: Primero genera el 'Video Final Narrado'.")
            return
        if not self.generated_srt_path or not os.path.exists(self.generated_srt_path):
            self.status_label.configure(text="Error Sub Burn: Primero genera el archivo '.SRT'.")
            return

        try:
            font_options = {
                'font': self.subtitle_font_var.get(),
                'fontsize': int(self.subtitle_fontsize_var.get()),
                'color': self.subtitle_color_entry.get() or 'white',
                'stroke_color': self.subtitle_strokecolor_entry.get() or 'black',
                'stroke_width': float(self.subtitle_strokewidth_var.get()),
                'bg_color': self.subtitle_bgcolor_entry.get() or 'rgba(0,0,0,0.5)',
                'position_choice': self.subtitle_pos_var.get() 
            }
        except ValueError:
            self.status_label.configure(text="Error Sub Burn: Valor inválido en opciones de estilo (ej. tamaño o ancho de borde deben ser números).")
            return
        
        video_basename = os.path.splitext(os.path.basename(self.narrated_video_path))[0]
        output_video_with_subs_filename = f"{video_basename}_con_subtitulos.mp4"
        
        self.status_label.configure(text="Grabando subtítulos en video... Esto puede tardar mucho.")
        self.update_idletasks()

        success = video_processor.burn_subtitles_on_video(
            self.narrated_video_path,
            self.generated_srt_path,
            output_video_with_subs_filename,
            style_options=font_options # Cambiado de font_options a style_options para coincidir con video_processor.py
        )

        if success:
            full_path = os.path.abspath(output_video_with_subs_filename)
            self.status_label.configure(text=f"¡Video con subtítulos grabados!: {full_path}")
        else:
            self.status_label.configure(text="Error al grabar subtítulos en el video.")


if __name__ == "__main__":
    app = App()
    app.mainloop()