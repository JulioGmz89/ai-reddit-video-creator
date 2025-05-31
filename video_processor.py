# video_processor.py

import os
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip
from moviepy.video.fx.all import loop as vfx_loop # Para el bucle de video

def create_narrated_video(video_path: str, audio_path: str, output_path: str) -> bool:
    """
    Combina un archivo de video con un archivo de audio para crear un video narrado.

    Args:
        video_path (str): Ruta al archivo de video de entrada (vertical).
        audio_path (str): Ruta al archivo de audio de narración.
        output_path (str): Ruta donde se guardará el video MP4 de salida.

    Returns:
        bool: True si el video se creó exitosamente, False en caso contrario.
    """
    try:
        print(f"Procesamiento de video iniciado: Video='{video_path}', Audio='{audio_path}'")

        # Cargar los clips de video y audio
        video_clip = VideoFileClip(video_path)
        audio_clip = AudioFileClip(audio_path)

        # --- CORRECCIÓN AQUÍ ---
        # Asignar el nuevo audio directamente al atributo 'audio' del videoclip
        video_clip.audio = audio_clip
        video_clip_with_narration = video_clip # video_clip ahora contiene la nueva narración
        # --- FIN DE LA CORRECCIÓN ---

        # Ajustar la duración del video para que coincida con la del audio
        if audio_clip.duration > video_clip_with_narration.duration:
            print(f"Audio ({audio_clip.duration:.2f}s) es más largo que el video ({video_clip_with_narration.duration:.2f}s). Aplicando bucle al video.")
            final_video_clip = vfx_loop(video_clip_with_narration, duration=audio_clip.duration)
            final_video_clip = final_video_clip.set_duration(audio_clip.duration) # Asegurar duración exacta
        elif audio_clip.duration < video_clip_with_narration.duration:
            print(f"Audio ({audio_clip.duration:.2f}s) es más corto que el video ({video_clip_with_narration.duration:.2f}s). Cortando video.")
            final_video_clip = video_clip_with_narration.subclip(0, audio_clip.duration)
        else:
            final_video_clip = video_clip_with_narration

        print(f"Escribiendo video final en: {output_path}")
        final_video_clip.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac",
            temp_audiofile='temp-audio.m4a', 
            remove_temp=True,
            threads=4, 
            fps=video_clip.fps 
        )

        video_clip.close() # Cerrar el clip original de video
        audio_clip.close()
        # No es necesario cerrar video_clip_with_narration si es el mismo objeto que video_clip
        # final_video_clip también se cierra usualmente por write_videofile o se puede cerrar explícitamente
        # si se va a reutilizar o hay problemas de bloqueo de archivos.
        if final_video_clip != video_clip_with_narration : # si se creó un nuevo clip (loop o subclip)
             if hasattr(final_video_clip, 'close') and callable(getattr(final_video_clip, 'close')):
                  final_video_clip.close()


        print("Procesamiento de video completado exitosamente.")
        return True

    except Exception as e:
        print(f"Error durante el procesamiento de video: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    # --- Bloque de Prueba ---
    print("Iniciando prueba del módulo video_processor...")

    # REEMPLAZA ESTOS VALORES con rutas a tus archivos reales de video y audio
    test_video_file = "dummy_test_video.mp4" 
    test_audio_file = "dummy_test_audio.wav" 
    # --------------------------------------------------------------------
    
    output_video_file = "narrated_output_test.mp4"

    create_dummy_files = False # Mantén en False a menos que quieras crear archivos dummy

    if create_dummy_files:
        # (Código para crear archivos dummy - sin cambios)
        if not os.path.exists(test_video_file):
            from moviepy.editor import ColorClip
            try:
                clip = ColorClip(size=(720, 1280), color=(0,0,0), duration=5, ismask=False, fps=24)
                clip.write_videofile(test_video_file)
                print(f"Video dummy creado: {test_video_file}")
            except Exception as e_dummy_vid:
                print(f"No se pudo crear video dummy: {e_dummy_vid}")
            finally:
                if 'clip' in locals(): clip.close()
        if not os.path.exists(test_audio_file):
            import wave, numpy as np
            try:
                sample_rate = 24000; duration = 10; frequency = 440
                n_samples = int(sample_rate * duration)
                t = np.linspace(0, duration, n_samples, endpoint=False)
                audio_data = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)
                with wave.open(test_audio_file, 'w') as wf:
                    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sample_rate)
                    wf.writeframes(audio_data.tobytes())
                print(f"Audio dummy creado: {test_audio_file}")
            except Exception as e_dummy_audio:
                print(f"No se pudo crear audio dummy: {e_dummy_audio}")
    
    print(f"\nUsando video: '{os.path.abspath(test_video_file)}' y audio: '{os.path.abspath(test_audio_file)}' para la prueba.")
    print(f"El video de salida se guardará como: '{os.path.abspath(output_video_file)}'")
    
    if os.path.exists(test_video_file) and os.path.exists(test_audio_file):
        success = create_narrated_video(test_video_file, test_audio_file, output_video_file)
        if success:
            print(f"Prueba completada. Video narrado generado: {output_video_file}")
        else:
            print("Fallo en la prueba de generación de video.")
    else:
        print("\nError: Los archivos de video o audio de prueba no existen.")
        print(f"Asegúrate de tenerlos o modifica las variables 'test_video_file' y 'test_audio_file'.")