# video_processor.py
import os
import traceback
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
from moviepy.video.fx.all import loop as vfx_loop
import pysrt # Para parsear archivos SRT
from PIL import Image
import numpy as np 

SUBTITLE_PREVIEW_IMAGE_TEMP_FILE = "_subtitle_preview_image_temp.png"
PREVIEW_SUBTITLE_HEIGHT = 80 # Altura fija para la imagen de previsualización del subtítulo

VIDEO_TEMPLATES_DIR = "video_templates" 
THUMBNAIL_CACHE_DIR = os.path.join(VIDEO_TEMPLATES_DIR, ".thumbnails_cache") 

COMBINED_PREVIEW_IMAGE_TEMP_FILE = "_combined_preview_temp.png" 
# Constante para la imagen temporal del TextClip del subtítulo (si se guarda por separado primero)
SUBTITLE_ONLY_PREVIEW_IMAGE_TEMP_FILE = "_subtitle_only_preview_temp.png" 

if not os.path.exists(VIDEO_TEMPLATES_DIR):
    os.makedirs(VIDEO_TEMPLATES_DIR)
    print(f"VideoProc - Directorio de plantillas creado: {VIDEO_TEMPLATES_DIR}")
if not os.path.exists(THUMBNAIL_CACHE_DIR):
    os.makedirs(THUMBNAIL_CACHE_DIR)
    print(f"VideoProc - Directorio de caché de miniaturas creado: {THUMBNAIL_CACHE_DIR}")


def list_video_templates() -> list[str]:
    """Devuelve una lista de rutas completas a archivos de video en VIDEO_TEMPLATES_DIR."""
    video_files = []
    if not os.path.exists(VIDEO_TEMPLATES_DIR):
        print(f"VideoProc - Directorio de plantillas '{VIDEO_TEMPLATES_DIR}' no encontrado.")
        return video_files

    valid_extensions = ('.mp4', '.mov', '.avi', '.mkv') # Extensiones de video comunes
    for filename in sorted(os.listdir(VIDEO_TEMPLATES_DIR)): # Ordenar para consistencia
        if filename.lower().endswith(valid_extensions):
            video_files.append(os.path.join(VIDEO_TEMPLATES_DIR, filename))
    return video_files

def get_or_create_thumbnail(video_path: str, time_sec: float = 1.0, size: tuple = (128, 227)) -> str | None:
    if not os.path.exists(video_path): # ... (sin cambios)
        return None

    video_filename = os.path.basename(video_path)
    # AÑADIR TAMAÑO AL NOMBRE DE LA MINIATURA EN CACHÉ
    thumbnail_filename = f"{os.path.splitext(video_filename)[0]}_thumb_{size[0]}x{size[1]}.png"
    thumbnail_cache_path = os.path.join(THUMBNAIL_CACHE_DIR, thumbnail_filename)

    if os.path.exists(thumbnail_cache_path):
        return thumbnail_cache_path
    # ... (resto de la función como estaba, usando el 'size' proporcionado para .resize()) ...
    try:
        print(f"VideoProc - Generando miniatura ({size[0]}x{size[1]}) para: {video_filename}...")
        with VideoFileClip(video_path) as clip:
            frame = clip.get_frame(time_sec) 
        pil_image = Image.fromarray(frame)
        pil_image_resized = pil_image.resize(size, Image.Resampling.LANCZOS) # O BICUBIC
        pil_image_resized.save(thumbnail_cache_path, "PNG")
        print(f"VideoProc - Miniatura guardada en: {thumbnail_cache_path}")
        return thumbnail_cache_path
    except Exception as e:
        print(f"VideoProc - Error generando miniatura para {video_path}: {e}")
        traceback.print_exc()
        return None

def create_narrated_video(video_path: str, audio_path: str, output_path: str) -> bool:
    """
    Combina un archivo de video con un archivo de audio para crear un video narrado.
    El audio original del video se reemplaza. La duración del video se ajusta al audio.
    """
    try:
        print(f"VideoProc - Iniciando combinación: Video='{video_path}', Audio='{audio_path}'")

        video_clip = VideoFileClip(video_path)
        audio_clip = AudioFileClip(audio_path)

        # Asignar el nuevo audio directamente al atributo 'audio' del videoclip
        video_clip.audio = audio_clip
        video_with_narration = video_clip # video_clip ahora contiene la nueva narración

        # Ajustar la duración del video para que coincida con la del audio
        if audio_clip.duration > video_with_narration.duration:
            print(f"VideoProc - Audio ({audio_clip.duration:.2f}s) > Video ({video_with_narration.duration:.2f}s). Aplicando bucle al video.")
            final_video_clip = vfx_loop(video_with_narration, duration=audio_clip.duration)
            final_video_clip = final_video_clip.set_duration(audio_clip.duration)
        elif audio_clip.duration < video_with_narration.duration:
            print(f"VideoProc - Audio ({audio_clip.duration:.2f}s) < Video ({video_with_narration.duration:.2f}s). Cortando video.")
            final_video_clip = video_with_narration.subclip(0, audio_clip.duration)
        else:
            final_video_clip = video_with_narration

        print(f"VideoProc - Escribiendo video narrado en: {output_path}")
        final_video_clip.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac",
            temp_audiofile='temp-audio.m4a', 
            remove_temp=True,
            threads=4, 
            fps=video_clip.fps # Usar FPS del video original o un valor estándar como 24 o 30
        )

        # Cerrar clips para liberar recursos
        if hasattr(video_clip, 'reader') and video_clip.reader: video_clip.reader.close()
        if hasattr(video_clip, 'audio') and video_clip.audio and hasattr(video_clip.audio, 'reader') and video_clip.audio.reader : video_clip.audio.reader.close_proc()
        
        if hasattr(audio_clip, 'reader') and audio_clip.reader: audio_clip.reader.close_proc()
        
        if final_video_clip != video_with_narration : # si se creó un nuevo clip (loop o subclip)
             if hasattr(final_video_clip, 'reader') and final_video_clip.reader : final_video_clip.reader.close()
             if hasattr(final_video_clip, 'audio') and final_video_clip.audio and hasattr(final_video_clip.audio, 'reader') and final_video_clip.audio.reader : final_video_clip.audio.reader.close_proc()
        
        print("VideoProc - Combinación de audio y video completada.")
        return True

    except Exception as e:
        print(f"VideoProc - Error durante combinación de audio/video: {e}")
        traceback.print_exc()
        return False

def srt_time_to_seconds(srt_time_obj) -> float:
    """Convierte un objeto de tiempo de pysrt a segundos totales."""
    return srt_time_obj.hours * 3600 + srt_time_obj.minutes * 60 + srt_time_obj.seconds + srt_time_obj.milliseconds / 1000.0

def burn_subtitles_on_video(
    video_path: str, 
    srt_path: str, 
    output_path: str,
    style_options: dict = None 
) -> bool:
    if not os.path.exists(video_path):
        print(f"Error SubBurn: Video de entrada no encontrado en '{video_path}'")
        return False
    if not os.path.exists(srt_path):
        print(f"Error SubBurn: Archivo SRT no encontrado en '{srt_path}'")
        return False

    default_style = {
        'font': 'Arial', 'fontsize': 24, 'color': 'white',
        'stroke_color': 'black', 'stroke_width': 1, 
        'bg_color': 'rgba(0, 0, 0, 0.5)', # Fondo semitransparente
        'position_choice': 'Abajo', # "Arriba", "Centro", "Abajo"
        'method': 'caption', 'align': 'center'
    }
    
    current_style = default_style.copy()
    if style_options:
        current_style.update(style_options)
    
    position_choice = current_style.pop('position_choice', 'Abajo')
    
    actual_pos_tuple = ('center', 0.85) # Default Abajo
    if position_choice == "Arriba": actual_pos_tuple = ('center', 0.10)
    elif position_choice == "Centro": actual_pos_tuple = ('center', 'center')
    elif position_choice == "Abajo": actual_pos_tuple = ('center', 0.85)

    try:
        print(f"SubBurn - Iniciando. Video: '{video_path}', SRT: '{srt_path}'")
        print(f"SubBurn - Opciones de estilo: {current_style}, Posición final: {actual_pos_tuple}")

        main_video_clip = VideoFileClip(video_path)
        video_width, video_height = main_video_clip.size

        subs = pysrt.open(srt_path, encoding='utf-8')
        
        subtitle_clips = []
        for sub_item in subs:
            start_s = srt_time_to_seconds(sub_item.start)
            end_s = srt_time_to_seconds(sub_item.end)
            duration_s = end_s - start_s
            
            if duration_s <= 0: continue

            text_clip_w = int(video_width * 0.90)
            
            textclip_creation_args = {
                'txt': sub_item.text,
                'font': current_style['font'],
                'fontsize': int(current_style['fontsize']),
                'color': current_style['color'],
                'bg_color': current_style['bg_color'],
                'stroke_color': current_style['stroke_color'],
                'stroke_width': float(current_style['stroke_width']),
                'method': current_style['method'],
                'align': current_style['align']
            }
            if current_style['method'] == 'caption':
                textclip_creation_args['size'] = (text_clip_w, None) # Ancho fijo, altura auto

            txt_clip = TextClip(**textclip_creation_args)
            txt_clip = txt_clip.set_position(actual_pos_tuple, relative=True).set_duration(duration_s).set_start(start_s)
            subtitle_clips.append(txt_clip)

        if not subtitle_clips:
            print("SubBurn - No se generaron clips de subtítulos.")
            main_video_clip.close()
            return False 

        print(f"SubBurn - Componiendo video con {len(subtitle_clips)} subtítulos.")
        # Asegurarse de que el audio del video principal se mantenga
        final_video = CompositeVideoClip([main_video_clip] + subtitle_clips, size=main_video_clip.size).set_audio(main_video_clip.audio)
        
        print(f"SubBurn - Escribiendo video con subtítulos quemados en: {output_path}")
        final_video.write_videofile(
            output_path, codec="libx264", audio_codec="aac",
            temp_audiofile='temp-subburn-audio.m4a', remove_temp=True,
            threads=4, fps=main_video_clip.fps
        )
        
        # Cerrar clips
        if hasattr(main_video_clip, 'reader') and main_video_clip.reader: main_video_clip.reader.close()
        if hasattr(main_video_clip, 'audio') and main_video_clip.audio and hasattr(main_video_clip.audio, 'reader') and main_video_clip.audio.reader : main_video_clip.audio.reader.close_proc()

        for tc in subtitle_clips: # TextClips no suelen tener 'reader' para cerrar, pero por si acaso.
            if hasattr(tc, 'reader') and tc.reader: tc.reader.close()
            if hasattr(tc, 'mask') and hasattr(tc.mask, 'reader') and tc.mask.reader: tc.mask.reader.close()


        if hasattr(final_video, 'reader') and final_video.reader: final_video.reader.close()
        if hasattr(final_video, 'audio') and final_video.audio and hasattr(final_video.audio, 'reader') and final_video.audio.reader : final_video.audio.reader.close_proc()


        print("SubBurn - Proceso de grabar subtítulos completado.")
        return True

    except Exception as e:
        print(f"Error SubBurn - Ocurrió un error grabando subtítulos: {e}")
        traceback.print_exc()
        return False
    
def generate_subtitle_preview_image_file(
    text: str, 
    style_options: dict, 
    preview_width: int = 300 
) -> str | None:
    try:
        position_choice = style_options.get('position_choice', 'Abajo') 
        text_align = 'South' 
        if position_choice == "Arriba": text_align = 'North'
        elif position_choice == "Centro": text_align = 'Center'
        
        fontsize = int(style_options.get('fontsize', 24))
        stroke_width = float(style_options.get('stroke_width', 1))

        textclip_kwargs = {
            'txt': text,
            'font': style_options.get('font', 'Arial'),
            'fontsize': fontsize,
            'color': style_options.get('color', 'white'),
            'bg_color': 'transparent', # Fondo transparente para la imagen del texto
            'stroke_color': style_options.get('stroke_color'),
            'stroke_width': stroke_width,
            'method': 'caption', 
            'align': text_align, # Esto alinea el texto DENTRO de la caja del TextClip
             # Tamaño: Ancho fijo, altura fija para que se note la alineación vertical
            'size': (preview_width, PREVIEW_SUBTITLE_HEIGHT) 
        }
        
        if stroke_width == 0:
            textclip_kwargs.pop('stroke_color', None)
            textclip_kwargs.pop('stroke_width', None)

        print(f"SubPreview Gen - Creando TextClip con: {textclip_kwargs}")
        with TextClip(**textclip_kwargs) as clip:
            clip.save_frame(SUBTITLE_PREVIEW_IMAGE_TEMP_FILE, t=0) 
        
        return SUBTITLE_PREVIEW_IMAGE_TEMP_FILE
    except Exception as e:
        print(f"SubPreview Gen - Error generando imagen de TextClip para preview: {e}")
        traceback.print_exc()
        if os.path.exists(SUBTITLE_PREVIEW_IMAGE_TEMP_FILE):
            try: os.remove(SUBTITLE_PREVIEW_IMAGE_TEMP_FILE)
            except Exception as e_del: print(f"SubPreview Gen - Error borrando preview: {e_del}")
        return None
    
def create_composite_preview_image(
    base_video_thumbnail_path: str,
    subtitle_text: str,
    style_options: dict
) -> str | None:
    if not os.path.exists(base_video_thumbnail_path):
        print(f"PreviewComp - Miniatura de video base no encontrada: {base_video_thumbnail_path}")
        return None

    try:
        base_img_pil = Image.open(base_video_thumbnail_path).convert("RGBA")
        base_width, base_height = base_img_pil.size

        # Ancho para el TextClip del subtítulo (un poco menos que la miniatura base)
        text_clip_width = int(base_width * 0.90) 
        # La altura del TextClip será automática (None) para que se ajuste al texto
        text_clip_height_allowance = None # Dejar que MoviePy decida la altura del TextClip

        position_choice = style_options.get('position_choice', 'Abajo')
        text_align_map = {"Arriba": "North", "Centro": "Center", "Abajo": "South"}
        text_align = text_align_map.get(position_choice, 'South')
        fontsize = int(style_options.get('fontsize', 36)) # Usar un fontsize por defecto más grande para preview
        stroke_width = float(style_options.get('stroke_width', 1.5))

        textclip_kwargs = {
            'txt': subtitle_text,
            'font': style_options.get('font', 'Arial'),
            'fontsize': fontsize,
            'color': style_options.get('color', 'yellow'),
            'bg_color': 'transparent', # <<<--- MUY IMPORTANTE para la superposición
            'stroke_color': style_options.get('stroke_color', 'black'),
            'stroke_width': stroke_width,
            'method': 'caption', # 'caption' es bueno para multilínea
            'align': text_align, # Alineación del texto DENTRO de la caja del TextClip
            'size': (text_clip_width, text_clip_height_allowance) 
        }
        if stroke_width == 0: # MoviePy puede dar error si stroke_width es 0 y stroke_color está definido
            textclip_kwargs.pop('stroke_color', None)
            textclip_kwargs.pop('stroke_width', None)
        
        print(f"PreviewComp - Creando TextClip para subtítulo: '{subtitle_text[:20]}...' con {textclip_kwargs}")
        # Crear el TextClip y obtener su frame como un array NumPy RGBA
        with TextClip(**textclip_kwargs) as txt_clip:
            # .get_frame(0) para imagen estática. El canal alfa es crucial.
            # Asegurarse de que el clip se renderice con alfa:
            subtitle_frame_array = txt_clip.get_frame(0) # Esto es (height, width, 3) si no hay alfa
            # Para asegurar canal alfa si TextClip no lo añade por defecto con bg_color='transparent'
            # Es mejor que TextClip genere una máscara alfa si es posible.
            # Alternativamente, crear una imagen PIL desde el array y asegurar que es RGBA.
            # Si txt_clip.mask no existe o bg_color no fue suficiente para crear alfa:
            if subtitle_frame_array.shape[2] == 3: # Si es RGB, añadir canal alfa
                 alpha = np.full((subtitle_frame_array.shape[0], subtitle_frame_array.shape[1], 1), 255, dtype=np.uint8)
                 # Crear una máscara simple basada en si el color es el de fondo (si no es transparente)
                 # Esto es complejo si no sabemos el color de fondo real que usa TextClip si 'transparent' falla.
                 # Lo ideal es que TextClip con bg_color='transparent' produzca un frame con alfa.
                 # Por ahora, asumimos que si es RGB, el texto no es transparente.
                 # Si el texto es 'white' y el fondo 'transparent', el alfa debe ser 0 donde no hay texto.
                 # MoviePy debería manejar esto con save_frame a PNG.
                 # Vamos a intentar guardar el TextClip en un archivo PNG temporal para obtener el RGBA correcto.
            txt_clip.save_frame(SUBTITLE_ONLY_PREVIEW_IMAGE_TEMP_FILE, t=0) # Usar la constante global

        if not os.path.exists(SUBTITLE_ONLY_PREVIEW_IMAGE_TEMP_FILE):
            print("PreviewComp - Fallo al generar la imagen temporal del subtítulo desde TextClip.")
            return None
            
        subtitle_img_pil = Image.open(SUBTITLE_ONLY_PREVIEW_IMAGE_TEMP_FILE).convert("RGBA")
        sub_width, sub_height = subtitle_img_pil.size

        # Calcular posición para superponer el subtítulo
        pos_x = (base_width - sub_width) // 2 
        pos_y = 0
        if position_choice == "Arriba":   pos_y = int(base_height * 0.10) 
        elif position_choice == "Centro": pos_y = (base_height // 2) - (sub_height // 2)
        elif position_choice == "Abajo":  pos_y = int(base_height * 0.90) - sub_height 
        
        pos_y = max(0, min(pos_y, base_height - sub_height)) # Asegurar que esté dentro de los límites
        pos_x = max(0, min(pos_x, base_width - sub_width))   # Asegurar que esté dentro de los límites


        print(f"PreviewComp - Componiendo. Base: {base_width}x{base_height}, Sub: {sub_width}x{sub_height}, Pos: ({pos_x},{pos_y})")
        composite_img = base_img_pil.copy() # Usar la miniatura del video como base
        composite_img.paste(subtitle_img_pil, (pos_x, pos_y), subtitle_img_pil) # Usar el canal alfa de la imagen del subtítulo como máscara

        composite_img.save(COMBINED_PREVIEW_IMAGE_TEMP_FILE, "PNG") # Guardar la imagen compuesta
        print(f"PreviewComp - Imagen compuesta guardada: {COMBINED_PREVIEW_IMAGE_TEMP_FILE}")
        
        # Limpiar la imagen temporal solo del subtítulo
        if os.path.exists(SUBTITLE_ONLY_PREVIEW_IMAGE_TEMP_FILE):
            try: os.remove(SUBTITLE_ONLY_PREVIEW_IMAGE_TEMP_FILE)
            except Exception as e_del: print(f"PreviewComp - No se pudo borrar {SUBTITLE_ONLY_PREVIEW_IMAGE_TEMP_FILE}: {e_del}")
            
        return COMBINED_PREVIEW_IMAGE_TEMP_FILE

    except Exception as e:
        print(f"PreviewComp - Error creando imagen compuesta: {e}"); traceback.print_exc()
        return None

if __name__ == '__main__':
    print("--- Probando funciones de miniaturas de video ---")
    # 1. Crea una carpeta "video_templates" en tu proyecto y pon algunos videos .mp4 cortos allí.
    # 2. Luego ejecuta este script.
    
    videos = list_video_templates()
    if videos:
        print(f"\nVideos encontrados en '{VIDEO_TEMPLATES_DIR}':")
        for vid in videos:
            print(f"  - {vid}")
            thumb_path = get_or_create_thumbnail(vid)
            if thumb_path:
                print(f"    Miniatura -> {thumb_path}")
            else:
                print(f"    No se pudo generar miniatura para {vid}")
        
        # Probar de nuevo para ver si usa la caché
        print("\nVolviendo a pedir miniaturas (debería usar caché):")
        for vid in videos:
            thumb_path = get_or_create_thumbnail(vid)
            if thumb_path:
                print(f"  - Miniatura para {os.path.basename(vid)}: {thumb_path} (desde caché probablemente)")

    else:
        print(f"No se encontraron videos en la carpeta '{VIDEO_TEMPLATES_DIR}'. Por favor, añade algunos videos para probar.")
    
    # --- Bloque de Prueba para burn_subtitles_on_video ---
    print("\n--- Iniciando prueba del módulo burn_subtitles_on_video ---")
    
    # Debes tener estos archivos generados por los pasos anteriores de tu app
    test_input_narrated_video = "video_final_narrado.mp4" 
    test_input_srt_file = "historia_narrada.srt"       
    test_output_video_with_subs = "video_con_subtitulos_quemados_prueba.mp4"

    font_options_for_test = {
        'font': 'Arial-Bold', 
        'fontsize': 36, # Aumentado para visibilidad en prueba
        'color': 'yellow',
        'stroke_color': 'black',
        'stroke_width': 2,
        'bg_color': 'rgba(0,0,0,0.6)', 
        'position_choice': 'Abajo' 
    }

    if os.path.exists(test_input_narrated_video) and os.path.exists(test_input_srt_file):
        print(f"Usando video narrado: '{test_input_narrated_video}' y SRT: '{test_input_srt_file}'")
        print(f"Opciones de estilo para prueba: {font_options_for_test}")
        success_burn = burn_subtitles_on_video(
            test_input_narrated_video,
            test_input_srt_file,
            test_output_video_with_subs,
            style_options=font_options_for_test # Cambiado a style_options
        )
        if success_burn:
            print(f"Prueba de grabar subtítulos completada. Video generado: {test_output_video_with_subs}")
        else:
            print("Fallo en la prueba de grabar subtítulos.")
    else:
        print("\nError Crítico para prueba de burn_subtitles:")
        if not os.path.exists(test_input_narrated_video):
            print(f"  - El video narrado de entrada '{test_input_narrated_video}' no existe.")
        if not os.path.exists(test_input_srt_file):
            print(f"  - El archivo SRT de entrada '{test_input_srt_file}' no existe.")
        print("Asegúrate de tener estos archivos (productos de los pasos anteriores del programa).")

    # También puedes añadir aquí la prueba de create_narrated_video si lo deseas,
    # pero asegúrate de tener un video base y un audio para ello.