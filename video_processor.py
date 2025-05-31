# video_processor.py
import os
import traceback
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
from moviepy.video.fx.all import loop as vfx_loop
import pysrt # <--- Importar pysrt

# ... (tu función create_narrated_video existente sin cambios) ...
# def create_narrated_video(video_path: str, audio_path: str, output_path: str) -> bool:
#    # ... tu código ...


def srt_time_to_seconds(srt_time_obj) -> float:
    """Convierte un objeto de tiempo de pysrt (o similar) a segundos totales."""
    return srt_time_obj.hours * 3600 + srt_time_obj.minutes * 60 + srt_time_obj.seconds + srt_time_obj.milliseconds / 1000.0

def burn_subtitles_on_video(
    video_path: str, 
    srt_path: str, 
    output_path: str,
    font_options: dict = None
) -> bool:
    """
    Graba los subtítulos de un archivo SRT en un video.

    Args:
        video_path (str): Ruta al video de entrada (el que ya tiene la narración).
        srt_path (str): Ruta al archivo .srt.
        output_path (str): Ruta para guardar el video con subtítulos grabados.
        font_options (dict, optional): Diccionario con opciones de estilo para los subtítulos.
            Ej: {'font': 'Arial-Bold', 'fontsize': 24, 'color': 'white', 
                 'stroke_color': 'black', 'stroke_width': 1, 'bg_color': 'transparent',
                 'position': ('center', 0.85)} # Posición relativa (85% hacia abajo)
    Returns:
        bool: True si fue exitoso, False en caso contrario.
    """
    if not os.path.exists(video_path):
        print(f"Error SubBurn: Video de entrada no encontrado en '{video_path}'")
        return False
    if not os.path.exists(srt_path):
        print(f"Error SubBurn: Archivo SRT no encontrado en '{srt_path}'")
        return False

    # Opciones de fuente por defecto si no se proporcionan
    default_font_options = {
        'font': 'Arial', # Prueba con fuentes comunes. Puedes necesitar especificar la ruta a un .ttf
        'fontsize': 24,
        'color': 'white',
        'stroke_color': 'black', # Color del borde
        'stroke_width': 1,      # Ancho del borde
        'bg_color': 'rgba(0, 0, 0, 0.5)', # Fondo semitransparente para legibilidad
        'method': 'caption',    # 'caption' para auto-ajuste de texto, 'label' para una línea
        'align': 'center'
        # La posición se aplicará más abajo para que sea relativa al tamaño del video.
    }
    current_font_options = default_font_options.copy()
    if font_options:
        current_font_options.update(font_options)
    
    # Posición por defecto para los subtítulos (relativa al video)
    # ('center', 0.85) significa centrado horizontalmente, y al 85% de la altura desde arriba.
    subtitle_position = current_font_options.pop('position', ('center', 0.85))


    try:
        print(f"SubBurn - Iniciando proceso para video: '{video_path}' y SRT: '{srt_path}'")
        main_video_clip = VideoFileClip(video_path)
        video_width, video_height = main_video_clip.size

        subs = pysrt.open(srt_path, encoding='utf-8')
        
        subtitle_clips = []
        for sub_item in subs:
            start_time = srt_time_to_seconds(sub_item.start)
            end_time = srt_time_to_seconds(sub_item.end)
            duration = end_time - start_time
            
            if duration <= 0: # Ignorar subtítulos con duración inválida
                continue

            # Configurar el tamaño del TextClip para que se ajuste (ej. 80% del ancho del video)
            # Esto es especialmente útil con method='caption'
            text_clip_width = int(video_width * 0.9) # Subtítulos pueden ocupar el 90% del ancho

            text_options_for_clip = current_font_options.copy()
            if text_options_for_clip['method'] == 'caption':
                text_options_for_clip['size'] = (text_clip_width, None) # Ancho fijo, altura automática


            txt_clip = TextClip(
                sub_item.text,
                font=text_options_for_clip['font'],
                fontsize=text_options_for_clip['fontsize'],
                color=text_options_for_clip['color'],
                bg_color=text_options_for_clip['bg_color'],
                stroke_color=text_options_for_clip['stroke_color'],
                stroke_width=text_options_for_clip['stroke_width'],
                method=text_options_for_clip['method'],
                align=text_options_for_clip['align'],
                size=text_options_for_clip.get('size') # Usar el tamaño si se definió (para caption)
            )
            
            txt_clip = txt_clip.set_position(subtitle_position, relative=True).set_duration(duration).set_start(start_time)
            subtitle_clips.append(txt_clip)

        if not subtitle_clips:
            print("SubBurn - No se generaron clips de subtítulos. ¿El archivo SRT está vacío o tiene formato incorrecto?")
            main_video_clip.close()
            # Guardamos el video original si no hay subtítulos para quemar? O indicamos error?
            # Por ahora, si no hay subtítulos, no modificamos el video.
            return False 

        print(f"SubBurn - Componiendo video con {len(subtitle_clips)} segmentos de subtítulos.")
        # Crear el video final componiendo el video original con todos los TextClips
        final_video = CompositeVideoClip([main_video_clip] + subtitle_clips, size=main_video_clip.size)
        
        print(f"SubBurn - Escribiendo video final con subtítulos en: {output_path}")
        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac", # El audio ya debería estar del video de entrada
            temp_audiofile='temp-subburn-audio.m4a',
            remove_temp=True,
            threads=4,
            fps=main_video_clip.fps
        )

        main_video_clip.close()
        # for tc in subtitle_clips: tc.close() # TextClip no siempre tiene close() o no es necesario
        # final_video.close()

        print("SubBurn - Proceso de grabar subtítulos completado.")
        return True

    except Exception as e:
        print(f"Error SubBurn - Ocurrió un error grabando subtítulos: {e}")
        traceback.print_exc()
        return False

if __name__ == '__main__':
    # --- Bloque de Prueba para burn_subtitles_on_video ---
    print("\n--- Iniciando prueba del módulo burn_subtitles_on_video ---")
    
    # Necesitas un video YA NARRADO (ej. el 'video_final_narrado.mp4' de la etapa anterior)
    # y un archivo SRT (ej. 'historia_narrada.srt')
    test_input_narrated_video = "video_final_narrado.mp4" # REEMPLAZA si es necesario
    test_input_srt_file = "historia_narrada.srt"       # REEMPLAZA si es necesario
    test_output_video_with_subs = "video_con_subtitulos_quemados.mp4"

    # Opciones de fuente para la prueba
    font_options_test = {
        'font': 'Arial-Bold', # Asegúrate que esta fuente esté disponible o usa una genérica como 'Arial'
        'fontsize': 28,
        'color': 'yellow',
        'stroke_color': 'black',
        'stroke_width': 1.5,
        'bg_color': 'rgba(0, 0, 0, 0.3)', # Un poco más transparente
        'position': ('center', 0.9) # 90% hacia abajo
    }

    if os.path.exists(test_input_narrated_video) and os.path.exists(test_input_srt_file):
        print(f"Usando video narrado: '{test_input_narrated_video}' y SRT: '{test_input_srt_file}'")
        success = burn_subtitles_on_video(
            test_input_narrated_video,
            test_input_srt_file,
            test_output_video_with_subs,
            font_options=font_options_test
        )
        if success:
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