# main.py
import customtkinter
from customtkinter import filedialog, CTkImage # CTkImage ya está aquí
from PIL import Image, ImageTk # Asegúrate de que ImageTk esté importado aquí
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

        self.title("AI Reddit Video Generator")
        self.geometry("1400x900")
        self.configure(fg_color=COLOR_BACKGROUND_MAIN)
        
        self.ASSETS_BASE_PATH = "assets/"
        self.VOICE_AVATAR_PATH = os.path.join(self.ASSETS_BASE_PATH, "avatars/")
        self.APP_ICON_PATH = os.path.join(self.ASSETS_BASE_PATH, "RedditVidGen_Logo.ico") # Cambiado a .ico
        self.long_process_active = False

        self.BUTTONS_ASSETS_PATH = os.path.join(self.ASSETS_BASE_PATH, "buttons/")
        self.PHONE_FRAME_IMAGE_PATH = os.path.join(self.ASSETS_BASE_PATH, "phoneframe.png")
        self.phone_frame_template_pil = None

        # Set application icon
        try:
            if os.path.exists(self.APP_ICON_PATH):
                # Para las ventanas emergentes, aún necesitamos el PhotoImage
                self._pil_app_icon = Image.open(self.APP_ICON_PATH) # Mantener una referencia a la imagen PIL
                self.app_icon_photoimage = ImageTk.PhotoImage(self._pil_app_icon) # Usar la imagen PIL referenciada
                
                # Para la ventana principal, intentar iconbitmap directamente.
                # Esto podría ser más estable en algunas configuraciones de Windows si PhotoImage es problemático.
                self.iconbitmap(self.APP_ICON_PATH)
                print(f"Application icon set for main window using iconbitmap: {self.APP_ICON_PATH}")
                # Las ventanas emergentes usarán self.app_icon_photoimage mediante iconphoto(False, ...)
            else:
                print(f"Warning: Application icon not found at {self.APP_ICON_PATH}")
        except Exception as e:
            print(f"Error setting application icon: {e}"); traceback.print_exc()

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
        self.selected_voice_button_widget = None
        self.voice_buttons_map = {}
        self.active_main_ui_voices_meta = [] # Voces actualmente mostradas en la UI principal

        self.subtitle_font_color_hex = "#FFFF00"
        self.subtitle_stroke_color_hex = "#000000"

        # Definiciones de fuentes:
        # Clave: Nombre de familia para la UI
        # Valor: Diccionario con:
        #   "styles": {UI_Style_Name: MoviePy_Font_Name, ...}
        #   "source": "moviepy_list" (confirmada por MoviePy) o "user_request_convention" (no confirmada)
        self.font_definitions = {
            # Fuentes confirmadas por MoviePy (basado en la lista del usuario)
            "Agency FB": {
                "styles": {"Regular": "Agency-FB", "Bold": "Agency-FB-Bold"},
                "source": "moviepy_list"
            },
            "Algerian": {
                "styles": {"Regular": "Algerian"}, "source": "moviepy_list"
            },
            "Arial": {
                "styles": {
                    "Regular": "Arial", "Black": "Arial-Black", "Bold": "Arial-Bold",
                    "Bold Italic": "Arial-Bold-Italic", "Italic": "Arial-Italic"
                }, "source": "moviepy_list"
            },
            "Arial Narrow": {
                "styles": {
                    "Regular": "Arial-Narrow", "Bold": "Arial-Narrow-Bold",
                    "Bold Italic": "Arial-Narrow-Bold-Italic", "Italic": "Arial-Narrow-Italic"
                }, "source": "moviepy_list"
            },
            "Arial Rounded MT Bold": { # Considerado familia única ya que no hay "Arial-Rounded-MT" regular en la lista
                "styles": {"Regular": "Arial-Rounded-MT-Bold"}, "source": "moviepy_list"
            },
            "Bahnschrift": {
                "styles": {"Regular": "Bahnschrift"}, "source": "moviepy_list"
            },
            "Baskerville Old Face": {
                "styles": {"Regular": "Baskerville-Old-Face"}, "source": "moviepy_list"
            },
            "Bauhaus 93": {
                "styles": {"Regular": "Bauhaus-93"}, "source": "moviepy_list"
            },
            "Bell MT": {
                "styles": {"Regular": "Bell-MT", "Bold": "Bell-MT-Bold", "Italic": "Bell-MT-Italic"},
                "source": "moviepy_list"
            },
            "Berlin Sans FB": {
                "styles": {"Regular": "Berlin-Sans-FB", "Bold": "Berlin-Sans-FB-Bold", "Demi Bold": "Berlin-Sans-FB-Demi-Bold"},
                "source": "moviepy_list"
            },
            "Bernard MT Condensed": {
                "styles": {"Regular": "Bernard-MT-Condensed"}, "source": "moviepy_list"
            },
            "Blackadder ITC": {
                "styles": {"Regular": "Blackadder-ITC"}, "source": "moviepy_list"
            },
            "Bodoni MT": {
                "styles": {
                    "Regular": "Bodoni-MT", "Black": "Bodoni-MT-Black", "Black Italic": "Bodoni-MT-Black-Italic",
                    "Bold": "Bodoni-MT-Bold", "Bold Italic": "Bodoni-MT-Bold-Italic", "Italic": "Bodoni-MT-Italic"
                }, "source": "moviepy_list"
            },
            "Bodoni MT Condensed": {
                "styles": {
                    "Regular": "Bodoni-MT-Condensed", "Bold": "Bodoni-MT-Condensed-Bold",
                    "Bold Italic": "Bodoni-MT-Condensed-Bold-Italic", "Italic": "Bodoni-MT-Condensed-Italic"
                }, "source": "moviepy_list"
            },
            "Bodoni MT Poster Compressed": {
                "styles": {"Regular": "Bodoni-MT-Poster-Compressed"}, "source": "moviepy_list"
            },
            "Book Antiqua": {
                "styles": {"Regular": "Book-Antiqua", "Bold": "Book-Antiqua-Bold", "Bold Italic": "Book-Antiqua-Bold-Italic", "Italic": "Book-Antiqua-Italic"},
                "source": "moviepy_list"
            },
            "Bookman Old Style": {
                "styles": {"Regular": "Bookman-Old-Style", "Bold": "Bookman-Old-Style-Bold", "Bold Italic": "Bookman-Old-Style-Bold-Italic", "Italic": "Bookman-Old-Style-Italic"},
                "source": "moviepy_list"
            },
            "Bookshelf Symbol 7": {
                "styles": {"Regular": "Bookshelf-Symbol-7"}, "source": "moviepy_list"
            },
            "Bradley Hand ITC": {
                "styles": {"Regular": "Bradley-Hand-ITC"}, "source": "moviepy_list"
            },
            "Britannic Bold": {
                "styles": {"Regular": "Britannic-Bold"}, "source": "moviepy_list"
            },
            "Broadway": {
                "styles": {"Regular": "Broadway"}, "source": "moviepy_list"
            },
            "Brush Script MT Italic": { # Considerado familia única
                "styles": {"Regular": "Brush-Script-MT-Italic"}, "source": "moviepy_list"
            },
            "Calibri": {
                "styles": {"Regular": "Calibri", "Bold": "Calibri-Bold", "Bold Italic": "Calibri-Bold-Italic", "Italic": "Calibri-Italic", "Light": "Calibri-Light", "Light Italic": "Calibri-Light-Italic"},
                "source": "moviepy_list"
            },
            "Californian FB": {
                "styles": {"Regular": "Californian-FB", "Bold": "Californian-FB-Bold", "Italic": "Californian-FB-Italic"},
                "source": "moviepy_list"
            },
            "Calisto MT": {
                "styles": {"Regular": "Calisto-MT", "Bold": "Calisto-MT-Bold", "Bold Italic": "Calisto-MT-Bold-Italic", "Italic": "Calisto-MT-Italic"},
                "source": "moviepy_list"
            },
            "Cambria & Cambria Math": { # Nombre largo como familia
                "styles": {"Regular": "Cambria-&-Cambria-Math"}, "source": "moviepy_list"
            },
            "Cambria": {
                "styles": {"Regular": "Cambria", "Bold": "Cambria-Bold", "Bold Italic": "Cambria-Bold-Italic", "Italic": "Cambria-Italic"},
                "source": "moviepy_list"
            },
            "Candara": {
                "styles": {"Regular": "Candara", "Bold": "Candara-Bold", "Bold Italic": "Candara-Bold-Italic", "Italic": "Candara-Italic", "Light": "Candara-Light", "Light Italic": "Candara-Light-Italic"},
                "source": "moviepy_list"
            },
            "Cascadia Code Regular": {
                "styles": {"Regular": "Cascadia-Code-Regular"}, "source": "moviepy_list"
            },
            "Cascadia Mono Regular": {
                "styles": {"Regular": "Cascadia-Mono-Regular"}, "source": "moviepy_list"
            },
            "Castellar": {"styles": {"Regular": "Castellar"}, "source": "moviepy_list"},
            "Centaur": {"styles": {"Regular": "Centaur"}, "source": "moviepy_list"},
            "Century": {"styles": {"Regular": "Century"}, "source": "moviepy_list"},
            "Century Gothic": {
                "styles": {"Regular": "Century-Gothic", "Bold": "Century-Gothic-Bold", "Bold Italic": "Century-Gothic-Bold-Italic", "Italic": "Century-Gothic-Italic"},
                "source": "moviepy_list"
            },
            "Century Schoolbook": {
                "styles": {"Regular": "Century-Schoolbook", "Bold": "Century-Schoolbook-Bold", "Bold Italic": "Century-Schoolbook-Bold-Italic", "Italic": "Century-Schoolbook-Italic"},
                "source": "moviepy_list"
            },
            "Chiller": {"styles": {"Regular": "Chiller"}, "source": "moviepy_list"},
            "Colonna MT": {"styles": {"Regular": "Colonna-MT"}, "source": "moviepy_list"},
            "Comic Sans MS": {
                "styles": {"Regular": "Comic-Sans-MS", "Bold": "Comic-Sans-MS-Bold", "Bold Italic": "Comic-Sans-MS-Bold-Italic", "Italic": "Comic-Sans-MS-Italic"},
                "source": "moviepy_list"
            },
            "Consolas": {
                "styles": {"Regular": "Consolas", "Bold": "Consolas-Bold", "Bold Italic": "Consolas-Bold-Italic", "Italic": "Consolas-Italic"},
                "source": "moviepy_list"
            },
            "Constantia": {
                "styles": {"Regular": "Constantia", "Bold": "Constantia-Bold", "Bold Italic": "Constantia-Bold-Italic", "Italic": "Constantia-Italic"},
                "source": "moviepy_list"
            },
            "Cooper Black": {"styles": {"Regular": "Cooper-Black"}, "source": "moviepy_list"},
            "Copperplate Gothic Bold": {"styles": {"Regular": "Copperplate-Gothic-Bold"}, "source": "moviepy_list"}, # Asumiendo familia única
            "Copperplate Gothic Light": {"styles": {"Regular": "Copperplate-Gothic-Light"}, "source": "moviepy_list"}, # Asumiendo familia única
            "Corbel": {
                "styles": {"Regular": "Corbel", "Bold": "Corbel-Bold", "Bold Italic": "Corbel-Bold-Italic", "Italic": "Corbel-Italic", "Light": "Corbel-Light", "Light Italic": "Corbel-Light-Italic"},
                "source": "moviepy_list"
            },
            "Courier New": { # Ya estaba, confirmado
                "styles": {"Regular": "Courier-New", "Bold": "Courier-New-Bold", "Bold Italic": "Courier-New-Bold-Italic", "Italic": "Courier-New-Italic"},
                "source": "moviepy_list"
            },
            "Curlz MT": {"styles": {"Regular": "Curlz-MT"}, "source": "moviepy_list"},
            "Dubai": { # MoviePy lista "Dubai-Bold", "Dubai-Light", "Dubai-Medium", "Dubai-Regular"
                "styles": {"Bold": "Dubai-Bold", "Light": "Dubai-Light", "Medium": "Dubai-Medium", "Regular": "Dubai-Regular"},
                "source": "moviepy_list"
            },
            "Ebrima": {
                "styles": {"Regular": "Ebrima", "Bold": "Ebrima-Bold"}, "source": "moviepy_list"
            },
            "Edwardian Script ITC": {"styles": {"Regular": "Edwardian-Script-ITC"}, "source": "moviepy_list"},
            "Elephant": {
                "styles": {"Regular": "Elephant", "Italic": "Elephant-Italic"}, "source": "moviepy_list"
            },
            "Engravers MT": {"styles": {"Regular": "Engravers-MT"}, "source": "moviepy_list"},
            "Eras ITC": { # Agrupando Eras. MoviePy: Eras-Bold-ITC, Eras-Demi-ITC, Eras-Light-ITC, Eras-Medium-ITC
                "styles": {"Bold": "Eras-Bold-ITC", "Demi": "Eras-Demi-ITC", "Light": "Eras-Light-ITC", "Medium": "Eras-Medium-ITC"},
                "source": "moviepy_list"
            },
            "Felix Titling": {"styles": {"Regular": "Felix-Titling"}, "source": "moviepy_list"},
            "Footlight MT Light": {"styles": {"Regular": "Footlight-MT-Light"}, "source": "moviepy_list"},
            "Forte": {"styles": {"Regular": "Forte"}, "source": "moviepy_list"},
            "Franklin Gothic Book": { # Franklin Gothic es complejo. Agrupando por sub-familias.
                "styles": {"Regular": "Franklin-Gothic-Book", "Italic": "Franklin-Gothic-Book-Italic"}, "source": "moviepy_list"
            },
            "Franklin Gothic Demi": {
                "styles": {"Regular": "Franklin-Gothic-Demi", "Cond": "Franklin-Gothic-Demi-Cond", "Italic": "Franklin-Gothic-Demi-Italic"}, "source": "moviepy_list"
            },
            "Franklin Gothic Heavy": {
                "styles": {"Regular": "Franklin-Gothic-Heavy", "Italic": "Franklin-Gothic-Heavy-Italic"}, "source": "moviepy_list"
            },
            "Franklin Gothic Medium": {
                "styles": {"Regular": "Franklin-Gothic-Medium", "Cond": "Franklin-Gothic-Medium-Cond", "Italic": "Franklin-Gothic-Medium-Italic"}, "source": "moviepy_list"
            },
            "Freestyle Script": {"styles": {"Regular": "Freestyle-Script"}, "source": "moviepy_list"},
            "French Script MT": {"styles": {"Regular": "French-Script-MT"}, "source": "moviepy_list"},
            "Gabriola": {"styles": {"Regular": "Gabriola"}, "source": "moviepy_list"},
            "Gadugi": {
                "styles": {"Regular": "Gadugi", "Bold": "Gadugi-Bold"}, "source": "moviepy_list"
            },
            "Garamond": {
                "styles": {"Regular": "Garamond", "Bold": "Garamond-Bold", "Italic": "Garamond-Italic"}, "source": "moviepy_list"
            },
            "Georgia": {
                "styles": {"Regular": "Georgia", "Bold": "Georgia-Bold", "Bold Italic": "Georgia-Bold-Italic", "Italic": "Georgia-Italic"}, "source": "moviepy_list"
            },
            "Gigi": {"styles": {"Regular": "Gigi"}, "source": "moviepy_list"},
            "Gill Sans MT": {
                "styles": {"Regular": "Gill-Sans-MT", "Bold": "Gill-Sans-MT-Bold", "Bold Italic": "Gill-Sans-MT-Bold-Italic", "Condensed": "Gill-Sans-MT-Condensed", "Italic": "Gill-Sans-MT-Italic"},
                "source": "moviepy_list" # Ext-Condensed-Bold y Ultra-Bold como familias separadas
            },
            "Gill Sans MT Ext Condensed Bold": {"styles": {"Regular": "Gill-Sans-MT-Ext-Condensed-Bold"}, "source": "moviepy_list"},
            "Gill Sans Ultra Bold": {"styles": {"Regular": "Gill-Sans-Ultra-Bold"}, "source": "moviepy_list"},
            "Gill Sans Ultra Bold Condensed": {"styles": {"Regular": "Gill-Sans-Ultra-Bold-Condensed"}, "source": "moviepy_list"},
            "Gloucester MT Extra Condensed": {"styles": {"Regular": "Gloucester-MT-Extra-Condensed"}, "source": "moviepy_list"},
            "Goudy Old Style": {
                "styles": {"Regular": "Goudy-Old-Style", "Bold": "Goudy-Old-Style-Bold", "Italic": "Goudy-Old-Style-Italic"}, "source": "moviepy_list"
            },
            "Goudy Stout": {"styles": {"Regular": "Goudy-Stout"}, "source": "moviepy_list"},
            "Haettenschweiler": {"styles": {"Regular": "Haettenschweiler"}, "source": "moviepy_list"},
            "Harlow Solid Italic": {"styles": {"Regular": "Harlow-Solid-Italic"}, "source": "moviepy_list"},
            "Harrington": {"styles": {"Regular": "Harrington"}, "source": "moviepy_list"},
            "High Tower Text": {
                "styles": {"Regular": "High-Tower-Text", "Italic": "High-Tower-Text-Italic"}, "source": "moviepy_list"
            },
            "Holo MDL2 Assets": {"styles": {"Regular": "Holo-MDL2-Assets"}, "source": "moviepy_list"},
            "Impact": {
                "styles": {"Regular": "Impact"}, "source": "moviepy_list"
            },
             "Imprint MT Shadow": {"styles": {"Regular": "Imprint-MT-Shadow"}, "source": "moviepy_list"},
            "Informal Roman": {"styles": {"Regular": "Informal-Roman"}, "source": "moviepy_list"},
            "Ink Free": {"styles": {"Regular": "Ink-Free"}, "source": "moviepy_list"},
            "Javanese Text": {"styles": {"Regular": "Javanese-Text"}, "source": "moviepy_list"},
            "Jokerman": {"styles": {"Regular": "Jokerman"}, "source": "moviepy_list"},
            "Juice ITC": {"styles": {"Regular": "Juice-ITC"}, "source": "moviepy_list"},
            "Kristen ITC": {"styles": {"Regular": "Kristen-ITC"}, "source": "moviepy_list"},
            "Kunstler Script": {"styles": {"Regular": "Kunstler-Script"}, "source": "moviepy_list"},
            "Leelawadee UI": {
                "styles": {"Regular": "Leelawadee-UI", "Bold": "Leelawadee-UI-Bold", "Semilight": "Leelawadee-UI-Semilight"}, "source": "moviepy_list"
            },
            "Lucida Bright": {"styles": {"Regular": "Lucida-Bright"}, "source": "moviepy_list"}, # No hay variantes en la lista
            "Lucida Calligraphy Italic": {"styles": {"Regular": "Lucida-Calligraphy-Italic"}, "source": "moviepy_list"},
            "Lucida Console": {"styles": {"Regular": "Lucida-Console"}, "source": "moviepy_list"},
            "Lucida Fax": { # MoviePy: Lucida-Fax-Demibold, Lucida-Fax-Demibold-Italic, Lucida-Fax-Italic, Lucida-Fax-Regular
                "styles": {"Demibold": "Lucida-Fax-Demibold", "Demibold Italic": "Lucida-Fax-Demibold-Italic", "Italic": "Lucida-Fax-Italic", "Regular": "Lucida-Fax-Regular"},
                "source": "moviepy_list"
            },
            "Lucida Handwriting Italic": {"styles": {"Regular": "Lucida-Handwriting-Italic"}, "source": "moviepy_list"},
            "Lucida Sans": { # MoviePy: Lucida-Sans-Demibold-Italic, Lucida-Sans-Demibold-Roman, Lucida-Sans-Italic
                "styles": {"Demibold Italic": "Lucida-Sans-Demibold-Italic", "Demibold Roman": "Lucida-Sans-Demibold-Roman", "Italic": "Lucida-Sans-Italic"},
                "source": "moviepy_list" # Asumiendo que "Lucida-Sans" (regular) no está, o se agrupa aquí.
            },
            "Lucida Sans Typewriter": { # MoviePy: Lucida-Sans-Typewriter-Bold-Oblique, Lucida-Sans-Typewriter-Oblique
                "styles": {"Bold Oblique": "Lucida-Sans-Typewriter-Bold-Oblique", "Oblique": "Lucida-Sans-Typewriter-Oblique"},
                "source": "moviepy_list"
            },
            "Lucida Sans Unicode": {"styles": {"Regular": "Lucida-Sans-Unicode"}, "source": "moviepy_list"},
            "MS Gothic & MS UI Gothic & MS PGothic": {"styles": {"Regular": "MS-Gothic-&-MS-UI-Gothic-&-MS-PGothic"}, "source": "moviepy_list"},
            "MS Outlook": {"styles": {"Regular": "MS-Outlook"}, "source": "moviepy_list"},
            "MS Reference Sans Serif": {"styles": {"Regular": "MS-Reference-Sans-Serif"}, "source": "moviepy_list"},
            "MS Reference Specialty": {"styles": {"Regular": "MS-Reference-Specialty"}, "source": "moviepy_list"},
            "MT Extra": {"styles": {"Regular": "MT-Extra"}, "source": "moviepy_list"},
            "MV Boli": {"styles": {"Regular": "MV-Boli"}, "source": "moviepy_list"},
            "Magneto Bold": {"styles": {"Regular": "Magneto-Bold"}, "source": "moviepy_list"},
            "Maiandra GD": {"styles": {"Regular": "Maiandra-GD"}, "source": "moviepy_list"},
            "Malgun Gothic": { # MoviePy: Malgun-Gothic, Malgun-Gothic-Bold, Malgun-Gothic-SemiLight
                "styles": {"Regular": "Malgun-Gothic", "Bold": "Malgun-Gothic-Bold", "Semilight": "Malgun-Gothic-SemiLight"},
                "source": "moviepy_list"
            },
            "Matura MT Script Capitals": {"styles": {"Regular": "Matura-MT-Script-Capitals"}, "source": "moviepy_list"},
            "Microsoft Himalaya": {"styles": {"Regular": "Microsoft-Himalaya"}, "source": "moviepy_list"},
            "Microsoft JhengHei & Microsoft JhengHei UI": {"styles": {"Regular": "Microsoft-JhengHei-&-Microsoft-JhengHei-UI"}, "source": "moviepy_list"},
            "Microsoft JhengHei Bold & Microsoft JhengHei UI Bold": {"styles": {"Regular": "Microsoft-JhengHei-Bold-&-Microsoft-JhengHei-UI-Bold"}, "source": "moviepy_list"},
            "Microsoft JhengHei Light & Microsoft JhengHei UI Light": {"styles": {"Regular": "Microsoft-JhengHei-Light-&-Microsoft-JhengHei-UI-Light"}, "source": "moviepy_list"},
            "Microsoft New Tai Lue": {
                "styles": {"Regular": "Microsoft-New-Tai-Lue", "Bold": "Microsoft-New-Tai-Lue-Bold"}, "source": "moviepy_list"
            },
            "Microsoft PhagsPa": {
                "styles": {"Regular": "Microsoft-PhagsPa", "Bold": "Microsoft-PhagsPa-Bold"}, "source": "moviepy_list"
            },
            "Microsoft Sans Serif": {"styles": {"Regular": "Microsoft-Sans-Serif"}, "source": "moviepy_list"},
            "Microsoft Tai Le": {
                "styles": {"Regular": "Microsoft-Tai-Le", "Bold": "Microsoft-Tai-Le-Bold"}, "source": "moviepy_list"
            },
            "Microsoft YaHei & Microsoft YaHei UI": {"styles": {"Regular": "Microsoft-YaHei-&-Microsoft-YaHei-UI"}, "source": "moviepy_list"},
            "Microsoft YaHei Bold & Microsoft YaHei UI Bold": {"styles": {"Regular": "Microsoft-YaHei-Bold-&-Microsoft-YaHei-UI-Bold"}, "source": "moviepy_list"},
            "Microsoft YaHei Light & Microsoft YaHei UI Light": {"styles": {"Regular": "Microsoft-YaHei-Light-&-Microsoft-YaHei-UI-Light"}, "source": "moviepy_list"},
            "Microsoft Yi Baiti": {"styles": {"Regular": "Microsoft-Yi-Baiti"}, "source": "moviepy_list"},
            "MingLiU ExtB & PMingLiU ExtB & MingLiU_HKSCS ExtB": {"styles": {"Regular": "MingLiU-ExtB-&-PMingLiU-ExtB-&-MingLiU_HKSCS-ExtB"}, "source": "moviepy_list"},
            "Mistral": {"styles": {"Regular": "Mistral"}, "source": "moviepy_list"},
            "Modern No. 20": {"styles": {"Regular": "Modern-No.-20"}, "source": "moviepy_list"},
            "Mongolian Baiti": {"styles": {"Regular": "Mongolian-Baiti"}, "source": "moviepy_list"},
            "Monotype Corsiva": {"styles": {"Regular": "Monotype-Corsiva"}, "source": "moviepy_list"},
            "Myanmar Text": {
                "styles": {"Regular": "Myanmar-Text", "Bold": "Myanmar-Text-Bold"}, "source": "moviepy_list"
            },
            "Niagara Engraved": {"styles": {"Regular": "Niagara-Engraved"}, "source": "moviepy_list"},
            "Niagara Solid": {"styles": {"Regular": "Niagara-Solid"}, "source": "moviepy_list"},
            "Nirmala UI Collection": {"styles": {"Regular": "Nirmala-UI-&-Nirmala-UI-Bold-&-Nirmala-UI-Semilight-&-Nirmala-Text-&-Nirmala-Text-Bold-&-Nirmala-Text-Semilight"}, "source": "moviepy_list"},
            "OCR A Extended": {"styles": {"Regular": "OCR-A-Extended"}, "source": "moviepy_list"},
            "Old English Text MT": {"styles": {"Regular": "Old-English-Text-MT"}, "source": "moviepy_list"},
            "Onyx": {"styles": {"Regular": "Onyx"}, "source": "moviepy_list"},
            "Palace Script MT": {"styles": {"Regular": "Palace-Script-MT"}, "source": "moviepy_list"},
            "Palatino Linotype": {
                "styles": {"Regular": "Palatino-Linotype", "Bold": "Palatino-Linotype-Bold", "Bold Italic": "Palatino-Linotype-Bold-Italic", "Italic": "Palatino-Linotype-Italic"},
                "source": "moviepy_list"
            },
            "Papyrus": {"styles": {"Regular": "Papyrus"}, "source": "moviepy_list"},
            "Parchment": {"styles": {"Regular": "Parchment"}, "source": "moviepy_list"},
            "Perpetua": {
                "styles": {"Regular": "Perpetua", "Bold": "Perpetua-Bold", "Bold Italic": "Perpetua-Bold-Italic", "Italic": "Perpetua-Italic"}, "source": "moviepy_list"
            },
            "Perpetua Titling MT": { # MoviePy: Perpetua-Titling-MT-Bold, Perpetua-Titling-MT-Light
                "styles": {"Bold": "Perpetua-Titling-MT-Bold", "Light": "Perpetua-Titling-MT-Light"}, "source": "moviepy_list"
            },
            "Playbill": {"styles": {"Regular": "Playbill"}, "source": "moviepy_list"},
            "Poor Richard": {"styles": {"Regular": "Poor-Richard"}, "source": "moviepy_list"},
            "Pristina": {"styles": {"Regular": "Pristina"}, "source": "moviepy_list"},
            "ROG FONTS": {"styles": {"Regular": "ROG-FONTS"}, "source": "moviepy_list"}, # Nombres especiales
            "ROG Fonts v1.5": {"styles": {"Regular": "ROG-Fonts-v1.5"}, "source": "moviepy_list"},
            "Rage Italic": {"styles": {"Regular": "Rage-Italic"}, "source": "moviepy_list"},
            "Ravie": {"styles": {"Regular": "Ravie"}, "source": "moviepy_list"},
            "Rockwell": {
                "styles": {"Regular": "Rockwell", "Bold": "Rockwell-Bold", "Bold Italic": "Rockwell-Bold-Italic", "Condensed": "Rockwell-Condensed", "Condensed Bold": "Rockwell-Condensed-Bold", "Extra Bold": "Rockwell-Extra-Bold", "Italic": "Rockwell-Italic"},
                "source": "moviepy_list"
            },
            "Sans Serif Collection": {"styles": {"Regular": "Sans-Serif-Collection"}, "source": "moviepy_list"},
            "Script MT Bold": {"styles": {"Regular": "Script-MT-Bold"}, "source": "moviepy_list"},
            "Segoe Fluent Icons": {"styles": {"Regular": "Segoe-Fluent-Icons"}, "source": "moviepy_list"},
            "Segoe MDL2 Assets": {"styles": {"Regular": "Segoe-MDL2-Assets"}, "source": "moviepy_list"},
            "Segoe Print": {
                "styles": {"Regular": "Segoe-Print", "Bold": "Segoe-Print-Bold"}, "source": "moviepy_list"
            },
            "Segoe Script": {
                "styles": {"Regular": "Segoe-Script", "Bold": "Segoe-Script-Bold"}, "source": "moviepy_list"
            },
            "Segoe UI": {
                "styles": {
                    "Regular": "Segoe-UI", "Black": "Segoe-UI-Black", "Black Italic": "Segoe-UI-Black-Italic",
                    "Bold": "Segoe-UI-Bold", "Bold Italic": "Segoe-UI-Bold-Italic", "Italic": "Segoe-UI-Italic",
                    "Light": "Segoe-UI-Light", "Light Italic": "Segoe-UI-Light-Italic",
                    "Semibold": "Segoe-UI-Semibold", "Semibold Italic": "Segoe-UI-Semibold-Italic",
                    "Semilight": "Segoe-UI-Semilight", "Semilight Italic": "Segoe-UI-Semilight-Italic"
                }, "source": "moviepy_list" # Emoji, Historic, Symbol, Variable como familias separadas
            },
            "Segoe UI Emoji": {"styles": {"Regular": "Segoe-UI-Emoji"}, "source": "moviepy_list"},
            "Segoe UI Historic": {"styles": {"Regular": "Segoe-UI-Historic"}, "source": "moviepy_list"},
            "Segoe UI Symbol": {"styles": {"Regular": "Segoe-UI-Symbol"}, "source": "moviepy_list"},
            "Segoe UI Variable": {"styles": {"Regular": "Segoe-UI-Variable"}, "source": "moviepy_list"},
            "Showcard Gothic": {"styles": {"Regular": "Showcard-Gothic"}, "source": "moviepy_list"},
            "SimSun & NSimSun": {"styles": {"Regular": "SimSun-&-NSimSun"}, "source": "moviepy_list"},
            "SimSun ExtB": {"styles": {"Regular": "SimSun-ExtB"}, "source": "moviepy_list"},
            "SimSun ExtG": {"styles": {"Regular": "SimSun-ExtG"}, "source": "moviepy_list"}, # No es "SimSun-ExtG" sino "SimSun ExtG"
            "Sitka Text": { # MoviePy: Sitka-Text, Sitka-Text-Italic
                "styles": {"Regular": "Sitka-Text", "Italic": "Sitka-Text-Italic"}, "source": "moviepy_list"
            },
            "Snap ITC": {"styles": {"Regular": "Snap-ITC"}, "source": "moviepy_list"},
            "Stencil": {"styles": {"Regular": "Stencil"}, "source": "moviepy_list"},
            "Sylfaen": {"styles": {"Regular": "Sylfaen"}, "source": "moviepy_list"},
            "Symbol": {"styles": {"Regular": "Symbol"}, "source": "moviepy_list"},
            "Tahoma": {
                "styles": {"Regular": "Tahoma", "Bold": "Tahoma-Bold"}, "source": "moviepy_list"
            },
            "Tempus Sans ITC": {"styles": {"Regular": "Tempus-Sans-ITC"}, "source": "moviepy_list"},
            "Times New Roman": {
                "styles": {"Regular": "Times-New-Roman", "Bold": "Times-New-Roman-Bold", "Bold Italic": "Times-New-Roman-Bold-Italic", "Italic": "Times-New-Roman-Italic"},
                "source": "moviepy_list"
            },
            "Trebuchet MS": {
                "styles": {"Regular": "Trebuchet-MS", "Bold": "Trebuchet-MS-Bold", "Bold Italic": "Trebuchet-MS-Bold-Italic", "Italic": "Trebuchet-MS-Italic"},
                "source": "moviepy_list"
            },
            "Tw Cen MT": { # MoviePy: Tw-Cen-MT, Tw-Cen-MT-Bold, Tw-Cen-MT-Bold-Italic, Tw-Cen-MT-Condensed, Tw-Cen-MT-Condensed-Bold, Tw-Cen-MT-Condensed-Extra-Bold, Tw-Cen-MT-Italic
                "styles": {
                    "Regular": "Tw-Cen-MT", "Bold": "Tw-Cen-MT-Bold", "Bold Italic": "Tw-Cen-MT-Bold-Italic",
                    "Condensed": "Tw-Cen-MT-Condensed", "Condensed Bold": "Tw-Cen-MT-Condensed-Bold",
                    "Condensed Extra Bold": "Tw-Cen-MT-Condensed-Extra-Bold", "Italic": "Tw-Cen-MT-Italic"
                }, "source": "moviepy_list"
            },
            "Verdana": {
                "styles": {
                    "Regular": "Verdana", "Bold": "Verdana-Bold", "Italic": "Verdana-Italic", "Bold Italic": "Verdana-Bold-Italic"
                }, "source": "moviepy_list"
            },
                      "Viner Hand ITC": {"styles": {"Regular": "Viner-Hand-ITC"}, "source": "moviepy_list"},
            "Vivaldi Italic": {"styles": {"Regular": "Vivaldi-Italic"}, "source": "moviepy_list"},
            "Vladimir Script": {"styles": {"Regular": "Vladimir-Script"}, "source": "moviepy_list"},
            "Webdings": {"styles": {"Regular": "Webdings"}, "source": "moviepy_list"},
            "Wide Latin": {"styles": {"Regular": "Wide-Latin"}, "source": "moviepy_list"},
            "Wingdings": {"styles": {"Regular": "Wingdings"}, "source": "moviepy_list"},
            "Wingdings 2": {"styles": {"Regular": "Wingdings-2"}, "source": "moviepy_list"},
            "Wingdings 3": {"styles": {"Regular": "Wingdings-3"}, "source": "moviepy_list"},
            "Yu Gothic Bold & Yu Gothic UI Semibold & Yu Gothic UI Bold": {"styles": {"Regular": "Yu-Gothic-Bold-&-Yu-Gothic-UI-Semibold-&-Yu-Gothic-UI-Bold"}, "source": "moviepy_list"},
            "Yu Gothic Light & Yu Gothic UI Light": {"styles": {"Regular": "Yu-Gothic-Light-&-Yu-Gothic-UI-Light"}, "source": "moviepy_list"},
            "Yu Gothic Medium & Yu Gothic UI Regular": {"styles": {"Regular": "Yu-Gothic-Medium-&-Yu-Gothic-UI-Regular"}, "source": "moviepy_list"},
            "Yu Gothic Regular & Yu Gothic UI Semilight": {"styles": {"Regular": "Yu-Gothic-Regular-&-Yu-Gothic-UI-Semilight"}, "source": "moviepy_list"},
            "ZWAdobeF": {"styles": {"Regular": "ZWAdobeF"}, "source": "moviepy_list"}
        }
        self.all_video_templates = []
        self.combined_preview_ctk_image = None
        self.phone_frame_ctk_image = None

        self.task_queue = queue.Queue()
        # Using lambda to ensure 'self' context is correct for check_queue_for_updates
        self.after(100, lambda: self.check_queue_for_updates())
        
        # Add debug check for icon reference periodically
        def check_icon_reference():
            if not hasattr(self, 'app_icon_photoimage') or self.app_icon_photoimage is None:
                print("DEBUG: app_icon_photoimage is missing or None!")
            self.after(5000, check_icon_reference) # Check every 5 seconds
        check_icon_reference() # Start the periodic check


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
        generate_button_text_fallback = "Generate Video" if not self.generate_image_default else ""
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
        self.reddit_url_entry = customtkinter.CTkEntry(reddit_url_frame, placeholder_text="Reddit URL", fg_color=COLOR_BACKGROUND_CARD, text_color=COLOR_TEXT_PRIMARY, height=35, corner_radius=CORNER_RADIUS_INPUT, border_color=COLOR_BACKGROUND_CARD)
        self.reddit_url_entry.grid(row=0, column=0, padx=(0,10), pady=5, sticky="ew")
        self.reddit_fetch_button = customtkinter.CTkButton(reddit_url_frame, text="Search", command=self.fetch_reddit_post_threaded, fg_color=COLOR_PRIMARY_ACTION, hover_color=COLOR_PRIMARY_ACTION_HOVER, text_color=COLOR_TEXT_PRIMARY, height=35, width=100, corner_radius=CORNER_RADIUS_BUTTON, font=("Arial", 13, "bold"))
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

        self.story_textbox_placeholder_text = "1. Fetch a story using the URL or generate one with AI.\n2. Configure Voice, Video Background, and Subtitles.\n3. Click the play button to create video."
        self.story_textbox_is_placeholder_active = False # Se establecerá en True por _setup_story_textbox_placeholder
        self._setup_story_textbox_placeholder()
        
        # Bind events for placeholder behavior and button state
        self.story_textbox.bind("<KeyRelease>", lambda event: self._check_story_and_set_generate_button_state())
        self.story_textbox.bind("<FocusIn>", self._on_story_textbox_focus_in)
        self.story_textbox.bind("<FocusOut>", self._on_story_textbox_focus_out)
        self.ai_subject_entry = customtkinter.CTkEntry(self); self.ai_style_entry = customtkinter.CTkEntry(self)
        self.ai_max_tokens_slider_var = customtkinter.IntVar(value=150)
        self.ai_max_tokens_menu_var = customtkinter.StringVar(value=str(self.ai_max_tokens_slider_var.get()))

        self.voice_selection_outer_frame = customtkinter.CTkFrame(self.left_scrollable_frame, fg_color=COLOR_BACKGROUND_CARD, corner_radius=CORNER_RADIUS_FRAME)
        self.voice_selection_outer_frame.grid(row=current_row_in_left_panel, column=0, sticky="ew", padx=5, pady=10); current_row_in_left_panel += 1
        header_frame_voice = customtkinter.CTkFrame(self.voice_selection_outer_frame, fg_color="transparent")
        header_frame_voice.pack(fill="x", padx=15, pady=(10,5))
        customtkinter.CTkLabel(header_frame_voice, text="Select a voice", font=("Arial", 15, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left")
        self.view_all_voices_button = customtkinter.CTkButton(header_frame_voice, text="View all", command=self.open_view_all_voices_popup, width=80, corner_radius=CORNER_RADIUS_BUTTON, fg_color=COLOR_BACKGROUND_WIDGET_INPUT, hover_color=COLOR_BUTTON_SECONDARY_HOVER, text_color=COLOR_TEXT_SECONDARY)
        self.view_all_voices_button.pack(side="right")
        self.voice_thumbnail_grid_main = customtkinter.CTkFrame(self.voice_selection_outer_frame, fg_color="transparent")
        self.voice_thumbnail_grid_main.pack(fill="x", expand=True, padx=15, pady=5)
        
        # Definición ÚNICA y COMPLETA de las voces deseadas para la UI.
        # Esta lista ya existe más arriba en tu código, asegúrate que sea esta la que se use.
        # self.desired_main_ui_voices_meta = [
        #     {"tech": "af_heart", "friendly_short": "Heart", "img": "heart.png", "lang_code_for_sentence": "en"},
        #     {"tech": "am_fenrir", "friendly_short": "Fenrir", "img": "fenrir.png", "lang_code_for_sentence": "en"},
        #     # ... (hasta 14 voces)
        # ]
        # La redefinición que existía aquí con 6 voces ha sido eliminada en un commit anterior, lo cual es correcto.

        self._load_all_available_voices() # Carga y establece la voz por defecto
        self.refresh_main_voice_avatar_grid() # Dibuja los avatares iniciales
        
        # Configurar la voz seleccionada por defecto y resaltarla
        if self.selected_voice_technical_name:
            # Asegurar que tts_voice_menu_var tenga el nombre corto si el defecto es de active_main_ui_voices_meta
            default_voice_meta = next((vm for vm in self.active_main_ui_voices_meta if vm["tech"] == self.selected_voice_technical_name), None)
            if default_voice_meta:
                self.tts_voice_menu_var.set(default_voice_meta["friendly_short"]) # Usar friendly_short para el display inicial
            else: # Si el defecto vino del fallback general
                full_fn = next((fn for fn, tn in self.available_voices_map.items() if tn == self.selected_voice_technical_name), "Unknown Voice")
                self.tts_voice_menu_var.set(full_fn.split(" (")[0].split(" ")[-1])

            self.after(150, lambda tech_name=self.selected_voice_technical_name: self.highlight_selected_voice_avatar(tech_name))
        
        self.test_voice_button = customtkinter.CTkButton(self.voice_selection_outer_frame, text="Test Selected Voice", command=self.play_voice_sample_threaded, corner_radius=CORNER_RADIUS_BUTTON, fg_color=COLOR_BACKGROUND_WIDGET_INPUT, hover_color=COLOR_BUTTON_SECONDARY_HOVER, text_color=COLOR_TEXT_SECONDARY)
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
        
        # Fila 1: Max Words | Position
        self.srt_max_words_options = ["Whisper (Default)", "1", "2", "3", "4", "5", "6", "7"]; self.srt_max_words_var = customtkinter.StringVar(value="1")
        create_caption_optionmenu_local(self.srt_style_frame, "Max words per segment:", self.srt_max_words_options, self.srt_max_words_var, col=0)
        self.subtitle_pos_options = ["Bottom", "Center", "Top"]; self.subtitle_pos_var = customtkinter.StringVar(value="Center")
        create_caption_optionmenu_local(self.srt_style_frame, "Position:", self.subtitle_pos_options, self.subtitle_pos_var, cmd=lambda choice: self.update_subtitle_preview_display(), col=2)
        self.cap_row_internal += 1

        # Fila 2: Font Family | Font Style
        self.subtitle_font_options = sorted(list(self.font_definitions.keys())) # Usar las claves del mapa como opciones, ordenadas
        self.subtitle_font_var = customtkinter.StringVar(value="Impact") # Valor inicial
        create_caption_optionmenu_local(self.srt_style_frame, "Font:", self.subtitle_font_options, self.subtitle_font_var, cmd=self._on_font_family_change, col=0)
        
        initial_font_styles = list(self.font_definitions[self.subtitle_font_var.get()]["styles"].keys()) if self.subtitle_font_var.get() in self.font_definitions else ["Regular"]
        self.subtitle_fontstyle_var = customtkinter.StringVar(value="Regular") # Valor inicial, se ajustará si es necesario
        self.subtitle_fontstyle_menu = create_caption_optionmenu_local(self.srt_style_frame, "Font Style:", initial_font_styles, self.subtitle_fontstyle_var, cmd=lambda choice: self.update_subtitle_preview_display(), col=2)
        self.cap_row_internal += 1

        # Fila 3: Font Size | Stroke Width
        self.subtitle_fontsize_options = ["18", "24", "32", "36", "40", "48", "56", "64", "72"]; self.subtitle_fontsize_var = customtkinter.StringVar(value="64")
        create_caption_optionmenu_local(self.srt_style_frame, "Font size:", self.subtitle_fontsize_options, self.subtitle_fontsize_var, cmd=lambda choice: self.update_subtitle_preview_display(), col=0)
        self.subtitle_strokewidth_options = ["0", "0.5", "1", "1.5", "2", "3"]; self.subtitle_strokewidth_var = customtkinter.StringVar(value="0")
        create_caption_optionmenu_local(self.srt_style_frame, "Stroke Width:", self.subtitle_strokewidth_options, self.subtitle_strokewidth_var, cmd=lambda choice: self.update_subtitle_preview_display(), col=2)
        self.cap_row_internal += 1

        # Fila 4: Text Color | Stroke Color (custom layout, no change to this row's logic, just its self.cap_row_internal value)
        customtkinter.CTkLabel(self.srt_style_frame, text="Text Color:", text_color=COLOR_TEXT_SECONDARY, font=("Arial",12)).grid(row=self.cap_row_internal, column=0, padx=(15,5), pady=5, sticky="w")
        self.subtitle_text_color_button = customtkinter.CTkButton(self.srt_style_frame, text="CHOOSE", width=80, command=lambda: self.pick_color_for('text_fg'), corner_radius=CORNER_RADIUS_BUTTON, fg_color=COLOR_BACKGROUND_WIDGET_INPUT, hover_color=COLOR_BUTTON_SECONDARY_HOVER, text_color=COLOR_TEXT_SECONDARY); self.subtitle_text_color_button.grid(row=self.cap_row_internal, column=1, padx=5, pady=5, sticky="w")
        self.subtitle_text_color_preview = customtkinter.CTkFrame(self.srt_style_frame, width=30, height=30, fg_color=self.subtitle_font_color_hex, border_width=1, border_color=COLOR_TEXT_SECONDARY, corner_radius=4); self.subtitle_text_color_preview.grid(row=self.cap_row_internal, column=1, padx=(100,5), pady=5, sticky="w")
        customtkinter.CTkLabel(self.srt_style_frame, text="Stroke Color:", text_color=COLOR_TEXT_SECONDARY, font=("Arial",12)).grid(row=self.cap_row_internal, column=2, padx=(15,5), pady=5, sticky="w")
        self.subtitle_stroke_color_button = customtkinter.CTkButton(self.srt_style_frame, text="CHOOSE", width=80, command=lambda: self.pick_color_for('stroke_fg'), corner_radius=CORNER_RADIUS_BUTTON, fg_color=COLOR_BACKGROUND_WIDGET_INPUT, hover_color=COLOR_BUTTON_SECONDARY_HOVER, text_color=COLOR_TEXT_SECONDARY); self.subtitle_stroke_color_button.grid(row=self.cap_row_internal, column=3, padx=(5,85), pady=5, sticky="w")
        self.subtitle_stroke_color_preview = customtkinter.CTkFrame(self.srt_style_frame, width=30, height=30, fg_color=self.subtitle_stroke_color_hex, border_width=1, border_color=COLOR_TEXT_SECONDARY, corner_radius=4); self.subtitle_stroke_color_preview.grid(row=self.cap_row_internal, column=3, padx=(100,15), pady=5, sticky="w"); self.cap_row_internal += 1
        
        # Fila 5: Background Text (ocupa las primeras dos columnas de menú)
        self.subtitle_bgcolor_map = { "Transparent": "transparent", "Black Semi (40%)": "rgba(0,0,0,0.4)", "Black Semi (60%)": "rgba(0,0,0,0.6)"}; self.subtitle_bgcolor_options = list(self.subtitle_bgcolor_map.keys()); self.subtitle_bgcolor_var = customtkinter.StringVar(value="Transparent")
        menu_bg = create_caption_optionmenu_local(self.srt_style_frame, "Background Text:", self.subtitle_bgcolor_options, self.subtitle_bgcolor_var, cmd=lambda choice: self.update_subtitle_preview_display(), col=0); menu_bg.grid(pady=(5,15), sticky="ew", columnspan=1) # Label col 0, Menu col 1. columnspan=1 for menu to not overlap.
        # Considerar ajustar columnspan o la estructura de create_caption_optionmenu_local si se quiere que ocupe más. Por ahora, se ajusta a una pareja.
        self.cap_row_internal +=1

        self.status_frame = customtkinter.CTkFrame(self.left_scrollable_frame, fg_color="transparent")
        self.status_frame.grid(row=current_row_in_left_panel, column=0, sticky="ew", padx=5, pady=(10,0)); current_row_in_left_panel += 1
        self.status_label = customtkinter.CTkLabel(self.status_frame, text="Status: Ready.", text_color=COLOR_TEXT_SECONDARY, anchor="w", font=("Arial",12))
        self.status_label.grid(row=0, column=0, padx=0, pady=0, sticky="ew")

        self._load_video_templates_list()
        self.refresh_main_thumbnail_grid()
        # self.highlight_selected_voice_avatar() se llama después de refresh_main_voice_avatar_grid
        self.update_subtitle_preview_display()
        self._check_story_and_set_generate_button_state()


    def _load_all_available_voices(self):
        """Carga las voces disponibles y configura la lista activa de voces para la UI principal."""
        self.available_voices_map = tts_kokoro_module.list_available_kokoro_voices()
        self.voice_friendly_names = list(self.available_voices_map.keys())

        # Esta es la lista completa de voces preferidas con metadatos detallados.
        # Asegúrate de que esta definición sea la única para self.desired_main_ui_voices_meta en __init__.
        self.desired_main_ui_voices_meta = [
            {"tech": "af_heart", "friendly_short": "Heart", "img": "heart.png", "lang_code_for_sentence": "en"},
            {"tech": "am_fenrir", "friendly_short": "Fenrir", "img": "fenrir.png", "lang_code_for_sentence": "en"},
            {"tech": "af_bella", "friendly_short": "Bella", "img": "bella.png", "lang_code_for_sentence": "en"},
            {"tech": "bf_emma", "friendly_short": "Emma", "img": "emma.png", "lang_code_for_sentence": "en"},
            {"tech": "am_michael", "friendly_short": "Michael", "img": "michael.png", "lang_code_for_sentence": "en"},
            {"tech": "bm_george", "friendly_short": "George", "img": "george.png", "lang_code_for_sentence": "en"},
            {"tech": "af_alloy", "friendly_short": "Alloy", "img": "alloy.png", "lang_code_for_sentence": "en"},
            {"tech": "af_aoede", "friendly_short": "Aoede", "img": "aoede.png", "lang_code_for_sentence": "en"},
            {"tech": "af_kore", "friendly_short": "Kore", "img": "kore.png", "lang_code_for_sentence": "en"},
            {"tech": "af_nicole", "friendly_short": "Nicole", "img": "nicole.png", "lang_code_for_sentence": "en"},
            {"tech": "af_nova", "friendly_short": "Nova", "img": "nova.png", "lang_code_for_sentence": "en"},
            {"tech": "af_sarah", "friendly_short": "Sarah", "img": "sarah.png", "lang_code_for_sentence": "en"},
            {"tech": "am_puck", "friendly_short": "Puck", "img": "puck.png", "lang_code_for_sentence": "en"},
            {"tech": "bm_fable", "friendly_short": "Fable", "img": "fable.png", "lang_code_for_sentence": "en"}
        ]

        self.active_main_ui_voices_meta = [
            vm for vm in self.desired_main_ui_voices_meta if vm["tech"] in self.available_voices_map.values()
        ]

        available_tech_names_list = list(self.available_voices_map.values())
        print(f"DEBUG: available_tech_names_list from Kokoro = {available_tech_names_list}") # Debug print

        default_voice_tech, default_voice_friendly_display = None, "No voices"
        if self.active_main_ui_voices_meta: # Prioritize from active (preferred and available)
            default_voice_tech = self.active_main_ui_voices_meta[0]["tech"]
            default_voice_friendly_display = self.active_main_ui_voices_meta[0]["friendly_short"]
        elif available_tech_names_list: # Fallback to any available voice
                default_voice_tech = available_tech_names_list[0]
                for fn, tn in self.available_voices_map.items():
                    if tn == default_voice_tech:
                        default_voice_friendly_display = fn.split(" (")[0].split(" ")[-1] # Short friendly name
                        break
        
        self.selected_voice_technical_name = default_voice_tech; self.can_generate_audio = bool(self.selected_voice_technical_name)
        self.tts_voice_menu_var = customtkinter.StringVar(value=default_voice_friendly_display)

    # --- METHODS ---

    def open_ai_story_generation_popup(self):
        if hasattr(self, 'ai_popup') and self.ai_popup.winfo_exists():
            self.ai_popup.focus(); self.ai_popup.grab_set(); return

        self.ai_popup = customtkinter.CTkToplevel(self)
        self.ai_popup.title("Generate a story with AI"); self.ai_popup.geometry("500x400") # Adjusted height for slider
        self.ai_popup.attributes("-topmost", True); self.ai_popup.resizable(False, False)
        self.ai_popup.configure(fg_color=COLOR_BACKGROUND_MAIN); self.ai_popup.grab_set()
        # Set popup icon
        try:
            if hasattr(self, 'app_icon_photoimage') and self.app_icon_photoimage:
                self.ai_popup.iconphoto(False, self.app_icon_photoimage)
            else:
                print(f"Warning: App icon not found for AI story popup at {self.APP_ICON_PATH}")
        except Exception as e: print(f"Error setting icon for AI story popup: {e}")

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
        if not hasattr(self, 'combined_preview_display_label'):
            print("DEBUG: combined_preview_display_label not found in update_subtitle_preview_display")
            return
        if not hasattr(self, 'phone_frame_template_pil') or self.phone_frame_template_pil is None:
            self.combined_preview_display_label.configure(image=None, text="[Phone GFX Missing]")
            print("DEBUG: phone_frame_template_pil not found or is None")
            return

        try:
            phone_template_pil = self.phone_frame_template_pil.copy() # Work with a copy
            pt_width, pt_height = phone_template_pil.size

            # 1. Get/Generate Screen Content (video frame + text)
            style_opts = self._get_current_subtitle_style_options()
            if not style_opts:
                self.combined_preview_display_label.configure(image=None, text="[Style Error]")
                return
            preview_text = "This is a sample subtitle text."

            screen_content_pil = None
            if self.current_video_thumbnail_for_composite_path and os.path.exists(self.current_video_thumbnail_for_composite_path):
                # Assuming create_composite_preview_image returns a path to an image
                # that is *only* the screen content (video frame + subtitles thereon).
                # This function MUST NOT add its own phone frame.
                generated_screen_content_path = video_processor.create_composite_preview_image(
                    self.current_video_thumbnail_for_composite_path,
                    preview_text,
                    style_opts
                )
                if generated_screen_content_path and os.path.exists(generated_screen_content_path):
                    screen_content_pil = Image.open(generated_screen_content_path).convert("RGBA")
                else:
                    print(f"WARN: Screen content generation failed or path not found: {generated_screen_content_path}")
                    # Create a placeholder if generation fails to see if compositing works
                    # screen_content_pil = Image.new("RGBA", (int(pt_width * 0.8), int(pt_height * 0.8)), "blue") 
            else:
                print("INFO: No video selected for preview content.")
                # Create a placeholder if no video is selected
                # screen_content_pil = Image.new("RGBA", (int(pt_width * 0.8), int(pt_height * 0.8)), "darkgrey")

            # 2. Define Screen Area within the phone_template_pil
            screen_area_x = pt_width * PHONE_SCREEN_PADDING_X_FACTOR
            screen_area_y = pt_height * PHONE_SCREEN_PADDING_Y_TOP_FACTOR
            screen_area_width = pt_width * (1 - 2 * PHONE_SCREEN_PADDING_X_FACTOR)
            screen_area_height = pt_height * (1 - PHONE_SCREEN_PADDING_Y_TOP_FACTOR - PHONE_SCREEN_PADDING_Y_BOTTOM_FACTOR)

            screen_area_x_int = int(screen_area_x)
            screen_area_y_int = int(screen_area_y)
            screen_area_width_int = int(screen_area_width)
            screen_area_height_int = int(screen_area_height)

            # 3. Prepare Screen Content PIL for pasting
            # Create a base for the final composite image, same size as the phone template, fully transparent.
            composite_base_pil = Image.new('RGBA', phone_template_pil.size, (0, 0, 0, 0))

            if screen_content_pil:
                # Resize actual screen_content_pil to fit the calculated screen_area
                resized_screen_content_pil = screen_content_pil.resize(
                    (screen_area_width_int, screen_area_height_int), 
                    Image.Resampling.LANCZOS
                )
                # Paste the resized screen content onto the composite base at the screen position.
                composite_base_pil.paste(resized_screen_content_pil, (screen_area_x_int, screen_area_y_int))
            # If screen_content_pil is None, composite_base_pil remains transparent in the screen area.

            # 4. Composite the phone frame graphic on top
            final_composite_pil = Image.alpha_composite(composite_base_pil, phone_template_pil)

            # 5. Update Display
            # The CTkImage should be sized to the final_composite_pil's dimensions.
            # The combined_preview_display_label container (phone_frame_container) is already scaled to 380px width.
            # So, final_composite_pil (which is based on phone_template_pil) should be used for CTkImage size.
            
            # If phone_template_pil was from the original file, and display_phone_width was 380,
            # we should resize final_composite_pil to (display_phone_width, display_phone_height) 
            # IF its original dimensions were different.
            # From __init__, self.phone_frame_template_pil IS the original image, not scaled yet.
            # Let's re-evaluate sizing for display here.

            display_phone_width = 380 # As used in __init__ to size the container
            final_aspect_ratio = final_composite_pil.height / final_composite_pil.width
            display_composite_height = int(display_phone_width * final_aspect_ratio)

            self.combined_preview_ctk_image = CTkImage(
                light_image=final_composite_pil,
                dark_image=final_composite_pil,
                size=(display_phone_width, display_composite_height) # Display size
            )
            self.combined_preview_display_label.configure(image=self.combined_preview_ctk_image, text="")

        except Exception as e:
            print(f"ERROR in update_subtitle_preview_display: {e}")
            traceback.print_exc()
            self.combined_preview_display_label.configure(image=None, text="[Preview Gen Error]")

    def _on_font_family_change(self, selected_font_family: str):
        """Actualiza las opciones del menú de estilo de fuente cuando cambia la familia de fuente."""
        font_def = self.font_definitions.get(selected_font_family)
        if font_def and "styles" in font_def:
            valid_styles = list(font_def["styles"].keys())
        else:
            valid_styles = ["Regular"] # Fallback
            print(f"WARN: Font family '{selected_font_family}' not found in font_definitions or has no styles.")
        
        current_style = self.subtitle_fontstyle_var.get()
        
        # Actualizar las opciones del menú desplegable de estilo de fuente
        if hasattr(self, 'subtitle_fontstyle_menu'):
            self.subtitle_fontstyle_menu.configure(values=valid_styles)
        
        # Si el estilo actual no es válido para la nueva familia, seleccionar "Regular" o el primer estilo válido
        if current_style not in valid_styles:
            if "Regular" in valid_styles:
                self.subtitle_fontstyle_var.set("Regular")
            elif valid_styles: # Si "Regular" no está pero hay otros estilos válidos
                self.subtitle_fontstyle_var.set(valid_styles[0])
        
        self.update_subtitle_preview_display()

    def _get_current_subtitle_style_options(self) -> dict | None:
        # print(f"DEBUG_SELF (_get_current_subtitle_style_options): type(self) is {type(self)}, id(self) is {id(self)}")
        if not all(hasattr(self, attr_name) for attr_name in ['subtitle_bgcolor_map', 'subtitle_bgcolor_var', 'subtitle_fontsize_var', 'subtitle_strokewidth_var', 'subtitle_font_var', 'subtitle_font_color_hex', 'subtitle_stroke_color_hex', 'subtitle_pos_var']):
            missing_attrs = [attr for attr in ['subtitle_bgcolor_map', 'subtitle_bgcolor_var', 'subtitle_fontsize_var', 'subtitle_strokewidth_var', 'subtitle_font_var', 'subtitle_fontstyle_var', 'subtitle_font_color_hex', 'subtitle_stroke_color_hex', 'subtitle_pos_var'] if not hasattr(self, attr)]
            print(f"CRITICAL DEBUG: Subtitle style attributes missing in _get_current_subtitle_style_options: {', '.join(missing_attrs)} on self (id: {id(self)})")
            return None

        font_family_ui = self.subtitle_font_var.get()
        font_style_ui = self.subtitle_fontstyle_var.get()
        
        final_font_name = font_family_ui # Fallback al nombre de la familia

        font_def = self.font_definitions.get(font_family_ui)
        if font_def and "styles" in font_def:
            final_font_name = font_def["styles"].get(font_style_ui, font_family_ui)
            # Si el estilo no se encuentra (no debería pasar), usa el nombre de la familia.
            # Si el estilo es "Regular" y no está explícitamente, pero la familia sí, usa el nombre de la familia.
        else:
            # Si la familia no está en las definiciones (no debería pasar), intenta construirlo.
            if font_style_ui != "Regular": final_font_name = f"{font_family_ui}-{font_style_ui}"

        actual_bg_color = self.subtitle_bgcolor_map.get(self.subtitle_bgcolor_var.get(), "rgba(0,0,0,0.4)")
        try: fontsize, strokewidth = int(self.subtitle_fontsize_var.get()), float(self.subtitle_strokewidth_var.get())
        except ValueError: fontsize, strokewidth = 36, 1.5; self.status_label.configure(text="Warn: Invalid sub style.")
        
        print(f"DEBUG (Subtitle Style Options): Attempting to use font='{final_font_name}', fontsize={fontsize}, color='{self.subtitle_font_color_hex}', stroke_color='{self.subtitle_stroke_color_hex}', stroke_width={strokewidth}, bg_color='{actual_bg_color}', position='{self.subtitle_pos_var.get()}'")
        return {'font': final_font_name, 'fontsize': fontsize, 'color': self.subtitle_font_color_hex, 'stroke_color': self.subtitle_stroke_color_hex, 'stroke_width': strokewidth, 'bg_color': actual_bg_color, 'position_choice': self.subtitle_pos_var.get()}

    # --- ALL OTHER METHODS from the previous response MUST BE COPIED HERE ---
    # (check_queue_for_updates, _get_main_action_buttons_for_state_management, etc.)

    def _setup_story_textbox_placeholder(self):
        """Inserta el placeholder y configura el color inicial."""
        self.story_textbox.insert("1.0", self.story_textbox_placeholder_text)
        self.story_textbox.configure(text_color=COLOR_TEXT_SECONDARY) # Color más claro para el placeholder
        self.story_textbox_is_placeholder_active = True

    def _on_story_textbox_focus_in(self, event=None):
        """Maneja el evento FocusIn para el story_textbox."""
        if self.story_textbox_is_placeholder_active:
            self.story_textbox.delete("1.0", "end")
            self.story_textbox.configure(text_color=COLOR_TEXT_PRIMARY) # Color normal para la entrada del usuario
            self.story_textbox_is_placeholder_active = False

    def _on_story_textbox_focus_out(self, event=None):
        """Maneja el evento FocusOut para el story_textbox."""
        if not self.story_textbox.get("1.0", "end-1c").strip(): # Si está vacío
            self.story_textbox.insert("1.0", self.story_textbox_placeholder_text)
            self.story_textbox.configure(text_color=COLOR_TEXT_SECONDARY) # Color del placeholder
            self.story_textbox_is_placeholder_active = True

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

    def highlight_selected_voice_avatar(self, technical_name_to_select):
        if self.selected_voice_button_widget: self.selected_voice_button_widget.configure(border_width=0, fg_color=COLOR_BACKGROUND_WIDGET_INPUT)
        self.selected_voice_button_widget = self.voice_buttons_map.get(technical_name_to_select)
        if self.selected_voice_button_widget: self.selected_voice_button_widget.configure(border_width=2, border_color=COLOR_BORDER_SELECTED, fg_color=COLOR_BUTTON_SECONDARY_HOVER)

    def select_voice_from_avatar(self, friendly_name, technical_name, button_widget_ref):
        self.update_selected_voice_technical_name(friendly_name); self.highlight_selected_voice_avatar(technical_name)

    def show_generating_video_popup(self):
        if hasattr(self, 'generating_popup') and self.generating_popup.winfo_exists(): self.generating_popup.focus(); self.generating_popup.grab_set(); return
        self.generating_popup = customtkinter.CTkToplevel(self)
        self.generating_popup.title("Processing Video"); self.generating_popup.geometry("480x380")
        self.generating_popup.attributes("-topmost", True); self.generating_popup.protocol("WM_DELETE_WINDOW", lambda: None)
        self.generating_popup.grab_set(); self.generating_popup.configure(fg_color=COLOR_BACKGROUND_MAIN)
        # Set popup icon
        try:
            if hasattr(self, 'app_icon_photoimage') and self.app_icon_photoimage:
                self.generating_popup.iconphoto(False, self.app_icon_photoimage)
            else:
                print(f"Warning: App icon not found for generating video popup at {self.APP_ICON_PATH}")
        except Exception as e: print(f"Error setting icon for generating video popup: {e}")
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

    def refresh_main_voice_avatar_grid(self):
        """Redibuja los avatares de voz en la UI principal."""
        for widget in self.voice_thumbnail_grid_main.winfo_children():
            widget.destroy()
        self.voice_buttons_map.clear()
        self.selected_voice_button_widget = None # Anular referencia al botón antiguo

        vr, vc = 0, 0
        # Mostrar solo hasta MAX_THUMBNAILS_MAIN_GUI de self.active_main_ui_voices_meta
        for voice_meta in self.active_main_ui_voices_meta[:MAX_THUMBNAILS_MAIN_GUI]:
            tech_name = voice_meta["tech"]
            friendly_display_name = voice_meta["friendly_short"] # Usar friendly_short para el texto del botón
            img_file = voice_meta["img"]
            
            avatar_img = None
            try:
                avatar_img_path = os.path.join(self.VOICE_AVATAR_PATH, img_file)
                if os.path.exists(avatar_img_path):
                    avatar_img = CTkImage(Image.open(avatar_img_path), size=(45,45))
            except Exception as e: print(f"AVATAR MAIN DEBUG: Error loading {img_file} for {friendly_display_name}: {e}")
            if not avatar_img: print(f"AVATAR MAIN DEBUG: Image NOT LOADED/FOUND for {friendly_display_name}: {avatar_img_path if 'avatar_img_path' in locals() else 'path unknown'}")
            
            voice_button = customtkinter.CTkButton(self.voice_thumbnail_grid_main, text=friendly_display_name, image=avatar_img, compound="top", fg_color=COLOR_BACKGROUND_WIDGET_INPUT, hover_color=COLOR_BUTTON_SECONDARY_HOVER, corner_radius=CORNER_RADIUS_BUTTON, width=110, height=75, text_color=COLOR_TEXT_SECONDARY, font=("Arial", 11))
            voice_button.configure(command=lambda fs=friendly_display_name, tn=tech_name, b=voice_button: self.select_voice_from_avatar(fs, tn, b))
            voice_button.grid(row=vr, column=vc, padx=4, pady=4, sticky="nsew"); self.voice_buttons_map[tech_name] = voice_button; vc += 1
            if vc >= VOICE_AVATAR_GRID_COLUMNS_MAIN: vc = 0; vr += 1
        for i in range(VOICE_AVATAR_GRID_COLUMNS_MAIN): self.voice_thumbnail_grid_main.grid_columnconfigure(i, weight=1)

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

    def _process_all_worker(self, story, voice_tech, bg_video, srt_words, sub_style, id_str):
        paths, step = {}, ""
        try:
            self.task_queue.put(self.show_generating_video_popup)
            step = "TTS"; self.task_queue.put(lambda: self.update_generating_log(f"1/4: {step}..."))
            paths['audio'] = os.path.join(file_manager.AUDIO_DIR, f"{id_str}.wav")
            if not tts_kokoro_module.generate_speech_with_voice_name(story, voice_tech, paths['audio']): raise Exception("TTS failed.")
            step = "Narrated Video"; self.task_queue.put(lambda: self.update_generating_log(f"2/4: {step}..."))
            paths['narr_vid'] = os.path.join(file_manager.NARRATED_VIDEO_DIR, f"{id_str}.mp4")
            if not video_processor.create_narrated_video(bg_video, paths['audio'], paths['narr_vid']): raise Exception("Narrated video failed.")
            step = "SRT Gen"; self.task_queue.put(lambda: self.update_generating_log(f"3/4: {step}..."))
            paths['srt'] = os.path.join(file_manager.SRT_DIR, f"{id_str}.srt")
            if not srt_generator.create_srt_file(paths['audio'], paths['srt'], max_words_per_segment=srt_words): raise Exception("SRT failed.")
            step = "Burn Subs"; self.task_queue.put(lambda: self.update_generating_log(f"4/4: {step}..."))
            paths['final'] = os.path.join(file_manager.FINAL_VIDEO_DIR, f"{id_str}_{voice_tech}.mp4")
            if not video_processor.burn_subtitles_on_video(paths['narr_vid'], paths['srt'], paths['final'], style_options=sub_style): raise Exception("Burn subs failed.")
            self.task_queue.put(lambda: self._update_gui_after_all_processing(True, f"Video '{id_str}' created! Path: {os.path.abspath(paths['final'])}"))
        except Exception as e: err_msg = f"Err in '{step}': {e}"; print(err_msg); traceback.print_exc(); self.task_queue.put(lambda: self._update_gui_after_all_processing(False, err_msg))
        finally: self.task_queue.put(self.hide_generating_video_popup)

    def _update_gui_after_all_processing(self, success: bool, message: str):
        self.status_label.configure(text=message)
        if hasattr(self, 'generating_log_textbox') and self.generating_log_textbox.winfo_exists(): self.update_generating_log(f"Final: {message}")
        self._enable_main_action_button()

    def process_all_steps_threaded(self):
        story = self.story_textbox.get("1.0", "end-1c").strip()
        placeholders = ["1. Fetch a story", "Loading", "Generating"]
        if not story or any(story.startswith(p) for p in placeholders if p): self.status_label.configure(text="Err: No valid story."); return
        if not self.can_generate_audio or not self.selected_voice_technical_name: self.status_label.configure(text="Err: No TTS voice."); return
        if not self.background_video_path or not os.path.exists(self.background_video_path): self.status_label.configure(text="Err: BG video not found."); return
        max_words_str = self.srt_max_words_var.get()
        srt_words = int(max_words_str) if max_words_str.isdigit() else None
        if max_words_str != "Whisper (Defecto)" and srt_words is None: self.status_label.configure(text="Err SRT: Invalid Max words."); return
        sub_style = self._get_current_subtitle_style_options()
        if not sub_style: self.status_label.configure(text="Err: Subtitle style options invalid."); return
        id_str = file_manager.get_next_id_str()
        self.status_label.configure(text=f"Starting video gen (ID: {id_str})..."); self.update_idletasks()
        self._disable_main_action_button()
        threading.Thread(target=self._process_all_worker, args=(story, self.selected_voice_technical_name, self.background_video_path, srt_words, sub_style, id_str), daemon=True).start()

    def open_view_all_voices_popup(self): # Stub - copy from previous
        print("open_view_all_voices_popup called")
        if hasattr(self, 'all_voices_popup') and self.all_voices_popup.winfo_exists(): self.all_voices_popup.focus(); self.all_voices_popup.grab_set(); return
        self.all_voices_popup = customtkinter.CTkToplevel(self)
        self.all_voices_popup.title("Choose a voice"); self.all_voices_popup.geometry("720x600")
        self.all_voices_popup.attributes("-topmost", True); self.all_voices_popup.configure(fg_color=COLOR_BACKGROUND_MAIN); self.all_voices_popup.grab_set()
        # Set popup icon
        try:
            if hasattr(self, 'app_icon_photoimage') and self.app_icon_photoimage:
                self.all_voices_popup.iconphoto(False, self.app_icon_photoimage)
            else:
                print(f"Warning: App icon not found for all voices popup at {self.APP_ICON_PATH}")
        except Exception as e: print(f"Error setting icon for all voices popup: {e}")
        customtkinter.CTkLabel(self.all_voices_popup, text="Choose a voice", font=("Arial", 18, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(pady=15)
        scrollable_frame = customtkinter.CTkScrollableFrame(self.all_voices_popup, fg_color=COLOR_BACKGROUND_MAIN, scrollbar_button_color=COLOR_BACKGROUND_CARD, scrollbar_button_hover_color=COLOR_BUTTON_SECONDARY_HOVER)
        scrollable_frame.pack(expand=True, fill="both", padx=20, pady=(0,20))
        vr, vc = 0, 0
        # Usar self.desired_main_ui_voices_meta (la lista de 14) para obtener metadatos de imagen
        # y self.available_voices_map para iterar sobre todas las voces disponibles.
        for friendly_name, tech_name in self.available_voices_map.items():
            # Intentar obtener la imagen de self.desired_main_ui_voices_meta
            voice_meta_info = next((vm for vm in self.desired_main_ui_voices_meta if vm["tech"] == tech_name), None)
            img_file_guess = "default_avatar.png" # Un avatar por defecto si no se encuentra
            if voice_meta_info and "img" in voice_meta_info:
                img_file_guess = voice_meta_info["img"]
            else: # Si no está en desired_main_ui_voices_meta, intentar adivinar
                img_file_guess = f"{tech_name.split('_')[-1] if '_' in tech_name else tech_name}.png"

            # Determinar el texto para mostrar en el botón (friendly_short)
            button_display_text = friendly_name # Por defecto, el nombre completo
            if voice_meta_info and "friendly_short" in voice_meta_info:
                button_display_text = voice_meta_info["friendly_short"]
            else:
                # Fallback si no está en desired_main_ui_voices_meta o no tiene friendly_short
                # Intentar extraer una parte corta del nombre amigable completo
                parts = friendly_name.split(" (")[0].split(" ")
                if len(parts) > 1: button_display_text = parts[-1] # Tomar la última palabra antes del paréntesis

            avatar_img = None
            try: avatar_img_path = os.path.join(self.VOICE_AVATAR_PATH, img_file_guess); os.path.exists(avatar_img_path) and (avatar_img := CTkImage(Image.open(avatar_img_path), size=(50,50)))
            except Exception as e: print(f"POPUP AVATAR DEBUG: Error loading {img_file_guess} for {friendly_name}: {e}")
            voice_button = customtkinter.CTkButton(scrollable_frame, text=button_display_text, image=avatar_img, compound="top", command=lambda fn=friendly_name, tn=tech_name: self.select_voice_from_popup(fn, tn), fg_color=COLOR_BACKGROUND_CARD, hover_color=COLOR_BUTTON_SECONDARY_HOVER, corner_radius=CORNER_RADIUS_BUTTON, height=90, text_color=COLOR_TEXT_PRIMARY, font=("Arial",11))
            voice_button.grid(row=vr, column=vc, padx=5, pady=5, sticky="nsew"); vc += 1
            if vc >= VOICE_AVATAR_GRID_COLUMNS_POPUP: vc = 0; vr += 1
        for i in range(VOICE_AVATAR_GRID_COLUMNS_POPUP): scrollable_frame.grid_columnconfigure(i, weight=1)

    def select_voice_from_popup(self, full_friendly_name_from_popup: str, technical_name_from_popup: str):
        print(f"select_voice_from_popup: FullFN='{full_friendly_name_from_popup}', TechN='{technical_name_from_popup}'")
        
        # 1. Actualizar la selección global de voz
        self.update_selected_voice_technical_name(full_friendly_name_from_popup) # Esto actualiza self.selected_voice_technical_name

        # --- INICIO LÓGICA PARA MOVER LA VOZ AL FRENTE DE LA UI PRINCIPAL ---
        target_voice_meta = next((vm for vm in self.desired_main_ui_voices_meta if vm["tech"] == technical_name_from_popup), None)
            
        if not target_voice_meta: # Si no está en las deseadas, construir metadatos básicos
            # Esto es para voces que están en available_voices_map pero no en desired_main_ui_voices_meta
            short_friendly = full_friendly_name_from_popup.split(" (")[0].split(" ")[-1]
            img_file_name_guess = f"{technical_name_from_popup.split('_')[-1] if '_' in technical_name_from_popup else technical_name_from_popup}.png"
            
            lang_code_guess = "en" # Default
            if technical_name_from_popup.startswith("es_") or "_es_" in technical_name_from_popup: lang_code_guess = "es"
                
            target_voice_meta = {
                "tech": technical_name_from_popup, 
                "friendly_short": short_friendly, 
                "img": img_file_name_guess, # Usar el nombre de archivo adivinado
                "lang_code_for_sentence": lang_code_guess
            }

        # Mover la voz seleccionada (target_voice_meta) al principio de active_main_ui_voices_meta
        if target_voice_meta: # Asegurarse de que tenemos una meta para la voz
            # Eliminarla de active_main_ui_voices_meta si ya existía (para evitar duplicados y asegurar que se mueva desde cualquier posición)
            self.active_main_ui_voices_meta = [vm for vm in self.active_main_ui_voices_meta if vm["tech"] != technical_name_from_popup]
            # Insertarla al principio
            self.active_main_ui_voices_meta.insert(0, target_voice_meta)
        # --- FIN LÓGICA PARA MOVER LA VOZ ---

        # 2. Cerrar el popup
        if hasattr(self, 'all_voices_popup') and self.all_voices_popup.winfo_exists():
            self.all_voices_popup.grab_release()
            self.all_voices_popup.destroy()
            delattr(self, 'all_voices_popup')

        # 3. Redibujar la cuadrícula principal (que ahora tendrá la voz seleccionada al inicio de active_main_ui_voices_meta)
        self.refresh_main_voice_avatar_grid() 
        
        # 4. Resaltar la voz en la NUEVA cuadrícula principal
        self.highlight_selected_voice_avatar(technical_name_from_popup) # technical_name_from_popup es el nombre técnico de la voz seleccionada

    def open_view_all_videos_popup(self): # Stub - copy from previous
        print("open_view_all_videos_popup called")
        if not self.all_video_templates: self.status_label.configure(text="No video templates found."); return
        if hasattr(self, 'all_videos_main_popup') and self.all_videos_main_popup.winfo_exists(): self.all_videos_main_popup.focus(); self.all_videos_main_popup.grab_set(); return
        self.all_videos_main_popup = customtkinter.CTkToplevel(self)
        self.all_videos_main_popup.title("Choose a background video"); self.all_videos_main_popup.geometry("780x650")
        self.all_videos_main_popup.attributes("-topmost", True); self.all_videos_main_popup.configure(fg_color=COLOR_BACKGROUND_MAIN); self.all_videos_main_popup.grab_set()
        # Set popup icon
        try:
            if hasattr(self, 'app_icon_photoimage') and self.app_icon_photoimage:
                self.all_videos_main_popup.iconphoto(False, self.app_icon_photoimage)
            else:
                print(f"Warning: App icon not found for all videos popup at {self.APP_ICON_PATH}")
        except Exception as e: print(f"Error setting icon for all videos popup: {e}")
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

    def select_voice_from_avatar(self, friendly_short_name: str, technical_name: str, button_widget_ref):
        """Llamado cuando se hace clic en un avatar de la UI principal."""
        # Encontrar el nombre amigable completo para actualizar el estado global
        full_friendly_name = next((fn for fn, tn in self.available_voices_map.items() if tn == technical_name), None)
        if full_friendly_name:
            self.update_selected_voice_technical_name(full_friendly_name) # Esto actualiza selected_voice_technical_name, tts_voice_menu_var, etc.
        self.highlight_selected_voice_avatar(technical_name) # Resalta el botón clickeado

    def _select_video_from_thumbnail_internal(self, video_path: str, from_popup: bool = False, popup_window_ref: customtkinter.CTkToplevel = None):
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

    def update_selected_voice_technical_name(self, selected_full_friendly_name: str):
        """Actualiza la voz TTS seleccionada globalmente. Espera un nombre amigable completo."""
        self.selected_voice_technical_name = self.available_voices_map.get(selected_full_friendly_name)

        if self.selected_voice_technical_name:
            self.can_generate_audio = True
            # El tts_voice_menu_var debe reflejar el nombre corto para consistencia si es una voz principal
            voice_meta_for_display = next((vm for vm in self.active_main_ui_voices_meta if vm["tech"] == self.selected_voice_technical_name), None)
            if voice_meta_for_display and "friendly_short" in voice_meta_for_display:
                display_name_for_menu = voice_meta_for_display["friendly_short"]
            else: # Si no está en active_main_ui_voices_meta o no tiene friendly_short, usar parte del full_friendly_name
                display_name_for_menu = selected_full_friendly_name.split(" (")[0].split(" ")[-1]
            
            self.tts_voice_menu_var.set(display_name_for_menu) # Actualiza el OptionMenu (si lo usaras para mostrar la selección)
            
            status_display_name = selected_full_friendly_name.split("(")[0].strip()
            self.status_label.configure(text=f"TTS Voice selected: {status_display_name}")
            if hasattr(self, 'test_voice_button'): self.test_voice_button.configure(state="normal", fg_color=COLOR_BACKGROUND_WIDGET_INPUT)
        else:
            self.can_generate_audio = False
            self.status_label.configure(text=f"Voice not found: {selected_full_friendly_name}")
            if hasattr(self, 'test_voice_button'): self.test_voice_button.configure(state="disabled", fg_color="grey50")
        self._check_story_and_set_generate_button_state()

    def _is_story_valid(self) -> bool:
        if not hasattr(self, 'story_textbox'): return False
        story_text = self.story_textbox.get("1.0", "end-1c").strip()
        placeholders = [ # Add the initial text as a placeholder
            self.story_textbox_placeholder_text, # Usar la variable del placeholder
            "Loading story from Reddit...",
            "Generating AI story...",
            # Puedes añadir más placeholders si los usas
        ]
        # Considera también una longitud mínima si es necesario, ej: len(story_text) < 10
        if not story_text or any(story_text.startswith(p_text) for p_text in placeholders if p_text):
            return False
        return True

    def _check_story_and_set_generate_button_state(self):
        if not hasattr(self, 'generate_video_button') or not self.generate_video_button.winfo_exists():
            return
        if self.long_process_active: 
            # Si un proceso largo está activo, el botón debe permanecer deshabilitado
            # y la imagen actualizada para reflejar eso, independientemente del contenido del textbox.
            return
            
        if self._is_story_valid():
            self.generate_video_button.configure(state="normal")
        else:
            self.generate_video_button.configure(state="disabled")
        self._update_generate_button_image()

    def _update_generate_button_image(self):
        if not hasattr(self, 'generate_video_button') or not self.generate_video_button.winfo_exists():
            return

        current_image = None
        button_state = self.generate_video_button.cget("state")

        if button_state == "disabled":
            current_image = self.generate_image_disabled
        elif self.generate_button_is_pressed:
            current_image = self.generate_image_active
        elif self.mouse_is_over_generate_button:
            current_image = self.generate_image_hover
        else:
            current_image = self.generate_image_default

        if current_image is None and self.generate_image_default:
            current_image = self.generate_image_default
        
        if isinstance(current_image, customtkinter.CTkImage) or current_image is None:
            self.generate_video_button.configure(image=current_image)
        elif self.generate_image_default:
            self.generate_video_button.configure(image=self.generate_image_default)

    def _on_generate_button_enter(self, event):
        if not hasattr(self, 'generate_video_button') or not self.generate_video_button.winfo_exists(): return
        self.mouse_is_over_generate_button = True
        if self.generate_video_button.cget("state") == "normal":
            self._update_generate_button_image()

    def _on_generate_button_leave(self, event):
        if not hasattr(self, 'generate_video_button') or not self.generate_video_button.winfo_exists(): return
        self.mouse_is_over_generate_button = False
        if self.generate_video_button.cget("state") == "normal":
            self._update_generate_button_image()

    def _on_generate_button_press(self, event):
        if not hasattr(self, 'generate_video_button') or not self.generate_video_button.winfo_exists(): return
        if self.generate_video_button.cget("state") == "normal":
            self.generate_button_is_pressed = True
            self._update_generate_button_image()

    def _on_generate_button_release(self, event):
        if not hasattr(self, 'generate_video_button') or not self.generate_video_button.winfo_exists(): return
        if self.generate_button_is_pressed: 
            self.generate_button_is_pressed = False
            if self.generate_video_button.cget("state") == "normal":
                self._update_generate_button_image()


if __name__ == "__main__":
    app = App()
    app.mainloop()