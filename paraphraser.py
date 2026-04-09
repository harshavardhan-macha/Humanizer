import copy
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

# Local cache path for group beam search custom generator (Windows-friendly)
_GROUP_BEAM_CUSTOM_GENERATE_PATH = None

# Model configurations with fallback options
MODEL_CONFIGS = {
    "t5-small": {
        "requires_sentencepiece": True,
        "model_name": "t5-small",
        "prefix": "paraphrase: ",
        "max_length": 512,
        "num_beams": 1,
        "do_sample": False,
        "temperature": 0.7,
        "top_k": 50
    },
    "humarin/chatgpt_paraphraser_on_T5_base": {
        "requires_sentencepiece": True,
        "model_name": "humarin/chatgpt_paraphraser_on_T5_base",
        "prefix": "paraphrase: ",
        "max_length": 512,
        "num_beams": 1,
        "do_sample": False,
        "temperature": 0.7,
        "top_k": 50
    },
    "Vamsi/T5_Paraphrase_Paws": {
        "requires_sentencepiece": True,
        "model_name": "Vamsi/T5_Paraphrase_Paws",
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
        # Lazy initialize if no model is loaded yet
        if current_model is None:
            initialize_paraphraser()
        
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
        
        # Prepare input
        if config["prefix"]:
            input_text = f"{config['prefix']}{text}"
        else:
            input_text = text
        
        # Tokenize input
        inputs = tokenizer.encode(input_text, return_tensors="pt", max_length=512, truncation=True)
        inputs = inputs.to(device)
        
        # Generate paraphrase with optimized settings
        with torch.no_grad():
            outputs = current_model.generate(
                inputs,
                max_length=min(len(text.split()) * 2 + 30, config["max_length"]),
                num_return_sequences=1,
                num_beams=config.get("num_beams", 1),
                do_sample=config.get("do_sample", False),
                early_stopping=True
            )
        
        # Decode output
        paraphrased = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        
        # Clean up output if it contains the prefix (case-insensitive)
        if config["prefix"]:
            prefix_lower = config["prefix"].lower()
            if paraphrased.lower().startswith(prefix_lower):
                # Find the actual prefix in the output and remove it
                paraphrased = paraphrased[len(config["prefix"]):].strip()
        
        return paraphrased, None
            
    except Exception as e:
        error_msg = f"Error in paraphrasing: {str(e)}"
        logger.error(error_msg)
        return "", error_msg


def paraphrase_sentence_advanced(
    sentence: str,
    model_name_param: str = None,
    generation_kwargs: Optional[dict] = None,
) -> Tuple[str, Optional[str]]:
    """
    Paraphrase a single sentence using custom generation settings.

    This is used by the "humanize" pipeline to enforce a specific decoding setup
    (diverse beams + sampling) while keeping model loading centralized here.
    """
    global current_model, model_name, tokenizer, device

    try:
        if not sentence or not sentence.strip():
            return "", None

        # Lazy initialize if no model is loaded yet
        if current_model is None:
            initialize_paraphraser()

        # Load model if not loaded or different model requested
        if current_model is None or (model_name_param and model_name_param != model_name):
            success, error = load_model(model_name_param)
            if not success:
                return "", error

        if current_model is None or tokenizer is None:
            return "", "No model available for paraphrasing"

        prefix = "paraphrase: "
        input_text = f"{prefix}{sentence.strip()}"

        inputs = tokenizer.encode(
            input_text, return_tensors="pt", max_length=512, truncation=True
        ).to(device)

        gen = {
            "max_length": 512,
            "num_return_sequences": 1,
            "early_stopping": True,
        }
        if generation_kwargs:
            gen.update(generation_kwargs)

        # Convenience: allow callers to specify min_length as a ratio of input length.
        # This keeps decoding settings centralized while letting pipelines enforce
        # "substantial" outputs.
        if "min_length_ratio" in gen:
            try:
                ratio = float(gen.pop("min_length_ratio"))
                gen["min_length"] = max(0, int(inputs.shape[1] * ratio))
            except Exception:
                gen.pop("min_length_ratio", None)

        # Transformers now externalizes group beam search. On Windows, remote loading
        # may hit path separator issues, so we snapshot the repo locally and point
        # `custom_generate` to a local directory.
        if gen.get("num_beam_groups", 1) and gen.get("num_beam_groups", 1) > 1:
            # The current group beam search implementation does not support sampling.
            # If callers request sampling, fall back to standard beam search (single group)
            # and skip loading custom generation code.
            if gen.get("do_sample", False):
                gen["num_beam_groups"] = 1
                gen.pop("diversity_penalty", None)
            else:
                gen.setdefault("trust_remote_code", True)

                global _GROUP_BEAM_CUSTOM_GENERATE_PATH
                if _GROUP_BEAM_CUSTOM_GENERATE_PATH is None:
                    try:
                        from huggingface_hub import snapshot_download

                        _GROUP_BEAM_CUSTOM_GENERATE_PATH = snapshot_download(
                            repo_id="transformers-community/group-beam-search",
                            allow_patterns=["custom_generate/*", "README.md", "config.json", "generation_config.json"],
                        )
                    except Exception as e:
                        return "", f"Failed to prepare group beam search generator: {e}"

                gen.setdefault("custom_generate", _GROUP_BEAM_CUSTOM_GENERATE_PATH)

        with torch.no_grad():
            outputs = current_model.generate(inputs, **gen)

        paraphrased = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

        # Remove prefix if present
        if paraphrased.lower().startswith(prefix):
            paraphrased = paraphrased[len(prefix) :].strip()

        return paraphrased, None

    except Exception as e:
        error_msg = f"Error in advanced paraphrasing: {str(e)}"
        logger.error(error_msg)
        return "", error_msg


def paraphrase_sentences_batched(
    sentences: List[str],
    model_name_param: str = None,
    generation_kwargs: Optional[dict] = None,
    batch_size: Optional[int] = None,
) -> Tuple[List[str], Optional[str]]:
    """
    Paraphrase multiple sentences with fewer GPU/CPU round-trips than one generate() per sentence.
    Falls back to sequential paraphrase_sentence_advanced if batching fails.
    """
    global current_model, model_name, tokenizer, device

    if not sentences:
        return [], None

    if batch_size is None:
        batch_size = 8 if torch.cuda.is_available() else 4

    prefix = "paraphrase: "
    n = len(sentences)
    out: List[str] = [""] * n

    # Indices that need model work
    work: List[Tuple[int, str]] = []
    for i, s in enumerate(sentences):
        if s and s.strip():
            work.append((i, s.strip()))
        else:
            out[i] = sentences[i] if sentences[i] is not None else ""

    if not work:
        return out, None

    try:
        if current_model is None:
            initialize_paraphraser()

        if current_model is None or (model_name_param and model_name_param != model_name):
            success, error = load_model(model_name_param)
            if not success:
                for i, s in work:
                    p, err = paraphrase_sentence_advanced(
                        s, model_name_param=model_name_param, generation_kwargs=generation_kwargs
                    )
                    out[i] = p.strip() if not err and p.strip() else s
                return out, None

        if current_model is None or tokenizer is None:
            for i, s in work:
                p, err = paraphrase_sentence_advanced(
                    s, model_name_param=model_name_param, generation_kwargs=generation_kwargs
                )
                out[i] = p.strip() if not err and p.strip() else s
            return out, None

        gen = {
            "max_length": 256,
            "num_return_sequences": 1,
            "early_stopping": True,
            "num_beams": 4,
            "do_sample": True,
            "temperature": 0.88,
            "top_k": 50,
            "top_p": 0.92,
            "repetition_penalty": 2.5,
            "no_repeat_ngram_size": 3,
            "length_penalty": 1.15,
        }
        if generation_kwargs:
            gen.update(copy.deepcopy(generation_kwargs))
        # Batched path: group beam + min_length_ratio are awkward per-row; use simpler defaults.
        gen.pop("min_length_ratio", None)
        gen["num_beam_groups"] = 1
        gen.pop("diversity_penalty", None)

        for start in range(0, len(work), batch_size):
            chunk = work[start : start + batch_size]
            batch_texts = [prefix + t for _, t in chunk]
            enc = tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            input_ids = enc["input_ids"].to(device)
            attention_mask = enc["attention_mask"].to(device)

            with torch.no_grad():
                batch_out = current_model.generate(
                    input_ids,
                    attention_mask=attention_mask,
                    pad_token_id=tokenizer.pad_token_id,
                    **gen,
                )

            for row, (idx, _orig) in enumerate(chunk):
                decoded = tokenizer.decode(batch_out[row], skip_special_tokens=True).strip()
                if decoded.lower().startswith(prefix):
                    decoded = decoded[len(prefix) :].strip()
                out[idx] = decoded if decoded else _orig

        return out, None

    except Exception as e:
        logger.warning(f"Batched paraphrase failed ({e}), falling back to sequential.")
        for i, s in work:
            p, err = paraphrase_sentence_advanced(
                s, model_name_param=model_name_param, generation_kwargs=generation_kwargs
            )
            out[i] = p.strip() if not err and p.strip() else s
        return out, None


def initialize_paraphraser():
    """Initialize the paraphraser with error handling and fallbacks (called lazily)"""
    global current_model, model_name
    
    # Skip if already initialized
    if current_model is not None:
        return
    
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
            logger.info("Paraphraser will attempt to use available models on demand")
    except Exception as e:
        logger.error(f"Failed to initialize paraphraser: {str(e)}")

# DO NOT initialize on import - use lazy loading when paraphrase_text() is called
# This avoids downloading large models unnecessarily
# initialize_paraphraser() will be called on first use
