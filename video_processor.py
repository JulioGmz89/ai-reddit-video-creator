# video_processor.py
import os
import traceback
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
from moviepy.video.fx.all import loop as vfx_loop
import pysrt # Para parsear archivos SRT

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

if __name__ == '__main__':
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