# file_manager.py
import os
import re # Para expresiones regulares al buscar IDs

BASE_OUTPUT_DIR = r"C:\AI Reddit Videos" # Ruta base para todas las salidas

# Definición de subdirectorios
AUDIO_DIR_NAME = "audio"
NARRATED_VIDEO_DIR_NAME = "videowvoice" # Videos con narración pero sin subtítulos quemados
SRT_DIR_NAME = "srt"
FINAL_VIDEO_DIR_NAME = "finalvideo" # Videos finales con subtítulos quemados

# Construir rutas completas
AUDIO_DIR = os.path.join(BASE_OUTPUT_DIR, AUDIO_DIR_NAME)
NARRATED_VIDEO_DIR = os.path.join(BASE_OUTPUT_DIR, NARRATED_VIDEO_DIR_NAME)
SRT_DIR = os.path.join(BASE_OUTPUT_DIR, SRT_DIR_NAME)
FINAL_VIDEO_DIR = os.path.join(BASE_OUTPUT_DIR, FINAL_VIDEO_DIR_NAME)

ALL_DIRS = [BASE_OUTPUT_DIR, AUDIO_DIR, NARRATED_VIDEO_DIR, SRT_DIR, FINAL_VIDEO_DIR]

def ensure_directories_exist():
    """Asegura que todos los directorios de salida necesarios existan. Si no, los crea."""
    print("File Manager: Verificando directorios de salida...")
    for dir_path in ALL_DIRS:
        try:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                print(f"File Manager: Directorio creado: {dir_path}")
        except OSError as e:
            print(f"File Manager: Error creando directorio {dir_path}: {e}")
            # Podrías querer manejar este error de forma más robusta, 
            # por ejemplo, deteniendo la aplicación si no se pueden crear.
            # Por ahora, solo imprimimos el error.

def get_next_id_str() -> str:
    """
    Genera el siguiente ID numérico como un string de 3 dígitos (ej. "001", "002").
    Escanea el directorio FINAL_VIDEO_DIR para determinar el último ID usado.
    """
    ensure_directories_exist() # Asegura que el directorio existe antes de escanear
    
    last_id = 0
    try:
        if os.path.exists(FINAL_VIDEO_DIR):
            # Buscar archivos que sigan el patrón NNN.<ext> (ej. 001.mp4)
            # Usamos una expresión regular para extraer solo los números del nombre base.
            id_pattern = re.compile(r"^(\d{3,})\..*$") # 3 o más dígitos al inicio del nombre de archivo
            
            for filename in os.listdir(FINAL_VIDEO_DIR):
                match = id_pattern.match(filename)
                if match:
                    try:
                        file_id = int(match.group(1))
                        if file_id > last_id:
                            last_id = file_id
                    except ValueError:
                        continue # Ignorar si el nombre no es un número válido después de la coincidencia
    except Exception as e:
        print(f"File Manager: Error escaneando IDs existentes: {e}")
        # Si hay un error, empezamos desde 1 como fallback seguro, aunque podría sobrescribir.
        # Una mejor estrategia podría ser añadir un sufijo único si el escaneo falla.

    next_id = last_id + 1
    return f"{next_id:03d}" # Formatear a 3 dígitos con ceros a la izquierda

if __name__ == '__main__':
    print("Probando File Manager...")
    ensure_directories_exist()
    for i in range(5):
        next_id = get_next_id_str()
        print(f"Siguiente ID generado: {next_id}")
        # Para simular la creación de un archivo para la siguiente prueba de ID:
        if i == 0: # Crear un dummy la primera vez
            try:
                dummy_file_path = os.path.join(FINAL_VIDEO_DIR, f"{next_id}.mp4")
                with open(dummy_file_path, 'w') as f:
                    f.write("dummy content") # Crear archivo para probar la siguiente llamada a get_next_id_str
                print(f"Archivo dummy creado para prueba: {dummy_file_path}")
            except Exception as e:
                print(f"No se pudo crear archivo dummy para prueba: {e}")

    print("\nRutas de Directorio:")
    print(f"Audio: {AUDIO_DIR}")
    print(f"Video con Voz: {NARRATED_VIDEO_DIR}")
    print(f"SRT: {SRT_DIR}")
    print(f"Video Final: {FINAL_VIDEO_DIR}")