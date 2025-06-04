# file_manager.py
import os
import re # For regular expressions when finding IDs

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# Subdirectory definitions
AUDIO_DIR_NAME = "audio"
NARRATED_VIDEO_DIR_NAME = "videowvoice" # Videos with narration but without burned-in subtitles
SRT_DIR_NAME = "srt"
FINAL_VIDEO_DIR_NAME = "finalvideo" # Final videos with burned-in subtitles

# Full paths
AUDIO_DIR = os.path.join(BASE_OUTPUT_DIR, AUDIO_DIR_NAME)
NARRATED_VIDEO_DIR = os.path.join(BASE_OUTPUT_DIR, NARRATED_VIDEO_DIR_NAME) # This seems unused, videowvoice is used in main.py for temp path
SRT_DIR = os.path.join(BASE_OUTPUT_DIR, SRT_DIR_NAME)
FINAL_VIDEO_DIR = os.path.join(BASE_OUTPUT_DIR, FINAL_VIDEO_DIR_NAME)

ALL_DIRS = [BASE_OUTPUT_DIR, AUDIO_DIR, NARRATED_VIDEO_DIR, SRT_DIR, FINAL_VIDEO_DIR]

def ensure_directories_exist():
    """Ensures all necessary output directories exist. Creates them if not."""
    # print("File Manager: Verifying output directories...") # Optional debug
    for dir_path in ALL_DIRS:
        try:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                # print(f"File Manager: Directory created: {dir_path}") # Optional debug
        except OSError as e:
            print(f"File Manager: Error creating directory {dir_path}: {e}")
            # Consider more robust error handling if directory creation is critical

def get_next_id_str() -> str:
    """
    Generates the next numerical ID as a 4-digit string (e.g., "0001", "0002").
    Scans the FINAL_VIDEO_DIR to determine the last used ID.
    """
    ensure_directories_exist() 
    
    last_id = 0
    try:
        if os.path.exists(FINAL_VIDEO_DIR):
            # Search for files matching the pattern NNNN.<ext> (e.g., 0001.mp4)
            id_pattern = re.compile(r"^(\d{4,})\..*$") # 4 or more digits at the start of the filename
            
            for filename in os.listdir(FINAL_VIDEO_DIR):
                match = id_pattern.match(filename)
                if match:
                    try:
                        file_id = int(match.group(1))
                        if file_id > last_id:
                            last_id = file_id
                    except ValueError:
                        continue # Ignore if the name isn't a valid number after matching
    except Exception as e:
        print(f"File Manager: Error scanning existing IDs: {e}")
        # Fallback to 1 if scanning fails, though this could overwrite.
        # A better strategy might be a unique suffix if scanning fails.

    next_id = last_id + 1
    return f"{next_id:04d}" # Format to 4 digits with leading zeros

if __name__ == '__main__':
    print("Testing File Manager...")
    ensure_directories_exist()
    
    # Store initial next_id before creating any dummy files for this test run
    initial_next_id_for_test = get_next_id_str() 
    print(f"Initial next ID for this test run: {initial_next_id_for_test}")

    # Test ID generation multiple times
    for i in range(3):
        next_id = get_next_id_str()
        print(f"Next ID generated: {next_id}")
        # Simulate creating a file to test if the next ID increments correctly
        if i < 2: # Create a few dummy files
            try:
                dummy_file_path = os.path.join(FINAL_VIDEO_DIR, f"{next_id}.mp4")
                with open(dummy_file_path, 'w') as f:
                    f.write("dummy content for test")
                print(f"Dummy file created for testing: {dummy_file_path}")
            except Exception as e:
                print(f"Could not create dummy file for testing: {e}")

    print("\nDirectory Paths:")
    print(f"Base Output: {BASE_OUTPUT_DIR}")
    print(f"Audio: {AUDIO_DIR}")
    print(f"Narrated Video (temp concept): {NARRATED_VIDEO_DIR}") # Clarified as it's not directly used for final output storage
    print(f"SRT: {SRT_DIR}")
    print(f"Final Video: {FINAL_VIDEO_DIR}")