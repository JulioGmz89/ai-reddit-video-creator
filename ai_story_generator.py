# ai_story_generator.py
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import traceback

MODEL_NAME = "google/gemma-2b-it"
GENERATION_DEVICE = None
model = None
tokenizer = None
IS_INITIALIZED = False

def _initialize_model():
    global model, tokenizer, GENERATION_DEVICE, IS_INITIALIZED
    if IS_INITIALIZED:
        return True

    print(f"AI Story Gen - Initializing Gemma model ({MODEL_NAME}). This may take time on first run...")
    try:
        if torch.cuda.is_available():
            GENERATION_DEVICE = "cuda"
            print(f"AI Story Gen - Using device: {GENERATION_DEVICE} (GPU)")
            model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                torch_dtype=torch.bfloat16,
                device_map="auto", # Automatically select device for model parts
            )
        else: 
            GENERATION_DEVICE = "cpu"
            print(f"AI Story Gen - Using device: {GENERATION_DEVICE} (CPU)")
            print(f"AI Story Gen - Loading model {MODEL_NAME} on CPU. This might require significant RAM.")
            model_dtype = torch.bfloat16 
            try:
                print(f"AI Story Gen - Attempting to load with dtype: {model_dtype}")
                model = AutoModelForCausalLM.from_pretrained(
                    MODEL_NAME,
                    torch_dtype=model_dtype,
                )
            except Exception as e_bf16:
                print(f"AI Story Gen - Failed to load with bfloat16 ({e_bf16}). Attempting with float16...")
                model_dtype = torch.float16
                model = AutoModelForCausalLM.from_pretrained(
                    MODEL_NAME,
                    torch_dtype=model_dtype,
                )
        
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

        print(f"AI Story Gen - Gemma model ({MODEL_NAME}) loaded and initialized on {GENERATION_DEVICE}.")
        IS_INITIALIZED = True
        return True

    except Exception as e:
        print(f"AI Story Gen - CRITICAL ERROR initializing Gemma model: {e}")
        traceback.print_exc()
        IS_INITIALIZED = False
        return False

def generate_story(subject: str, style: str, max_new_tokens: int = 300) -> str:
    """Generates a story based on the subject and style using the initialized AI model."""
    if not IS_INITIALIZED:
        if not _initialize_model(): 
            return "Error: AI story generation model could not be initialized."

    if not subject or not style:
        return "Error: Subject and style (in English) are required to generate the story."

    # Construct the prompt in English for the model
    messages = [
        {"role": "user", "content": f"Write a creative and engaging fictional story. The theme is '{subject}' and the style should be similar to '{style}'. Please develop the narrative well and ensure it is a complete story."}
    ]
    
    prompt_for_model = tokenizer.apply_chat_template(
        messages, 
        tokenize=False, 
        add_generation_prompt=True 
    )

    print(f"AI Story Gen - Generating English story with subject: '{subject}', style: '{style}', max_tokens: {max_new_tokens}...")
    # print(f"AI Story Gen - Formatted prompt (start): {prompt_for_model[:300]}...") # Useful for debugging prompt issues

    inputs = tokenizer(prompt_for_model, return_tensors="pt")
    
    if model.device.type != 'cpu': # Move inputs to GPU if model is on GPU
        inputs = inputs.to(model.device)

    try:
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.75, 
            top_p=0.95,
            top_k=50,
            do_sample=True, 
            pad_token_id=tokenizer.eos_token_id 
        )
        
        generated_text = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        
        # print(f"AI Story Gen - English story generated (start): {generated_text[:300]}...") # Useful for seeing generation start
        return generated_text.strip()

    except Exception as e:
        print(f"AI Story Gen - Error during story generation: {e}")
        traceback.print_exc()
        return f"Error during AI story generation: {e}"

if __name__ == '__main__':
    print("--- Starting AI Story Generator module test (Gemma 2B IT) ---")
    
    # Test with English inputs
    subject1 = "an ancient map found in a forgotten book"
    style1 = "adventure and mystery with a light fantasy touch"
    print(f"\nTest 1: Subject='{subject1}', Style='{style1}'")
    story1 = generate_story(subject1, style1, max_new_tokens=150) # Reduced tokens for faster test
    print("\n--- Generated Story 1 (Gemma 2B IT) ---")
    print(story1)
    print("--------------------------------------")

    # subject2 = "a lonely robot on a desolate planet"
    # style2 = "poignant science fiction"
    # print(f"\nTest 2: Subject='{subject2}', Style='{style2}'")
    # story2 = generate_story(subject2, style2, max_new_tokens=100) 
    # print("\n--- Generated Story 2 (Gemma 2B IT) ---")
    # print(story2)
    # print("--------------------------------------")