# generate_voice_samples.py
import os
import shutil # Para borrar la carpeta de muestras si es necesario
import tts_kokoro_module # Importamos para la lista de voces y la generación

OUTPUT_SAMPLE_DIR = "voice_samples"

def create_sample_sentence(voice_friendly_name: str, voice_technical_name: str) -> str:
    """Construye la frase de prueba para una voz dada."""
    test_sentence = ""
    if "Español" in voice_friendly_name or "_es_" in voice_technical_name or voice_technical_name.startswith("es_") or voice_technical_name.startswith("ef_") or voice_technical_name.startswith("em_"):
        name_part = voice_friendly_name.split("(")[-1].split("/")[0].replace(")", "").strip() # Intenta obtener el nombre real
        if not name_part or len(name_part) > 15: # Fallback si el parseo del nombre amigable falla
            name_part = voice_friendly_name.split(" ")[1] if " " in voice_friendly_name else voice_technical_name

        gender_desc = "femenina" if " F (" in voice_friendly_name or voice_technical_name.startswith("ef_") else \
                      "masculina" if " M (" in voice_friendly_name or voice_technical_name.startswith("em_") else ""
        test_sentence = f"Hola, soy {name_part}, una voz {gender_desc} en Español. Mucho gusto."
    
    elif "Inglés" in voice_friendly_name or "_en_" in voice_technical_name or voice_technical_name.startswith("en_") or voice_technical_name.startswith("af_") or voice_technical_name.startswith("am_") or voice_technical_name.startswith("bf_") or voice_technical_name.startswith("bm_"):
        try:
            name_part = voice_friendly_name.split('(')[1].split('/')[0].strip()
            desc_part = voice_friendly_name.split('F (')[0].replace("Inglés ","").strip() + " Female" if " F (" in voice_friendly_name else \
                        voice_friendly_name.split('M (')[0].replace("Inglés ","").strip() + " Male"
            test_sentence = f"Hello, I am {name_part}, a {desc_part} voice. Nice to meet you."
        except IndexError:
            test_sentence = f"Hello, this is a test of the {voice_friendly_name} voice."
    else: # Fallback genérico si no se puede determinar el idioma por el nombre amigable
        test_sentence = f"This is a test of the {voice_friendly_name} voice, technical name {voice_technical_name}."
    return test_sentence

def generate_all_samples():
    print(f"Asegurando que el directorio de muestras '{OUTPUT_SAMPLE_DIR}' exista...")
    if not os.path.exists(OUTPUT_SAMPLE_DIR):
        os.makedirs(OUTPUT_SAMPLE_DIR)
        print(f"Directorio '{OUTPUT_SAMPLE_DIR}' creado.")
    else:
        # Opcional: borrar contenido anterior para regenerar todo
        # print(f"Borrando contenido anterior de '{OUTPUT_SAMPLE_DIR}'...")
        # for filename in os.listdir(OUTPUT_SAMPLE_DIR):
        #     file_path = os.path.join(OUTPUT_SAMPLE_DIR, filename)
        #     try:
        #         if os.path.isfile(file_path) or os.path.islink(file_path):
        #             os.unlink(file_path)
        #         elif os.path.isdir(file_path):
        #             shutil.rmtree(file_path)
        #     except Exception as e:
        #         print(f'Fallo al borrar {file_path}. Razón: {e}')
        pass


    available_voices = tts_kokoro_module.list_available_kokoro_voices()
    print(f"Se generarán muestras para {len(available_voices)} voces.")

    if not tts_kokoro_module.PIPELINE_INSTANCE:
         print("Inicializando pipeline de Kokoro globalmente desde el script de generación de muestras...")
         # Esta llamada es la que tienes en tu tts_kokoro_module.py para inicializar PIPELINE_INSTANCE
         # Si tu módulo no lo hace al importarse, necesitas una función para llamarla.
         # Asumiendo que tu tts_kokoro_module.py tiene initialize_global_pipeline() o similar:
         if hasattr(tts_kokoro_module, 'initialize_global_pipeline') and callable(getattr(tts_kokoro_module, 'initialize_global_pipeline')):
             tts_kokoro_module.initialize_global_pipeline()
         else: # Si no, intenta inicializar un pipeline aquí para este script (no recomendado si el módulo ya lo hace global)
             print("ADVERTENCIA: No se encontró una función de inicialización global en tts_kokoro_module.")
             print("Asegúrate de que PIPELINE_INSTANCE en tts_kokoro_module esté inicializado antes de ejecutar este script masivamente.")


    for friendly_name, tech_name in available_voices.items():
        output_filename = os.path.join(OUTPUT_SAMPLE_DIR, f"{tech_name}.wav")
        
        # Omitir si el archivo ya existe (para no regenerar innecesariamente)
        if os.path.exists(output_filename):
            print(f"Muestra para '{friendly_name}' ({tech_name}.wav) ya existe. Omitiendo.")
            continue

        sentence = create_sample_sentence(friendly_name, tech_name)
        print(f"\nGenerando muestra para: {friendly_name} ({tech_name}.wav)")
        print(f"  Texto: \"{sentence}\"")

        success = tts_kokoro_module.generate_speech_with_voice_name(
            sentence,
            tech_name,
            output_filename
        )
        if success:
            print(f"  Muestra generada: {output_filename}")
        else:
            print(f"  FALLO al generar muestra para {friendly_name}")

    print("\nGeneración de todas las muestras de voz completada.")

if __name__ == "__main__":
    # Este script podría tardar bastante en ejecutarse la primera vez
    # si descarga muchos archivos .pt para las voces.
    
    # Asegúrate que la inicialización de Kokoro (incluyendo la descarga del modelo base)
    # ya haya ocurrido o esté manejada dentro de tts_kokoro_module.
    # Es posible que necesites ejecutar tu main.py una vez para que Kokoro se configure
    # completamente si la inicialización es perezosa.
    
    # Antes de ejecutar, verifica que tts_kokoro_module.PIPELINE_INSTANCE
    # se inicialice correctamente cuando se importa o se llama.
    # Si tu PIPELINE_INSTANCE en tts_kokoro_module.py se inicializa con un speaker_id
    # por defecto, eso está bien, ya que generate_speech_with_voice_name
    # usa el `voice_technical_name` que anula el speaker_id por defecto del pipeline
    # (asumiendo que la lógica interna de `kokoro` que descarga los .pt funciona así).

    # Si tts_kokoro_module.PIPELINE_INSTANCE no está listo, la primera llamada a
    # tts_kokoro_module.generate_speech_with_voice_name lo inicializará.
    
    print("Este script generará archivos de muestra para todas las voces listadas.")
    print(f"Los archivos se guardarán en la carpeta: '{os.path.abspath(OUTPUT_SAMPLE_DIR)}'")
    input("Presiona Enter para comenzar la generación de muestras (esto puede tardar)...")
    generate_all_samples()