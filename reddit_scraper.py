# reddit_scraper.py
import requests
from bs4 import BeautifulSoup
import traceback # For detailed error logging if needed

def get_post_details(url: str) -> tuple[str, str]:
    """
    Extracts the title and body of a Reddit post using its URL.
    Targets specific HTML elements for content.

    Args:
        url: The full URL of the Reddit post.

    Returns:
        A tuple containing (title, text_body).
        Returns indicative error messages if content is not found or an error occurs.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    title_not_found_msg = "Title not found."
    body_not_found_msg = "Post body not found." # Initial message

    try:
        response = requests.get(url, headers=headers, timeout=15) # Increased timeout
        response.raise_for_status() # Will raise HTTPError for bad responses (4XX or 5XX)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Reddit's structure often uses <shreddit-post> as the main container
        post_element = soup.find('shreddit-post')

        if post_element:
            # Extract Title
            # First attempt: specific slot for title
            title_tag = post_element.find('h1', {'slot': 'title'})
            if title_tag:
                title = title_tag.get_text(strip=True)
            else:
                # Fallback: find the first h1 inside the post element (less specific)
                h1_tags_in_post = post_element.find_all('h1', limit=1)
                if h1_tags_in_post:
                    title = h1_tags_in_post[0].get_text(strip=True)
                else:
                    title = title_not_found_msg # "Title not found within post structure."

            # Extract Post Body (using slot="text-body")
            body_content_container = post_element.find('div', {'slot': 'text-body'})
            
            if body_content_container:
                paragraphs = body_content_container.find_all('p')
                body_texts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
                if body_texts:
                    body = '\n\n'.join(body_texts)
                else:
                    body = "Post body container (slot='text-body') found, but no readable paragraph text."
            else:
                body = "Post body container (slot='text-body') not found. The post might not be text-based (e.g., image, video)."
        
        else: # <shreddit-post> not found
            title = "Main post structure ('shreddit-post') not found."
            body = "Could not parse content. Verify URL or page structure."

        # Final adjustments to messages
        if title != title_not_found_msg and body == body_not_found_msg: # Title found, but default body message
             body = "Post has a title, but the text body is empty or could not be extracted (might be an image, video, or link)."
        elif title == title_not_found_msg and body == body_not_found_msg: # If both failed generically
             return "Could not find either title or body of the post. Verify URL or Reddit page structure.", ""


        return title, body

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"Error: Post not found at URL (404 Error). Please check the link.", ""
        # For other HTTP errors, provide more details
        return f"HTTP Error accessing URL: {e.response.status_code} {e.response.reason}", ""
    except requests.exceptions.RequestException as e: # Covers network issues, timeout, etc.
        return f"Network error while trying to access URL: {e}", ""
    except Exception as e:
        # print(f"An unexpected error occurred while parsing HTML: {e} ({type(e).__name__})") # Useful for dev debug
        traceback.print_exc() # For more detailed logs during development
        return f"An unexpected error occurred while processing the page. Details: {type(e).__name__}", ""

# Example usage for testing (optional)
if __name__ == "__main__":
    # Test with a known text-based Reddit post URL
    # Replace with a current, valid Reddit post URL for testing
    # test_url_text_post = "https://www.reddit.com/r/tifu/comments/100ja00/tifu_by_accidentally_convincing_my_whole_family/" # Example, might be old
    test_url_text_post = "https://www.reddit.com/r/Python/comments/1cfhrd2/what_are_your_favorite_lesser_known_standard/" # More recent example
    
    print(f"Fetching details for: {test_url_text_post}")
    post_title, post_body = get_post_details(test_url_text_post)
    
    print("\n--- Post Details ---")
    print(f"Title: {post_title}")
    print(f"\nBody:\n{post_body}")
    print("--------------------")

    # Test with a URL that might be an image or video post (expect less body text)
    # test_url_media_post = "https://www.reddit.com/r/pics/comments/100l2q5/a_beautiful_sunset_i_captured_last_night/" # Example
    # print(f"\nFetching details for media post: {test_url_media_post}")
    # media_title, media_body = get_post_details(test_url_media_post)
    # print("\n--- Media Post Details ---")
    # print(f"Title: {media_title}")
    # print(f"\nBody:\n{media_body}") # Expect this to be minimal or an error message
    # print("--------------------")

    # Test with a non-existent URL
    test_url_non_existent = "https://www.reddit.com/r/thisdoesnotexist/abcdef12345"
    print(f"\nFetching details for non-existent post: {test_url_non_existent}")
    non_existent_title, non_existent_body = get_post_details(test_url_non_existent)
    print("\n--- Non-Existent Post Details ---")
    print(f"Title: {non_existent_title}") # Expect error message here
    print(f"\nBody:\n{non_existent_body}")
    print("--------------------")