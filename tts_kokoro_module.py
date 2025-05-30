# tts_kokoro_module.py

from kokoro import KPipeline
import soundfile as sf
import torch
import traceback

DEVICE = None
KOKORO_REPO_ID = 'hexgrad/Kokoro-82M' # El repo_id del modelo que queremos usar
PIPELINE_INSTANCE = None # Pipeline global para este módulo

def _initialize_device():
    global DEVICE
    if DEVICE is None:
        if torch.cuda.is_available():
            DEVICE = "cuda"
        elif torch.backends.mps.is_available(): 
            DEVICE = "mps"
        else:
            DEVICE = "cpu"
        print(f"TTS - Usando dispositivo: {DEVICE}")
    return DEVICE

def initialize_global_pipeline():
    """Intenta inicializar KPipeline globalmente."""
    global PIPELINE_INSTANCE
    if PIPELINE_INSTANCE is not None:
        # print("KPipeline global ya está inicializado.")
        return True

    device = _initialize_device()
    print(f"Intentando inicializar KPipeline globalmente con repo_id='{KOKORO_REPO_ID}'...")
    
    try:
        PIPELINE_INSTANCE = KPipeline(
            lang_code='a', # Como se sugiere en el README de Kokoro-82M para auto-detección
            device=device,
            repo_id=KOKORO_REPO_ID # Es crucial que la biblioteca use este repo_id
        )
        print("KPipeline global parece haberse inicializado.")
        
        # Depuración: Verificar si el modelo y config tienen sample_rate
        if hasattr(PIPELINE_INSTANCE, 'model') and PIPELINE_INSTANCE.model and \
           hasattr(PIPELINE_INSTANCE.model, 'config') and PIPELINE_INSTANCE.model.config and \
           hasattr(PIPELINE_INSTANCE.model.config, 'sampling_rate'):
            print(f"DEBUG: Sample rate obtenido de PIPELINE_INSTANCE.model.config: {PIPELINE_INSTANCE.model.config.sampling_rate}")
        else:
            print("DEBUG: No se pudo acceder a PIPELINE_INSTANCE.model.config.sampling_rate. Se usará un valor por defecto para sf.write si es necesario.")
            
        return True

    except Exception as e:
        print(f"Error GRAVE inicializando KPipeline globalmente: {e}")
        traceback.print_exc()
        PIPELINE_INSTANCE = None
        return False

# Intentar inicializar el pipeline cuando se carga el módulo
initialize_global_pipeline()


def list_english_voices_for_pip_package() -> dict:
    """
    Lista voces en inglés que podrían funcionar con el paquete pip kokoro
    si sus archivos .pt correspondientes existen en la carpeta 'voices/'
    del repo_id que el sistema del usuario está viendo.
    """
    voices = {
        "American Female (Heart / af_heart)": "af_heart",
        # Ejemplo: Si descubres que "af_alloy" funciona, la añadirías aquí:
        # "American Female (Alloy / af_alloy)": "af_alloy",
    }
    return voices

def generate_speech_with_voice_name(text: str, voice_technical_name: str, output_filename: str = "output.wav") -> bool:
    if not PIPELINE_INSTANCE:
        print("Error: KPipeline global no está disponible/inicializado.")
        # Podríamos intentar inicializarlo aquí de nuevo si falló antes, pero es mejor que falle claramente.
        return False
    if not text.strip():
        print("Error: El texto para generar audio está vacío.")
        return False

    try:
        print(f"Generando audio para el texto: '{text[:50]}...' (Voz solicitada: '{voice_technical_name}')")
        all_audio_segments = []
        
        # Usamos el argumento 'voice' con el nombre técnico.
        # La biblioteca kokoro~=0.9.4 internamente llamará a self.load_voice(voice_technical_name)
        # lo que intentará descargar .../voices/<voice_technical_name>.pt
        for i, (_batch_size, _phoneme_speed, audio_segment) in enumerate(PIPELINE_INSTANCE(text, voice=voice_technical_name)):
            if isinstance(audio_segment, torch.Tensor):
                audio_segment = audio_segment.cpu().numpy()
            all_audio_segments.append(audio_segment)
        
        if not all_audio_segments:
            print("Error: No se generaron segmentos de audio.")
            return False

        final_audio = all_audio_segments[0]
        if len(all_audio_segments) > 1:
            print(f"Advertencia: Se generaron {len(all_audio_segments)} segmentos de audio. Se usará el primero.")

        # Corregir cómo obtenemos el sample_rate
        sample_rate = 24000 # Valor por defecto si no se encuentra en la config
        if hasattr(PIPELINE_INSTANCE, 'model') and PIPELINE_INSTANCE.model and \
           hasattr(PIPELINE_INSTANCE.model, 'config') and PIPELINE_INSTANCE.model.config and \
           hasattr(PIPELINE_INSTANCE.model.config, 'sampling_rate'):
            sample_rate = PIPELINE_INSTANCE.model.config.sampling_rate
        else:
             # Si el pipeline tiene un atributo sample_rate directamente (menos probable pero posible)
            if hasattr(PIPELINE_INSTANCE, 'sample_rate'):
                sample_rate = PIPELINE_INSTANCE.sample_rate
            else:
                print(f"Advertencia: No se pudo obtener sample_rate de la configuración del modelo o del pipeline. Usando por defecto {sample_rate} Hz.")


        sf.write(output_filename, final_audio, sample_rate)
        print(f"Audio guardado como '{output_filename}' con sample rate {sample_rate} Hz.")
        return True
    except ValueError as ve:
        if "Specify a voice" in str(ve):
            print(f"Error de ValueError: {ve} - La biblioteca 'kokoro' requiere el argumento 'voice'.")
        else:
            print(f"Error de ValueError durante la generación: {ve}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"Error general/inesperado durante la generación de audio (Voz: {voice_technical_name}): {e}")
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("\n--- Iniciando prueba de TTS del módulo (enfocada en 'af_heart' con paquete pip) ---")
    if not PIPELINE_INSTANCE:
        print("Finalizando prueba: KPipeline global no se pudo inicializar durante la carga del módulo.")
    else:
        test_text_en = "I'm late for school. How I slept through the 200 clocks in the bedroom is beyond me. Why do I have so many clocks? I can't remember anything about the night before, and I'm still dressed. Clearly I'd just crashed so hard it took the some Huey Lewis and the News to wake me up. That shit is tight."
        
        voice_map = list_english_voices_for_pip_package()
        technical_name_to_test = voice_map.get("American Female (Heart / af_heart)")

        if technical_name_to_test:
            print(f"Probando con la voz técnica: '{technical_name_to_test}'")
            success = generate_speech_with_voice_name(test_text_en, technical_name_to_test, "prueba_kokoro_af_heart_pip.wav")
            if success:
                print("Prueba con 'af_heart' completada. Verifica 'prueba_kokoro_af_heart_pip.wav'.")
            else:
                print("Fallo en la prueba con 'af_heart'.")
        else:
            # Esto no debería ocurrir si la clave está bien escrita
            print(f"Error: No se encontró el nombre técnico para 'American Female (Heart / af_heart)'.")