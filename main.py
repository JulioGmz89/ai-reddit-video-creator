# main.py (Refactorizado para nuevo flujo)
import customtkinter
from customtkinter import filedialog
import os
import traceback
import threading
import queue
from tkinter import colorchooser

# Importar tus módulos personalizados
import reddit_scraper
import tts_kokoro_module 
import ai_story_generator 
import video_processor 
import srt_generator 
import file_manager # <--- NUESTRO NUEVO GESTOR DE ARCHIVOS

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Reddit Story Video Creator v2.0")
        self.geometry("850x850") # Ajustar altura según sea necesario con menos botones

        # Variables de instancia para selecciones del usuario
        self.background_video_path = None
        self.can_generate_audio = False # Para el botón de TTS, aunque ahora es parte de un flujo mayor
        self.selected_voice_technical_name = None
        
        # Colores para subtítulos (con valores por defecto para MoviePy y vistas previas)
        self.subtitle_font_color_hex = "#FFFF00"     # Amarillo
        self.subtitle_stroke_color_hex = "#000000"   # Negro
        
        self.task_queue = queue.Queue()
        self.after(100, self.check_queue_for_updates) 

        # Asegurar que los directorios de salida existan al iniciar
        file_manager.ensure_directories_exist()

        self.grid_columnconfigure(0, weight=1)
        # Reajustar filas según los nuevos frames
        self.grid_rowconfigure(0, weight=0)  # input_frame (Reddit URL)
        self.grid_rowconfigure(1, weight=0)  # ai_story_config_frame
        self.grid_rowconfigure(2, weight=0)  # tts_voice_and_video_select_frame
        self.grid_rowconfigure(3, weight=0)  # srt_and_subtitle_style_frame
        self.grid_rowconfigure(4, weight=1)  # story_frame (Textbox) - ESTE SE EXPANDE
        self.grid_rowconfigure(5, weight=0)  # main_action_frame
        self.grid_rowconfigure(6, weight=0)  # status_frame


        # --- Sección 1: Entrada de Texto (Reddit o Manual) ---
        self.input_frame = customtkinter.CTkFrame(self)
        self.input_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.input_frame.grid_columnconfigure(1, weight=1)
        customtkinter.CTkLabel(self.input_frame, text="URL de Reddit:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.reddit_url_entry = customtkinter.CTkEntry(self.input_frame, placeholder_text="Pega aquí la URL de un post de Reddit...")
        self.reddit_url_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.reddit_fetch_button = customtkinter.CTkButton(self.input_frame, text="Obtener Historia", command=self.fetch_reddit_post_threaded)
        self.reddit_fetch_button.grid(row=0, column=2, padx=10, pady=10)

        # --- Sección 2: Generación de Historia con IA ---
        self.ai_story_config_frame = customtkinter.CTkFrame(self)
        self.ai_story_config_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.ai_story_config_frame.grid_columnconfigure(1, weight=1) 
        customtkinter.CTkLabel(self.ai_story_config_frame, text="Tema Historia IA (Inglés):").grid(row=0, column=0, padx=(10,0), pady=5, sticky="w")
        self.ai_subject_entry = customtkinter.CTkEntry(self.ai_story_config_frame, placeholder_text="Ej: alien encounter, haunted house")
        self.ai_subject_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew") 
        customtkinter.CTkLabel(self.ai_story_config_frame, text="Estilo Historia IA (Inglés):").grid(row=1, column=0, padx=(10,0), pady=5, sticky="w")
        self.ai_style_entry = customtkinter.CTkEntry(self.ai_story_config_frame, placeholder_text="Ej: r/nosleep, comedy, mystery")
        self.ai_style_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="ew") 
        customtkinter.CTkLabel(self.ai_story_config_frame, text="Tokens Máx. IA:").grid(row=2, column=0, padx=(10,0), pady=5, sticky="w")
        self.max_tokens_options = ["200", "300", "400", "500"] 
        self.ai_max_tokens_menu_var = customtkinter.StringVar(value=self.max_tokens_options[1]) 
        self.ai_max_tokens_menu = customtkinter.CTkOptionMenu(
            self.ai_story_config_frame, values=self.max_tokens_options, variable=self.ai_max_tokens_menu_var)
        self.ai_max_tokens_menu.grid(row=2, column=1, padx=10, pady=5, sticky="w") 
        self.generate_ai_story_button = customtkinter.CTkButton(
            self.ai_story_config_frame, text="Generar Historia con IA", command=self.process_ai_story_generation_threaded)
        self.generate_ai_story_button.grid(row=2, column=2, padx=10, pady=5, sticky="e")

        # --- Sección 3: Selección de Voz TTS y Video de Fondo ---
        self.tts_video_select_frame = customtkinter.CTkFrame(self)
        self.tts_video_select_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.tts_video_select_frame.grid_columnconfigure(1, weight=1)
        self.tts_video_select_frame.grid_columnconfigure(3, weight=1)

        customtkinter.CTkLabel(self.tts_video_select_frame, text="Voz TTS:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.available_voices_map = tts_kokoro_module.list_english_voices_for_pip_package()
        self.voice_friendly_names = list(self.available_voices_map.keys())
        default_voice_friendly = ""
        if not self.voice_friendly_names:
            self.voice_friendly_names = ["No hay voces"] ; default_voice_friendly = self.voice_friendly_names[0]; self.can_generate_audio = False
        else:
            default_voice_friendly = self.voice_friendly_names[0]; self.selected_voice_technical_name = self.available_voices_map[default_voice_friendly]; self.can_generate_audio = True
        self.tts_voice_menu_var = customtkinter.StringVar(value=default_voice_friendly)
        self.tts_voice_menu = customtkinter.CTkOptionMenu(
            self.tts_video_select_frame, values=self.voice_friendly_names,
            variable=self.tts_voice_menu_var, command=self.update_selected_voice_technical_name)
        self.tts_voice_menu.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        if not self.can_generate_audio: self.tts_voice_menu.configure(state="disabled")

        self.select_video_button = customtkinter.CTkButton(
            self.tts_video_select_frame, text="Seleccionar Video Fondo", command=self.select_background_video)
        self.select_video_button.grid(row=0, column=2, padx=(20,5), pady=10, sticky="w")
        self.selected_video_label = customtkinter.CTkLabel(self.tts_video_select_frame, text="Video no seleccionado")
        self.selected_video_label.grid(row=0, column=3, padx=5, pady=10, sticky="ew")

        # --- Sección 4: Configuración de Subtítulos (SRT y Estilo) ---
        self.srt_style_frame = customtkinter.CTkFrame(self)
        self.srt_style_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        # Configurar columnas para layout (label, control, label, control)
        self.srt_style_frame.grid_columnconfigure(1, weight=1); self.srt_style_frame.grid_columnconfigure(3, weight=1)

        customtkinter.CTkLabel(self.srt_style_frame, text="Palabras Máx./SRT:").grid(row=0, column=0, padx=(10,0), pady=5, sticky="w")
        self.srt_max_words_options = ["Whisper (Defecto)", "1", "2", "3", "4", "5", "6", "7"]
        self.srt_max_words_var = customtkinter.StringVar(value="3") 
        self.srt_max_words_menu = customtkinter.CTkOptionMenu(
            self.srt_style_frame, values=self.srt_max_words_options, variable=self.srt_max_words_var)
        self.srt_max_words_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        customtkinter.CTkLabel(self.srt_style_frame, text="Posición Subs:").grid(row=0, column=2, padx=(10,0), pady=5, sticky="w")
        self.subtitle_pos_options = ["Abajo", "Centro", "Arriba"]
        self.subtitle_pos_var = customtkinter.StringVar(value="Abajo")
        self.subtitle_pos_menu = customtkinter.CTkOptionMenu(self.srt_style_frame, values=self.subtitle_pos_options, variable=self.subtitle_pos_var)
        self.subtitle_pos_menu.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        customtkinter.CTkLabel(self.srt_style_frame, text="Fuente Sub:").grid(row=1, column=0, padx=(10,0), pady=5, sticky="w")
        self.subtitle_font_options = ["Arial", "Verdana", "Times New Roman", "Impact", "Courier New", "Tahoma", "Georgia"]
        self.subtitle_font_var = customtkinter.StringVar(value="Arial")
        self.subtitle_font_menu = customtkinter.CTkOptionMenu(self.srt_style_frame, values=self.subtitle_font_options, variable=self.subtitle_font_var)
        self.subtitle_font_menu.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        customtkinter.CTkLabel(self.srt_style_frame, text="Tamaño Fuente:").grid(row=1, column=2, padx=(10,0), pady=5, sticky="w")
        self.subtitle_fontsize_options = ["18", "20", "22", "24", "26", "28", "30", "32", "36", "40", "44", "48", "52", "56", "60", "64", "72"]
        self.subtitle_fontsize_var = customtkinter.StringVar(value="36")
        self.subtitle_fontsize_menu = customtkinter.CTkOptionMenu(self.srt_style_frame, values=self.subtitle_fontsize_options, variable=self.subtitle_fontsize_var)
        self.subtitle_fontsize_menu.grid(row=1, column=3, padx=5, pady=5, sticky="ew")
        
        customtkinter.CTkLabel(self.srt_style_frame, text="Color Texto Sub:").grid(row=2, column=0, padx=(10,0), pady=5, sticky="w")
        self.subtitle_text_color_button = customtkinter.CTkButton(self.srt_style_frame, text="Elegir...", width=100, command=lambda: self.pick_color_for('text_fg'))
        self.subtitle_text_color_button.grid(row=2, column=1, padx=(5,0), pady=5, sticky="w")
        self.subtitle_text_color_preview = customtkinter.CTkFrame(self.srt_style_frame, width=60, height=28, fg_color=self.subtitle_font_color_hex, border_width=1, border_color="gray50")
        self.subtitle_text_color_preview.grid(row=2, column=1, padx=(120,5), pady=5, sticky="w")

        customtkinter.CTkLabel(self.srt_style_frame, text="Color Borde Sub:").grid(row=2, column=2, padx=(10,0), pady=5, sticky="w")
        self.subtitle_stroke_color_button = customtkinter.CTkButton(self.srt_style_frame, text="Elegir...", width=100, command=lambda: self.pick_color_for('stroke_fg'))
        self.subtitle_stroke_color_button.grid(row=2, column=3, padx=(5,0), pady=5, sticky="w") # Cambiado sticky a "w"
        self.subtitle_stroke_color_preview = customtkinter.CTkFrame(self.srt_style_frame, width=60, height=28, fg_color=self.subtitle_stroke_color_hex, border_width=1, border_color="gray50")
        self.subtitle_stroke_color_preview.grid(row=2, column=3, padx=(120,5), pady=5, sticky="w") # Cambiado sticky a "w"

        customtkinter.CTkLabel(self.srt_style_frame, text="Ancho Borde Sub:").grid(row=3, column=0, padx=(10,0), pady=5, sticky="w")
        self.subtitle_strokewidth_options = ["0", "0.5", "1", "1.5", "2", "2.5", "3", "3.5", "4", "4.5", "5"]
        self.subtitle_strokewidth_var = customtkinter.StringVar(value="1.5") 
        self.subtitle_strokewidth_menu = customtkinter.CTkOptionMenu(self.srt_style_frame, values=self.subtitle_strokewidth_options, variable=self.subtitle_strokewidth_var)
        self.subtitle_strokewidth_menu.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        
        customtkinter.CTkLabel(self.srt_style_frame, text="Fondo Sub:").grid(row=3, column=2, padx=(10,0), pady=5, sticky="w")
        self.subtitle_bgcolor_map = { 
            "Transparente Total": "transparent", "Negro Semi (40%)": "rgba(0,0,0,0.4)",
            "Negro Semi (60%)": "rgba(0,0,0,0.6)", "Gris Semi (50%)": "rgba(128,128,128,0.5)",
            "Blanco (Opaco)": "white", "Negro (Opaco)": "black" }
        self.subtitle_bgcolor_options = list(self.subtitle_bgcolor_map.keys())
        self.subtitle_bgcolor_var = customtkinter.StringVar(value="Negro Semi (40%)") 
        self.subtitle_bgcolor_menu = customtkinter.CTkOptionMenu(
            self.srt_style_frame, values=self.subtitle_bgcolor_options, variable=self.subtitle_bgcolor_var)
        self.subtitle_bgcolor_menu.grid(row=3, column=3, padx=5, pady=5, sticky="ew")

        # --- Sección 5: Cuadro de Texto para la Historia ---
        self.story_frame = customtkinter.CTkFrame(self)
        self.story_frame.grid(row=4, column=0, padx=10, pady=5, sticky="nsew") # Fila ajustada
        self.story_frame.grid_columnconfigure(0, weight=1); self.story_frame.grid_rowconfigure(0, weight=1)
        self.story_textbox = customtkinter.CTkTextbox(self.story_frame, wrap="word", font=("Arial", 14))
        self.story_textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.story_textbox.insert("1.0", "1. Obtén/Genera una historia aquí.\n2. Configura Voz, Video Fondo y Subtítulos.\n3. Haz clic en 'CREAR VIDEO FINAL COMPLETO'.")

        # --- Sección 6: Botón de Acción Principal ---
        self.main_action_frame = customtkinter.CTkFrame(self)
        self.main_action_frame.grid(row=5, column=0, padx=10, pady=10, sticky="ew")
        self.main_action_frame.grid_columnconfigure(0, weight=1) # Para centrar el botón

        self.generate_all_button = customtkinter.CTkButton(
            self.main_action_frame, 
            text="CREAR VIDEO FINAL COMPLETO (Narrado y Subtitulado)", 
            command=self.process_all_steps_threaded,
            height=40, font=("Arial", 14, "bold")
        )
        self.generate_all_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # --- Sección 7: Estado --- 
        self.status_frame = customtkinter.CTkFrame(self) 
        self.status_frame.grid(row=6, column=0, padx=10, pady=(5,10), sticky="ew") # Fila ajustada
        self.status_label = customtkinter.CTkLabel(self.status_frame, text="Estado: Listo. Configura y crea tu video.")
        self.status_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

    # --- Métodos de la App ---
    def check_queue_for_updates(self): #OK
        try:
            callback = self.task_queue.get(block=False)
            if callable(callback): callback()
            self.task_queue.task_done()
        except queue.Empty: pass
        finally: self.after(100, self.check_queue_for_updates)

    def _disable_main_action_button(self):
        if hasattr(self, 'generate_all_button') and self.generate_all_button.winfo_exists():
            self.generate_all_button.configure(state="disabled")
        # Podrías desactivar también los botones de config si lo deseas
        if hasattr(self, 'reddit_fetch_button'): self.reddit_fetch_button.configure(state="disabled")
        if hasattr(self, 'generate_ai_story_button'): self.generate_ai_story_button.configure(state="disabled")


    def _enable_main_action_button(self):
        if hasattr(self, 'generate_all_button') and self.generate_all_button.winfo_exists():
            self.generate_all_button.configure(state="normal")
        if hasattr(self, 'reddit_fetch_button'): self.reddit_fetch_button.configure(state="normal")
        if hasattr(self, 'generate_ai_story_button'): self.generate_ai_story_button.configure(state="normal")

    def update_selected_voice_technical_name(self, selected_friendly_name: str): #OK
        if self.can_generate_audio:
            self.selected_voice_technical_name = self.available_voices_map.get(selected_friendly_name)
            self.status_label.configure(text=f"Voz seleccionada: {selected_friendly_name}")

    def pick_color_for(self, color_target: str): #OK
        initial_color = None
        if color_target == 'text_fg': initial_color = self.subtitle_font_color_hex
        elif color_target == 'stroke_fg': initial_color = self.subtitle_stroke_color_hex
        
        color_info = colorchooser.askcolor(initialcolor=initial_color, title=f"Selecciona color para {color_target.replace('_fg','').replace('text','texto').replace('stroke','borde')}")
        if color_info and color_info[1]:
            hex_color = color_info[1]
            if color_target == 'text_fg':
                self.subtitle_font_color_hex = hex_color
                if hasattr(self, 'subtitle_text_color_preview'): self.subtitle_text_color_preview.configure(fg_color=hex_color)
                self.status_label.configure(text=f"Color de texto subtítulos: {hex_color}")
            elif color_target == 'stroke_fg':
                self.subtitle_stroke_color_hex = hex_color
                if hasattr(self, 'subtitle_stroke_color_preview'): self.subtitle_stroke_color_preview.configure(fg_color=hex_color)
                self.status_label.configure(text=f"Color de borde subtítulos: {hex_color}")
        else:
            self.status_label.configure(text=f"Selección de color para {color_target.replace('_fg','')} cancelada.")

    # --- Reddit Fetch (Threaded) ---
    def _reddit_fetch_worker(self, url: str): #OK
        try:
            title, body = reddit_scraper.get_post_details(url)
            self.task_queue.put(lambda t=title, b=body: self._update_gui_after_reddit_fetch(t, b))
        except Exception as e:
            error_msg = f"Error en hilo Reddit: {str(e)}\n{traceback.format_exc()}"; print(error_msg)
            self.task_queue.put(lambda: self._update_gui_after_reddit_fetch(None, None, error_msg=str(e)))
            
    def _update_gui_after_reddit_fetch(self, title: str | None, body: str | None, error_msg: str = None): #OK
        self.story_textbox.delete("1.0", "end")
        if error_msg:
            self.story_textbox.insert("1.0", f"Error obteniendo post de Reddit:\n{error_msg}")
            self.status_label.configure(text="Error crítico al obtener post de Reddit.")
        elif title is None or body is None or "Error" in title or "no encontrado" in title or (title == "Título no encontrado." and body == "Cuerpo del post no encontrado.") : 
            display_title = title if title else "Error"
            display_body = body if body else "No se pudo obtener contenido."
            full_story = f"{display_title}\n\n{display_body}" 
            self.story_textbox.insert("1.0", full_story)
            self.status_label.configure(text="Error al obtener historia de Reddit o post no textual.")
        else:
            full_story = f"{title}\n\n{body}"
            self.story_textbox.insert("1.0", full_story)
            self.status_label.configure(text="Historia de Reddit cargada.")
        self._enable_main_action_button()

    def fetch_reddit_post_threaded(self): #OK
        url = self.reddit_url_entry.get()
        if not url:
            self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", "Error: URL de Reddit vacía.")
            self.status_label.configure(text="Error: URL de Reddit vacía."); return
        
        self.status_label.configure(text="Obteniendo post de Reddit (en hilo)..."); self.update_idletasks()
        self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", "Cargando..."); self.update_idletasks() 
        self._disable_main_action_button()
        thread = threading.Thread(target=self._reddit_fetch_worker, args=(url,), daemon=True)
        thread.start()

    # --- AI Story Generation (Threaded) ---
    def _ai_story_worker(self, subject: str, style: str, max_tokens: int): #OK
        try:
            generated_story_text = ai_story_generator.generate_story(subject, style, max_tokens)
            self.task_queue.put(lambda s=generated_story_text: self._update_gui_after_ai_story(s, is_error=False))
        except Exception as e:
            error_msg = f"Error en el hilo de IA: {str(e)}\n{traceback.format_exc()}"; print(error_msg)
            self.task_queue.put(lambda: self._update_gui_after_ai_story(f"Error generando historia: {str(e)}", is_error=True))

    def _update_gui_after_ai_story(self, story_or_error_message: str, is_error: bool): #OK
        self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", story_or_error_message)
        if is_error: self.status_label.configure(text="IA: Error al generar historia.")
        else:
            if story_or_error_message.startswith("Error:"): self.status_label.configure(text=f"IA: {story_or_error_message}")
            else: self.status_label.configure(text="IA: ¡Historia en INGLÉS generada!")
        self._enable_main_action_button()

    def process_ai_story_generation_threaded(self): #OK
        subject = self.ai_subject_entry.get().strip(); style = self.ai_style_entry.get().strip()
        if not subject or not style: self.status_label.configure(text="Error IA: Ingresa Tema y Estilo."); return
        try: max_tokens = int(self.ai_max_tokens_menu_var.get())
        except ValueError: self.status_label.configure(text="Error IA: Tokens inválido."); return
        self.status_label.configure(text="IA: Iniciando generación (hilo)..."); self.update_idletasks()
        self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", "Generando IA (hilo)..."); self.update_idletasks() 
        self._disable_main_action_button()
        thread = threading.Thread(target=self._ai_story_worker, args=(subject, style, max_tokens), daemon=True)
        thread.start()
            
    def select_background_video(self): #OK
        filetypes = (("Archivos de Video", "*.mp4 *.mov *.avi *.mkv"),("Todos los archivos", "*.*")) 
        filepath = filedialog.askopenfilename(title="Selecciona un video de fondo", filetypes=filetypes)
        if filepath:
            self.background_video_path = filepath; filename = os.path.basename(filepath) 
            self.selected_video_label.configure(text=filename)
            self.status_label.configure(text=f"Video de fondo: {filename}")
        else:
            self.background_video_path = None; self.selected_video_label.configure(text="Video no seleccionado")

    # --- NUEVO FLUJO DE PROCESAMIENTO COMPLETO (Threaded) ---
    def _process_all_worker(self, story_text, tts_voice_tech_name, bg_video_path, srt_max_words, subtitle_style_options, current_id):
        intermediate_audio_path = None
        intermediate_narrated_video_path = None
        intermediate_srt_path = None
        final_video_path_with_subs = None
        current_step = ""

        try:
            # Paso 1: Generar Audio TTS
            current_step = "Generando Audio (TTS)..."
            self.task_queue.put(lambda: self.status_label.configure(text=f"Procesando (1/4): {current_step}"))
            intermediate_audio_path = os.path.join(file_manager.AUDIO_DIR, f"{current_id}.wav")
            tts_success = tts_kokoro_module.generate_speech_with_voice_name(story_text, tts_voice_tech_name, intermediate_audio_path)
            if not tts_success: raise Exception("Fallo en la generación de audio TTS.")

            # Paso 2: Generar Video Narrado (Video + Audio TTS)
            current_step = "Creando video narrado..."
            self.task_queue.put(lambda: self.status_label.configure(text=f"Procesando (2/4): {current_step}"))
            intermediate_narrated_video_path = os.path.join(file_manager.NARRATED_VIDEO_DIR, f"{current_id}.mp4")
            video_narr_success = video_processor.create_narrated_video(bg_video_path, intermediate_audio_path, intermediate_narrated_video_path)
            if not video_narr_success: raise Exception("Fallo en la creación del video narrado.")

            # Paso 3: Generar Archivo SRT
            current_step = "Generando subtítulos SRT..."
            self.task_queue.put(lambda: self.status_label.configure(text=f"Procesando (3/4): {current_step}"))
            intermediate_srt_path = os.path.join(file_manager.SRT_DIR, f"{current_id}.srt")
            srt_success = srt_generator.create_srt_file(intermediate_audio_path, intermediate_srt_path, max_words_per_segment=srt_max_words)
            if not srt_success: raise Exception("Fallo en la generación del archivo SRT.")
            
            # Paso 4: Grabar Subtítulos en el Video Narrado
            current_step = "Grabando subtítulos en video..."
            self.task_queue.put(lambda: self.status_label.configure(text=f"Procesando (4/4): {current_step}"))
            final_video_path_with_subs = os.path.join(file_manager.FINAL_VIDEO_DIR, f"{current_id}.mp4")
            burn_success = video_processor.burn_subtitles_on_video(intermediate_narrated_video_path, intermediate_srt_path, final_video_path_with_subs, style_options=subtitle_style_options)
            if not burn_success: raise Exception("Fallo al grabar los subtítulos en el video.")

            # Si todo fue exitoso
            self.task_queue.put(lambda: self._update_gui_after_all_processing(True, f"¡Video final completo! Guardado en: {os.path.abspath(final_video_path_with_subs)}"))

        except Exception as e:
            error_full_msg = f"Error durante '{current_step}': {str(e)}\n{traceback.format_exc()}"
            print(error_full_msg) # Log completo a consola
            self.task_queue.put(lambda: self._update_gui_after_all_processing(False, f"Error en '{current_step}': {str(e)}"))


    def _update_gui_after_all_processing(self, success: bool, message: str):
        self.status_label.configure(text=message)
        self._enable_main_action_button() # Reactivar el botón principal y los de obtención de texto

    def process_all_steps_threaded(self):
        print("Iniciando proceso completo de generación de video...")
        # 1. Recoger todo el texto
        story_text = self.story_textbox.get("1.0", "end-1c").strip()
        placeholders = ["Aquí aparecerá la historia...", "Cargando...", "Generando historia..."] 
        is_placeholder = any(story_text.startswith(p_start) for p_start in placeholders if p_start)
        if not story_text or is_placeholder:
            self.status_label.configure(text="Error: No hay texto válido en la historia para procesar."); return
        
        # 2. Verificar voz TTS
        if not self.can_generate_audio or not self.selected_voice_technical_name:
            self.status_label.configure(text="Error: Voz TTS no válida seleccionada."); return
        tts_voice_tech_name = self.selected_voice_technical_name

        # 3. Verificar video de fondo
        if not self.background_video_path or not os.path.exists(self.background_video_path):
            self.status_label.configure(text="Error: Selecciona un video de fondo válido."); return
        bg_video_path = self.background_video_path

        # 4. Recoger configuración SRT
        max_words_str = self.srt_max_words_var.get()
        srt_max_words = None 
        if max_words_str.isdigit(): srt_max_words = int(max_words_str)
        elif max_words_str != "Whisper (Defecto)":
            self.status_label.configure(text="Error SRT: 'Palabras Máx.' inválido."); return

        # 5. Recoger opciones de estilo de subtítulos
        try:
            selected_bg_color_friendly = self.subtitle_bgcolor_var.get()
            actual_bg_color = self.subtitle_bgcolor_map.get(selected_bg_color_friendly, "rgba(0,0,0,0.4)")

            subtitle_style_options = { 
                'font': self.subtitle_font_var.get(), 
                'fontsize': int(self.subtitle_fontsize_var.get()),
                'color': self.subtitle_font_color_hex, 
                'stroke_color': self.subtitle_stroke_color_hex,
                'stroke_width': float(self.subtitle_strokewidth_var.get()), 
                'bg_color': actual_bg_color, 
                'position_choice': self.subtitle_pos_var.get() 
            }
        except ValueError:
            self.status_label.configure(text="Error: Valor numérico inválido en opciones de estilo de subtítulos."); return

        # Generar ID único para esta tanda de archivos
        current_id = file_manager.get_next_id_str()
        self.status_label.configure(text=f"Iniciando proceso completo para ID: {current_id}... (Esto puede tardar mucho)"); self.update_idletasks()
        self._disable_main_action_button()

        # Lanzar el trabajador principal en un hilo
        master_thread = threading.Thread(
            target=self._process_all_worker,
            args=(story_text, tts_voice_tech_name, bg_video_path, srt_max_words, subtitle_style_options, current_id),
            daemon=True
        )
        master_thread.start()

if __name__ == "__main__":
    app = App()
    app.mainloop()