# srt_generator.py
import whisper
import os
import traceback

def _format_timestamp(seconds: float) -> str:
    """Converts seconds to SRT time format HH:MM:SS,mmm."""
    assert seconds >= 0, "Timestamp cannot be negative"
    milliseconds = round(seconds * 1000.0)

    hours = int(milliseconds // 3_600_000)
    milliseconds %= 3_600_000
    minutes = int(milliseconds // 60_000)
    milliseconds %= 60_000
    seconds_val = int(milliseconds // 1_000) # Renamed to avoid conflict
    milliseconds %= 1_000
    return f"{hours:02d}:{minutes:02d}:{seconds_val:02d},{milliseconds:03d}"

def create_srt_file(
    audio_path: str, 
    srt_path: str, 
    model_size: str = "base.en", 
    language: str = "en",
    max_words_per_segment: int | None = None
) -> bool:
    """
    Generates an SRT file from an audio file using Whisper,
    with an option to limit words per subtitle segment.
    """
    if not os.path.exists(audio_path):
        print(f"Error SRT: Audio file not found at '{audio_path}'")
        return False

    try:
        # print(f"SRT Gen - Loading Whisper model '{model_size}'. This may take time on first run...") # Optional debug
        model = whisper.load_model(model_size) 
        # print("SRT Gen - Whisper model loaded.") # Optional debug

        # print(f"SRT Gen - Transcribing audio from: {audio_path}. This can take time...") # Optional debug
        
        should_get_word_timestamps = isinstance(max_words_per_segment, int) and max_words_per_segment > 0
        
        result = model.transcribe(
            audio_path, 
            language=language, 
            verbose=False, # Keep False for cleaner output, True for detailed progress
            word_timestamps=should_get_word_timestamps 
        )
        # print("SRT Gen - Transcription completed.") # Optional debug

        srt_segment_index = 1
        with open(srt_path, "w", encoding="utf-8") as f:
            if should_get_word_timestamps:
                # print(f"SRT Gen - Applying limit of {max_words_per_segment} words per subtitle segment.") # Optional debug
                for segment_from_whisper in result["segments"]:
                    if 'words' not in segment_from_whisper or not segment_from_whisper['words']: # Check if 'words' exists and is not empty
                        # print("Warning SRT: No word timestamps found in a segment or segment is empty, using original segment.") # Useful debug
                        # Fallback: use the original segment if no 'words'
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
                    current_chunk_words_info = [] # Stores word dicts {text, start, end}

                    for i, word_info in enumerate(words_in_segment):
                        current_chunk_words_info.append(word_info)
                        
                        if len(current_chunk_words_info) == max_words_per_segment or i == len(words_in_segment) - 1:
                            if not current_chunk_words_info: 
                                continue

                            chunk_text = " ".join([word_data['word'] for word_data in current_chunk_words_info]).strip()
                            # Ensure 'start' and 'end' keys exist for all word_data, Whisper should provide them
                            chunk_start_time = current_chunk_words_info[0]['start']
                            chunk_end_time = current_chunk_words_info[-1]['end']
                            
                            if chunk_text: 
                                f.write(f"{srt_segment_index}\n")
                                f.write(f"{_format_timestamp(chunk_start_time)} --> {_format_timestamp(chunk_end_time)}\n")
                                f.write(f"{chunk_text}\n\n")
                                srt_segment_index += 1
                            
                            current_chunk_words_info = [] 
            else: # Original behavior: one SRT entry per Whisper segment
                for segment in result["segments"]:
                    start_time = _format_timestamp(segment["start"])
                    end_time = _format_timestamp(segment["end"])
                    text = segment["text"].strip()
                    if text: # Only write if there is text
                        f.write(f"{srt_segment_index}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{text}\n\n")
                        srt_segment_index += 1
        
        # print(f"SRT Gen - Subtitles file saved to: {srt_path}") # Optional debug
        return True

    except FileNotFoundError: # Specifically for ffmpeg
        print("Error SRT: ffmpeg not found. Ensure ffmpeg is installed and in your system's PATH.")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"Error SRT - An error occurred during subtitle generation: {e}")
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("--- Starting SRT Generator module test ---")
    
    # This test requires a .wav file named "test_audio.wav" in the same directory
    # or you can modify the path.
    # A dummy WAV is created if "test_audio.wav" is not found.
    test_audio_input_path = "test_audio.wav" 
    
    if not os.path.exists(test_audio_input_path):
        print(f"WARNING: '{test_audio_input_path}' not found. Creating a dummy WAV for testing.")
        try:
            import wave, numpy as np
            sample_rate, duration_s, num_channels, sample_width_bytes = 24000, 3, 1, 2
            frequency_hz = 440
            num_frames = int(duration_s * sample_rate)
            t = np.linspace(0, duration_s, num_frames, endpoint=False)
            audio_data_np = (np.sin(2 * np.pi * frequency_hz * t) * (2**(8 * sample_width_bytes - 1) - 1)).astype(np.int16)
            with wave.open(test_audio_input_path, 'w') as wf:
                wf.setnchannels(num_channels)
                wf.setsampwidth(sample_width_bytes)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data_np.tobytes())
            print(f"Dummy audio file created: {test_audio_input_path}")
        except Exception as e_dummy: 
            print(f"Could not create dummy audio file: {e_dummy}. Test may fail.")

    if os.path.exists(test_audio_input_path):
        print(f"Using test audio: {test_audio_input_path}")
        
        # Test with word limit per segment
        max_words_test = 3
        output_srt_custom_path = f"test_subtitles_max_{max_words_test}_words.srt"
        print(f"\nTesting with max_words_per_segment = {max_words_test}")
        success_custom = create_srt_file(
            test_audio_input_path, 
            output_srt_custom_path, 
            model_size="tiny.en", # Using a smaller model for faster testing
            language="en",
            max_words_per_segment=max_words_test
        )
        if success_custom:
            print(f"Test with max_words={max_words_test} completed. Output: {output_srt_custom_path}")
        else:
            print(f"Test failed for max_words={max_words_test}.")

        # Test with Whisper's default segmentation
        output_srt_default_path = "test_subtitles_default_segments.srt"
        print("\nTesting with Whisper's default segmentation...")
        success_default = create_srt_file(
            test_audio_input_path, 
            output_srt_default_path, 
            model_size="tiny.en", 
            language="en"
        )
        if success_default:
            print(f"Test with default segmentation completed. Output: {output_srt_default_path}")
        else:
            print("Test failed for default segmentation.")
    else:
        print(f"\nCRITICAL Error: Test audio file '{test_audio_input_path}' does NOT EXIST and dummy creation failed.")