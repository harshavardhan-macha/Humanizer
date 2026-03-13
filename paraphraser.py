import os
import logging
import torch
from typing import Tuple, Optional, List

# Suppress warnings
os.environ["TORCH_DYNAMO_DISABLE"] = "1"
os.environ["BITSANDBYTES_NOWELCOME"] = "1"

logger = logging.getLogger(__name__)

# Global variables for model management
current_model = None
model_name = None
device = None
tokenizer = None
model = None

# Model configurations with fallback options
MODEL_CONFIGS = {
   
    "humarin/chatgpt_paraphraser_on_T5_base": {
        "requires_sentencepiece": True,
        "model_name": "humarin/chatgpt_paraphraser_on_T5_base",
        "prefix": "paraphrase: ",
        "max_length": 512,
        "num_beams": 1,
        "do_sample": False,
        "temperature": 0.7,
        "top_k": 50
    }
}

def get_device_info():
    """Get device information"""
    if torch.cuda.is_available():
        return f"CUDA ({torch.cuda.get_device_name()})"
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return "MPS (Apple Silicon)"
    else:
        return "CPU"

def check_sentencepiece_available():
    """Check if sentencepiece is available"""
    try:
        import sentencepiece
        return True
    except ImportError:
        return False

def get_available_models() -> List[str]:
    """Return list of available models based on installed dependencies"""
    available = []
    sentencepiece_available = check_sentencepiece_available()
    
    for model_key, config in MODEL_CONFIGS.items():
        if config["requires_sentencepiece"] and not sentencepiece_available:
            continue
        available.append(model_key)
    
    return available

def get_current_model() -> Optional[str]:
    """Get currently loaded model name"""
    return model_name if current_model is not None else None

def load_model(model_name_param: str = None) -> Tuple[bool, Optional[str]]:
    """
    Load a paraphrasing model with proper error handling and fallbacks
    """
    global current_model, model_name, device, tokenizer, model
    
    try:
        # Determine which model to load
        if model_name_param is None:
            # Try to find a working model
            available_models = get_available_models()
            if not available_models:
                return False, "No compatible models available. Please install sentencepiece."
            model_name_param = available_models[0]
        
        if model_name_param not in MODEL_CONFIGS:
            return False, f"Model {model_name_param} not supported"
        
        config = MODEL_CONFIGS[model_name_param]
        
        # Check sentencepiece requirement
        if config["requires_sentencepiece"] and not check_sentencepiece_available():
            return False, f"Model {model_name_param} requires sentencepiece. Please install it with: pip install sentencepiece"
        
        logger.info(f"Loading model: {model_name_param}")
        
        # Determine device
        if torch.cuda.is_available():
            device = "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        
        logger.info(f"Using device: {device}")
        
        # Load model based on type
        if config["requires_sentencepiece"]:
            # T5 models
            from transformers import T5Tokenizer, T5ForConditionalGeneration
            tokenizer = T5Tokenizer.from_pretrained(config["model_name"])
            model = T5ForConditionalGeneration.from_pretrained(config["model_name"])
        else:
            # Pegasus models (BART support removed)
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            tokenizer = AutoTokenizer.from_pretrained(config["model_name"])
            model = AutoModelForSeq2SeqLM.from_pretrained(config["model_name"])
        
        # Move model to device
        model = model.to(device)
        model.eval()
        
        # Use half-precision (float16) on GPU for faster inference
        if device == "cuda":
            try:
                model = model.half()
                logger.info("Enabled half-precision (float16) for faster inference")
            except:
                logger.warning("Could not enable half-precision, using float32")
        
        # Store in global variable (we'll use direct generation instead of pipeline)
        current_model = model
        
        model_name = model_name_param
        logger.info(f"Successfully loaded {model_name_param}")
        return True, None
        
    except Exception as e:
        error_msg = f"Error loading model {model_name_param}: {str(e)}"
        logger.error(error_msg)
        current_model = None
        model_name = None
        return False, error_msg

def _chunk_text_for_paraphrasing(text: str, max_tokens: int) -> List[str]:
    """Split text into smaller chunks that fit within the model's token limit."""
    # Simple sentence-based chunking to keep units coherent
    try:
        import nltk
        from nltk.tokenize import sent_tokenize
    except ImportError:
        # Fallback to naive sentence splitting
        sentences = text.split('.')
    else:
        sentences = sent_tokenize(text)

    chunks = []
    current = []
    current_tokens = 0

    for sent in sentences:
        if not sent.strip():
            continue

        # Estimate tokens using tokenizer if available, otherwise word count
        try:
            token_ids = tokenizer.encode(sent, add_special_tokens=False)
            sent_tokens = len(token_ids)
        except Exception:
            sent_tokens = len(sent.split())

        # If sentence itself is too long, force-split on words
        if sent_tokens > max_tokens:
            words = sent.split()
            segment = []
            seg_tokens = 0
            for word in words:
                seg_tokens += 1
                segment.append(word)
                if seg_tokens >= max_tokens:
                    chunks.append(' '.join(segment))
                    segment = []
                    seg_tokens = 0
            if segment:
                chunks.append(' '.join(segment))
            continue

        if current_tokens + sent_tokens > max_tokens and current:
            chunks.append(' '.join(current))
            current = [sent]
            current_tokens = sent_tokens
        else:
            current.append(sent)
            current_tokens += sent_tokens

    if current:
        chunks.append(' '.join(current))

    return chunks


def paraphrase_text(text: str, model_name_param: str = None) -> Tuple[str, Optional[str]]:
    """
    Paraphrase text using the loaded model
    """
    global current_model, model_name
    
    try:
        # Load model if not loaded or different model requested
        if current_model is None or (model_name_param and model_name_param != model_name):
            success, error = load_model(model_name_param)
            if not success:
                return "", error
        
        if current_model is None or tokenizer is None:
            return "", "No model available for paraphrasing"
        
        # Get model config
        config = MODEL_CONFIGS.get(model_name)
        if config is None:
            return "", f"Internal error: configuration for model {model_name} not found"
        
        # Chunk the input text if it is too long
        max_input_tokens = config.get("max_length", 512) - 30
        chunks = [text]
        try:
            chunks = _chunk_text_for_paraphrasing(text, max_input_tokens)
        except Exception:
            chunks = [text]

        paraphrased_chunks = []
        for chunk in chunks:
            if config["prefix"]:
                input_text = f"{config['prefix']}{chunk}"
            else:
                input_text = chunk

            # Tokenize input (truncation should not happen for well-formed chunks)
            inputs = tokenizer.encode(input_text, return_tensors="pt", max_length=config.get("max_length", 512), truncation=True)
            inputs = inputs.to(device)
            
            # Generate paraphrase with optimized settings
            with torch.no_grad():
                outputs = current_model.generate(
                    inputs,
                    max_length=min(len(chunk.split()) * 2 + 30, config["max_length"]),
                    num_return_sequences=1,
                    num_beams=config.get("num_beams", 1),
                    do_sample=config.get("do_sample", False),
                    early_stopping=True
                )
            
            # Decode output
            paraphrased = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
            
            # Clean up output if it contains the prefix
            if config["prefix"] and paraphrased.startswith(config["prefix"]):
                paraphrased = paraphrased[len(config["prefix"]):].strip()

            paraphrased_chunks.append(paraphrased)

        # Join the paraphrased chunks with double newlines to preserve separation
        paraphrased_text = "\n\n".join([c for c in paraphrased_chunks if c])
        return paraphrased_text, None
            
    except Exception as e:
        error_msg = f"Error in paraphrasing: {str(e)}"
        logger.error(error_msg)
        return "", error_msg

def initialize_paraphraser():
    """Initialize the paraphraser with error handling and fallbacks"""
    try:
        available_models = get_available_models()
        
        if not available_models:
            logger.warning("No compatible models available")
            logger.info("To enable T5 models, install sentencepiece: pip install sentencepiece")
            return
        
        # Try to load the first available model
        success, error = load_model(available_models[0])
        if success:
            logger.info(f"Paraphraser initialized successfully with {model_name}")
        else:
            logger.warning(f"Paraphraser initialization failed: {error}")
            logger.info("Paraphraser will run without AI model support")
    except Exception as e:
        logger.error(f"Failed to initialize paraphraser: {str(e)}")

# Initialize on import
initialize_paraphraser()
