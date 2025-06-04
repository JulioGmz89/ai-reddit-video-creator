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
# import functools # Not actively used but kept for potential future use

# Importar tus módulos personalizados
import reddit_scraper
import tts_kokoro_module
import ai_story_generator
import video_processor
import srt_generator
import file_manager

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("blue")

# --- Updated Color Palette ---
COLOR_PRIMARY_ACTION = "#FE4501"
COLOR_PRIMARY_ACTION_HOVER = "#D83A01"
COLOR_BACKGROUND_MAIN = "#2A252C"
COLOR_BACKGROUND_CARD = "#322E34"
COLOR_BACKGROUND_WIDGET_INPUT = "#3F3A41"
COLOR_TEXT_PRIMARY = "white"
COLOR_TEXT_SECONDARY = "#BFBFBF"
COLOR_BUTTON_SECONDARY_HOVER = "#423E44"
COLOR_BORDER_SELECTED = COLOR_PRIMARY_ACTION
COLOR_SEPARATOR_TEXT = "#6A656C"

CORNER_RADIUS_BUTTON = 8
CORNER_RADIUS_FRAME = 10
CORNER_RADIUS_INPUT = 6

VOICE_SAMPLE_DIR = "voice_samples"
MAX_THUMBNAILS_MAIN_GUI = 3
VIDEO_THUMBNAIL_GRID_COLUMNS = 3
VOICE_AVATAR_GRID_COLUMNS_MAIN = 3
VOICE_AVATAR_GRID_COLUMNS_POPUP = 4

VIDEO_PREVIEW_THUMBNAIL_SIZE = (360, 640) # Target aspect ratio for preview content
PHONE_SCREEN_PADDING_X_FACTOR = 0.075
PHONE_SCREEN_PADDING_Y_TOP_FACTOR = 0.05 # Reduced from 0.07
PHONE_SCREEN_PADDING_Y_BOTTOM_FACTOR = 0.05 # Reduced from 0.075

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        # print(f"DEBUG_SELF (App __init__ start): type(self) is {type(self)}, id(self) is {id(self)}")

        self.title("AI Reddit Story Video Creator")
        self.geometry("1400x900")
        self.configure(fg_color=COLOR_BACKGROUND_MAIN)
        
        self.long_process_active = False

        self.ASSETS_BASE_PATH = "assets/"
        self.VOICE_AVATAR_PATH = os.path.join(self.ASSETS_BASE_PATH, "avatars/")
        self.BUTTONS_ASSETS_PATH = os.path.join(self.ASSETS_BASE_PATH, "buttons/")
        self.PHONE_FRAME_IMAGE_PATH = os.path.join(self.ASSETS_BASE_PATH, "phoneframe.png")
        self.phone_frame_template_pil = None

        # Paths for the new Generate Video button images
        self.GENERATE_ICON_DEFAULT_PATH = os.path.join(self.BUTTONS_ASSETS_PATH, "generatevideo_default.png")
        self.GENERATE_ICON_HOVER_PATH = os.path.join(self.BUTTONS_ASSETS_PATH, "generatevideo_hover.png")
        self.GENERATE_ICON_ACTIVE_PATH = os.path.join(self.BUTTONS_ASSETS_PATH, "generatevideo_active.png")
        self.GENERATE_ICON_DISABLED_PATH = os.path.join(self.BUTTONS_ASSETS_PATH, "generatevideo_disabled.png")

        # Load new Generate Video button images
        generate_button_icon_size = (300, 61) # New size for rectangular button
        try:
            self.generate_image_default = CTkImage(Image.open(self.GENERATE_ICON_DEFAULT_PATH).convert("RGBA"), size=generate_button_icon_size) # <--- CORREGIDO
        except Exception as e:
            print(f"Error loading generatevideo_default.png: {e}"); self.generate_image_default = None
        try:
            self.generate_image_hover = CTkImage(Image.open(self.GENERATE_ICON_HOVER_PATH).convert("RGBA"), size=generate_button_icon_size)
        except Exception as e:
            print(f"Error loading generatevideo_hover.png: {e}"); self.generate_image_hover = self.generate_image_default # Fallback
        try:
            self.generate_image_active = CTkImage(Image.open(self.GENERATE_ICON_ACTIVE_PATH).convert("RGBA"), size=generate_button_icon_size)
        except Exception as e:
            print(f"Error loading generatevideo_active.png: {e}"); self.generate_image_active = self.generate_image_default # Fallback
        try:
            self.generate_image_disabled = CTkImage(Image.open(self.GENERATE_ICON_DISABLED_PATH).convert("RGBA"), size=generate_button_icon_size)
        except Exception as e:
            print(f"Error loading generatevideo_disabled.png: {e}"); self.generate_image_disabled = self.generate_image_default # Fallback

        # Variables de estado para el botón de generación
        self.generate_button_is_pressed = False
        self.mouse_is_over_generate_button = False

        for asset_dir in [self.VOICE_AVATAR_PATH, self.BUTTONS_ASSETS_PATH]: # Corrected variable name
            if not os.path.exists(asset_dir):
                try: os.makedirs(asset_dir)
                except OSError as e: print(f"Error creating directory {asset_dir}: {e}")
                print(f"Created/Checked directory: {asset_dir}. Please place relevant assets here.")

        self.background_video_path = None
        self.can_generate_audio = False
        self.selected_voice_technical_name = None
        self.selected_voice_friendly_name_full = None
        self.selected_voice_button_widget = None
        self.voice_buttons_map = {}

        self.subtitle_font_color_hex = "#FFFF00"
        self.subtitle_stroke_color_hex = "#000000"

        self.all_video_templates = []
        self.combined_preview_ctk_image = None
        self.phone_frame_ctk_image = None

        self.task_queue = queue.Queue()
        # Using lambda to ensure 'self' context is correct for check_queue_for_updates
        self.after(100, lambda: self.check_queue_for_updates())


        file_manager.ensure_directories_exist()

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self.left_scrollable_frame = customtkinter.CTkScrollableFrame(
            self, fg_color=COLOR_BACKGROUND_MAIN,
            scrollbar_button_color=COLOR_BACKGROUND_CARD,
            scrollbar_button_hover_color=COLOR_BUTTON_SECONDARY_HOVER
        )
        self.left_scrollable_frame.grid(row=0, column=0, padx=(20,10), pady=20, sticky="nsew")
        self.left_scrollable_frame.grid_columnconfigure(0, weight=1)

        self.right_pane = customtkinter.CTkFrame(self, fg_color=COLOR_BACKGROUND_MAIN, corner_radius=0)
        self.right_pane.grid(row=0, column=1, padx=(10,20), pady=20, sticky="nsew")
        self.phone_frame_container = customtkinter.CTkFrame(self.right_pane, fg_color="transparent")
        self.phone_frame_container.place(relx=0.5, rely=0.40, anchor="center") # Adjusted rely for button space

        try:
            phone_pil_image_original = Image.open(self.PHONE_FRAME_IMAGE_PATH)
            if phone_pil_image_original.mode != 'RGBA':
                phone_pil_image_original = phone_pil_image_original.convert('RGBA')
            transparent_background_for_phone = Image.new('RGBA', phone_pil_image_original.size, (0, 0, 0, 0))
            self.phone_frame_template_pil = Image.alpha_composite(transparent_background_for_phone, phone_pil_image_original)
            display_phone_width = 380 
            aspect_ratio = self.phone_frame_template_pil.height / self.phone_frame_template_pil.width
            display_phone_height = int(display_phone_width * aspect_ratio)
            self.phone_frame_container.configure(width=display_phone_width, height=display_phone_height)
            self.combined_preview_display_label = customtkinter.CTkLabel(
                self.phone_frame_container, text="", fg_color="transparent"
            )
            self.combined_preview_display_label.place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception as e:
            print(f"Error loading phone frame template or setting up preview display: {e}. Displaying error in preview area.")
            traceback.print_exc()
            self.combined_preview_display_label = customtkinter.CTkLabel(
                self.right_pane, text="Phone Frame Load Error.\\nPlease check assets/phoneframe.png",
                font=("Arial", 12), fg_color=COLOR_BACKGROUND_CARD, text_color=COLOR_TEXT_SECONDARY,
                corner_radius=CORNER_RADIUS_FRAME, wraplength=300
            )
            self.combined_preview_display_label.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8, relheight=0.8)

        # New Generate Video Button
        generate_button_text_fallback = "" if self.generate_image_default else "GENERAR VIDEO"
        initial_fg_color = COLOR_BACKGROUND_MAIN if self.generate_image_default else COLOR_PRIMARY_ACTION
        initial_hover_color = COLOR_BACKGROUND_MAIN if self.generate_image_default else COLOR_PRIMARY_ACTION_HOVER
        self.generate_video_button = customtkinter.CTkButton(
            self.right_pane, # Parent is the right pane
            text=generate_button_text_fallback,
            image=self.generate_image_default, # Default image
            width=generate_button_icon_size[0],
            height=generate_button_icon_size[1],
            corner_radius=CORNER_RADIUS_BUTTON, # Use standard corner radius
            fg_color=COLOR_BACKGROUND_MAIN,    # Match background, rely on image for visuals
            hover_color=COLOR_BACKGROUND_MAIN, # Match background for image-based hover
            border_width=0,
            command=self.process_all_steps_threaded,
            font=("Arial", 16, "bold") if generate_button_text_fallback else None
        )
        # Place it below the phone_frame_container
        self.generate_video_button.place(relx=0.5, rely=0.82, anchor="center") # Adjusted rely

        # Bindings for the new generate button states
        self.generate_video_button.bind("<Enter>", self._on_generate_button_enter)
        self.generate_video_button.bind("<Leave>", self._on_generate_button_leave)
        self.generate_video_button.bind("<ButtonPress-1>", self._on_generate_button_press)
        self.generate_video_button.bind("<ButtonRelease-1>", self._on_generate_button_release)

        current_row_in_left_panel = 0
        self.input_method_frame = customtkinter.CTkFrame(self.left_scrollable_frame, fg_color="transparent")
        self.input_method_frame.grid(row=current_row_in_left_panel, column=0, sticky="ew", padx=5, pady=(0,10)); current_row_in_left_panel += 1
        self.input_method_frame.grid_columnconfigure(0, weight=1)
        reddit_url_frame = customtkinter.CTkFrame(self.input_method_frame, fg_color="transparent")
        reddit_url_frame.grid(row=0, column=0, sticky="ew", pady=(0,5)); reddit_url_frame.grid_columnconfigure(0, weight=1)
        self.reddit_url_entry = customtkinter.CTkEntry(reddit_url_frame, placeholder_text="TEXT INPUT REDDIT URL", fg_color=COLOR_BACKGROUND_CARD, text_color=COLOR_TEXT_PRIMARY, height=35, corner_radius=CORNER_RADIUS_INPUT, border_color=COLOR_BACKGROUND_CARD)
        self.reddit_url_entry.grid(row=0, column=0, padx=(0,10), pady=5, sticky="ew")
        self.reddit_fetch_button = customtkinter.CTkButton(reddit_url_frame, text="SEARCH", command=self.fetch_reddit_post_threaded, fg_color=COLOR_PRIMARY_ACTION, hover_color=COLOR_PRIMARY_ACTION_HOVER, text_color=COLOR_TEXT_PRIMARY, height=35, width=100, corner_radius=CORNER_RADIUS_BUTTON, font=("Arial", 13, "bold"))
        self.reddit_fetch_button.grid(row=0, column=1, pady=5)
        separator_label = customtkinter.CTkLabel(self.input_method_frame, text=" OR ", text_color=COLOR_SEPARATOR_TEXT, font=("Arial", 12))
        separator_label.grid(row=1, column=0, pady=8, sticky="ew")
        self.generate_ai_story_popup_button = customtkinter.CTkButton(self.input_method_frame, text="Generate with AI", command=self.open_ai_story_generation_popup, fg_color=COLOR_PRIMARY_ACTION, hover_color=COLOR_PRIMARY_ACTION_HOVER, text_color=COLOR_TEXT_PRIMARY, height=40, corner_radius=CORNER_RADIUS_BUTTON, font=("Arial", 14, "bold"))
        self.generate_ai_story_popup_button.grid(row=2, column=0, pady=5, sticky="ew")

        self.story_frame = customtkinter.CTkFrame(self.left_scrollable_frame, fg_color=COLOR_BACKGROUND_CARD, corner_radius=CORNER_RADIUS_FRAME)
        self.story_frame.grid(row=current_row_in_left_panel, column=0, sticky="nsew", padx=5, pady=10); current_row_in_left_panel += 1
        self.story_frame.grid_columnconfigure(0, weight=1); self.story_frame.grid_rowconfigure(1, weight=1)
        customtkinter.CTkLabel(self.story_frame, text="Text to Speech", font=("Arial", 15, "bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, pady=(10,5), padx=15, sticky="w")
        self.story_textbox = customtkinter.CTkTextbox(self.story_frame, wrap="word", font=("Arial", 13), height=150, activate_scrollbars=True, fg_color=COLOR_BACKGROUND_WIDGET_INPUT, text_color=COLOR_TEXT_PRIMARY, corner_radius=CORNER_RADIUS_INPUT, border_width=1, border_color=COLOR_BACKGROUND_WIDGET_INPUT)
        self.story_textbox.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0,15))
        self.story_textbox.insert("1.0", "1. Fetch a story using the URL or generate one with AI.\n2. Configure Voice, Video Background, and Subtitles.\n3. Click the play button to create video.")
        self.ai_subject_entry = customtkinter.CTkEntry(self); self.ai_style_entry = customtkinter.CTkEntry(self)
        self.ai_max_tokens_slider_var = customtkinter.IntVar(value=150)
        self.ai_max_tokens_menu_var = customtkinter.StringVar(value=str(self.ai_max_tokens_slider_var.get()))

        self.voice_selection_outer_frame = customtkinter.CTkFrame(self.left_scrollable_frame, fg_color=COLOR_BACKGROUND_CARD, corner_radius=CORNER_RADIUS_FRAME)
        self.voice_selection_outer_frame.grid(row=current_row_in_left_panel, column=0, sticky="ew", padx=5, pady=10); current_row_in_left_panel += 1
        header_frame_voice = customtkinter.CTkFrame(self.voice_selection_outer_frame, fg_color="transparent")
        header_frame_voice.pack(fill="x", padx=15, pady=(10,5)) # Usar pack para layout simple dentro del outer_frame
        customtkinter.CTkLabel(header_frame_voice, text="Select a voice", font=("Arial", 15, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left")
        self.view_all_voices_button = customtkinter.CTkButton(header_frame_voice, text="View all", command=self.open_view_all_voices_popup, width=80, corner_radius=CORNER_RADIUS_BUTTON, fg_color=COLOR_BACKGROUND_WIDGET_INPUT, hover_color=COLOR_BUTTON_SECONDARY_HOVER, text_color=COLOR_TEXT_SECONDARY)
        self.view_all_voices_button.pack(side="right")
        self.voice_thumbnail_grid_main = customtkinter.CTkFrame(self.voice_selection_outer_frame, fg_color="transparent")
        self.voice_thumbnail_grid_main.pack(fill="x", expand=True, padx=15, pady=5) # Usar pack
        
        for i in range(VOICE_AVATAR_GRID_COLUMNS_MAIN): # Configurar columnas para el grid de voces
            self.voice_thumbnail_grid_main.grid_columnconfigure(i, weight=1)
        
        self.available_voices_map = tts_kokoro_module.list_available_kokoro_voices() # Mapa de Amigable_Completo -> Técnico
        
        self.desired_main_ui_voices_meta = [
            {"tech": "af_heart", "friendly_short": "Heart", "img": "heart.png", "lang_code_for_sentence": "en"},
            {"tech": "af_bella", "friendly_short": "Bella", "img": "bella.png", "lang_code_for_sentence": "en"},
            {"tech": "af_alloy", "friendly_short": "Alloy", "img": "alloy.png", "lang_code_for_sentence": "en"}, # Asegúrate que todas tengan estas 3 claves + lang_code
            {"tech": "af_aoede", "friendly_short": "Aoede", "img": "aoede.png", "lang_code_for_sentence": "en"},
            {"tech": "af_kore", "friendly_short": "Kore", "img": "kore.png", "lang_code_for_sentence": "en"},
            {"tech": "af_nicole", "friendly_short": "Nicole", "img": "nicole.png", "lang_code_for_sentence": "en"},
            {"tech": "af_nova", "friendly_short": "Nova", "img": "nova.png", "lang_code_for_sentence": "en"},
            {"tech": "af_sarah", "friendly_short": "Sarah", "img": "sarah.png", "lang_code_for_sentence": "en"},
            {"tech": "am_fenrir", "friendly_short": "Fenrir", "img": "fenrir.png", "lang_code_for_sentence": "en"},
            {"tech": "am_michael", "friendly_short": "Michael", "img": "michael.png", "lang_code_for_sentence": "en"},
            {"tech": "am_puck", "friendly_short": "Puck", "img": "puck.png", "lang_code_for_sentence": "en"},
            {"tech": "bf_emma", "friendly_short": "Emma", "img": "emma.png", "lang_code_for_sentence": "en"},
            {"tech": "bm_fable", "friendly_short": "Fable", "img": "fable.png", "lang_code_for_sentence": "en"},
            {"tech": "bm_george", "friendly_short": "George", "img": "george.png", "lang_code_for_sentence": "en"},
            # Si eliminaste las voces en español de tts_kokoro_module.py, no las pongas aquí.
        ]
        
        self.active_main_ui_voices_meta = [
            vm for vm in self.desired_main_ui_voices_meta if vm["tech"] in self.available_voices_map.values()
        ]

        self.test_voice_button = customtkinter.CTkButton(self.voice_selection_outer_frame, text="Test Selected Voice", command=self.play_voice_sample_threaded, corner_radius=CORNER_RADIUS_BUTTON, fg_color=COLOR_BACKGROUND_WIDGET_INPUT, hover_color=COLOR_BUTTON_SECONDARY_HOVER, text_color=COLOR_TEXT_SECONDARY)
        self.test_voice_button.pack(pady=(5,15), padx=15, anchor="w")
        
        self.available_voices_map = tts_kokoro_module.list_available_kokoro_voices()
        print(f"DEBUG: self.available_voices_map = {self.available_voices_map}") # Debug print
        self.voice_friendly_names = list(self.available_voices_map.keys())
        # La redefinición de self.desired_main_ui_voices_meta que estaba aquí ha sido eliminada.
        # Se usará la definición de las líneas 226-242 que contiene "friendly_short".
        available_tech_names_list = list(self.available_voices_map.values())
        print(f"DEBUG: available_tech_names_list from Kokoro = {available_tech_names_list}") # Debug print

        default_voice_tech, default_voice_friendly_display = None, "No voices"
        if self.voice_friendly_names: # Check if any voices were loaded at all
            # Usar la (ahora única) self.desired_main_ui_voices_meta (la lista larga y correcta)
            for voice_meta_item in self.desired_main_ui_voices_meta: # Iterar sobre la lista correcta
                if voice_meta_item["tech"] in available_tech_names_list: default_voice_tech, default_voice_friendly_display = voice_meta_item["tech"], voice_meta_item["friendly_short"]; break # Usar friendly_short
            if not default_voice_tech and available_tech_names_list: # Fallback if none of desired are available, but others are
                default_voice_tech = available_tech_names_list[0]
                # Find corresponding friendly name for this tech name
                for fn, tn in self.available_voices_map.items():
                    if tn == default_voice_tech: default_voice_friendly_display = fn.split(" (")[0].split(" ")[-1]; break # Crear un nombre corto amigable
        self.selected_voice_technical_name = default_voice_tech; self.can_generate_audio = bool(self.selected_voice_technical_name)
        self.tts_voice_menu_var = customtkinter.StringVar(value=default_voice_friendly_display)
        
        # Este bucle es redundante ya que refresh_main_voice_avatar_grid() se llama más tarde
        # y se encarga de dibujar los avatares basados en self.active_main_ui_voices_meta.

        #self.test_voice_button = customtkinter.CTkButton(self.voice_selection_outer_frame, text="Test Selected Voice", command=self.play_voice_sample_threaded, corner_radius=CORNER_RADIUS_BUTTON, fg_color=COLOR_BACKGROUND_WIDGET_INPUT, hover_color=COLOR_BUTTON_SECONDARY_HOVER, text_color=COLOR_TEXT_SECONDARY)
        self.test_voice_button.pack(pady=(5,15), padx=15, anchor="w"); self.test_voice_button.configure(state="disabled" if not self.can_generate_audio else "normal", fg_color="grey50" if not self.can_generate_audio else COLOR_BACKGROUND_WIDGET_INPUT)

        self.video_template_selection_frame = customtkinter.CTkFrame(self.left_scrollable_frame, fg_color=COLOR_BACKGROUND_CARD, corner_radius=CORNER_RADIUS_FRAME)
        self.video_template_selection_frame.grid(row=current_row_in_left_panel, column=0, sticky="ew", padx=5, pady=10); current_row_in_left_panel += 1; self.video_template_selection_frame.grid_columnconfigure(0, weight=1)
        header_frame_video = customtkinter.CTkFrame(self.video_template_selection_frame, fg_color="transparent"); header_frame_video.grid(row=0, column=0, sticky="ew", padx=15, pady=(10,5))
        customtkinter.CTkLabel(header_frame_video, text="Select a video background", font=("Arial", 15, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left")
        self.view_all_videos_button_main = customtkinter.CTkButton(header_frame_video, text="View all", command=self.open_view_all_videos_popup, width=80, corner_radius=CORNER_RADIUS_BUTTON, fg_color=COLOR_BACKGROUND_WIDGET_INPUT, hover_color=COLOR_BUTTON_SECONDARY_HOVER, text_color=COLOR_TEXT_SECONDARY); self.view_all_videos_button_main.pack(side="right")
        self.active_video_display_label = customtkinter.CTkLabel(self.video_template_selection_frame, text="Selected: None", wraplength=500, text_color=COLOR_TEXT_SECONDARY, font=("Arial",12)); self.active_video_display_label.grid(row=1, column=0, padx=15, pady=(0,5), sticky="w")
        self.thumbnail_grid_frame = customtkinter.CTkFrame(self.video_template_selection_frame, fg_color="transparent"); self.thumbnail_grid_frame.grid(row=2, column=0, padx=15, pady=(0,15), sticky="ew")

        self.cap_row_internal = 1
        def create_caption_optionmenu_local(parent, text, options_list, var, cmd=None, col=0):
            target_col_label, target_col_menu = col, col + 1; px_label, px_menu = ((15,5),(5,15)) if col == 0 else ((15,5),(5,15))
            customtkinter.CTkLabel(parent, text=text, text_color=COLOR_TEXT_SECONDARY, font=("Arial",12)).grid(row=self.cap_row_internal, column=target_col_label, padx=px_label, pady=5, sticky="w")
            menu = customtkinter.CTkOptionMenu(parent, values=options_list, variable=var, command=lambda choice: cmd(choice) if cmd else None, corner_radius=CORNER_RADIUS_INPUT, fg_color=COLOR_BACKGROUND_WIDGET_INPUT, button_color=COLOR_BACKGROUND_WIDGET_INPUT, button_hover_color=COLOR_BUTTON_SECONDARY_HOVER, text_color=COLOR_TEXT_PRIMARY, dropdown_fg_color=COLOR_BACKGROUND_CARD, dropdown_hover_color=COLOR_BUTTON_SECONDARY_HOVER, dropdown_text_color=COLOR_TEXT_PRIMARY)
            menu.grid(row=self.cap_row_internal, column=target_col_menu, padx=px_menu, pady=5, sticky="ew"); return menu
        self.srt_style_frame = customtkinter.CTkFrame(self.left_scrollable_frame, fg_color=COLOR_BACKGROUND_CARD, corner_radius=CORNER_RADIUS_FRAME)
        self.srt_style_frame.grid(row=current_row_in_left_panel, column=0, sticky="ew", padx=5, pady=10); current_row_in_left_panel += 1; self.srt_style_frame.grid_columnconfigure(1, weight=1); self.srt_style_frame.grid_columnconfigure(3, weight=1)
        customtkinter.CTkLabel(self.srt_style_frame, text="Captions configuration", font=("Arial", 15, "bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, columnspan=4, padx=15, pady=(10,10), sticky="w")
        self.srt_max_words_options = ["Whisper (Defecto)", "1", "2", "3", "4", "5", "6", "7"]; self.srt_max_words_var = customtkinter.StringVar(value="1")
        create_caption_optionmenu_local(self.srt_style_frame, "Max words per segment:", self.srt_max_words_options, self.srt_max_words_var, col=0)
        self.subtitle_fontsize_options = ["18", "24", "32", "36", "40", "48", "56", "64", "72"]; self.subtitle_fontsize_var = customtkinter.StringVar(value="64")
        create_caption_optionmenu_local(self.srt_style_frame, "Font size:", self.subtitle_fontsize_options, self.subtitle_fontsize_var, cmd=lambda choice: self.update_subtitle_preview_display(), col=2); self.cap_row_internal += 1
        self.subtitle_pos_options = ["Abajo", "Centro", "Arriba"]; self.subtitle_pos_var = customtkinter.StringVar(value="Centro")
        create_caption_optionmenu_local(self.srt_style_frame, "Position:", self.subtitle_pos_options, self.subtitle_pos_var, cmd=lambda choice: self.update_subtitle_preview_display(), col=0)
        self.subtitle_font_options = ["Arial", "Verdana", "Impact", "Courier New"]; self.subtitle_font_var = customtkinter.StringVar(value="Impact")
        create_caption_optionmenu_local(self.srt_style_frame, "Font:", self.subtitle_font_options, self.subtitle_font_var, cmd=lambda choice: self.update_subtitle_preview_display(), col=2); self.cap_row_internal += 1
        customtkinter.CTkLabel(self.srt_style_frame, text="Text Color:", text_color=COLOR_TEXT_SECONDARY, font=("Arial",12)).grid(row=self.cap_row_internal, column=0, padx=(15,5), pady=5, sticky="w")
        self.subtitle_text_color_button = customtkinter.CTkButton(self.srt_style_frame, text="CHOOSE", width=80, command=lambda: self.pick_color_for('text_fg'), corner_radius=CORNER_RADIUS_BUTTON, fg_color=COLOR_BACKGROUND_WIDGET_INPUT, hover_color=COLOR_BUTTON_SECONDARY_HOVER, text_color=COLOR_TEXT_SECONDARY); self.subtitle_text_color_button.grid(row=self.cap_row_internal, column=1, padx=5, pady=5, sticky="w")
        self.subtitle_text_color_preview = customtkinter.CTkFrame(self.srt_style_frame, width=30, height=30, fg_color=self.subtitle_font_color_hex, border_width=1, border_color=COLOR_TEXT_SECONDARY, corner_radius=4); self.subtitle_text_color_preview.grid(row=self.cap_row_internal, column=1, padx=(100,5), pady=5, sticky="w")
        customtkinter.CTkLabel(self.srt_style_frame, text="Stroke Color:", text_color=COLOR_TEXT_SECONDARY, font=("Arial",12)).grid(row=self.cap_row_internal, column=2, padx=(15,5), pady=5, sticky="w")
        self.subtitle_stroke_color_button = customtkinter.CTkButton(self.srt_style_frame, text="CHOOSE", width=80, command=lambda: self.pick_color_for('stroke_fg'), corner_radius=CORNER_RADIUS_BUTTON, fg_color=COLOR_BACKGROUND_WIDGET_INPUT, hover_color=COLOR_BUTTON_SECONDARY_HOVER, text_color=COLOR_TEXT_SECONDARY); self.subtitle_stroke_color_button.grid(row=self.cap_row_internal, column=3, padx=(5,85), pady=5, sticky="w")
        self.subtitle_stroke_color_preview = customtkinter.CTkFrame(self.srt_style_frame, width=30, height=30, fg_color=self.subtitle_stroke_color_hex, border_width=1, border_color=COLOR_TEXT_SECONDARY, corner_radius=4); self.subtitle_stroke_color_preview.grid(row=self.cap_row_internal, column=3, padx=(100,15), pady=5, sticky="w"); self.cap_row_internal += 1
        self.subtitle_strokewidth_options = ["0", "0.5", "1", "1.5", "2", "3"]; self.subtitle_strokewidth_var = customtkinter.StringVar(value="0")
        create_caption_optionmenu_local(self.srt_style_frame, "Stroke Width:", self.subtitle_strokewidth_options, self.subtitle_strokewidth_var, cmd=lambda choice: self.update_subtitle_preview_display(), col=0)
        self.subtitle_bgcolor_map = { "Transparent": "transparent", "Black Semi (40%)": "rgba(0,0,0,0.4)", "Black Semi (60%)": "rgba(0,0,0,0.6)"}; self.subtitle_bgcolor_options = list(self.subtitle_bgcolor_map.keys()); self.subtitle_bgcolor_var = customtkinter.StringVar(value="Transparent")
        menu_bg = create_caption_optionmenu_local(self.srt_style_frame, "Background Text:", self.subtitle_bgcolor_options, self.subtitle_bgcolor_var, cmd=lambda choice: self.update_subtitle_preview_display(), col=2); menu_bg.grid(pady=(5,15)); self.cap_row_internal +=1

        self.status_frame = customtkinter.CTkFrame(self.left_scrollable_frame, fg_color="transparent")
        self.status_frame.grid(row=current_row_in_left_panel, column=0, sticky="ew", padx=5, pady=(10,0)); current_row_in_left_panel += 1
        self.status_label = customtkinter.CTkLabel(self.status_frame, text="Status: Ready.", text_color=COLOR_TEXT_SECONDARY, anchor="w", font=("Arial",12))
        self.status_label.grid(row=0, column=0, padx=0, pady=0, sticky="ew")

        # Eliminar la redefinición de self.desired_main_ui_voices_meta
        # La definición original en las líneas 226-242 es la que se usará.
        # self.desired_main_ui_voices_meta = [{"tech": "af_heart", ...}] # Esta línea (originalmente ~250) se elimina.

        self._load_all_available_voices() # Carga y establece la voz por defecto usando la lista correcta
        self.refresh_main_voice_avatar_grid() # Dibuja los avatares iniciales
        
        self._load_video_templates_list() 
        self.refresh_main_thumbnail_grid() 
        self.update_subtitle_preview_display()
        self._check_story_and_set_generate_button_state()


    # --- METHODS ---

    def open_ai_story_generation_popup(self):
        if hasattr(self, 'ai_popup') and self.ai_popup.winfo_exists():
            self.ai_popup.focus(); self.ai_popup.grab_set(); return

        self.ai_popup = customtkinter.CTkToplevel(self)
        self.ai_popup.title("Generate a story with AI"); self.ai_popup.geometry("500x400") # Adjusted height for slider
        self.ai_popup.attributes("-topmost", True); self.ai_popup.resizable(False, False)
        self.ai_popup.configure(fg_color=COLOR_BACKGROUND_MAIN); self.ai_popup.grab_set()

        main_frame = customtkinter.CTkFrame(self.ai_popup, fg_color=COLOR_BACKGROUND_CARD, corner_radius=CORNER_RADIUS_FRAME)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        customtkinter.CTkLabel(main_frame, text="Generate a story with AI", font=("Arial", 18, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(pady=(0,20))

        customtkinter.CTkLabel(main_frame, text="Story Subject (English):", anchor="w", text_color=COLOR_TEXT_SECONDARY, font=("Arial",13)).pack(fill="x", padx=10)
        self.popup_ai_subject_entry = customtkinter.CTkEntry(main_frame, placeholder_text="e.g., camping trip", fg_color=COLOR_BACKGROUND_WIDGET_INPUT, text_color=COLOR_TEXT_PRIMARY, corner_radius=CORNER_RADIUS_INPUT, height=35, border_color=COLOR_BACKGROUND_WIDGET_INPUT)
        self.popup_ai_subject_entry.pack(fill="x", padx=10, pady=(2,15)); self.popup_ai_subject_entry.insert(0, self.ai_subject_entry.get())

        customtkinter.CTkLabel(main_frame, text="Story Style (English):", anchor="w", text_color=COLOR_TEXT_SECONDARY, font=("Arial",13)).pack(fill="x", padx=10)
        self.popup_ai_style_entry = customtkinter.CTkEntry(main_frame, placeholder_text="e.g., /nosleep, funny", fg_color=COLOR_BACKGROUND_WIDGET_INPUT, text_color=COLOR_TEXT_PRIMARY, corner_radius=CORNER_RADIUS_INPUT, height=35, border_color=COLOR_BACKGROUND_WIDGET_INPUT)
        self.popup_ai_style_entry.pack(fill="x", padx=10, pady=(2,15)); self.popup_ai_style_entry.insert(0, self.ai_style_entry.get())

        # Slider for Word Count
        word_count_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        word_count_frame.pack(fill="x", padx=10, pady=(5,5)) # Reduced pady
        customtkinter.CTkLabel(word_count_frame, text="Word Count (Max Tokens):", anchor="w", text_color=COLOR_TEXT_SECONDARY, font=("Arial",13)).pack(side="left", padx=(0,10))
        self.popup_ai_max_tokens_value_label = customtkinter.CTkLabel(word_count_frame, text=str(self.ai_max_tokens_slider_var.get()), text_color=COLOR_TEXT_PRIMARY, font=("Arial",13))
        self.popup_ai_max_tokens_value_label.pack(side="right")

        self.popup_ai_max_tokens_slider = customtkinter.CTkSlider(
            main_frame, from_=100, to=500, number_of_steps=400,
            variable=self.ai_max_tokens_slider_var,
            command=lambda value: self.popup_ai_max_tokens_value_label.configure(text=str(int(value))),
            button_color=COLOR_PRIMARY_ACTION, progress_color=COLOR_PRIMARY_ACTION, button_hover_color=COLOR_PRIMARY_ACTION_HOVER,
            height=20
        )
        self.popup_ai_max_tokens_slider.pack(fill="x", padx=10, pady=(0,20))
        self.ai_max_tokens_slider_var.set(150) # Set initial value for slider and label
        self.popup_ai_max_tokens_value_label.configure(text="150")


        generate_button = customtkinter.CTkButton(main_frame, text="GENERATE", command=self.trigger_ai_story_from_popup, fg_color=COLOR_PRIMARY_ACTION, hover_color=COLOR_PRIMARY_ACTION_HOVER, text_color=COLOR_TEXT_PRIMARY, corner_radius=CORNER_RADIUS_BUTTON, height=40, font=("Arial", 14, "bold"))
        generate_button.pack(pady=(10,0)); self.ai_popup.bind("<Return>", lambda event: generate_button.invoke())

    def trigger_ai_story_from_popup(self):
        subject = self.popup_ai_subject_entry.get(); style = self.popup_ai_style_entry.get()
        max_tokens_val = int(self.ai_max_tokens_slider_var.get())

        self.ai_subject_entry.delete(0, "end"); self.ai_subject_entry.insert(0, subject)
        self.ai_style_entry.delete(0, "end"); self.ai_style_entry.insert(0, style)
        self.ai_max_tokens_menu_var.set(str(max_tokens_val))

        if hasattr(self, 'ai_popup'): self.ai_popup.grab_release(); self.ai_popup.destroy(); delattr(self, 'ai_popup')
        self.process_ai_story_generation_threaded()

    def process_ai_story_generation_threaded(self):
        subject, style = self.ai_subject_entry.get().strip(), self.ai_style_entry.get().strip()
        if not subject or not style: self.status_label.configure(text="Error AI: Subject/Style req."); return
        try:
            max_tokens = int(self.ai_max_tokens_menu_var.get()) # This now gets value from slider via trigger_ai_story_from_popup
        except ValueError: self.status_label.configure(text="Error AI: Invalid Max Tokens."); return

        self.status_label.configure(text="AI Story: Generating..."); self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", "Generating AI story..."); self.update_idletasks()
        self._disable_main_action_button(); threading.Thread(target=self._ai_story_worker, args=(subject, style, max_tokens), daemon=True).start()


    def update_subtitle_preview_display(self, _=None): 
        if not hasattr(self, 'combined_preview_display_label'): return
        if not hasattr(self, 'phone_frame_template_pil') or self.phone_frame_template_pil is None: 
            self.combined_preview_display_label.configure(image=None, text="[Phone GFX Missing]"); return
        try:
            phone_template_pil = self.phone_frame_template_pil.copy()
            pt_width, pt_height = phone_template_pil.size
            style_opts = self._get_current_subtitle_style_options()
            if not style_opts: self.combined_preview_display_label.configure(image=None, text="[Style Error]"); return
            preview_text = "This is a sample subtitle text."
            screen_content_pil = None
            if self.current_video_thumbnail_for_composite_path and os.path.exists(self.current_video_thumbnail_for_composite_path):
                # Pasar el style_opts directamente
                style_opts_for_preview = style_opts.copy() # Copiar para no modificar el original si es necesario
                style_opts_for_preview['preview_subtitle_fixed_height'] = video_processor.PREVIEW_SUBTITLE_HEIGHT
                # El ancho se pasará directamente a la función de video_processor si es necesario
                generated_screen_content_path = video_processor.create_composite_preview_image(
                    self.current_video_thumbnail_for_composite_path, preview_text, style_opts_for_preview )
                if generated_screen_content_path and os.path.exists(generated_screen_content_path):
                    screen_content_pil = Image.open(generated_screen_content_path).convert("RGBA")
                else: print(f"WARN: Screen content generation failed or path not found: {generated_screen_content_path}")
            else: print("INFO: No video selected for preview content.")

            composite_base_pil = Image.new('RGBA', phone_template_pil.size, (0, 0, 0, 0))
            if screen_content_pil:
                screen_area_x_int = int(pt_width * PHONE_SCREEN_PADDING_X_FACTOR)
                screen_area_y_int = int(pt_height * PHONE_SCREEN_PADDING_Y_TOP_FACTOR)
                screen_area_width_int = int(pt_width * (1 - 2 * PHONE_SCREEN_PADDING_X_FACTOR))
                screen_area_height_int = int(pt_height * (1 - PHONE_SCREEN_PADDING_Y_TOP_FACTOR - PHONE_SCREEN_PADDING_Y_BOTTOM_FACTOR))
                # Redimensionar el contenido (video+subtítulo) para que quepa en el área de la pantalla del teléfono
                resized_screen_content_pil = screen_content_pil.resize((screen_area_width_int, screen_area_height_int), Image.Resampling.LANCZOS)
                composite_base_pil.paste(resized_screen_content_pil, (screen_area_x_int, screen_area_y_int))
            
            final_composite_pil = Image.alpha_composite(composite_base_pil, phone_template_pil)
            
            display_phone_width = 380 
            final_aspect_ratio = final_composite_pil.height / final_composite_pil.width if final_composite_pil.width > 0 else 1.0
            display_composite_height = int(display_phone_width * final_aspect_ratio)

            self.combined_preview_ctk_image = CTkImage(light_image=final_composite_pil, dark_image=final_composite_pil, size=(display_phone_width, display_composite_height))
            self.combined_preview_display_label.configure(image=self.combined_preview_ctk_image, text="")
        except Exception as e:
            print(f"ERROR in update_subtitle_preview_display: {e}"); traceback.print_exc()
            self.combined_preview_display_label.configure(image=None, text="[Preview Gen Error]")


    def _get_current_subtitle_style_options(self) -> dict | None:
        if not all(hasattr(self, attr_name) for attr_name in ['subtitle_bgcolor_map', 'subtitle_bgcolor_var', 'subtitle_fontsize_var', 'subtitle_strokewidth_var', 'subtitle_font_var', 'subtitle_font_color_hex', 'subtitle_stroke_color_hex', 'subtitle_pos_var']):
            print(f"CRITICAL DEBUG: Subtitle style attributes missing in _get_current_subtitle_style_options!")
            return None
        actual_bg_color = self.subtitle_bgcolor_map.get(self.subtitle_bgcolor_var.get(), "rgba(0,0,0,0.4)")
        try: fontsize, strokewidth = int(self.subtitle_fontsize_var.get()), float(self.subtitle_strokewidth_var.get())
        except ValueError: fontsize, strokewidth = 36, 1.5; self.status_label.configure(text="Warn: Invalid sub style.")
        return {'font': self.subtitle_font_var.get(), 'fontsize': fontsize, 'color': self.subtitle_font_color_hex, 
                 'stroke_color': self.subtitle_stroke_color_hex, 'stroke_width': strokewidth, 'bg_color': actual_bg_color, 
                 'position_choice': self.subtitle_pos_var.get()}

    # --- ALL OTHER METHODS from the previous response MUST BE COPIED HERE ---
    # (check_queue_for_updates, _get_main_action_buttons_for_state_management, etc.)
    # ...
    # For brevity, I am only showing the modified __init__ and open_ai_story_generation_popup.
    # You NEED to re-insert all other methods from the previous complete main.py here.
    # I've included stubs for the remaining methods from the prior version.
    # You should replace these stubs with the full method implementations from the previous complete main.py file.
    
    def check_queue_for_updates(self):
        # print(f"DEBUG_SELF (check_queue_for_updates): type(self) is {type(self)}, id(self) is {id(self)}")
        try:
            callback = self.task_queue.get(block=False)
            if callable(callback): callback()
            self.task_queue.task_done()
        except queue.Empty: pass
        finally:
            # Use lambda for the recursive call as well
            self.after(100, lambda: self.check_queue_for_updates())
            
    def _get_main_action_buttons_for_state_management(self):
        return [self.reddit_fetch_button, self.generate_ai_story_popup_button]
    
    def _disable_main_action_button(self):
        self.long_process_active = True # Indicar que un proceso largo ha comenzado
        for button in self._get_main_action_buttons_for_state_management():
            button.configure(state="disabled", fg_color="grey50")
        if hasattr(self, 'test_voice_button') and self.test_voice_button.winfo_exists():
            self.test_voice_button.configure(state="disabled", fg_color="grey50")
        if hasattr(self, 'generate_video_button') and self.generate_video_button.winfo_exists(): # New button
            self.generate_video_button.configure(state="disabled") # fg_color is image based
            self._update_generate_button_image() 

    def _enable_main_action_button(self):
        self.long_process_active = False # Indicar que el proceso largo ha terminado
        self.reddit_fetch_button.configure(state="normal", fg_color=COLOR_PRIMARY_ACTION)
        self.generate_ai_story_popup_button.configure(state="normal", fg_color=COLOR_PRIMARY_ACTION)
        
        state_test_voice, fg_test_voice = ("normal", COLOR_BACKGROUND_WIDGET_INPUT) if self.can_generate_audio else ("disabled", "grey50")
        if hasattr(self, 'test_voice_button') and self.test_voice_button.winfo_exists():
            self.test_voice_button.configure(state=state_test_voice, fg_color=fg_test_voice)
            
        self._check_story_and_set_generate_button_state() # Use renamed method
        
    def update_selected_voice_technical_name(self, selected_friendly_name: str):
        self.selected_voice_technical_name = None
        if selected_friendly_name in self.available_voices_map: # selected_friendly_name is a key from tts_kokoro_module
            self.selected_voice_technical_name = self.available_voices_map[selected_friendly_name]
        else: # Fallback: check if selected_friendly_name is a short version (e.g., "Heart")
            desired_main_ui_voices_meta = [{"tech": "af_heart", "friendly": "Heart", "img": "heart.png"}, {"tech": "am_fenrir", "friendly": "Fenrir", "img": "fenrir.png"}, {"tech": "af_bella", "friendly": "Bella", "img": "bella.png"}, {"tech": "bf_emma", "friendly": "Emma", "img": "emma.png"}, {"tech": "am_michael", "friendly": "Michael", "img": "michael.png"}, {"tech": "bm_george", "friendly": "George", "img": "george.png"},]
            for voice_meta_item in desired_main_ui_voices_meta:
                if voice_meta_item["friendly"] == selected_friendly_name:
                    if voice_meta_item["tech"] in list(self.available_voices_map.values()):
                        self.selected_voice_technical_name = voice_meta_item["tech"]
                        for fn_key, tn_val in self.available_voices_map.items():
                            if tn_val == self.selected_voice_technical_name: selected_friendly_name = fn_key; break
                        break
        if self.selected_voice_technical_name:
            self.can_generate_audio = True; self.status_label.configure(text=f"Voice: {selected_friendly_name.split('(')[0].strip()}")
            self.tts_voice_menu_var.set(selected_friendly_name); self.update_subtitle_preview_display()
            if hasattr(self, 'test_voice_button'): self.test_voice_button.configure(state="normal", fg_color=COLOR_BACKGROUND_WIDGET_INPUT)
        else:
            self.can_generate_audio = False; self.status_label.configure(text=f"Voice not found: {selected_friendly_name}")
            if hasattr(self, 'test_voice_button'): self.test_voice_button.configure(state="disabled", fg_color="grey50")

    def pick_color_for(self, color_target: str):
        initial_color = self.subtitle_font_color_hex if color_target == 'text_fg' else self.subtitle_stroke_color_hex
        title = "Select Text Color" if color_target == 'text_fg' else "Select Stroke Color"
        color_info = colorchooser.askcolor(initialcolor=initial_color, title=title, parent=self)
        if color_info and color_info[1]:
            hex_color = color_info[1]
            preview_attr = f"subtitle_{'text' if color_target == 'text_fg' else 'stroke'}_color_preview"
            if color_target == 'text_fg': self.subtitle_font_color_hex = hex_color
            elif color_target == 'stroke_fg': self.subtitle_stroke_color_hex = hex_color
            if hasattr(self, preview_attr): getattr(self, preview_attr).configure(fg_color=hex_color)
            self.status_label.configure(text=f"Subtitle {color_target} color updated."); self.update_subtitle_preview_display()

    def _load_video_templates_list(self):
        self.all_video_templates = video_processor.list_video_templates()
        if not self.all_video_templates:
            if hasattr(self, 'active_video_display_label'): self.active_video_display_label.configure(text="Video templates folder empty.")
            self.current_video_thumbnail_for_composite_path = None
        elif not self.background_video_path : self._select_video_from_thumbnail_internal(self.all_video_templates[0])
        self.update_subtitle_preview_display()

    def refresh_main_thumbnail_grid(self, newly_selected_path: str = None):
        if not hasattr(self, 'thumbnail_grid_frame'): return
        videos_to_show = list(self.all_video_templates)
        current_sel = newly_selected_path if newly_selected_path else self.background_video_path
        if current_sel and current_sel in videos_to_show: videos_to_show.remove(current_sel); videos_to_show.insert(0, current_sel)
        self._display_thumbnails_in_grid(self.thumbnail_grid_frame, videos_to_show, max_items_to_show=MAX_THUMBNAILS_MAIN_GUI)
        if not self.background_video_path and self.all_video_templates: self.update_subtitle_preview_display()

    def highlight_selected_voice_avatar(self, technical_name_to_select): #OK
        # Desmarcar el botón previamente seleccionado
        if self.selected_voice_button_widget and self.selected_voice_button_widget.winfo_exists():
            self.selected_voice_button_widget.configure(border_width=0, fg_color=COLOR_BACKGROUND_WIDGET_INPUT)
        
        # Marcar el nuevo botón seleccionado (solo si está en el grid principal)
        self.selected_voice_button_widget = self.voice_buttons_map.get(technical_name_to_select)
        if self.selected_voice_button_widget and self.selected_voice_button_widget.winfo_exists():
            self.selected_voice_button_widget.configure(border_width=2, border_color=COLOR_BORDER_SELECTED, fg_color=COLOR_BUTTON_SECONDARY_HOVER)

    def select_voice_from_avatar(self, friendly_name, technical_name, button_widget_ref):
        self.update_selected_voice_technical_name(friendly_name); self.highlight_selected_voice_avatar(technical_name)

    def show_generating_video_popup(self):
        if hasattr(self, 'generating_popup') and self.generating_popup.winfo_exists(): self.generating_popup.focus(); self.generating_popup.grab_set(); return
        self.generating_popup = customtkinter.CTkToplevel(self)
        self.generating_popup.title("Processing Video"); self.generating_popup.geometry("480x380")
        self.generating_popup.attributes("-topmost", True); self.generating_popup.protocol("WM_DELETE_WINDOW", lambda: None)
        self.generating_popup.grab_set(); self.generating_popup.configure(fg_color=COLOR_BACKGROUND_MAIN)
        progress_bar = customtkinter.CTkProgressBar(self.generating_popup, mode="indeterminate", progress_color=COLOR_PRIMARY_ACTION)
        progress_bar.pack(pady=(25,15), padx=50, fill="x"); progress_bar.start()
        customtkinter.CTkLabel(self.generating_popup, text="GENERATING VIDEO", font=("Arial", 18, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(pady=10)
        customtkinter.CTkLabel(self.generating_popup, text="LOG:", font=("Arial", 12), anchor="w", text_color=COLOR_TEXT_SECONDARY).pack(fill="x", padx=25, pady=(10,2))
        self.generating_log_textbox = customtkinter.CTkTextbox(self.generating_popup, height=120, wrap="word", fg_color=COLOR_BACKGROUND_CARD, text_color=COLOR_TEXT_PRIMARY, corner_radius=CORNER_RADIUS_INPUT, border_color=COLOR_BACKGROUND_CARD)
        self.generating_log_textbox.pack(expand=True, fill="both", padx=25, pady=(0,25)); self.generating_log_textbox.configure(state="disabled")

    def update_generating_log(self, message: str):
        if hasattr(self, 'generating_log_textbox') and self.generating_log_textbox.winfo_exists(): self.generating_log_textbox.configure(state="normal"); self.generating_log_textbox.insert("end", message + "\n"); self.generating_log_textbox.see("end"); self.generating_log_textbox.configure(state="disabled")

    def hide_generating_video_popup(self):
        if hasattr(self, 'generating_popup'):
            for widget in self.generating_popup.winfo_children():
                if isinstance(widget, customtkinter.CTkProgressBar): widget.stop()
            self.generating_popup.grab_release(); self.generating_popup.destroy(); delattr(self, 'generating_popup')
            if hasattr(self, 'generating_log_textbox'): delattr(self, 'generating_log_textbox')

    def _reddit_fetch_worker(self, url: str):
        try: title, body = reddit_scraper.get_post_details(url); self.task_queue.put(lambda: self._update_gui_after_reddit_fetch(title, body))
        except Exception as e: self.task_queue.put(lambda: self._update_gui_after_reddit_fetch(None, None, error_msg=str(e)))
    def _update_gui_after_reddit_fetch(self, title: str | None, body: str | None, error_msg: str = None):
        self.story_textbox.delete("1.0", "end")
        if error_msg: self.story_textbox.insert("1.0", f"Err fetch:\n{error_msg}"); self.status_label.configure(text="Err fetch Reddit.")
        elif title is None or body is None or "Error" in title or "no encontrado" in title: full_story = f"{title if title else 'Err'}\n\n{body if body else 'No content.'}"; self.story_textbox.insert("1.0", full_story); self.status_label.configure(text="Non-std Reddit content.")
        else: self.story_textbox.insert("1.0", f"{title}\n\n{body}"); self.status_label.configure(text="Reddit story loaded.")
        self._enable_main_action_button()
        self._check_story_and_set_generate_button_state()
    def fetch_reddit_post_threaded(self):
        url = self.reddit_url_entry.get()
        if not url: self.status_label.configure(text="Err: Reddit URL empty."); return
        self.status_label.configure(text="Fetching Reddit..."); self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", "Loading Reddit story..."); self.update_idletasks()
        self._disable_main_action_button(); threading.Thread(target=self._reddit_fetch_worker, args=(url,), daemon=True).start()

    def _ai_story_worker(self, subject: str, style: str, max_tokens: int):
        try: story = ai_story_generator.generate_story(subject, style, max_tokens); self.task_queue.put(lambda: self._update_gui_after_ai_story(story, False))
        except Exception as e: self.task_queue.put(lambda: self._update_gui_after_ai_story(f"Err AI gen: {e}", True))
    def _update_gui_after_ai_story(self, story_or_error: str, is_error: bool):
        self.story_textbox.delete("1.0", "end"); self.story_textbox.insert("1.0", story_or_error)
        self.status_label.configure(text="AI Story: Err gen." if is_error else ("AI Story: " + story_or_error if story_or_error.startswith("Error:") else "AI Story: Generated!"))
        self._enable_main_action_button()
        self._check_story_and_set_generate_button_state() 

    def _play_audio_worker(self, audio_filepath: str, voice_name: str):
        try: playsound(audio_filepath, True)
        except Exception as e: self.task_queue.put(lambda: self._update_gui_after_sample_playback(voice_name, False, str(e)))
        else: self.task_queue.put(lambda: self._update_gui_after_sample_playback(voice_name, True))
    def _update_gui_after_sample_playback(self, voice_name:str, success:bool, error_msg:str = None):
        self.status_label.configure(text=f"Finished sample for '{voice_name}'." if success else f"Err playing sample for '{voice_name}': {error_msg}")
        state, fg = ("normal", COLOR_BACKGROUND_WIDGET_INPUT) if self.can_generate_audio else ("disabled", "grey50")
        if hasattr(self, 'test_voice_button'): self.test_voice_button.configure(state=state, fg_color=fg)
    def play_voice_sample_threaded(self):
        if not self.can_generate_audio or not self.selected_voice_technical_name: self.status_label.configure(text="Err: No TTS voice selected."); return
        friendly, tech = self.tts_voice_menu_var.get(), self.selected_voice_technical_name
        sample_path = os.path.join(VOICE_SAMPLE_DIR, f"{tech}.wav")
        if not os.path.exists(sample_path): self.status_label.configure(text=f"Sample for '{friendly.split('(')[0].strip()}' not found. Run generate_voice_samples.py."); return
        self.status_label.configure(text=f"Playing sample for '{friendly.split('(')[0].strip()}'..."); self.update_idletasks()
        if hasattr(self, 'test_voice_button'): self.test_voice_button.configure(state="disabled", fg_color="grey50")
        threading.Thread(target=self._play_audio_worker, args=(sample_path, friendly), daemon=True).start()

    def _process_all_worker(self, story_text, tts_voice_tech_name, bg_video_path, srt_max_words, subtitle_style_options, current_id):
        paths, current_step = {}, ""
        try:
            self.task_queue.put(self.show_generating_video_popup) # Mostrar popup
            self.task_queue.put(lambda: self.update_generating_log(f"ID del Proyecto: {current_id}"))

            current_step = "Generando Audio (TTS)"; self.task_queue.put(lambda msg=current_step: self.update_generating_log(f"Paso 1/4: {msg}..."))
            paths['audio'] = os.path.join(file_manager.AUDIO_DIR, f"{current_id}.wav")
            if not tts_kokoro_module.generate_speech_with_voice_name(story_text, tts_voice_tech_name, paths['audio']): raise Exception("Fallo en generación de audio TTS.")

            current_step = "Creando video narrado"; self.task_queue.put(lambda msg=current_step: self.update_generating_log(f"Paso 2/4: {msg}..."))
            paths['narr_vid'] = os.path.join(file_manager.NARRATED_VIDEO_DIR, f"{current_id}.mp4")
            if not video_processor.create_narrated_video(bg_video_path, paths['audio'], paths['narr_vid']): raise Exception("Fallo en creación del video narrado.")

            current_step = "Generando subtítulos SRT"; self.task_queue.put(lambda msg=current_step: self.update_generating_log(f"Paso 3/4: {msg}..."))
            paths['srt'] = os.path.join(file_manager.SRT_DIR, f"{current_id}.srt")
            if not srt_generator.create_srt_file(paths['audio'], paths['srt'], max_words_per_segment=srt_max_words): raise Exception("Fallo en generación del archivo SRT.")
            
            current_step = "Grabando subtítulos en video"; self.task_queue.put(lambda msg=current_step: self.update_generating_log(f"Paso 4/4: {msg}..."))
            paths['final'] = os.path.join(file_manager.FINAL_VIDEO_DIR, f"{current_id}_{tts_voice_tech_name}.mp4")
            if not video_processor.burn_subtitles_on_video(paths['narr_vid'], paths['srt'], paths['final'], style_options=subtitle_style_options): raise Exception("Fallo al grabar los subtítulos en el video.")
            
            self.task_queue.put(lambda: self._update_gui_after_all_processing(True, f"¡Video ({current_id}) completo! {os.path.abspath(paths['final'])}"))
        except Exception as e: 
            error_full_msg = f"Error en '{current_step}': {str(e)}"; print(error_full_msg); traceback.print_exc()
            self.task_queue.put(lambda err=error_full_msg: self._update_gui_after_all_processing(False, err)) # Pasar el mensaje de error completo
        finally: 
            self.task_queue.put(self.hide_generating_video_popup) # Ocultar popup

    def _update_gui_after_all_processing(self, success: bool, message: str):
        self.status_label.configure(text=message)
        if hasattr(self, 'generating_log_textbox') and self.generating_log_textbox.winfo_exists(): self.update_generating_log(f"Resultado Final: {message}")
        self._enable_main_action_button()
        self._check_story_and_set_generate_button_state()

    def process_all_steps_threaded(self): #OK
        # 1. Recoger el texto de la historia
        story_text = self.story_textbox.get("1.0", "end-1c").strip()
        placeholders = [
            "1. Obtén/Genera una historia aquí.", 
            "1. Fetch a story using the URL or generate one with AI.", # Placeholder de tu nueva UI
            "Cargando...", 
            "Generando IA (hilo)...",
            "Loading Reddit story...", # Placeholder de tu nueva UI
            "Generating AI story..." # Placeholder de tu nueva UI
        ]
        is_placeholder = any(story_text.startswith(p_start) for p_start in placeholders if p_start)
        if not story_text or is_placeholder: 
            self.status_label.configure(text="Error: No hay texto válido en la historia para procesar.")
            return

        # 2. Verificar la voz TTS seleccionada
        if not self.can_generate_audio or not self.selected_voice_technical_name: 
            self.status_label.configure(text="Error: Voz TTS no válida seleccionada.")
            return
        tts_voice_tech_name = self.selected_voice_technical_name # Ya se actualiza con update_selected_voice_technical_name o select_voice_from_avatar

        # 3. Verificar el video de fondo seleccionado
        if not self.background_video_path: 
            self.status_label.configure(text="Error: Selecciona un video de fondo de las plantillas.")
            return
        if not os.path.exists(self.background_video_path): 
            self.status_label.configure(text=f"Error: Video de fondo '{os.path.basename(self.background_video_path)}' no encontrado. Por favor, re-selecciónalo.")
            return
        bg_video_path = self.background_video_path
        
        # 4. Recoger configuración de SRT (Max words per segment)
        max_words_str = self.srt_max_words_var.get()
        srt_max_words = None 
        if max_words_str.isdigit(): 
            srt_max_words = int(max_words_str)
        elif max_words_str != "Whisper (Defecto)": 
            self.status_label.configure(text="Error SRT: Opción de 'Palabras Máx. por Segmento' inválida.")
            return

        # 5. Recoger opciones de estilo de subtítulos
        # La función _get_current_subtitle_style_options ya maneja la conversión a int/float y los defaults
        subtitle_style_options = self._get_current_subtitle_style_options()
        if not subtitle_style_options : # Si _get_current_subtitle_style_options devolvió None por un error
            self.status_label.configure(text="Error: Opciones de estilo de subtítulo inválidas (ej. tamaño/ancho de borde no numérico).")
            return
        
        # 6. Generar ID único para esta tanda de archivos
        current_id = file_manager.get_next_id_str()
        self.status_label.configure(text=f"Iniciando proceso completo para ID: {current_id}... (Ver Pop-up y consola para progreso)")
        self.update_idletasks()
        
        self._disable_main_action_button() # Desactivar botones principales de la GUI
        
        # 7. Lanzar el trabajador principal en un hilo
        master_thread = threading.Thread(
            target=self._process_all_worker,
            args=(story_text, tts_voice_tech_name, bg_video_path, srt_max_words, subtitle_style_options, current_id),
            daemon=True
        )
        master_thread.start()
        
    def open_view_all_voices_popup(self):
        if hasattr(self, 'all_voices_popup') and self.all_voices_popup.winfo_exists():
            self.all_voices_popup.focus()
            self.all_voices_popup.grab_set()
            return

        self.all_voices_popup = customtkinter.CTkToplevel(self)
        self.all_voices_popup.title("Choose a voice")
        self.all_voices_popup.geometry("720x600") # Ajusta según necesites
        self.all_voices_popup.attributes("-topmost", True)
        self.all_voices_popup.configure(fg_color=COLOR_BACKGROUND_MAIN)
        self.all_voices_popup.grab_set()

        customtkinter.CTkLabel(self.all_voices_popup, text="Choose a voice", font=("Arial", 18, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(pady=15)

        scrollable_frame = customtkinter.CTkScrollableFrame(self.all_voices_popup, fg_color=COLOR_BACKGROUND_MAIN, scrollbar_button_color=COLOR_BACKGROUND_CARD, scrollbar_button_hover_color=COLOR_BUTTON_SECONDARY_HOVER)
        scrollable_frame.pack(expand=True, fill="both", padx=20, pady=(0,10))
        for i in range(VOICE_AVATAR_GRID_COLUMNS_POPUP): # Configurar columnas para el grid
            scrollable_frame.grid_columnconfigure(i, weight=1)

        # Crear la lista de metadata para TODAS las voces disponibles para el popup
        all_voices_meta_for_popup = []
        for full_friendly_name, tech_name in self.available_voices_map.items():
            # Intentar encontrar metadata predefinida para la imagen, si no, usar un fallback.
            predefined_meta = next((vm for vm in self.desired_main_ui_voices_meta if vm["tech"] == tech_name), None)

            img_file = predefined_meta.get("img") if predefined_meta else f"{tech_name.split('_')[0]}.png" # ej. af.png, am.png o un default_avatar.png
            # El nombre corto no es crucial para el popup si mostramos el full_friendly_name en el botón

            lang_code_for_sentence = "en" # Default
            if "Español" in full_friendly_name: lang_code_for_sentence = "es"
            # Añade más lógicas de idioma si es necesario

            all_voices_meta_for_popup.append({
                "tech": tech_name,
                "friendly_name_full": full_friendly_name, # Usar este para el texto del botón en el popup
                "friendly_short": predefined_meta.get("friendly_short") if predefined_meta else tech_name, # Para consistencia de la estructura
                "img": img_file,
                "lang_code_for_sentence": lang_code_for_sentence
            })

        # Llamar a _display_voice_avatars_in_grid
        # Esta función ahora necesita tomar la lista de diccionarios completos.
        self._display_voice_avatars_in_grid(
            scrollable_frame, 
            all_voices_meta_for_popup, # Pasar la lista completa de metadata
            from_popup=True, 
            popup_window_ref=self.all_voices_popup
        )
        customtkinter.CTkButton(self.all_voices_popup, text="Close", command=lambda: (self.all_voices_popup.grab_release(), self.all_voices_popup.destroy(), delattr(self, 'all_voices_popup')), width=100).pack(pady=(5,10))

    def select_voice_from_popup(self, friendly_name, technical_name): # Stub - copy from previous
        print(f"select_voice_from_popup: {friendly_name}, {technical_name}")
        self.update_selected_voice_technical_name(friendly_name)
        self.highlight_selected_voice_avatar(technical_name)
        if hasattr(self, 'all_voices_popup'): self.all_voices_popup.grab_release(); self.all_voices_popup.destroy(); delattr(self, 'all_voices_popup')

    def open_view_all_videos_popup(self): # Stub - copy from previous
        print("open_view_all_videos_popup called")
        if not self.all_video_templates: self.status_label.configure(text="No video templates found."); return
        if hasattr(self, 'all_videos_main_popup') and self.all_videos_main_popup.winfo_exists(): self.all_videos_main_popup.focus(); self.all_videos_main_popup.grab_set(); return
        self.all_videos_main_popup = customtkinter.CTkToplevel(self)
        self.all_videos_main_popup.title("Choose a background video"); self.all_videos_main_popup.geometry("780x650")
        self.all_videos_main_popup.attributes("-topmost", True); self.all_videos_main_popup.configure(fg_color=COLOR_BACKGROUND_MAIN); self.all_videos_main_popup.grab_set()
        customtkinter.CTkLabel(self.all_videos_main_popup, text="Choose a background video", font=("Arial",18, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(pady=15)
        scrollable_frame = customtkinter.CTkScrollableFrame(self.all_videos_main_popup, fg_color=COLOR_BACKGROUND_MAIN, scrollbar_button_color=COLOR_BACKGROUND_CARD, scrollbar_button_hover_color=COLOR_BUTTON_SECONDARY_HOVER)
        scrollable_frame.pack(expand=True, fill="both", padx=20, pady=(0,20))
        for i in range(VIDEO_THUMBNAIL_GRID_COLUMNS): scrollable_frame.grid_columnconfigure(i, weight=1)
        self._display_thumbnails_in_grid(scrollable_frame, self.all_video_templates, max_items_to_show=len(self.all_video_templates), from_popup=True, popup_window_ref=self.all_videos_main_popup)


    def _display_thumbnails_in_grid(self, parent_frame, video_paths_to_display, max_items_to_show=None, from_popup=False, popup_window_ref=None): # Stub - copy
        print(f"_display_thumbnails_in_grid called for {'popup' if from_popup else 'main'}")
        for widget in parent_frame.winfo_children(): widget.destroy()
        videos_to_render = video_paths_to_display[:max_items_to_show] if max_items_to_show is not None else video_paths_to_display
        grid_cols = VIDEO_THUMBNAIL_GRID_COLUMNS; thumb_size_w, thumb_size_h = (160, 284) if from_popup else (128,227)
        row, col = 0, 0
        for video_path in videos_to_render:
            is_selected_video = (self.background_video_path == video_path)
            thumb_path = video_processor.get_or_create_thumbnail(video_path, size=(thumb_size_w, thumb_size_h))
            if thumb_path:
                try:
                    pil_image = Image.open(thumb_path); ctk_image = CTkImage(light_image=pil_image, dark_image=pil_image, size=(pil_image.width, pil_image.height))
                    item_frame = customtkinter.CTkFrame(parent_frame, fg_color="transparent")
                    item_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
                    thumb_button = customtkinter.CTkButton(item_frame, image=ctk_image, text="", width=pil_image.width, height=pil_image.height, fg_color=COLOR_BACKGROUND_CARD, hover_color=COLOR_BUTTON_SECONDARY_HOVER, corner_radius=CORNER_RADIUS_BUTTON, border_width=2 if is_selected_video else 0, border_color=COLOR_BORDER_SELECTED if is_selected_video else COLOR_BACKGROUND_CARD, command=lambda vp=video_path, pop_ref=popup_window_ref: self._select_video_from_thumbnail_internal(vp, from_popup, pop_ref))
                    thumb_button.pack(pady=(0,3))
                    customtkinter.CTkLabel(item_frame, text=os.path.basename(video_path), font=("Arial", 10), wraplength=pil_image.width - 5, text_color=COLOR_TEXT_SECONDARY).pack(fill="x")
                except Exception as e: print(f"Error displaying thumbnail {thumb_path}: {e}")
            col += 1
            if col >= grid_cols: col = 0; row += 1
        for i in range(grid_cols): parent_frame.grid_columnconfigure(i, weight=1)


    def _select_video_from_thumbnail_internal(self, video_path: str, from_popup: bool = False, popup_window_ref: customtkinter.CTkToplevel = None): # Stub - copy
        print(f"_select_video_from_thumbnail_internal: {video_path}")
        self.background_video_path = video_path; filename = os.path.basename(video_path)
        if hasattr(self, 'active_video_display_label'): self.active_video_display_label.configure(text=f"Selected: {filename}")
        self.status_label.configure(text=f"Background video: {filename}")
        thumb_path = video_processor.get_or_create_thumbnail(video_path, size=VIDEO_PREVIEW_THUMBNAIL_SIZE)
        self.current_video_thumbnail_for_composite_path = thumb_path; self.update_subtitle_preview_display()
        if from_popup and popup_window_ref and popup_window_ref.winfo_exists():
            popup_window_ref.grab_release(); popup_window_ref.destroy()
            if popup_window_ref == getattr(self, 'all_videos_main_popup', None): delattr(self, 'all_videos_main_popup')
        self.refresh_main_thumbnail_grid(newly_selected_path=video_path)
    
    def _is_story_valid(self) -> bool: 
        if not hasattr(self, 'story_textbox'): return False
        story_text = self.story_textbox.get("1.0", "end-1c").strip()
        placeholders = ["1. Obtén/Genera una historia aquí.", "1. Fetch a story using the URL or generate one with AI.", "Cargando...", "Generando IA (hilo)...", "Loading Reddit story...","Generando AI story..."]
        if not story_text or any(story_text.startswith(p_text) for p_text in placeholders if p_text): return False
        return True

    def _check_story_and_set_generate_button_state(self):
        if not hasattr(self, 'generate_video_button') or not self.generate_video_button.winfo_exists(): return
        if self.long_process_active: return # No cambiar estado si un proceso largo ya está activo
        
        is_ready = self._is_story_valid() and self.can_generate_audio and self.background_video_path and os.path.exists(self.background_video_path)
        self.generate_video_button.configure(state="normal" if is_ready else "disabled")
        self._update_generate_button_image()

    def _update_generate_button_image(self):
        if not hasattr(self, 'generate_video_button') or not self.generate_video_button.winfo_exists():
            return

        current_image_to_set = None
        button_state = self.generate_video_button.cget("state")
        
        # Determinar qué imagen usar basado en el estado
        if button_state == "disabled":
            current_image_to_set = self.generate_image_disabled
        elif self.generate_button_is_pressed: # Estado presionado
            current_image_to_set = self.generate_image_active
        elif self.mouse_is_over_generate_button: # Estado hover
            current_image_to_set = self.generate_image_hover
        else: # Estado normal (ni hover, ni presionado, ni disabled)
            current_image_to_set = self.generate_image_default

        # Fallback final si la imagen específica del estado no cargó pero la default sí
        if current_image_to_set is None and self.generate_image_default is not None:
            current_image_to_set = self.generate_image_default
        
        # Configurar el botón
        if current_image_to_set:
            # Si tenemos una imagen para mostrar
            self.generate_video_button.configure(
                image=current_image_to_set,
                text="",  # Sin texto cuando hay imagen
                fg_color=COLOR_BACKGROUND_MAIN,  # Usar el color de fondo del panel derecho
                hover_color=COLOR_BACKGROUND_MAIN # Usar el mismo para hover, la imagen es la que cambia
            )
        else:
            # Si NO hay ninguna imagen disponible (ni siquiera la default), usar texto y colores sólidos
            generate_button_text_fallback = "GENERAR VIDEO" # Texto si no hay imagen
            fg_color_for_text_button = COLOR_PRIMARY_ACTION if button_state == "normal" else "grey50"
            hover_color_for_text_button = COLOR_PRIMARY_ACTION_HOVER if button_state == "normal" else "grey50"
            
            self.generate_video_button.configure(
                image=None,
                text=generate_button_text_fallback,
                fg_color=fg_color_for_text_button,
                hover_color=hover_color_for_text_button
            )

    def _on_generate_button_enter(self, event):
        if not hasattr(self, 'generate_video_button') or not self.generate_video_button.winfo_exists(): return
        self.mouse_is_over_generate_button = True
        if self.generate_video_button.cget("state") == "normal": self._update_generate_button_image()
    def _on_generate_button_leave(self, event):
        if not hasattr(self, 'generate_video_button') or not self.generate_video_button.winfo_exists(): return
        self.mouse_is_over_generate_button = False
        if self.generate_video_button.cget("state") == "normal": self._update_generate_button_image()
    def _on_generate_button_press(self, event):
        if not hasattr(self, 'generate_video_button') or not self.generate_video_button.winfo_exists(): return
        if self.generate_video_button.cget("state") == "normal": self.generate_button_is_pressed = True; self._update_generate_button_image()
    def _on_generate_button_release(self, event):
        if not hasattr(self, 'generate_video_button') or not self.generate_video_button.winfo_exists(): return
        if self.generate_button_is_pressed: self.generate_button_is_pressed = False
        # Llamar al comando solo si el botón seguía presionado y está normal
        if self.generate_video_button.cget("state") == "normal": 
            self._update_generate_button_image()
            # El comando self.process_all_steps_threaded() se llama por el click normal,
            # no es necesario invocarlo aquí de nuevo a menos que se quiera un comportamiento de "click en release".
                
    def _load_all_available_voices(self): #OK
        """Carga las voces y establece una por defecto si no hay ninguna seleccionada."""
        self.available_voices_map = tts_kokoro_module.list_available_kokoro_voices()
        self.voice_friendly_names_full = list(self.available_voices_map.keys()) # Nombres amigables completos

        if not self.selected_voice_technical_name and self.active_main_ui_voices_meta:
            # Si no hay nada seleccionado, selecciona la primera de la lista de UI principal activa
            first_voice_to_select_meta = self.active_main_ui_voices_meta[0]
            # Encontrar el nombre amigable completo para este nombre técnico
            full_friendly_name = ""
            for fn, tn in self.available_voices_map.items():
                if tn == first_voice_to_select_meta["tech"]:
                    full_friendly_name = fn
                    break
            if full_friendly_name:
                self._select_voice_internal(full_friendly_name, first_voice_to_select_meta["tech"])
        
        self.can_generate_audio = bool(self.selected_voice_technical_name)
        if hasattr(self, 'test_voice_button'): # Asegurarse que el botón existe
            self.test_voice_button.configure(state="normal" if self.can_generate_audio else "disabled", 
                                             fg_color=COLOR_BACKGROUND_WIDGET_INPUT if self.can_generate_audio else "grey50")


    def _display_voice_avatars_in_grid(self, parent_frame, voice_meta_list_to_display, from_popup=False, popup_window_ref=None):
        for widget in parent_frame.winfo_children(): widget.destroy()
        if not from_popup: self.voice_buttons_map.clear()

        grid_cols = VOICE_AVATAR_GRID_COLUMNS_POPUP if from_popup else VOICE_AVATAR_GRID_COLUMNS_MAIN
        avatar_size = (50,50) if from_popup else (45,45) # Puedes ajustar
        button_width = 150 if from_popup else 110 # Ancho de botón para popup puede ser mayor
        button_height = 100 if from_popup else 75 # Alto de botón

        row, col = 0, 0
        for voice_meta in voice_meta_list_to_display:
            tech_name = voice_meta["tech"]

            # Determinar el nombre a mostrar en el botón
            if from_popup:
                display_name_on_button = voice_meta.get("friendly_name_full", tech_name) # En popup, mostrar nombre completo
            else:
                display_name_on_button = voice_meta.get("friendly_short", tech_name) # En UI principal, nombre corto

            img_file = voice_meta.get("img", f"{tech_name}.png") # Fallback si no hay 'img'

            avatar_ctk_image = None
            try:
                avatar_path = os.path.join(self.VOICE_AVATAR_PATH, img_file)
                if os.path.exists(avatar_path):
                    pil_img = Image.open(avatar_path).convert("RGBA")
                    avatar_ctk_image = CTkImage(pil_img, size=avatar_size)
                else: 
                    # print(f"Avatar no encontrado para {display_name_on_button}: {avatar_path}") # Opcional: placeholder
                    pass
            except Exception as e: 
                print(f"Error cargando avatar {img_file} para {display_name_on_button}: {e}")

            voice_button = customtkinter.CTkButton(
                parent_frame, text=display_name_on_button, image=avatar_ctk_image, compound="top",
                fg_color=COLOR_BACKGROUND_WIDGET_INPUT, hover_color=COLOR_BUTTON_SECONDARY_HOVER,
                corner_radius=CORNER_RADIUS_BUTTON, width=button_width, height=button_height,
                text_color=COLOR_TEXT_SECONDARY, 
                font=("Arial", 10 if from_popup else 11),
                # El comando pasa el 'voice_meta' completo
                command=lambda vm=voice_meta, pop_ref=popup_window_ref: self._select_voice_from_avatar(vm, from_popup, pop_ref)
            )
            voice_button.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            if not from_popup:
                self.voice_buttons_map[tech_name] = voice_button

            col += 1
            if col >= grid_cols: col = 0; row += 1

        for i in range(grid_cols): parent_frame.grid_columnconfigure(i, weight=1)


    def _select_voice_internal(self, full_friendly_name: str, technical_name: str): #OK
        """Función interna para actualizar el estado de la voz seleccionada."""
        self.selected_voice_friendly_name_full = full_friendly_name
        self.selected_voice_technical_name = technical_name
        self.can_generate_audio = True
        
        status_display_name = full_friendly_name.split(" (")[0].strip() # Nombre más corto para el status
        self.status_label.configure(text=f"Voz TTS seleccionada: {status_display_name}")
        
        if hasattr(self, 'test_voice_button'): self.test_voice_button.configure(state="normal", fg_color=COLOR_BACKGROUND_WIDGET_INPUT)
        self._check_story_and_set_generate_button_state() # Actualizar estado del botón principal


    def _select_voice_from_avatar(self, voice_meta: dict, from_popup: bool = False, popup_window_ref: customtkinter.CTkToplevel = None):
        tech_name = voice_meta["tech"]
        # Usar el nombre amigable completo para la lógica interna y el status label
        full_friendly_name = voice_meta.get("friendly_name_full")

        # Intentar encontrar el nombre amigable completo desde el mapa principal si no vino en voice_meta
        if not full_friendly_name:
            for fn_map, tn_map in self.available_voices_map.items():
                if tn_map == tech_name:
                    full_friendly_name = fn_map
                    break

        if not full_friendly_name: # Fallback si sigue sin encontrarse
            full_friendly_name = voice_meta.get("friendly_short", tech_name)


        self._select_voice_internal(full_friendly_name, tech_name) # Actualizar estado interno
        self.highlight_selected_voice_avatar(tech_name) # Resaltar en la UI principal

        if from_popup and popup_window_ref and popup_window_ref.winfo_exists():
            popup_window_ref.grab_release()
            popup_window_ref.destroy()
            if popup_window_ref == getattr(self, 'all_voices_popup', None): # Limpiar atributo si es este popup
                delattr(self, 'all_voices_popup')

            # Lógica para actualizar la primera tarjeta de la UI principal
            is_already_in_main_grid_desired = any(vm["tech"] == tech_name for vm in self.desired_main_ui_voices_meta)

            if not is_already_in_main_grid_desired:
                # La voz seleccionada no está en la lista de "deseadas para la UI principal".
                # Reemplazar la primera de la lista activa.
                new_voice_meta_for_main_grid = {
                    "tech": tech_name,
                    # Usar el 'friendly_short' de voice_meta si existe, si no, construir uno.
                    "friendly_short": voice_meta.get("friendly_short", full_friendly_name.split(" (")[0].split(" ")[-1]),
                    "img": voice_meta.get("img", f"{tech_name}.png"), # Usar imagen de voice_meta
                    "lang_code_for_sentence": voice_meta.get("lang_code_for_sentence", "en")
                }
                if self.active_main_ui_voices_meta: # Si la lista activa no está vacía
                    print(f"PopUp Selection: Reemplazando '{self.active_main_ui_voices_meta[0]['tech']}' con '{tech_name}' en el grid principal.")
                    self.active_main_ui_voices_meta[0] = new_voice_meta_for_main_grid
                else: # Si estaba vacía, simplemente añadirla
                    self.active_main_ui_voices_meta = [new_voice_meta_for_main_grid]

                self.refresh_main_voice_avatar_grid(newly_selected_voice_tech_name=tech_name)
            else: # Si ya está en la lista de deseadas (y por ende en active_main_ui_voices_meta), solo refrescar
                self.refresh_main_voice_avatar_grid(newly_selected_voice_tech_name=tech_name)

        elif not from_popup: 
            self.refresh_main_voice_avatar_grid(newly_selected_voice_tech_name=tech_name)


    def refresh_main_voice_avatar_grid(self, newly_selected_voice_tech_name: str = None): #OK
        """Refresca la rejilla principal de avatares de voz."""
        if not hasattr(self, 'voice_thumbnail_grid_main'): return
        
        # Si se acaba de seleccionar una nueva voz (ej. del popup) y no está en la lista principal visible,
        # la ponemos al principio.
        if newly_selected_voice_tech_name:
            is_in_active_list = any(vm["tech"] == newly_selected_voice_tech_name for vm in self.active_main_ui_voices_meta)
            if not is_in_active_list:
                # Encontrar la metadata completa de esta voz (del available_voices_map y desired_main_ui_voices_meta si es posible)
                # Esto asume que self.desired_main_ui_voices_meta tiene una estructura con 'img' y 'friendly_short'
                # o que podemos construirla.
                new_voice_meta_for_main = None
                # Primero buscar en las voces "deseadas" si tiene una entrada completa
                for vm_desired in self.desired_main_ui_voices_meta:
                    if vm_desired["tech"] == newly_selected_voice_tech_name:
                        new_voice_meta_for_main = vm_desired
                        break
                if not new_voice_meta_for_main: # Si no, construir una básica
                    new_voice_meta_for_main = {
                        "tech": newly_selected_voice_tech_name,
                        "friendly_short": self.selected_voice_friendly_name_full.split(" (")[0].split(" ")[-1], # Nombre corto
                        "img": f"{newly_selected_voice_tech_name}.png" # Asumir nombre de imagen
                    }

                if self.active_main_ui_voices_meta:
                    self.active_main_ui_voices_meta.pop(0) # Quitar el primero
                    self.active_main_ui_voices_meta.insert(0, new_voice_meta_for_main) # Insertar el nuevo al inicio
                else: # Si estaba vacía, simplemente añadirlo
                    self.active_main_ui_voices_meta = [new_voice_meta_for_main]
        
        self._display_voice_avatars_in_grid(
            self.voice_thumbnail_grid_main, 
            self.active_main_ui_voices_meta[:VOICE_AVATAR_GRID_COLUMNS_MAIN * 2] # Mostrar hasta 2 filas
        )
        if self.selected_voice_technical_name: # Re-aplicar resaltado después de redibujar
            self.highlight_selected_voice_avatar(self.selected_voice_technical_name)


if __name__ == "__main__":
    app = App()
    app.mainloop()