# tts_kokoro_module.py
from kokoro import KPipeline
import soundfile as sf
import torch
import traceback
import os
import numpy as np
# from huggingface_hub import constants # Unused import

DEVICE = None
KOKORO_REPO_ID = 'hexgrad/Kokoro-82M' # Repository ID for the Kokoro model
PIPELINE_INSTANCE = None # Global pipeline instance for this module

def _initialize_device():
    """Initializes the computation device (CUDA, MPS, or CPU)."""
    global DEVICE
    if DEVICE is None:
        if torch.cuda.is_available():
            DEVICE = "cuda"
        elif torch.backends.mps.is_available(): # For MacOS Metal
            DEVICE = "mps"
        else:
            DEVICE = "cpu"
        # print(f"TTS - Using device: {DEVICE}") # Optional debug
    return DEVICE

def initialize_global_pipeline():
    """Initializes the KPipeline globally if not already done."""
    global PIPELINE_INSTANCE
    if PIPELINE_INSTANCE is not None:
        return True

    device = _initialize_device()
    # print(f"Attempting to initialize KPipeline globally with repo_id='{KOKORO_REPO_ID}' on device '{device}'...") # Optional debug
    
    try:
        PIPELINE_INSTANCE = KPipeline(
            lang_code='a', # 'a' for auto-detection as per Kokoro-82M README
            device=device,
            repo_id=KOKORO_REPO_ID
        )
        # print("KPipeline global initialized successfully.") # Optional debug
        
        # Debug check for sample rate (useful for troubleshooting)
        # if hasattr(PIPELINE_INSTANCE, 'model') and PIPELINE_INSTANCE.model and \
        #    hasattr(PIPELINE_INSTANCE.model, 'config') and PIPELINE_INSTANCE.model.config and \
        #    hasattr(PIPELINE_INSTANCE.model.config, 'sampling_rate'):
        #     print(f"DEBUG: Sample rate from PIPELINE_INSTANCE.model.config: {PIPELINE_INSTANCE.model.config.sampling_rate}")
        # else:
        #     print("DEBUG: Could not access PIPELINE_INSTANCE.model.config.sampling_rate. Default will be used for sf.write if needed.")
            
        return True

    except Exception as e:
        print(f"CRITICAL Error initializing KPipeline globally: {e}")
        traceback.print_exc()
        PIPELINE_INSTANCE = None
        return False

# Attempt to initialize the pipeline when the module is loaded
if not initialize_global_pipeline():
    print("TTS Module Warning: KPipeline failed to initialize on module load.")


def list_available_kokoro_voices() -> dict:
    """
    Lists English (American and British) voices with Quality B or higher
    that are expected to work with the Kokoro pip package.
    Returns a dictionary mapping friendly names to technical names.
    """
    voices = {
        # American English (Quality B or higher)
        "English American F (Heart)": "af_heart",   # Quality A
        "English American F (Bella)": "af_bella",   # Quality A
        "English American F (Alloy)": "af_alloy",   # Quality B
        "English American F (Aoede)": "af_aoede",   # Quality B
        "English American F (Kore)": "af_kore",    # Quality B
        "English American F (Nicole)": "af_nicole", # Quality B
        "English American F (Nova)": "af_nova",    # Quality B
        "English American F (Sarah)": "af_sarah",   # Quality B
        "English American M (Fenrir)": "am_fenrir", # Quality B
        "English American M (Michael)": "am_michael",# Quality B
        "English American M (Puck)": "am_puck",    # Quality B
        
        # British English (Quality B or higher)
        "English British F (Emma)": "bf_emma",     # Quality B
        "English British M (Fable)": "bm_fable",   # Quality B
        "English British M (George)": "bm_george", # Quality B
    }
    return voices

def generate_speech_with_voice_name(text: str, voice_technical_name: str, output_filename: str = "output.wav") -> bool:
    """Generates speech from text using the specified Kokoro voice and saves it to a file."""
    if not PIPELINE_INSTANCE:
        print("Error: KPipeline global is not available/initialized.")
        if not initialize_global_pipeline() or not PIPELINE_INSTANCE: # Retry initialization
            print("Error: Critical failure initializing KPipeline.")
            return False
            
    if not text.strip():
        print("Error: Text for audio generation is empty.")
        return False

    try:
        # print(f"Generating audio for text: '{text[:50]}...' (Voice: '{voice_technical_name}')") # Optional debug
        all_audio_segments = []
        
        # Kokoro pipeline might yield multiple segments for longer texts
        for i, (_batch_size, _phoneme_speed, audio_segment) in enumerate(PIPELINE_INSTANCE(text, voice=voice_technical_name)):
            if isinstance(audio_segment, torch.Tensor):
                audio_segment = audio_segment.detach().cpu().numpy() # Convert tensor to numpy array
            all_audio_segments.append(audio_segment)
        
        if not all_audio_segments:
            print("Error: No audio segments were generated.")
            return False

        # Concatenate all audio segments if multiple were produced
        if len(all_audio_segments) > 1:
            # print(f"{len(all_audio_segments)} audio segments generated. Concatenating...") # Optional debug
            try:
                final_audio = np.concatenate(all_audio_segments)
            except ValueError as e:
                print(f"Error concatenating audio segments (np.concatenate): {e}")
                print("This may occur if segments have incompatible shapes. Using only the first segment as fallback.")
                final_audio = all_audio_segments[0] 
        elif all_audio_segments: # Only one segment
            final_audio = all_audio_segments[0]
        else: 
            print("Error: Audio segments list is empty after processing.") # Should be caught by earlier check
            return False

        # Determine sample rate
        sample_rate = 24000 # Default sample rate
        if hasattr(PIPELINE_INSTANCE, 'model') and PIPELINE_INSTANCE.model and \
           hasattr(PIPELINE_INSTANCE.model, 'config') and PIPELINE_INSTANCE.model.config and \
           hasattr(PIPELINE_INSTANCE.model.config, 'sampling_rate'):
            sample_rate = PIPELINE_INSTANCE.model.config.sampling_rate
        elif hasattr(PIPELINE_INSTANCE, 'sample_rate'): # Fallback if pipeline has it directly
            sample_rate = PIPELINE_INSTANCE.sample_rate
        # else: # Optional debug
            # print(f"Warning: Could not determine sample_rate from pipeline. Using default {sample_rate} Hz.")

        sf.write(output_filename, final_audio, sample_rate)
        # print(f"Audio saved as '{output_filename}' with sample rate {sample_rate} Hz.") # Optional debug
        return True
    except ValueError as ve:
        if "Specify a voice" in str(ve): # Specific error from Kokoro library
            print(f"ValueError: {ve} - Kokoro library requires the 'voice' argument.")
        else:
            print(f"ValueError during generation: {ve}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"General error during audio generation (Voice: {voice_technical_name}): {e}")
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("\n--- Starting TTS Module Test ---")
    if not PIPELINE_INSTANCE:
        print("Test ended: Global KPipeline could not be initialized.")
    else:
        test_text = "This is a test sentence. This is a second sentence to ensure multiple segments if the text is long enough."
        
        voice_map_for_test = list_available_kokoro_voices()
        # Pick a voice for testing, e.g., the first one
        if voice_map_for_test:
            first_friendly_name = list(voice_map_for_test.keys())[0]
            technical_name_to_test = voice_map_for_test[first_friendly_name]

            print(f"Testing with voice: '{first_friendly_name}' (Technical: '{technical_name_to_test}')")
            output_file = "test_tts_output.wav"
            success = generate_speech_with_voice_name(test_text, technical_name_to_test, output_file)
            if success:
                print(f"TTS test successful. Check '{output_file}'.")
            else:
                print("TTS test failed.")
        else:
            print("Error: No voices available in the map for testing.")