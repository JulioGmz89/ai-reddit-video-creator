# reddit_scraper.py

import requests
from bs4 import BeautifulSoup

def get_post_details(url: str) -> tuple[str, str]:
    """
    Extrae el título y el cuerpo de una publicación de Reddit usando su URL.
    Ajustado para usar slot="text-body" para el contenedor del cuerpo.

    Args:
        url: La URL completa de la publicación de Reddit.

    Returns:
        Una tupla conteniendo (título, cuerpo_del_texto).
        Si ocurre un error o no se encuentra el contenido, se devuelven mensajes indicativos.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    title = "Título no encontrado."
    body = "Cuerpo del post no encontrado." # Mensaje inicial

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        post_element = soup.find('shreddit-post')

        if post_element:
            # --- Extracción del Título ---
            title_tag = post_element.find('h1', {'slot': 'title'})
            if title_tag:
                title = title_tag.get_text(strip=True)
            else:
                h1_tags_in_post = post_element.find_all('h1', limit=1)
                if h1_tags_in_post:
                    title = h1_tags_in_post[0].get_text(strip=True)
                else:
                    title = "Título no encontrado dentro de la estructura del post."

            # --- Extracción del Cuerpo del Post (Usando slot="text-body") ---
            # Este es el cambio principal: buscamos el div con slot="text-body"
            body_content_container = post_element.find('div', {'slot': 'text-body'})
            
            if body_content_container:
                paragraphs = body_content_container.find_all('p')
                body_texts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
                if body_texts:
                    body = '\n\n'.join(body_texts)
                else:
                    body = "Cuerpo del post encontrado (usando slot='text-body'), pero no contiene párrafos de texto legibles."
            else:
                # Si slot="text-body" falla, es un indicador más fuerte de un problema estructural o un post no textual.
                body = "Contenedor del cuerpo del post (buscado por slot='text-body') no encontrado dentro de shreddit-post. El post podría no ser de texto."
        
        else:
            title = "Estructura principal del post ('shreddit-post') no encontrada."
            body = "No se pudo analizar el contenido. Verifica la URL o la estructura de la página."

        # Ajuste final de mensajes si el cuerpo sigue con el mensaje por defecto pero el título sí se encontró.
        if title != "Título no encontrado." and body == "Cuerpo del post no encontrado.":
             body = "El post parece tener un título, pero el cuerpo del texto está vacío o no se pudo extraer (podría ser una imagen, video o enlace)."
        elif title == "Título no encontrado." and body == "Cuerpo del post no encontrado.": # Si ambos fallaron de forma genérica
             return "No se pudo encontrar ni el título ni el cuerpo del post. Verifica la URL o la estructura de la página de Reddit.", ""


        return title, body

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"Error: No se encontró el post en la URL (Error 404). Verifica el enlace.", ""
        return f"Error HTTP al acceder a la URL: {e}", ""
    except requests.exceptions.RequestException as e:
        return f"Error de red al intentar acceder a la URL: {e}", ""
    except Exception as e:
        print(f"Ocurrió un error inesperado al parsear el HTML: {e} ({type(e).__name__})")
        return f"Ocurrió un error inesperado al procesar la página. Detalles: {type(e).__name__}", ""