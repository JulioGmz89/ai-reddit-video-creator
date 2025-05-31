# srt_generator.py
import whisper
import os
import traceback

def _format_timestamp(seconds: float) -> str:
    """Convierte segundos a formato de tiempo SRT HH:MM:SS,mmm."""
    assert seconds >= 0, "El timestamp no puede ser negativo"
    milliseconds = round(seconds * 1000.0)

    hours = int(milliseconds // 3_600_000)
    milliseconds %= 3_600_000
    minutes = int(milliseconds // 60_000)
    milliseconds %= 60_000
    seconds = int(milliseconds // 1_000)
    milliseconds %= 1_000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def create_srt_file(
    audio_path: str, 
    srt_path: str, 
    model_size: str = "base.en", 
    language: str = "en",
    max_words_per_segment: int | None = None # Nuevo parámetro
) -> bool:
    """
    Genera un archivo SRT a partir de un archivo de audio usando Whisper,
    con opción de limitar las palabras por segmento.

    Args:
        audio_path (str): Ruta al archivo de audio de entrada.
        srt_path (str): Ruta donde se guardará el archivo .srt de salida.
        model_size (str, optional): Tamaño del modelo Whisper. Defaults to "base.en".
        language (str, optional): Idioma del audio. Defaults to "en".
        max_words_per_segment (int | None, optional): Número máximo de palabras por 
                                                     segmento de subtítulo. 
                                                     Si es None, usa la segmentación por defecto de Whisper.
                                                     Defaults to None.
    Returns:
        bool: True si el archivo SRT se creó exitosamente, False en caso contrario.
    """
    if not os.path.exists(audio_path):
        print(f"Error SRT: El archivo de audio no existe en '{audio_path}'")
        return False

    try:
        print(f"SRT Gen - Cargando modelo Whisper '{model_size}'. Esto puede tardar la primera vez...")
        model = whisper.load_model(model_size) 
        print("SRT Gen - Modelo Whisper cargado.")

        print(f"SRT Gen - Transcribiendo audio desde: {audio_path}. Esto puede tomar tiempo...")
        
        # Necesitamos word_timestamps=True si vamos a limitar las palabras por segmento
        should_get_word_timestamps = isinstance(max_words_per_segment, int) and max_words_per_segment > 0
        
        result = model.transcribe(
            audio_path, 
            language=language, 
            verbose=False, # Cambiado a False para una salida más limpia, pon True si quieres ver el progreso detallado
            word_timestamps=should_get_word_timestamps 
        )
        print("SRT Gen - Transcripción completada.")

        srt_segment_index = 1
        with open(srt_path, "w", encoding="utf-8") as f:
            if should_get_word_timestamps:
                print(f"SRT Gen - Aplicando límite de {max_words_per_segment} palabras por segmento de subtítulo.")
                for segment_from_whisper in result["segments"]: # Iterar sobre los segmentos originales de Whisper
                    if 'words' not in segment_from_whisper:
                        print("Advertencia SRT: No se encontraron timestamps de palabras en un segmento, usando el segmento completo.")
                        # Fallback: usar el segmento original si no hay 'words' (no debería pasar si word_timestamps=True)
                        start_time = _format_timestamp(segment_from_whisper["start"])
                        end_time = _format_timestamp(segment_from_whisper["end"])
                        text = segment_from_whisper["text"].strip()
                        if text:
                            f.write(f"{srt_segment_index}\n")
                            f.write(f"{start_time} --> {end_time}\n")
                            f.write(f"{text}\n\n")
                            srt_segment_index += 1
                        continue

                    words_in_segment = segment_from_whisper['words']
                    current_chunk_words = [] # Lista para guardar la información de las palabras del chunk actual

                    for i, word_info in enumerate(words_in_segment):
                        current_chunk_words.append(word_info)
                        
                        # Escribir el chunk si hemos alcanzado max_words_per_segment
                        # o si es la última palabra del segmento de Whisper
                        if len(current_chunk_words) == max_words_per_segment or i == len(words_in_segment) - 1:
                            if not current_chunk_words: # Si el chunk está vacío (no debería pasar)
                                continue

                            chunk_text = " ".join([word_data['word'] for word_data in current_chunk_words]).strip()
                            chunk_start_time = current_chunk_words[0]['start']
                            chunk_end_time = current_chunk_words[-1]['end']
                            
                            if chunk_text: # Solo escribir si hay texto
                                f.write(f"{srt_segment_index}\n")
                                f.write(f"{_format_timestamp(chunk_start_time)} --> {_format_timestamp(chunk_end_time)}\n")
                                f.write(f"{chunk_text}\n\n")
                                srt_segment_index += 1
                            
                            current_chunk_words = [] # Resetear para el siguiente chunk
            else: # Comportamiento original: un SRT por segmento de Whisper
                for segment in result["segments"]:
                    start_time = _format_timestamp(segment["start"])
                    end_time = _format_timestamp(segment["end"])
                    text = segment["text"].strip()
                    if text:
                        f.write(f"{srt_segment_index}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{text}\n\n")
                        srt_segment_index += 1
        
        print(f"SRT Gen - Archivo de subtítulos guardado en: {srt_path}")
        return True

    except FileNotFoundError:
        print("Error SRT: ffmpeg no encontrado. Asegúrate de que ffmpeg esté instalado y en el PATH de tu sistema.")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"Error SRT - Ocurrió un error durante la generación de subtítulos: {e}")
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("--- Iniciando prueba del módulo SRT Generator ---")
    
    test_audio_input_path = "historia_narrada.wav" 
    
    # Crear un dummy WAV si no existe, para que el script no falle al probar
    if not os.path.exists(test_audio_input_path):
        print(f"ADVERTENCIA: '{test_audio_input_path}' no existe. Creando dummy WAV.")
        try:
            import wave, numpy as np
            sr, dur, nchan, sw = 24000, 2, 1, 2; freq = 440
            nfr = int(dur*sr); t = np.linspace(0,dur,nfr,endpoint=False)
            ad = (np.sin(2*np.pi*freq*t)*(2**(8*sw-1)-1)).astype(np.int16)
            with wave.open(test_audio_input_path,'w') as wf:
                wf.setnchannels(nchan);wf.setsampwidth(sw);wf.setframerate(sr)
                wf.writeframes(ad.tobytes())
            print(f"Audio dummy creado: {test_audio_input_path}")
        except Exception as e_dummy: print(f"No se pudo crear audio dummy: {e_dummy}")

    if os.path.exists(test_audio_input_path):
        print(f"Usando audio de prueba: {test_audio_input_path}")
        
        # Prueba con el límite de palabras por segmento
        max_words = 3
        output_srt_custom = f"subtitulos_max_{max_words}_palabras.srt"
        print(f"\nProbando con max_words_per_segment = {max_words}")
        success_custom = create_srt_file(
            test_audio_input_path, 
            output_srt_custom, 
            model_size="base.en", 
            language="en",
            max_words_per_segment=max_words # Aplicando el límite
        )
        if success_custom:
            print(f"Prueba con max_words={max_words} completada. Archivo: {output_srt_custom}")
        else:
            print(f"Fallo prueba con max_words={max_words}.")

        # Prueba opcional con la segmentación por defecto de Whisper
        # output_srt_default = "subtitulos_default_segmentos.srt"
        # print("\nProbando con segmentación por defecto de Whisper...")
        # success_default = create_srt_file(
        #     test_audio_input_path, 
        #     output_srt_default, 
        #     model_size="base.en", 
        #     language="en"
        #     # No se pasa max_words_per_segment para usar el default
        # )
        # if success_default:
        #     print(f"Prueba con segmentación por defecto completada. Archivo: {output_srt_default}")
        # else:
        #     print("Fallo prueba con segmentación por defecto.")
    else:
        print(f"\nError Crítico: El archivo de audio de prueba '{test_audio_input_path}' NO EXISTE y no se pudo crear un dummy.")