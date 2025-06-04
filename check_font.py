# Script para listar fuentes de MoviePy
from moviepy.editor import TextClip

try:
    print("Listando fuentes disponibles para MoviePy (puede tardar un momento)...")
    available_fonts = TextClip.list('font')
    if available_fonts:
        print("\n--- Fuentes Disponibles ---")
        for font_name in sorted(available_fonts): # Ordenar alfabéticamente
            print(font_name)
        print(f"\nTotal de fuentes encontradas: {len(available_fonts)}")
    else:
        print("No se encontraron fuentes disponibles o hubo un error al listarlas.")
    
    # También puedes probar una fuente específica si conoces su nombre exacto
    # print("\nProbando 'Arial-Bold':")
    # try:
    #     TextClip("test", font="Arial-Bold", fontsize=20, color='white').close()
    #     print("  'Arial-Bold' parece ser reconocida.")
    # except Exception as e:
    #     print(f"  Error con 'Arial-Bold': {e}")

except Exception as e:
    print(f"Ocurrió un error al intentar listar las fuentes: {e}")
    import traceback
    traceback.print_exc()

