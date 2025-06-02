# main.py
import customtkinter
from customtkinter import filedialog, CTkImage
from PIL import Image 
import os
import traceback
import threading 
import queue     
from tkinter import colorchooser 
from playsound import playsound 

# Importar tus módulos personalizados
import reddit_scraper
import tts_kokoro_module 
import ai_story_generator 
import video_processor 
import srt_generator 
import file_manager 

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("blue")

VOICE_SAMPLE_DIR = "voice_samples" 
MAX_THUMBNAILS_MAIN_GUI = 6 
THUMBNAIL_GRID_COLUMNS = 3
VIDEO_PREVIEW_THUMBNAIL_SIZE = (360, 640)
SUBTITLE_PREVIEW_IMAGE_PATH = "_subtitle_preview_temp.png" # Usado por video_processor

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Reddit Story Video Creator v2.5") 
        self.geometry("1250x800")

        # --- Definición inicial de variables de instancia ---
        self.background_video_path = None
        self.can_generate_audio = False
        self.selected_voice_technical_name = None
        
        self.subtitle_font_color_hex = "#FFFF00"     
        self.subtitle_stroke_color_hex = "#000000"   
        
        self.all_video_templates = [] 
        self.current_thumbnail_widgets_main = [] # Para los widgets en la rejilla principal
        
        self.video_preview_ctk_image = None # Para la imagen del video en el panel derecho
        self.combined_preview_ctk_image = None # Para la imagen combinada en el panel derecho

        self.task_queue = queue.Queue()
        self.after(100, self.check_queue_for_updates) 

        file_manager.ensure_directories_exist()
        
        # --- Configuración del Grid Principal de la App (2 columnas) ---
        self.grid_columnconfigure(0, weight=2) 
        self.grid_columnconfigure(1, weight=1) 
        self.grid_rowconfigure(0, weight=1)  

        # --- Panel Izquierdo (Desplazable) para Controles ---
        self.left_scrollable_frame = customtkinter.CTkScrollableFrame(self, label_text="Configuración y Acciones")
        self.left_scrollable_frame.grid(row=0, column=0, padx=(10,5), pady=10, sticky="nsew")
        self.left_scrollable_frame.grid_columnconfigure(0, weight=1) 

        # --- Panel Derecho (Estático) para Previsualizaciones ---
        self.right_pane = customtkinter.CTkFrame(self, fg_color="gray18", width=VIDEO_PREVIEW_THUMBNAIL_SIZE[0] + 40) # Ancho un poco mayor que la miniatura
        self.right_pane.grid(row=0, column=1, padx=(5,10), pady=10, sticky="nsew")
        self.right_pane.grid_propagate(False) 
        self.right_pane.grid_columnconfigure(0, weight=1)
        self.right_pane.grid_rowconfigure(0, weight=1) # Para la previsualización combinada

        # --- CREACIÓN DE TODOS LOS WIDGETS ---

        # Sección 1: Entrada de Texto (Reddit o Manual) - en left_scrollable_frame
        self.input_frame = customtkinter.CTkFrame(self.left_scrollable_frame)
        self.input_frame.pack(fill="x", expand=False, padx=5, pady=5) 
        self.input_frame.grid_columnconfigure(1, weight=1)
        customtkinter.CTkLabel(self.input_frame, text="URL de Reddit:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.reddit_url_entry = customtkinter.CTkEntry(self.input_frame, placeholder_text="Pega aquí la URL de un post de Reddit...")
        self.reddit_url_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.reddit_fetch_button = customtkinter.CTkButton(self.input_frame, text="Obtener Historia", command=self.fetch_reddit_post_threaded)
        self.reddit_fetch_button.grid(row=0, column=2, padx=10, pady=10)

        # Sección 2: Generación de Historia con IA - en left_scrollable_frame
        self.ai_story_config_frame = customtkinter.CTkFrame(self.left_scrollable_frame)
        self.ai_story_config_frame.pack(fill="x", expand=False, padx=5, pady=5)
        self.ai_story_config_frame.grid_columnconfigure(1, weight=1) 
        customtkinter.CTkLabel(self.ai_story_config_frame, text="Tema Historia IA (Inglés):").grid(row=0, column=0, padx=(10,0), pady=5, sticky="w")
        self.ai_subject_entry = customtkinter.CTkEntry(self.ai_story_config_frame, placeholder_text="Ej: alien encounter")
        self.ai_subject_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew") 
        customtkinter.CTkLabel(self.ai_story_config_frame, text="Estilo Historia IA (Inglés):").grid(row=1, column=0, padx=(10,0), pady=5, sticky="w")
        self.ai_style_entry = customtkinter.CTkEntry(self.ai_story_config_frame, placeholder_text="Ej: r/nosleep, comedy")
        self.ai_style_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="ew") 
        customtkinter.CTkLabel(self.ai_story_config_frame, text="Tokens Máx. IA:").grid(row=2, column=0, padx=(10,0), pady=5, sticky="w")
        self.max_tokens_options = ["200", "300", "400", "500"] 
        self.ai_max_tokens_menu_var = customtkinter.StringVar(value=self.max_tokens_options[1]) 
        self.ai_max_tokens_menu = customtkinter.CTkOptionMenu(self.ai_story_config_frame, values=self.max_tokens_options, variable=self.ai_max_tokens_menu_var)
        self.ai_max_tokens_menu.grid(row=2, column=1, padx=10, pady=5, sticky="w") 
        self.generate_ai_story_button = customtkinter.CTkButton(self.ai_story_config_frame, text="Generar Historia con IA", command=self.process_ai_story_generation_threaded)
        self.generate_ai_story_button.grid(row=2, column=2, padx=10, pady=5, sticky="e")

        # Sección 3: Selección de Voz TTS - en left_scrollable_frame
        self.tts_config_frame = customtkinter.CTkFrame(self.left_scrollable_frame)
        self.tts_config_frame.pack(fill="x", expand=False, padx=5, pady=5)
        self.tts_config_frame.grid_columnconfigure(1, weight=1); self.tts_config_frame.grid_columnconfigure(2, weight=0) 
        customtkinter.CTkLabel(self.tts_config_frame, text="Voz TTS:").grid(row=0, column=0, padx=(10,5), pady=10, sticky="w")
        self.available_voices_map = tts_kokoro_module.list_available_kokoro_voices()
        self.voice_friendly_names = list(self.available_voices_map.keys())
        default_voice_friendly = self.voice_friendly_names[0] if self.voice_friendly_names else "No hay voces"
        self.selected_voice_technical_name = self.available_voices_map.get(default_voice_friendly)
        self.can_generate_audio = bool(self.selected_voice_technical_name)
        self.tts_voice_menu_var = customtkinter.StringVar(value=default_voice_friendly)
        self.tts_voice_menu = customtkinter.CTkOptionMenu(self.tts_config_frame, values=self.voice_friendly_names, variable=self.tts_voice_menu_var, command=self.update_selected_voice_technical_name)
        self.tts_voice_menu.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        if not self.can_generate_audio: self.tts_voice_menu.configure(state="disabled")
        self.test_voice_button = customtkinter.CTkButton(self.tts_config_frame, text="Probar Voz", width=100, command=self.play_voice_sample_threaded)
        self.test_voice_button.grid(row=0, column=2, padx=(10,5), pady=10, sticky="w")
        if not self.can_generate_audio: self.test_voice_button.configure(state="disabled")

        # Sección 3.5: Selección de Video de Fondo con Miniaturas - en left_scrollable_frame
        self.video_template_selection_frame = customtkinter.CTkFrame(self.left_scrollable_frame)
        self.video_template_selection_frame.pack(fill="x", expand=False, padx=5, pady=5)
        self.video_template_selection_frame.grid_columnconfigure(0, weight=1)
        customtkinter.CTkLabel(self.video_template_selection_frame, text="Video de Fondo (Plantillas):", font=("Arial", 14, "bold")).grid(row=0, column=0, padx=10, pady=(10,0), sticky="w")
        self.active_video_display_label = customtkinter.CTkLabel(self.video_template_selection_frame, text="Seleccionado: Ninguno", wraplength=400) 
        self.active_video_display_label.grid(row=1, column=0, padx=10, pady=(0,5), sticky="w")
        self.thumbnail_grid_frame = customtkinter.CTkFrame(self.video_template_selection_frame, fg_color="transparent")
        self.thumbnail_grid_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.view_all_videos_button = customtkinter.CTkButton(self.video_template_selection_frame, text="Ver Todas las Plantillas de Video...", command=self.open_view_all_videos_popup)
        self.view_all_videos_button.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        
        # Sección 4: Configuración de Subtítulos (SRT y Estilo) - en left_scrollable_frame
        self.srt_style_frame = customtkinter.CTkFrame(self.left_scrollable_frame)
        self.srt_style_frame.pack(fill="x", expand=False, padx=5, pady=5)
        self.srt_style_frame.grid_columnconfigure(1, weight=1); self.srt_style_frame.grid_columnconfigure(3, weight=1)
        customtkinter.CTkLabel(self.srt_style_frame, text="Palabras Máx./SRT:").grid(row=0, column=0, padx=(10,0), pady=5, sticky="w")
        self.srt_max_words_options = ["Whisper (Defecto)", "1", "2", "3", "4", "5", "6", "7"]
        self.srt_max_words_var = customtkinter.StringVar(value="3") 
        self.srt_max_words_menu = customtkinter.CTkOptionMenu(self.srt_style_frame, values=self.srt_max_words_options, variable=self.srt_max_words_var)
        self.srt_max_words_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.srt_style_frame, text="Posición Subs:").grid(row=0, column=2, padx=(10,0), pady=5, sticky="w")
        self.subtitle_pos_options = ["Abajo", "Centro", "Arriba"]
        self.subtitle_pos_var = customtkinter.StringVar(value="Abajo")
        self.subtitle_pos_menu = customtkinter.CTkOptionMenu(self.srt_style_frame, values=self.subtitle_pos_options, variable=self.subtitle_pos_var, command=self.update_subtitle_preview_display)
        self.subtitle_pos_menu.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.srt_style_frame, text="Fuente Sub:").grid(row=1, column=0, padx=(10,0), pady=5, sticky="w")
        self.subtitle_font_options = ["Arial", "Verdana", "Times New Roman", "Impact", "Courier New", "Tahoma", "Georgia"]
        self.subtitle_font_var = customtkinter.StringVar(value="Arial")
        self.subtitle_font_menu = customtkinter.CTkOptionMenu(self.srt_style_frame, values=self.subtitle_font_options, variable=self.subtitle_font_var, command=self.update_subtitle_preview_display)
        self.subtitle_font_menu.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.srt_style_frame, text="Tamaño Fuente:").grid(row=1, column=2, padx=(10,0), pady=5, sticky="w")
        self.subtitle_fontsize_options = ["18", "20", "22", "24", "26", "28", "30", "32", "36", "40", "44", "48", "52", "56", "60", "64", "72"]
        self.subtitle_fontsize_var = customtkinter.StringVar(value="36")
        self.subtitle_fontsize_menu = customtkinter.CTkOptionMenu(self.srt_style_frame, values=self.subtitle_fontsize_options, variable=self.subtitle_fontsize_var, command=self.update_subtitle_preview_display)
        self.subtitle_fontsize_menu.grid(row=1, column=3, padx=5, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.srt_style_frame, text="Color Texto Sub:").grid(row=2, column=0, padx=(10,0), pady=5, sticky="w")
        self.subtitle_text_color_button = customtkinter.CTkButton(self.srt_style_frame, text="Elegir...", width=100, command=lambda: self.pick_color_for('text_fg'))
        self.subtitle_text_color_button.grid(row=2, column=1, padx=(5,0), pady=5, sticky="w")
        self.subtitle_text_color_preview = customtkinter.CTkFrame(self.srt_style_frame, width=60, height=28, fg_color=self.subtitle_font_color_hex, border_width=1, border_color="gray50")
        self.subtitle_text_color_preview.grid(row=2, column=1, padx=(120,5), pady=5, sticky="w")
        customtkinter.CTkLabel(self.srt_style_frame, text="Color Borde Sub:").grid(row=2, column=2, padx=(10,0), pady=5, sticky="w")
        self.subtitle_stroke_color_button = customtkinter.CTkButton(self.srt_style_frame, text="Elegir...", width=100, command=lambda: self.pick_color_for('stroke_fg'))
        self.subtitle_stroke_color_button.grid(row=2, column=3, padx=(5,0), pady=5, sticky="w")
        self.subtitle_stroke_color_preview = customtkinter.CTkFrame(self.srt_style_frame, width=60, height=28, fg_color=self.subtitle_stroke_color_hex, border_width=1, border_color="gray50")
        self.subtitle_stroke_color_preview.grid(row=2, column=3, padx=(120,5), pady=5, sticky="w")
        customtkinter.CTkLabel(self.srt_style_frame, text="Ancho Borde Sub:").grid(row=3, column=0, padx=(10,0), pady=5, sticky="w")
        self.subtitle_strokewidth_options = ["0", "0.5", "1", "1.5", "2", "2.5", "3", "3.5", "4", "4.5", "5"]
        self.subtitle_strokewidth_var = customtkinter.StringVar(value="1.5") 
        self.subtitle_strokewidth_menu = customtkinter.CTkOptionMenu(self.srt_style_frame, values=self.subtitle_strokewidth_options, variable=self.subtitle_strokewidth_var, command=self.update_subtitle_preview_display)
        self.subtitle_strokewidth_menu.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        customtkinter.CTkLabel(self.srt_style_frame, text="Fondo Sub:").grid(row=3, column=2, padx=(10,0), pady=5, sticky="w")
        self.subtitle_bgcolor_map = { "Transparente Total": "transparent", "Negro Semi (40%)": "rgba(0,0,0,0.4)", "Negro Semi (60%)": "rgba(0,0,0,0.6)", "Gris Semi (50%)": "rgba(128,128,128,0.5)", "Blanco (Opaco)": "white", "Negro (Opaco)": "black" }
        self.subtitle_bgcolor_options = list(self.subtitle_bgcolor_map.keys())
        self.subtitle_bgcolor_var = customtkinter.StringVar(value="Negro Semi (40%)") 
        self.subtitle_bgcolor_menu = customtkinter.CTkOptionMenu( self.srt_style_frame, values=self.subtitle_bgcolor_options, variable=self.subtitle_bgcolor_var, command=self.update_subtitle_preview_display)
        self.subtitle_bgcolor_menu.grid(row=3, column=3, padx=5, pady=5, sticky="ew")

        # Sección 5: Cuadro de Texto para la Historia - en left_scrollable_frame
        self.story_frame = customtkinter.CTkFrame(self.left_scrollable_frame)
        self.story_frame.pack(fill="both", expand=True, padx=5, pady=5) 
        self.story_frame.grid_columnconfigure(0, weight=1); self.story_frame.grid_rowconfigure(0, weight=1)
        self.story_textbox = customtkinter.CTkTextbox(self.story_frame, wrap="word", font=("Arial", 14)) 
        self.story_textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.story_textbox.insert("1.0", "1. Obtén/Genera una historia aquí.\n2. Configura Voz, Video Fondo y Subtítulos.\n3. Haz clic en 'CREAR VIDEO FINAL COMPLETO'.")

        # Sección 6: Botón de Acción Principal - en left_scrollable_frame
        self.main_action_frame = customtkinter.CTkFrame(self.left_scrollable_frame)
        self.main_action_frame.pack(fill="x", expand=False, padx=5, pady=5)
        self.main_action_frame.grid_columnconfigure(0, weight=1) 
        self.generate_all_button = customtkinter.CTkButton(
            self.main_action_frame, 
            text="CREAR VIDEO FINAL COMPLETO", 
            command=self.process_all_steps_threaded,
            height=40, font=("Arial", 14, "bold")
        )
        self.generate_all_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Sección 7: Estado - en left_scrollable_frame
        self.status_frame = customtkinter.CTkFrame(self.left_scrollable_frame) 
        self.status_frame.pack(fill="x", expand=False, padx=5, pady=5) 
        self.status_label = customtkinter.CTkLabel(self.status_frame, text="Estado: Listo. Configura y crea tu video.")
        self.status_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # --- Panel Derecho (Estático) para Previsualizaciones ---
        # (La creación del panel derecho ya se hizo arriba)
        # Widgets dentro del panel derecho:
        self.combined_preview_display_label = customtkinter.CTkLabel(
            self.right_pane, text="Previsualización Aquí", font=("Arial", 12), fg_color="gray25")
        self.combined_preview_display_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")


        # --- LLAMADAS FINALES EN __init__ DESPUÉS DE CREAR TODOS LOS WIDGETS ---
        self._load_video_templates_list() 
        self.refresh_main_thumbnail_grid() # Esto actualiza la lista de miniaturas y la preview grande
        self.update_subtitle_preview_display() # Para la preview inicial de subtítulos

    # --- Métodos de la App (check_queue, enable/disable buttons, etc.) ---
    def check_queue_for_updates(self):
        try:
            callback = self.task_queue.get(block=False)
            if callable(callback): callback()
            self.task_queue.task_done()
        except queue.Empty: pass
        finally: self.after(100, self.check_queue_for_updates)

    def _get_main_action_buttons_for_state_management(self):
        buttons = [self.generate_all_button]
        if hasattr(self, 'reddit_fetch_button'): buttons.append(self.reddit_fetch_button)
        if hasattr(self, 'generate_ai_story_button'): buttons.append(self.generate_ai_story_button)
        return buttons

    def _disable_main_action_button(self):
        for button in self._get_main_action_buttons_for_state_management():
            if button.winfo_exists(): button.configure(state="disabled")
        if hasattr(self, 'test_voice_button') and self.test_voice_button.winfo_exists():
            self.test_voice_button.configure(state="disabled")

    def _enable_main_action_button(self):
        for button in self._get_main_action_buttons_for_state_management():
            if button.winfo_exists(): button.configure(state="normal")
        if hasattr(self, 'test_voice_button') and self.test_voice_button.winfo_exists():
            if self.can_generate_audio: self.test_voice_button.configure(state="normal")
            else: self.test_voice_button.configure(state="disabled")

    def update_selected_voice_technical_name(self, selected_friendly_name: str):
        if self.can_generate_audio:
            self.selected_voice_technical_name = self.available_voices_map.get(selected_friendly_name)
            self.status_label.configure(text=f"Voz TTS seleccionada: {selected_friendly_name}")
            self.update_subtitle_preview_display() 

    def pick_color_for(self, color_target: str):
        initial_color = None
        if color_target == 'text_fg': initial_color = self.subtitle_font_color_hex
        elif color_target == 'stroke_fg': initial_color = self.subtitle_stroke_color_hex
        
        color_info = colorchooser.askcolor(initialcolor=initial_color, title=f"Selecciona color")
        if color_info and color_info[1]:
            hex_color = color_info[1]
            if color_target == 'text_fg':
                self.subtitle_font_color_hex = hex_color
                if hasattr(self, 'subtitle_text_color_preview'): self.subtitle_text_color_preview.configure(fg_color=hex_color)
                self.status_label.configure(text=f"Color texto subs: {hex_color}")
            elif color_target == 'stroke_fg':
                self.subtitle_stroke_color_hex = hex_color
                if hasattr(self, 'subtitle_stroke_color_preview'): self.subtitle_stroke_color_preview.configure(fg_color=hex_color)
                self.status_label.configure(text=f"Color borde subs: {hex_color}")
            self.update_subtitle_preview_display()
        else:
            self.status_label.configure(text=f"Selección de color cancelada.")

    def _load_video_templates_list(self):
        self.all_video_templates = video_processor.list_video_templates()
        if not self.all_video_templates:
            print("Advertencia: No se encontraron videos en 'video_templates'.")
            if hasattr(self, 'active_video_display_label'): self.active_video_display_label.configure(text="Carpeta 'video_templates' vacía.")
            self.current_video_thumbnail_for_composite_path = None # No hay video para preview
            self.update_subtitle_preview_display() # Actualizar preview (mostrará mensaje de no video)
        elif not self.background_video_path: # Si no hay video seleccionado y hay plantillas
             if hasattr(self, 'active_video_display_label'):
                self._select_video_from_thumbnail_internal(self.all_video_templates[0]) # Seleccionar el primero

    def _display_thumbnails_in_grid(self, parent_frame, video_paths_to_display, max_items_to_show=None, from_popup=False, popup_window_ref=None):
        for widget in parent_frame.winfo_children(): widget.destroy()
        if not from_popup: self.current_thumbnail_widgets_main = []
        videos_to_render = video_paths_to_display
        if max_items_to_show is not None and len(video_paths_to_display) > max_items_to_show:
            videos_to_render = video_paths_to_display[:max_items_to_show]
        row, col = 0, 0
        for video_path in videos_to_render:
            thumb_path = video_processor.get_or_create_thumbnail(video_path) 
            if thumb_path:
                try:
                    pil_image = Image.open(thumb_path)
                    max_thumb_w, max_thumb_h = 128, 227 
                    pil_image.thumbnail((max_thumb_w, max_thumb_h), Image.Resampling.LANCZOS)
                    ctk_image = CTkImage(light_image=pil_image, dark_image=pil_image, size=(pil_image.width, pil_image.height)) 
                    item_frame = customtkinter.CTkFrame(parent_frame, fg_color="transparent")
                    item_frame.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
                    thumb_button = customtkinter.CTkButton(item_frame, image=ctk_image, text="", width=pil_image.width, height=pil_image.height, fg_color="transparent", hover_color="gray50", command=lambda vp=video_path, pop_ref=popup_window_ref: self._select_video_from_thumbnail_internal(vp, from_popup, pop_ref))
                    thumb_button.pack(pady=(0,1))
                    filename_label = customtkinter.CTkLabel(item_frame, text=os.path.basename(video_path), font=("Arial", 9), wraplength=pil_image.width)
                    filename_label.pack(fill="x")
                    if not from_popup: self.current_thumbnail_widgets_main.append(thumb_button)
                except Exception as e:
                    print(f"Error al cargar/mostrar miniatura {thumb_path}: {e}"); error_label = customtkinter.CTkLabel(parent_frame, text=f"Err\n{os.path.basename(video_path)}", width=128, height=200, fg_color="gray20"); error_label.grid(row=row, column=col, padx=5, pady=5)
            col += 1
            if col >= THUMBNAIL_GRID_COLUMNS: col = 0; row += 1
        for i in range(THUMBNAIL_GRID_COLUMNS): parent_frame.grid_columnconfigure(i, weight=1)

    def _select_video_from_thumbnail_internal(self, video_path: str, from_popup: bool = False, popup_window_ref: customtkinter.CTkToplevel = None):
        self.background_video_path = video_path # Video seleccionado para el proceso final
        filename = os.path.basename(video_path)
        if hasattr(self, 'active_video_display_label'): 
            self.active_video_display_label.configure(text=f"Seleccionado: {filename}")
        self.status_label.configure(text=f"Video de fondo cambiado a: {filename}")
        
        # Asegurar que la miniatura para la COMPOSICIÓN se genere con VIDEO_PREVIEW_THUMBNAIL_SIZE
        thumb_path = video_processor.get_or_create_thumbnail(
            video_path, 
            size=VIDEO_PREVIEW_THUMBNAIL_SIZE # <--- Usar el tamaño grande consistentemente
        )
        self.current_video_thumbnail_for_composite_path = thumb_path 
        
        self.update_subtitle_preview_display() # Regenerar la imagen compuesta

        if from_popup and popup_window_ref:
            popup_window_ref.destroy()
            self.refresh_main_thumbnail_grid(newly_selected_path=video_path)

    def refresh_main_thumbnail_grid(self, newly_selected_path: str = None):
        if not hasattr(self, 'thumbnail_grid_frame'): return 
        # self._load_video_templates_list() # Ya se llama en __init__, no es necesario aquí a menos que los archivos cambien dinámicamente
        videos_to_show_on_main = list(self.all_video_templates) 
        current_selection_for_display = newly_selected_path if newly_selected_path else self.background_video_path
        if current_selection_for_display and current_selection_for_display in videos_to_show_on_main:
            videos_to_show_on_main.remove(current_selection_for_display); videos_to_show_on_main.insert(0, current_selection_for_display)
        elif self.all_video_templates and not self.background_video_path : # Si no hay nada seleccionado, pero hay videos
            self._select_video_from_thumbnail_internal(self.all_video_templates[0]) # Seleccionar el primero
            # Y ahora videos_to_show_on_main también tendrá el primer video al inicio
            if self.all_video_templates[0] in videos_to_show_on_main: # Reordenar si es necesario tras la selección
                videos_to_show_on_main.remove(self.all_video_templates[0])
                videos_to_show_on_main.insert(0, self.all_video_templates[0])

        self._display_thumbnails_in_grid(self.thumbnail_grid_frame, videos_to_show_on_main, max_items_to_show=MAX_THUMBNAILS_MAIN_GUI)
        if not self.background_video_path and self.all_video_templates: # Si después de todo no hay video seleccionado
            self.update_subtitle_preview_display() # Llamar para que muestre "Selecciona un video"


    def open_view_all_videos_popup(self):
        if not self.all_video_templates: self.status_label.configure(text="No hay videos en 'video_templates'."); return
        popup = customtkinter.CTkToplevel(self); popup.geometry("750x600"); popup.title("Todas las Plantillas de Video"); popup.attributes("-topmost", True)
        popup_main_frame = customtkinter.CTkFrame(popup); popup_main_frame.pack(expand=True, fill="both", padx=5, pady=5)
        customtkinter.CTkLabel(popup_main_frame, text="Haz clic en una miniatura para seleccionar el video:", font=("Arial",12)).pack(pady=(5,5))
        scrollable_frame = customtkinter.CTkScrollableFrame(popup_main_frame); scrollable_frame.pack(expand=True, fill="both", padx=5, pady=5)
        for i in range(THUMBNAIL_GRID_COLUMNS): scrollable_frame.grid_columnconfigure(i, weight=1) 
        self._display_thumbnails_in_grid(scrollable_frame, self.all_video_templates, max_items_to_show=len(self.all_video_templates), from_popup=True, popup_window_ref=popup)
        customtkinter.CTkButton(popup_main_frame, text="Cerrar", command=popup.destroy, width=100).pack(pady=10)

    def update_subtitle_preview_display(self, _=None): 
        if not hasattr(self, 'combined_preview_display_label'): return

        try:
            style_opts = self._get_current_subtitle_style_options()
            preview_text = "This is a test subtitle"
            
            # El ancho del TextClip del subtítulo puede ser un poco menor que el de la miniatura del video
            preview_textclip_width = VIDEO_PREVIEW_THUMBNAIL_SIZE[0] - 40 
            if preview_textclip_width <= 20 : preview_textclip_width = VIDEO_PREVIEW_THUMBNAIL_SIZE[0] * 0.8 # Fallback

            if self.current_video_thumbnail_for_composite_path and os.path.exists(self.current_video_thumbnail_for_composite_path):
                style_opts['preview_subtitle_fixed_height'] = video_processor.PREVIEW_SUBTITLE_HEIGHT 
                style_opts['textclip_width_for_preview'] = preview_textclip_width
                
                composite_image_path = video_processor.create_composite_preview_image(
                    self.current_video_thumbnail_for_composite_path,
                    preview_text,
                    style_opts
                )
                if composite_image_path and os.path.exists(composite_image_path):
                    pil_image = Image.open(composite_image_path)
                    
                    # Forzar la imagen compuesta al tamaño de la previsualización de video
                    # Esto asegura que el combined_preview_display_label no cambie de tamaño.
                    # La imagen PIL ya tiene las dimensiones de VIDEO_PREVIEW_THUMBNAIL_SIZE
                    # porque create_composite_preview_image usa la miniatura base con ese tamaño.
                    self.combined_preview_ctk_image = CTkImage(
                        light_image=pil_image, 
                        dark_image=pil_image, 
                        size=(pil_image.width, pil_image.height) # Usar el tamaño de la imagen compuesta generada
                    )
                    self.combined_preview_display_label.configure(
                        image=self.combined_preview_ctk_image, 
                        text="",
                        width=VIDEO_PREVIEW_THUMBNAIL_SIZE[0], # Forzar ancho de etiqueta
                        height=VIDEO_PREVIEW_THUMBNAIL_SIZE[1] # Forzar alto de etiqueta
                    )
                else: 
                    self.combined_preview_display_label.configure(image=None, text="[Error generando preview compuesta]")
            else:
                # Si no hay video de fondo, podríamos generar solo el subtítulo y mostrarlo
                # o mantener el mensaje. Por ahora, mantenemos el mensaje.
                self.combined_preview_display_label.configure(image=None, text="Selecciona un video de fondo\npara ver la previsualización completa.", width=VIDEO_PREVIEW_THUMBNAIL_SIZE[0], height=VIDEO_PREVIEW_THUMBNAIL_SIZE[1])
        except Exception as e:
            print(f"Error actualizando previsualización: {e}"); traceback.print_exc()
            if hasattr(self, 'combined_preview_display_label'): 
                 self.combined_preview_display_label.configure(image=None, text="[Error Preview]", width=VIDEO_PREVIEW_THUMBNAIL_SIZE[0], height=VIDEO_PREVIEW_THUMBNAIL_SIZE[1])

    def _get_current_subtitle_style_options(self) -> dict:
        selected_bg_color_friendly = self.subtitle_bgcolor_var.get()
        actual_bg_color = self.subtitle_bgcolor_map.get(selected_bg_color_friendly, "rgba(0,0,0,0.4)")
        try: fontsize = int(self.subtitle_fontsize_var.get()); strokewidth = float(self.subtitle_strokewidth_var.get())
        except ValueError: fontsize = 36; strokewidth = 1.5; self.status_label.configure(text="Advertencia: Estilo de sub inválido, usando defaults.")
        return { 'font': self.subtitle_font_var.get(), 'fontsize': fontsize, 'color': self.subtitle_font_color_hex, 
                 'stroke_color': self.subtitle_stroke_color_hex, 'stroke_width': strokewidth, 'bg_color': actual_bg_color, 
                 'position_choice': self.subtitle_pos_var.get() }

    # --- Reddit Fetch (Threaded) ---
    def _reddit_fetch_worker(self, url: str): #OK
        try: title, body = reddit_scraper.get_post_details(url); self.task_queue.put(lambda t=title, b=body: self._update_gui_after_reddit_fetch(t, b))
        except Exception as e: error_msg = f"Error Reddit: {str(e)}"; print(error_msg); traceback.print_exc(); self.task_queue.put(lambda: self._update_gui_after_reddit_fetch(None, None, error_msg=str(e)))
    def _update_gui_after_reddit_fetch(self, title: str | None, body: str | None, error_msg: str = None): #OK
        self.story_textbox.delete("1.0", "end")
        if error_msg: self.story_textbox.insert("1.0", f"Error obteniendo post:\n{error_msg}"); self.status_label.configure(text="Error al obtener post de Reddit.")
        elif title is None or body is None or "Error" in title or "no encontrado" in title or (title == "Título no encontrado." and body == "Cuerpo del post no encontrado.") : 
            full_story = f"{title if title else 'Error'}\n\n{body if body else 'No contenido.'}"; self.story_textbox.insert("1.0", full_story); self.status_label.configure(text="Contenido de Reddit no estándar o error.")
        else: full_story = f"{title}\n\n{body}"; self.story_textbox.insert("1.0", full_story); self.status_label.configure(text="Historia Reddit cargada.")
        self._enable_main_action_button()
    def fetch_reddit_post_threaded(self): #OK
        url = self.reddit_url_entry.get()
        if not url: self.status_label.configure(text="Error: URL Reddit vacía."); return
        self.status_label.configure(text="Obteniendo post (hilo)..."); self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", "Cargando..."); self.update_idletasks() 
        self._disable_main_action_button(); thread = threading.Thread(target=self._reddit_fetch_worker, args=(url,), daemon=True); thread.start()

    # --- AI Story Generation (Threaded) ---
    def _ai_story_worker(self, subject: str, style: str, max_tokens: int): #OK
        try: generated_story_text = ai_story_generator.generate_story(subject, style, max_tokens); self.task_queue.put(lambda s=generated_story_text: self._update_gui_after_ai_story(s, is_error=False))
        except Exception as e: error_msg = f"Error IA: {str(e)}"; print(error_msg); traceback.print_exc(); self.task_queue.put(lambda: self._update_gui_after_ai_story(f"Error generando: {str(e)}", is_error=True))
    def _update_gui_after_ai_story(self, story_or_error_message: str, is_error: bool): #OK
        self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", story_or_error_message)
        if is_error: self.status_label.configure(text="IA: Error al generar.")
        else:
            if story_or_error_message.startswith("Error:"): self.status_label.configure(text=f"IA: {story_or_error_message}")
            else: self.status_label.configure(text="IA: ¡Historia INGLÉS generada!")
        self._enable_main_action_button()
    def process_ai_story_generation_threaded(self): #OK
        subject = self.ai_subject_entry.get().strip(); style = self.ai_style_entry.get().strip()
        if not subject or not style: self.status_label.configure(text="Error IA: Ingresa Tema y Estilo."); return
        try: max_tokens = int(self.ai_max_tokens_menu_var.get())
        except ValueError: self.status_label.configure(text="Error IA: Tokens inválido."); return
        self.status_label.configure(text="IA: Iniciando (hilo)..."); self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", "Generando IA (hilo)..."); self.update_idletasks() 
        self._disable_main_action_button(); thread = threading.Thread(target=self._ai_story_worker, args=(subject, style, max_tokens), daemon=True); thread.start()
            
    # --- Funciones de prueba de voz (Threaded) ---
    def _play_audio_worker(self, audio_filepath: str, voice_friendly_name: str): #OK
        try: playsound(audio_filepath) 
        except Exception as e_play: print(f"TestVoice Error reproducción: {audio_filepath}: {e_play}"); traceback.print_exc(); self.task_queue.put(lambda: self._update_gui_after_sample_playback(voice_friendly_name, success=False, error_message=str(e_play)))
        else: self.task_queue.put(lambda: self._update_gui_after_sample_playback(voice_friendly_name, success=True))
    def _update_gui_after_sample_playback(self, voice_friendly_name:str, success:bool, error_message:str = None): #OK
        if success: self.status_label.configure(text=f"Prueba voz '{voice_friendly_name}' finalizada.")
        else: self.status_label.configure(text=f"Error reproduciendo prueba '{voice_friendly_name}': {error_message}")
        if hasattr(self, 'test_voice_button') and self.test_voice_button.winfo_exists():
            self.test_voice_button.configure(state="normal" if self.can_generate_audio else "disabled")
    def play_voice_sample_threaded(self): #OK
        if not self.can_generate_audio or not self.selected_voice_technical_name: self.status_label.configure(text="Error: Voz TTS no válida."); return
        selected_friendly_name = self.tts_voice_menu_var.get(); technical_name = self.available_voices_map.get(selected_friendly_name)
        if not technical_name: self.status_label.configure(text=f"Error: Nombre técnico no hallado para '{selected_friendly_name}'."); return
        sample_audio_path = os.path.join(VOICE_SAMPLE_DIR, f"{technical_name}.wav")
        if not os.path.exists(sample_audio_path): self.status_label.configure(text=f"Muestra '{os.path.basename(sample_audio_path)}' no hallada. Ejecuta generate_voice_samples.py"); return
        self.status_label.configure(text=f"Reproduciendo '{selected_friendly_name}'..."); self.update_idletasks()
        if hasattr(self, 'test_voice_button'): self.test_voice_button.configure(state="disabled")
        playback_thread = threading.Thread(target=self._play_audio_worker, args=(sample_audio_path, selected_friendly_name), daemon=True); playback_thread.start()

    # --- FLUJO DE PROCESAMIENTO COMPLETO UNIFICADO (Threaded) ---
    def _process_all_worker(self, story_text, tts_voice_tech_name, bg_video_path, srt_max_words, subtitle_style_options, current_id): #OK
        intermediate_audio_path = None; intermediate_narrated_video_path = None
        intermediate_srt_path = None; final_video_path_with_subs = None; current_step = ""
        try:
            current_step = "Generando Audio (TTS)"; self.task_queue.put(lambda: self.status_label.configure(text=f"Proceso (1/4): {current_step}... ID: {current_id}"))
            intermediate_audio_path = os.path.join(file_manager.AUDIO_DIR, f"{current_id}.wav")
            if not tts_kokoro_module.generate_speech_with_voice_name(story_text, tts_voice_tech_name, intermediate_audio_path): raise Exception("Fallo TTS.")

            current_step = "Creando video narrado"; self.task_queue.put(lambda: self.status_label.configure(text=f"Proceso (2/4): {current_step}..."))
            intermediate_narrated_video_path = os.path.join(file_manager.NARRATED_VIDEO_DIR, f"{current_id}.mp4")
            if not video_processor.create_narrated_video(bg_video_path, intermediate_audio_path, intermediate_narrated_video_path): raise Exception("Fallo video narrado.")

            current_step = "Generando subtítulos SRT"; self.task_queue.put(lambda: self.status_label.configure(text=f"Proceso (3/4): {current_step}..."))
            intermediate_srt_path = os.path.join(file_manager.SRT_DIR, f"{current_id}.srt")
            if not srt_generator.create_srt_file(intermediate_audio_path, intermediate_srt_path, max_words_per_segment=srt_max_words): raise Exception("Fallo SRT.")
            
            current_step = "Grabando subtítulos en video"; self.task_queue.put(lambda: self.status_label.configure(text=f"Proceso (4/4): {current_step}..."))
            final_video_path_with_subs = os.path.join(file_manager.FINAL_VIDEO_DIR, f"{current_id}.mp4")
            if not video_processor.burn_subtitles_on_video(intermediate_narrated_video_path, intermediate_srt_path, final_video_path_with_subs, style_options=subtitle_style_options): raise Exception("Fallo quemado de subtítulos.")
            
            self.task_queue.put(lambda: self._update_gui_after_all_processing(True, f"¡Video final ({current_id}) completo!: {os.path.abspath(final_video_path_with_subs)}"))
        except Exception as e: error_full_msg = f"Error en '{current_step}': {str(e)}"; print(error_full_msg); traceback.print_exc(); self.task_queue.put(lambda: self._update_gui_after_all_processing(False, f"Error en '{current_step}': {str(e)}"))

    def _update_gui_after_all_processing(self, success: bool, message: str): #OK
        self.status_label.configure(text=message)
        self._enable_main_action_button()

    def process_all_steps_threaded(self): #OK
        story_text = self.story_textbox.get("1.0", "end-1c").strip()
        placeholders = ["1. Obtén/Genera una historia aquí...", "Cargando...", "Generando IA (hilo)..."]
        is_placeholder = any(story_text.startswith(p_start) for p_start in placeholders if p_start)
        if not story_text or is_placeholder: self.status_label.configure(text="Error: No hay texto válido para procesar."); return
        if not self.can_generate_audio or not self.selected_voice_technical_name: self.status_label.configure(text="Error: Voz TTS no válida."); return
        tts_voice_tech_name = self.selected_voice_technical_name
        if not self.background_video_path: self.status_label.configure(text="Error: Selecciona un video de fondo."); return
        if not os.path.exists(self.background_video_path): self.status_label.configure(text=f"Error: Video '{os.path.basename(self.background_video_path)}' no encontrado."); return
        bg_video_path = self.background_video_path
        max_words_str = self.srt_max_words_var.get()
        srt_max_words = None 
        if max_words_str.isdigit(): srt_max_words = int(max_words_str)
        elif max_words_str != "Whisper (Defecto)": self.status_label.configure(text="Error SRT: 'Palabras Máx.' inválido."); return
        try: subtitle_style_options = self._get_current_subtitle_style_options()
        except ValueError: self.status_label.configure(text="Error: Valor numérico inválido en estilo."); return
        
        current_id = file_manager.get_next_id_str()
        self.status_label.configure(text=f"Iniciando proceso ID: {current_id}... (Ver consola)"); self.update_idletasks()
        self._disable_main_action_button(); master_thread = threading.Thread(
            target=self._process_all_worker,
            args=(story_text, tts_voice_tech_name, bg_video_path, srt_max_words, subtitle_style_options, current_id),
            daemon=True); master_thread.start()

if __name__ == "__main__":
    app = App()
    app.mainloop()