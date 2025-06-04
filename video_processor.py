# video_processor.py
import os
import traceback
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
from moviepy.video.fx.all import loop as vfx_loop
import pysrt # For parsing SRT files
from PIL import Image
import numpy as np 

SUBTITLE_PREVIEW_IMAGE_TEMP_FILE = "_subtitle_preview_image_temp.png" # Unused, remove if not needed by other logic
PREVIEW_SUBTITLE_HEIGHT = 80 

VIDEO_TEMPLATES_DIR = "video_templates" 
THUMBNAIL_CACHE_DIR = os.path.join(VIDEO_TEMPLATES_DIR, ".thumbnails_cache") 

COMBINED_PREVIEW_IMAGE_TEMP_FILE = "_combined_preview_temp.png" 
SUBTITLE_ONLY_PREVIEW_IMAGE_TEMP_FILE = "_subtitle_only_preview_temp.png" 

if not os.path.exists(VIDEO_TEMPLATES_DIR):
    os.makedirs(VIDEO_TEMPLATES_DIR)
    # print(f"VideoProc - Templates directory created: {VIDEO_TEMPLATES_DIR}") # Optional debug
if not os.path.exists(THUMBNAIL_CACHE_DIR):
    os.makedirs(THUMBNAIL_CACHE_DIR)
    # print(f"VideoProc - Thumbnail cache directory created: {THUMBNAIL_CACHE_DIR}") # Optional debug


def list_video_templates() -> list[str]:
    """Returns a list of full paths to video files in VIDEO_TEMPLATES_DIR."""
    video_files = []
    if not os.path.exists(VIDEO_TEMPLATES_DIR):
        print(f"VideoProc - Templates directory '{VIDEO_TEMPLATES_DIR}' not found.")
        return video_files

    valid_extensions = ('.mp4', '.mov', '.avi', '.mkv') 
    for filename in sorted(os.listdir(VIDEO_TEMPLATES_DIR)):
        if filename.lower().endswith(valid_extensions):
            video_files.append(os.path.join(VIDEO_TEMPLATES_DIR, filename))
    return video_files

def get_or_create_thumbnail(video_path: str, time_sec: float = 1.0, size: tuple = (128, 227)) -> str | None:
    """Gets a thumbnail from cache or creates and caches it."""
    if not os.path.exists(video_path):
        print(f"VideoProc - Error: Video file not found at {video_path} for thumbnail generation.")
        return None

    video_filename = os.path.basename(video_path)
    thumbnail_filename = f"{os.path.splitext(video_filename)[0]}_thumb_{size[0]}x{size[1]}.png"
    thumbnail_cache_path = os.path.join(THUMBNAIL_CACHE_DIR, thumbnail_filename)

    if os.path.exists(thumbnail_cache_path):
        return thumbnail_cache_path
    
    try:
        # print(f"VideoProc - Generating thumbnail ({size[0]}x{size[1]}) for: {video_filename}...") # Optional debug
        with VideoFileClip(video_path) as clip:
            # Ensure time_sec is within video duration
            actual_time_sec = min(time_sec, clip.duration - 0.1) if clip.duration > 0.1 else 0 
            frame = clip.get_frame(actual_time_sec) 
        pil_image = Image.fromarray(frame)
        pil_image_resized = pil_image.resize(size, Image.Resampling.LANCZOS)
        pil_image_resized.save(thumbnail_cache_path, "PNG")
        # print(f"VideoProc - Thumbnail saved to: {thumbnail_cache_path}") # Optional debug
        return thumbnail_cache_path
    except Exception as e:
        print(f"VideoProc - Error generating thumbnail for {video_path}: {e}")
        traceback.print_exc()
        return None

def create_narrated_video(video_path: str, audio_path: str, output_path: str) -> bool:
    """
    Combines a video file with an audio file.
    Original video audio is replaced. Video duration is adjusted to audio duration.
    """
    try:
        # print(f"VideoProc - Starting combination: Video='{video_path}', Audio='{audio_path}'") # Optional debug

        video_clip = VideoFileClip(video_path)
        audio_clip = AudioFileClip(audio_path)

        video_clip = video_clip.set_audio(audio_clip) # More direct way to set audio

        # Adjust video duration to match audio
        if audio_clip.duration > video_clip.duration:
            # print(f"VideoProc - Audio ({audio_clip.duration:.2f}s) > Video ({video_clip.duration:.2f}s). Looping video.") # Optional debug
            final_video_clip = vfx_loop(video_clip, duration=audio_clip.duration)
            # final_video_clip = final_video_clip.set_duration(audio_clip.duration) # Loop already sets duration
        elif audio_clip.duration < video_clip.duration:
            # print(f"VideoProc - Audio ({audio_clip.duration:.2f}s) < Video ({video_clip.duration:.2f}s). Cutting video.") # Optional debug
            final_video_clip = video_clip.subclip(0, audio_clip.duration)
        else:
            final_video_clip = video_clip

        # print(f"VideoProc - Writing narrated video to: {output_path}") # Optional debug
        final_video_clip.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac",
            temp_audiofile=f'temp-audio-{os.path.basename(output_path)}.m4a', # Unique temp audio file
            remove_temp=True,
            threads=os.cpu_count() or 4, # Use available cores or default to 4
            fps=video_clip.fps if video_clip.fps else 24 # Use original FPS or default
        )

        # Close clips
        video_clip.close()
        audio_clip.close()
        if final_video_clip != video_clip: # If a new clip object was created (loop/subclip)
            final_video_clip.close()
        
        # print("VideoProc - Audio and video combination complete.") # Optional debug
        return True

    except Exception as e:
        print(f"VideoProc - Error during audio/video combination: {e}")
        traceback.print_exc()
        # Ensure clips are closed on error if they were opened
        if 'video_clip' in locals() and hasattr(video_clip, 'close'): video_clip.close()
        if 'audio_clip' in locals() and hasattr(audio_clip, 'close'): audio_clip.close()
        if 'final_video_clip' in locals() and final_video_clip != video_clip and hasattr(final_video_clip, 'close'): final_video_clip.close()
        return False

def srt_time_to_seconds(srt_time_obj) -> float:
    """Converts a pysrt time object to total seconds."""
    return srt_time_obj.hours * 3600 + srt_time_obj.minutes * 60 + srt_time_obj.seconds + srt_time_obj.milliseconds / 1000.0

def burn_subtitles_on_video(
    video_path: str, 
    srt_path: str, 
    output_path: str,
    style_options: dict = None 
) -> bool:
    """Burns subtitles from an SRT file onto a video."""
    if not os.path.exists(video_path):
        print(f"Error SubBurn: Input video not found at '{video_path}'")
        return False
    if not os.path.exists(srt_path):
        print(f"Error SubBurn: SRT file not found at '{srt_path}'")
        return False

    default_style = {
        'font': 'Arial', 'fontsize': 24, 'color': 'white',
        'stroke_color': 'black', 'stroke_width': 1, 
        'bg_color': 'rgba(0,0,0,0.5)', 
        'position_choice': 'Bottom', 
        'method': 'caption', 'align': 'center'
    }
    
    current_style = default_style.copy()
    if style_options:
        current_style.update(style_options)

    position_choice = current_style.pop('position_choice', 'Bottom')

    # Map position choice to MoviePy position tuples
    pos_map = {
        "Top": ('center', 0.10),
        "Center": ('center', 'center'),
        "Bottom": ('center', 0.85) # Default if choice is invalid
    }
    actual_pos_tuple = pos_map.get(position_choice, ('center', 0.85))


    try:
        # print(f"SubBurn - Starting. Video: '{video_path}', SRT: '{srt_path}'") # Optional debug
        # print(f"SubBurn - Style options: {current_style}, Final position: {actual_pos_tuple}") # Optional debug

        main_video_clip = VideoFileClip(video_path)
        video_width, video_height = main_video_clip.size

        subs = pysrt.open(srt_path, encoding='utf-8')
        
        subtitle_clips = []
        for sub_item in subs:
            start_s = srt_time_to_seconds(sub_item.start)
            end_s = srt_time_to_seconds(sub_item.end)
            duration_s = end_s - start_s
            
            if duration_s <= 0: continue

            text_clip_w = int(video_width * 0.90) # Width for the text clip box
            
            textclip_creation_args = {
                'txt': sub_item.text,
                'font': current_style['font'],
                'fontsize': int(current_style['fontsize']),
                'color': current_style['color'],
                'bg_color': current_style['bg_color'],
                'stroke_color': current_style['stroke_color'],
                'stroke_width': float(current_style['stroke_width']),
                'method': current_style['method'], # 'caption' for auto-wrap
                'align': current_style['align']   # Alignment within the text box
            }
            if current_style['method'] == 'caption':
                textclip_creation_args['size'] = (text_clip_w, None) # Fixed width, auto height

            txt_clip = TextClip(**textclip_creation_args)
            txt_clip = txt_clip.set_position(actual_pos_tuple, relative=True).set_duration(duration_s).set_start(start_s)
            subtitle_clips.append(txt_clip)

        if not subtitle_clips:
            print("SubBurn - No subtitle clips were generated. Check SRT content or timing.")
            main_video_clip.close()
            return False 

        # print(f"SubBurn - Compositing video with {len(subtitle_clips)} subtitles.") # Optional debug
        final_video = CompositeVideoClip([main_video_clip] + subtitle_clips, size=main_video_clip.size).set_audio(main_video_clip.audio)
        
        # print(f"SubBurn - Writing video with burned subtitles to: {output_path}") # Optional debug
        final_video.write_videofile(
            output_path, codec="libx264", audio_codec="aac",
            temp_audiofile=f'temp-subburn-audio-{os.path.basename(output_path)}.m4a', # Unique temp audio
            remove_temp=True,
            threads=os.cpu_count() or 4, fps=main_video_clip.fps if main_video_clip.fps else 24
        )
        
        main_video_clip.close()
        for tc in subtitle_clips: tc.close() # TextClips should be closed
        final_video.close()

        # print("SubBurn - Subtitle burning process completed.") # Optional debug
        return True

    except Exception as e:
        print(f"Error SubBurn - An error occurred while burning subtitles: {e}")
        traceback.print_exc()
        if 'main_video_clip' in locals() and hasattr(main_video_clip, 'close'): main_video_clip.close()
        if 'subtitle_clips' in locals(): 
            for tc in subtitle_clips: 
                if hasattr(tc, 'close'): tc.close()
        if 'final_video' in locals() and hasattr(final_video, 'close'): final_video.close()
        return False
    
# This function seems specific to an older preview logic not directly used by update_subtitle_preview_display in main.py.
# It might be dead code if create_composite_preview_image is the primary method for previews.
# Keeping for now, but mark as potentially unused.
# def generate_subtitle_preview_image_file( # POTENTIALLY UNUSED
#     text: str, 
#     style_options: dict, 
#     preview_width: int = 300 
# ) -> str | None:
#     try:
#         position_choice = style_options.get('position_choice', 'Bottom') 
#         text_align_map = {"Top": "North", "Center": "Center", "Bottom": "South"}
#         text_align = text_align_map.get(position_choice, 'South')
        
#         fontsize = int(style_options.get('fontsize', 24))
#         stroke_width = float(style_options.get('stroke_width', 1))

#         textclip_kwargs = {
#             'txt': text,
#             'font': style_options.get('font', 'Arial'),
#             'fontsize': fontsize,
#             'color': style_options.get('color', 'white'),
#             'bg_color': 'transparent', 
#             'stroke_color': style_options.get('stroke_color'),
#             'stroke_width': stroke_width,
#             'method': 'caption', 
#             'align': text_align, 
#             'size': (preview_width, PREVIEW_SUBTITLE_HEIGHT) 
#         }
        
#         if stroke_width == 0:
#             textclip_kwargs.pop('stroke_color', None)
#             textclip_kwargs.pop('stroke_width', None)

#         # print(f"SubPreview Gen - Creating TextClip with: {textclip_kwargs}") # Optional debug
#         # Use a unique temp file name to avoid conflicts if called multiple times
#         temp_preview_file = f"_subtitle_preview_temp_{os.urandom(4).hex()}.png"
#         with TextClip(**textclip_kwargs) as clip:
#             clip.save_frame(temp_preview_file, t=0) 
        
#         return temp_preview_file # Return the unique name
#     except Exception as e:
#         print(f"SubPreview Gen - Error generating TextClip image for preview: {e}")
#         traceback.print_exc()
#         if 'temp_preview_file' in locals() and os.path.exists(temp_preview_file):
#             try: os.remove(temp_preview_file)
#             except Exception as e_del: print(f"SubPreview Gen - Error deleting preview: {e_del}")
#         return None
    
def create_composite_preview_image(
    base_video_thumbnail_path: str,
    subtitle_text: str,
    style_options: dict
) -> str | None:
    """Creates a composite image of a video thumbnail with subtitle text overlaid."""
    if not os.path.exists(base_video_thumbnail_path):
        print(f"PreviewComp - Base video thumbnail not found: {base_video_thumbnail_path}")
        return None

    try:
        base_img_pil = Image.open(base_video_thumbnail_path).convert("RGBA")
        base_width, base_height = base_img_pil.size

        text_clip_width = int(base_width * 0.90) 
        text_clip_height_allowance = None # Auto height for TextClip

        position_choice = style_options.get('position_choice', 'Bottom')
        text_align_map = {"Top": "North", "Center": "Center", "Bottom": "South"}
        text_align = text_align_map.get(position_choice, 'South')
        
        fontsize = int(style_options.get('fontsize', 36))
        stroke_width = float(style_options.get('stroke_width', 1.5))

        textclip_kwargs = {
            'txt': subtitle_text,
            'font': style_options.get('font', 'Arial'),
            'fontsize': fontsize,
            'color': style_options.get('color', 'yellow'),
            'bg_color': 'transparent', # Crucial for overlay
            'stroke_color': style_options.get('stroke_color', 'black'),
            'stroke_width': stroke_width,
            'method': 'caption', 
            'align': text_align, 
            'size': (text_clip_width, text_clip_height_allowance) 
        }
        if stroke_width == 0:
            textclip_kwargs.pop('stroke_color', None)
            textclip_kwargs.pop('stroke_width', None)
        
        # print(f"PreviewComp - Creating TextClip for subtitle: '{subtitle_text[:20]}...' with {textclip_kwargs}") # Optional debug
        # Save TextClip to a temporary PNG to get correct RGBA for compositing
        with TextClip(**textclip_kwargs) as txt_clip:
            txt_clip.save_frame(SUBTITLE_ONLY_PREVIEW_IMAGE_TEMP_FILE, t=0) 

        if not os.path.exists(SUBTITLE_ONLY_PREVIEW_IMAGE_TEMP_FILE):
            print("PreviewComp - Failed to generate temporary subtitle image from TextClip.")
            return None
            
        subtitle_img_pil = Image.open(SUBTITLE_ONLY_PREVIEW_IMAGE_TEMP_FILE).convert("RGBA")
        sub_width, sub_height = subtitle_img_pil.size

        # Calculate position for overlaying subtitle
        pos_x = (base_width - sub_width) // 2 
        pos_y = 0
        if position_choice == "Top":   pos_y = int(base_height * 0.10)
        elif position_choice == "Center": pos_y = (base_height // 2) - (sub_height // 2)
        elif position_choice == "Bottom":  pos_y = int(base_height * 0.90) - sub_height
        
        pos_y = max(0, min(pos_y, base_height - sub_height)) 
        pos_x = max(0, min(pos_x, base_width - sub_width))   

        # print(f"PreviewComp - Compositing. Base: {base_width}x{base_height}, Sub: {sub_width}x{sub_height}, Pos: ({pos_x},{pos_y})") # Optional debug
        composite_img = base_img_pil.copy() 
        composite_img.paste(subtitle_img_pil, (pos_x, pos_y), subtitle_img_pil) # Use subtitle's alpha as mask

        composite_img.save(COMBINED_PREVIEW_IMAGE_TEMP_FILE, "PNG")
        # print(f"PreviewComp - Composite image saved: {COMBINED_PREVIEW_IMAGE_TEMP_FILE}") # Optional debug
        
        if os.path.exists(SUBTITLE_ONLY_PREVIEW_IMAGE_TEMP_FILE):
            try: os.remove(SUBTITLE_ONLY_PREVIEW_IMAGE_TEMP_FILE)
            except Exception as e_del: print(f"PreviewComp - Could not delete {SUBTITLE_ONLY_PREVIEW_IMAGE_TEMP_FILE}: {e_del}")
            
        return COMBINED_PREVIEW_IMAGE_TEMP_FILE

    except Exception as e:
        print(f"PreviewComp - Error creating composite image: {e}"); traceback.print_exc()
        # Clean up temp files on error
        if os.path.exists(SUBTITLE_ONLY_PREVIEW_IMAGE_TEMP_FILE):
            try: os.remove(SUBTITLE_ONLY_PREVIEW_IMAGE_TEMP_FILE)
            except Exception: pass
        if os.path.exists(COMBINED_PREVIEW_IMAGE_TEMP_FILE):
            try: os.remove(COMBINED_PREVIEW_IMAGE_TEMP_FILE)
            except Exception: pass
        return None

if __name__ == '__main__':
    print("--- Testing Video Processor Thumbnail Functions ---")
    # Ensure "video_templates" directory exists and contains some .mp4 files for testing.
    
    videos = list_video_templates()
    if videos:
        print(f"\nVideos found in '{VIDEO_TEMPLATES_DIR}':")
        for vid in videos:
            print(f"  - {os.path.basename(vid)}")
            thumb_path = get_or_create_thumbnail(vid, size=(200,355)) # Test with a different size
            if thumb_path:
                print(f"    Thumbnail -> {thumb_path}")
            else:
                print(f"    Could not generate thumbnail for {vid}")
        
        print("\nRequesting thumbnails again (should use cache):")
        for vid in videos:
            thumb_path = get_or_create_thumbnail(vid, size=(200,355))
            if thumb_path:
                print(f"  - Thumbnail for {os.path.basename(vid)}: {thumb_path}")

        # Test composite preview image generation
        print("\n--- Testing Composite Preview Image ---")
        test_video_thumb = get_or_create_thumbnail(videos[0], size=(360, 640)) # Use standard preview size
        if test_video_thumb:
            sample_text = "Hello World!\nThis is a test."
            sample_style = {
                'font': 'Impact', 'fontsize': 48, 'color': '#FFFF00',
                'stroke_color': '#000000', 'stroke_width': 2, 
                'bg_color': 'transparent', # Important for preview
                'position_choice': 'Bottom'
            }
            composite_path = create_composite_preview_image(test_video_thumb, sample_text, sample_style)
            if composite_path:
                print(f"Composite preview image generated: {composite_path}")
                # You can open this image to verify
            else:
                print("Failed to generate composite preview image.")
        else:
            print("Skipping composite preview test as no thumbnail was generated.")

    else:
        print(f"No videos found in '{VIDEO_TEMPLATES_DIR}'. Please add some videos to test.")
    
    # Test subtitle burning (requires pre-existing narrated video and SRT)
    # print("\n--- Testing Subtitle Burning ---")
    # test_input_narrated_video = "path/to/your/narrated_video.mp4" 
    # test_input_srt_file = "path/to/your/subtitle_file.srt"       
    # test_output_video_with_subs = "output_video_with_subs_test.mp4"
    # font_options_for_test = {
    #     'font': 'Arial-Bold', 'fontsize': 36, 'color': 'yellow',
    #     'stroke_color': 'black', 'stroke_width': 2, 'bg_color': 'rgba(0,0,0,0.6)', 
    #     'position_choice': 'Bottom' 
    # }
    # if os.path.exists(test_input_narrated_video) and os.path.exists(test_input_srt_file):
    #     print(f"Using narrated video: '{test_input_narrated_video}' and SRT: '{test_input_srt_file}'")
    #     success_burn = burn_subtitles_on_video(
    #         test_input_narrated_video, test_input_srt_file,
    #         test_output_video_with_subs, style_options=font_options_for_test
    #     )
    #     if success_burn:
    #         print(f"Subtitle burn test completed. Output: {test_output_video_with_subs}")
    #     else:
    #         print("Subtitle burn test failed.")
    # else:
    #     print("\nSkipping subtitle burn test: Ensure narrated video and SRT file paths are correct.")