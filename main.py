# main.py
import customtkinter
from customtkinter import filedialog
import os
import traceback
import threading # Para ejecutar tareas largas sin congelar la GUI
import queue     # Para comunicar resultados de los hilos a la GUI

# Importar tus módulos personalizados
import reddit_scraper
import tts_kokoro_module 
import ai_story_generator 
import video_processor 
import srt_generator 

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Reddit Story Video Creator")
        self.geometry("850x1000") 

        self.generated_audio_path = None
        self.background_video_path = None
        self.narrated_video_path = None 
        self.generated_srt_path = None  
        self.can_generate_audio = False

        self.task_queue = queue.Queue()
        self.after(100, self.check_queue_for_updates) 

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0); self.grid_rowconfigure(1, weight=0) 
        self.grid_rowconfigure(2, weight=0); self.grid_rowconfigure(3, weight=1) # story_frame
        self.grid_rowconfigure(4, weight=0); self.grid_rowconfigure(5, weight=0)
        self.grid_rowconfigure(6, weight=0); self.grid_rowconfigure(7, weight=0) 

        # --- Sección 1: Entrada de Texto (Reddit o Manual) ---
        self.input_frame = customtkinter.CTkFrame(self)
        self.input_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.input_frame.grid_columnconfigure(1, weight=1)
        customtkinter.CTkLabel(self.input_frame, text="URL de Reddit:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.reddit_url_entry = customtkinter.CTkEntry(self.input_frame, placeholder_text="Pega aquí la URL de un post de Reddit...")
        self.reddit_url_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.reddit_fetch_button = customtkinter.CTkButton(self.input_frame, text="Obtener Historia", command=self.fetch_reddit_post_threaded) # Threaded
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

        # --- Sección 3: Configuración de Texto a Voz (TTS) ---
        self.tts_config_frame = customtkinter.CTkFrame(self)
        self.tts_config_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.tts_config_frame.grid_columnconfigure(1, weight=1)
        customtkinter.CTkLabel(self.tts_config_frame, text="Voz TTS:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.available_voices_map = tts_kokoro_module.list_english_voices_for_pip_package()
        self.voice_friendly_names = list(self.available_voices_map.keys())
        default_voice_friendly = ""
        if not self.voice_friendly_names:
            self.voice_friendly_names = ["No hay voces disponibles"]; default_voice_friendly = self.voice_friendly_names[0]; self.can_generate_audio = False
        else:
            default_voice_friendly = self.voice_friendly_names[0]; self.selected_voice_technical_name = self.available_voices_map[default_voice_friendly]; self.can_generate_audio = True
        self.tts_voice_menu_var = customtkinter.StringVar(value=default_voice_friendly)
        self.tts_voice_menu = customtkinter.CTkOptionMenu(
            self.tts_config_frame, values=self.voice_friendly_names,
            variable=self.tts_voice_menu_var, command=self.update_selected_voice_technical_name)
        self.tts_voice_menu.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        if not self.can_generate_audio: self.tts_voice_menu.configure(state="disabled")
        self.generate_audio_button = customtkinter.CTkButton(
            self.tts_config_frame, text="Generar Audio de Historia", command=self.process_text_to_speech_threaded) # Threaded
        self.generate_audio_button.grid(row=0, column=2, padx=10, pady=10)
        if not self.can_generate_audio: self.generate_audio_button.configure(state="disabled")

        # --- Sección 4: Cuadro de Texto para la Historia ---
        self.story_frame = customtkinter.CTkFrame(self)
        self.story_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        self.story_frame.grid_columnconfigure(0, weight=1); self.story_frame.grid_rowconfigure(0, weight=1)
        self.story_textbox = customtkinter.CTkTextbox(self.story_frame, wrap="word", font=("Arial", 14))
        self.story_textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.story_textbox.insert("1.0", "Aquí aparecerá la historia de Reddit, la generada por IA, o la que escribas manualmente...")

        # --- Sección 5: Procesamiento de Video ---
        self.video_processing_frame = customtkinter.CTkFrame(self)
        self.video_processing_frame.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        self.video_processing_frame.grid_columnconfigure(1, weight=1) 
        self.select_video_button = customtkinter.CTkButton(
            self.video_processing_frame, text="Seleccionar Video de Fondo (.mp4)", command=self.select_background_video)
        self.select_video_button.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.selected_video_label = customtkinter.CTkLabel(self.video_processing_frame, text="Video no seleccionado")
        self.selected_video_label.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.generate_final_video_button = customtkinter.CTkButton(
            self.video_processing_frame, text="Generar Video Narrado", command=self.process_final_video_generation_threaded) # Threaded
        self.generate_final_video_button.grid(row=0, column=2, padx=10, pady=10, sticky="e")

        # --- Sección 6: Configuración de SRT ---
        self.srt_config_frame = customtkinter.CTkFrame(self)
        self.srt_config_frame.grid(row=5, column=0, padx=10, pady=5, sticky="ew")
        self.srt_config_frame.grid_columnconfigure(1, weight=0) 
        customtkinter.CTkLabel(self.srt_config_frame, text="Palabras Máx./Segmento SRT:").grid(row=0, column=0, padx=(10,0), pady=5, sticky="w")
        self.srt_max_words_options = ["Whisper (Defecto)", "1", "2", "3", "4", "5", "6", "7"]
        self.srt_max_words_var = customtkinter.StringVar(value="3") 
        self.srt_max_words_menu = customtkinter.CTkOptionMenu(
            self.srt_config_frame, values=self.srt_max_words_options, variable=self.srt_max_words_var)
        self.srt_max_words_menu.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self.generate_srt_button = customtkinter.CTkButton(
            self.srt_config_frame, text="1. Generar Archivo .SRT", command=self.process_srt_generation_threaded) # Threaded
        self.generate_srt_button.grid(row=0, column=2, padx=10, pady=5, sticky="e")

        # --- Sección 7: Estilo de Subtítulos y Grabado en Video ---
        self.subtitle_style_frame = customtkinter.CTkFrame(self)
        self.subtitle_style_frame.grid(row=6, column=0, padx=10, pady=5, sticky="ew")
        self.subtitle_style_frame.grid_columnconfigure(1, weight=1); self.subtitle_style_frame.grid_columnconfigure(3, weight=1)
        
        customtkinter.CTkLabel(self.subtitle_style_frame, text="Fuente Sub:").grid(row=0, column=0, padx=(10,0), pady=5, sticky="w")
        self.subtitle_font_options = ["Arial", "Verdana", "Times New Roman", "Impact", "Courier New"]
        self.subtitle_font_var = customtkinter.StringVar(value="Arial")
        self.subtitle_font_menu = customtkinter.CTkOptionMenu(self.subtitle_style_frame, values=self.subtitle_font_options, variable=self.subtitle_font_var)
        self.subtitle_font_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.subtitle_style_frame, text="Tamaño:").grid(row=0, column=2, padx=(10,0), pady=5, sticky="w")
        self.subtitle_fontsize_options = ["24", "28", "32", "36", "40", "48", "52", "60"]
        self.subtitle_fontsize_var = customtkinter.StringVar(value="36")
        self.subtitle_fontsize_menu = customtkinter.CTkOptionMenu(self.subtitle_style_frame, values=self.subtitle_fontsize_options, variable=self.subtitle_fontsize_var)
        self.subtitle_fontsize_menu.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.subtitle_style_frame, text="Color Texto:").grid(row=1, column=0, padx=(10,0), pady=5, sticky="w")
        self.subtitle_color_entry = customtkinter.CTkEntry(self.subtitle_style_frame, placeholder_text="white, yellow, #FFFF00"); self.subtitle_color_entry.insert(0, "yellow")
        self.subtitle_color_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.subtitle_style_frame, text="Posición:").grid(row=1, column=2, padx=(10,0), pady=5, sticky="w")
        self.subtitle_pos_options = ["Abajo", "Centro", "Arriba"]
        self.subtitle_pos_var = customtkinter.StringVar(value="Abajo")
        self.subtitle_pos_menu = customtkinter.CTkOptionMenu(self.subtitle_style_frame, values=self.subtitle_pos_options, variable=self.subtitle_pos_var)
        self.subtitle_pos_menu.grid(row=1, column=3, padx=5, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.subtitle_style_frame, text="Color Borde:").grid(row=2, column=0, padx=(10,0), pady=5, sticky="w")
        self.subtitle_strokecolor_entry = customtkinter.CTkEntry(self.subtitle_style_frame, placeholder_text="black, transparent"); self.subtitle_strokecolor_entry.insert(0, "black")
        self.subtitle_strokecolor_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.subtitle_style_frame, text="Ancho Borde:").grid(row=2, column=2, padx=(10,0), pady=5, sticky="w")
        self.subtitle_strokewidth_options = ["0", "0.5", "1", "1.5", "2", "2.5", "3"]
        self.subtitle_strokewidth_var = customtkinter.StringVar(value="1.5")
        self.subtitle_strokewidth_menu = customtkinter.CTkOptionMenu(self.subtitle_style_frame, values=self.subtitle_strokewidth_options, variable=self.subtitle_strokewidth_var)
        self.subtitle_strokewidth_menu.grid(row=2, column=3, padx=5, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.subtitle_style_frame, text="Color Fondo Sub:").grid(row=3, column=0, padx=(10,0), pady=5, sticky="w")
        self.subtitle_bgcolor_entry = customtkinter.CTkEntry(self.subtitle_style_frame, placeholder_text="transparent, rgba(0,0,0,0.5)"); self.subtitle_bgcolor_entry.insert(0, "rgba(0,0,0,0.4)")
        self.subtitle_bgcolor_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.burn_subtitles_button = customtkinter.CTkButton(
            self.subtitle_style_frame, text="2. Grabar Subtítulos en Video", command=self.process_burn_subtitles_threaded) # Threaded
        self.burn_subtitles_button.grid(row=3, column=2, columnspan=2, padx=10, pady=10, sticky="ew")

        # --- Sección 8: Estado --- 
        self.status_frame = customtkinter.CTkFrame(self) 
        self.status_frame.grid(row=7, column=0, padx=10, pady=(5,10), sticky="ew")
        self.status_label = customtkinter.CTkLabel(self.status_frame, text="Estado: Listo. ¡Bienvenido!")
        self.status_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

    # --- Métodos de la App ---
    def check_queue_for_updates(self):
        try:
            callback = self.task_queue.get(block=False)
            if callable(callback): callback()
            self.task_queue.task_done()
        except queue.Empty: pass
        finally: self.after(100, self.check_queue_for_updates)

    def _get_all_action_buttons(self):
        return [self.reddit_fetch_button, self.generate_ai_story_button, self.generate_audio_button,
                self.generate_final_video_button, self.generate_srt_button, self.burn_subtitles_button]

    def _disable_primary_action_buttons(self):
        for button in self._get_all_action_buttons():
            if button.winfo_exists(): button.configure(state="disabled")

    def _enable_primary_action_buttons(self):
        for button in self._get_all_action_buttons():
            if button.winfo_exists(): button.configure(state="normal")
        if not self.can_generate_audio and hasattr(self, 'generate_audio_button') and self.generate_audio_button.winfo_exists():
             self.generate_audio_button.configure(state="disabled")

    def update_selected_voice_technical_name(self, selected_friendly_name: str):
        if self.can_generate_audio:
            self.selected_voice_technical_name = self.available_voices_map.get(selected_friendly_name)
            self.status_label.configure(text=f"Voz seleccionada: {selected_friendly_name}")

    # --- Reddit Fetch (Threaded) ---
    def _reddit_fetch_worker(self, url: str):
        try:
            title, body = reddit_scraper.get_post_details(url)
            self.task_queue.put(lambda t=title, b=body: self._update_gui_after_reddit_fetch(t, b))
        except Exception as e:
            error_msg = f"Error en hilo Reddit: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.task_queue.put(lambda: self._update_gui_after_reddit_fetch(None, None, error_msg=str(e)))
            
    def _update_gui_after_reddit_fetch(self, title: str, body: str, error_msg: str = None):
        self.story_textbox.delete("1.0", "end")
        if error_msg:
            self.story_textbox.insert("1.0", f"Error obteniendo post de Reddit:\n{error_msg}")
            self.status_label.configure(text="Error crítico al obtener post de Reddit.")
        elif "Error" in title or "no encontrado" in title or (title == "Título no encontrado." and body == "Cuerpo del post no encontrado."): 
            full_story = f"{title}\n\n{body}" 
            self.story_textbox.insert("1.0", full_story)
            self.status_label.configure(text="Error al obtener historia de Reddit o post no textual.")
        else:
            full_story = f"{title}\n\n{body}"
            self.story_textbox.insert("1.0", full_story)
            self.status_label.configure(text="Historia de Reddit cargada.")
        self._enable_primary_action_buttons()

    def fetch_reddit_post_threaded(self):
        url = self.reddit_url_entry.get()
        if not url:
            self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", "Error: URL de Reddit vacía.")
            self.status_label.configure(text="Error: URL de Reddit vacía."); return
        
        self.status_label.configure(text="Obteniendo post de Reddit (en hilo)..."); self.update_idletasks()
        self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", "Cargando..."); self.update_idletasks() 
        self._disable_primary_action_buttons()
        thread = threading.Thread(target=self._reddit_fetch_worker, args=(url,), daemon=True)
        thread.start()

    # --- AI Story Generation (Threaded - ya implementado) ---
    def _ai_story_worker(self, subject: str, style: str, max_tokens: int):
        try:
            generated_story_text = ai_story_generator.generate_story(subject, style, max_tokens)
            self.task_queue.put(lambda s=generated_story_text: self._update_gui_after_ai_story(s, is_error=False))
        except Exception as e:
            error_msg = f"Error en el hilo de IA: {str(e)}\n{traceback.format_exc()}"; print(error_msg)
            self.task_queue.put(lambda: self._update_gui_after_ai_story(f"Error generando historia: {str(e)}", is_error=True))

    def _update_gui_after_ai_story(self, story_or_error_message: str, is_error: bool):
        self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", story_or_error_message)
        if is_error: self.status_label.configure(text="IA: Error al generar historia.")
        else:
            if story_or_error_message.startswith("Error:"): self.status_label.configure(text=f"IA: {story_or_error_message}")
            else: self.status_label.configure(text="IA: ¡Historia en INGLÉS generada!")
        self._enable_primary_action_buttons()

    def process_ai_story_generation_threaded(self):
        subject = self.ai_subject_entry.get().strip(); style = self.ai_style_entry.get().strip()
        if not subject or not style: self.status_label.configure(text="Error IA: Ingresa Tema y Estilo."); return
        try: max_tokens = int(self.ai_max_tokens_menu_var.get())
        except ValueError: self.status_label.configure(text="Error IA: Tokens inválido."); return
        self.status_label.configure(text="IA: Iniciando generación (hilo)..."); self.update_idletasks()
        self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", "Generando IA (hilo)..."); self.update_idletasks() 
        self._disable_primary_action_buttons()
        thread = threading.Thread(target=self._ai_story_worker, args=(subject, style, max_tokens), daemon=True)
        thread.start()
            
    # --- TTS (Threaded - ya implementado) ---
    def _tts_worker(self, story_text: str, technical_voice_name: str, output_filename: str):
        try:
            success = tts_kokoro_module.generate_speech_with_voice_name(story_text, technical_voice_name, output_filename)
            self.task_queue.put(lambda s=success, f=output_filename: self._update_gui_after_tts(s, f))
        except Exception as e:
            error_msg = f"Error en hilo TTS: {str(e)}\n{traceback.format_exc()}"; print(error_msg)
            self.task_queue.put(lambda: self._update_gui_after_tts(False, output_filename, error_msg=str(e)))

    def _update_gui_after_tts(self, success: bool, output_audio_filename: str, error_msg: str = None):
        if success:
            self.generated_audio_path = os.path.abspath(output_audio_filename) 
            self.status_label.configure(text=f"¡Audio generado!: {self.generated_audio_path}")
        else:
            self.generated_audio_path = None
            err_disp = error_msg if error_msg else "Error al generar audio (consola)."
            self.status_label.configure(text=err_disp)
        self._enable_primary_action_buttons()

    def process_text_to_speech_threaded(self): 
        if not self.can_generate_audio or not self.selected_voice_technical_name: self.status_label.configure(text="Error: Voz TTS no válida."); return
        story_text = self.story_textbox.get("1.0", "end-1c").strip() 
        placeholders = ["Aquí aparecerá la historia...", "Cargando...", "Generando historia..."]
        is_placeholder = any(story_text.startswith(p_start) for p_start in placeholders if p_start)
        if not story_text or is_placeholder: self.status_label.configure(text="Error: No hay texto válido para TTS."); return
        
        selected_friendly_name = self.tts_voice_menu_var.get()
        self.status_label.configure(text=f"TTS: Iniciando con '{selected_friendly_name}' (hilo)..."); self.update_idletasks()
        output_audio_filename = "historia_narrada.wav" 
        self._disable_primary_action_buttons()
        thread = threading.Thread(target=self._tts_worker, args=(story_text, self.selected_voice_technical_name, output_audio_filename), daemon=True)
        thread.start()

    def select_background_video(self):
        filetypes = (("Archivos de Video", "*.mp4 *.mov *.avi *.mkv"),("Todos los archivos", "*.*")) 
        filepath = filedialog.askopenfilename(title="Selecciona un video de fondo", filetypes=filetypes)
        if filepath:
            self.background_video_path = filepath; filename = os.path.basename(filepath) 
            self.selected_video_label.configure(text=filename)
            self.status_label.configure(text=f"Video de fondo: {filename}")
        else:
            self.background_video_path = None; self.selected_video_label.configure(text="Video no seleccionado")

    # --- Video Generation (Threaded) ---
    def _video_generation_worker(self, bg_video_path: str, audio_path: str, output_filename: str):
        try:
            success = video_processor.create_narrated_video(bg_video_path, audio_path, output_filename)
            self.task_queue.put(lambda s=success, f=output_filename: self._update_gui_after_video_generation(s, f))
        except Exception as e:
            error_msg = f"Error en hilo VideoGen: {str(e)}\n{traceback.format_exc()}"; print(error_msg)
            self.task_queue.put(lambda: self._update_gui_after_video_generation(False, output_filename, error_msg=str(e)))

    def _update_gui_after_video_generation(self, success: bool, output_filename: str, error_msg: str = None):
        if success:
            self.narrated_video_path = os.path.abspath(output_filename) 
            self.status_label.configure(text=f"¡Video narrado generado!: {self.narrated_video_path}")
        else:
            self.narrated_video_path = None
            err_disp = error_msg if error_msg else "Error al generar video narrado."
            self.status_label.configure(text=err_disp)
        self._enable_primary_action_buttons()
        
    def process_final_video_generation_threaded(self): 
        if not self.generated_audio_path or not os.path.exists(self.generated_audio_path): self.status_label.configure(text="Error: Primero genera el audio."); return
        if not self.background_video_path or not os.path.exists(self.background_video_path): self.status_label.configure(text="Error: Selecciona video de fondo."); return
        
        self.status_label.configure(text="VideoGen: Iniciando (hilo)... Puede tardar."); self.update_idletasks()
        output_filename = "video_final_narrado.mp4"
        self._disable_primary_action_buttons()
        thread = threading.Thread(target=self._video_generation_worker, args=(self.background_video_path, self.generated_audio_path, output_filename), daemon=True)
        thread.start()

    # --- SRT Generation (Threaded) ---
    def _srt_generation_worker(self, audio_path: str, output_filename: str, max_words: int | None):
        try:
            success = srt_generator.create_srt_file(audio_path, output_filename, max_words_per_segment=max_words)
            self.task_queue.put(lambda s=success, f=output_filename: self._update_gui_after_srt_generation(s,f))
        except Exception as e:
            error_msg = f"Error en hilo SRT: {str(e)}\n{traceback.format_exc()}"; print(error_msg)
            self.task_queue.put(lambda: self._update_gui_after_srt_generation(False, output_filename, error_msg=str(e)))

    def _update_gui_after_srt_generation(self, success: bool, output_filename: str, error_msg: str = None):
        if success:
            self.generated_srt_path = os.path.abspath(output_filename) 
            self.status_label.configure(text=f"¡SRT generado!: {self.generated_srt_path}")
        else:
            self.generated_srt_path = None
            err_disp = error_msg if error_msg else "Error al generar SRT."
            self.status_label.configure(text=err_disp)
        self._enable_primary_action_buttons()

    def process_srt_generation_threaded(self): 
        if not self.generated_audio_path or not os.path.exists(self.generated_audio_path): self.status_label.configure(text="Error SRT: Primero genera audio."); return
        max_words_str = self.srt_max_words_var.get()
        max_words_value = None 
        if max_words_str.isdigit(): max_words_value = int(max_words_str)
        elif max_words_str != "Whisper (Defecto)": self.status_label.configure(text="Error SRT: 'Palabras Máx.' inválido."); return
        
        self.status_label.configure(text="SRT: Iniciando generación (hilo)..."); self.update_idletasks()
        audio_basename = os.path.splitext(os.path.basename(self.generated_audio_path))[0]
        output_srt_filename = f"{audio_basename}.srt" 
        self._disable_primary_action_buttons()
        thread = threading.Thread(target=self._srt_generation_worker, args=(self.generated_audio_path, output_srt_filename, max_words_value), daemon=True)
        thread.start()
            
    # --- Burn Subtitles (Threaded) ---
    def _burn_subtitles_worker(self, narrated_video_p: str, srt_p: str, output_filename: str, style_opts: dict):
        try:
            success = video_processor.burn_subtitles_on_video(narrated_video_p, srt_p, output_filename, style_options=style_opts)
            self.task_queue.put(lambda s=success, f=output_filename: self._update_gui_after_burn_subtitles(s,f))
        except Exception as e:
            error_msg = f"Error en hilo SubBurn: {str(e)}\n{traceback.format_exc()}"; print(error_msg)
            self.task_queue.put(lambda: self._update_gui_after_burn_subtitles(False, output_filename, error_msg=str(e)))

    def _update_gui_after_burn_subtitles(self, success: bool, output_filename: str, error_msg: str = None):
        if success:
            full_path = os.path.abspath(output_filename)
            self.status_label.configure(text=f"¡Video con subtítulos grabados!: {full_path}")
        else:
            err_disp = error_msg if error_msg else "Error al grabar subtítulos."
            self.status_label.configure(text=err_disp)
        self._enable_primary_action_buttons()

    def process_burn_subtitles_threaded(self): 
        if not self.narrated_video_path or not os.path.exists(self.narrated_video_path): self.status_label.configure(text="Error Sub Burn: Genera 'Video Narrado'."); return
        if not self.generated_srt_path or not os.path.exists(self.generated_srt_path): self.status_label.configure(text="Error Sub Burn: Genera '.SRT'."); return
        try:
            style_options = { 
                'font': self.subtitle_font_var.get(), 'fontsize': int(self.subtitle_fontsize_var.get()),
                'color': self.subtitle_color_entry.get() or 'white', 'stroke_color': self.subtitle_strokecolor_entry.get() or 'black',
                'stroke_width': float(self.subtitle_strokewidth_var.get()), 'bg_color': self.subtitle_bgcolor_entry.get() or 'rgba(0,0,0,0.5)',
                'position_choice': self.subtitle_pos_var.get() }
        except ValueError: self.status_label.configure(text="Error Sub Burn: Valor inválido en estilo."); return
        
        video_basename = os.path.splitext(os.path.basename(self.narrated_video_path))[0]
        output_filename = f"{video_basename}_con_subtitulos.mp4"
        self.status_label.configure(text="SubBurn: Iniciando (hilo)... Puede tardar mucho."); self.update_idletasks()
        self._disable_primary_action_buttons()
        thread = threading.Thread(target=self._burn_subtitles_worker, args=(self.narrated_video_path, self.generated_srt_path, output_filename, style_options), daemon=True)
        thread.start()

if __name__ == "__main__":
    app = App()
    app.mainloop()