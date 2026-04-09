import functools
import re
import time
import random
from typing import Dict, Tuple, List, Optional

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

from fpdf import FPDF

# Import our utility modules
from paraphraser import (
    load_model,
    get_available_models,
    get_current_model,
    get_device_info,
    paraphrase_text,
    paraphrase_sentences_batched,
)
from rewriter import rewrite_text, get_synonym, refine_text
from detector import (
    AITextDetector, 
    detect_with_all_models, 
    detect_with_selected_models, 
    detect_with_top_models,
    detect_ai_text,
    is_ai_generated,
    get_available_models as get_detection_models,
    get_ai_lines,
    get_ai_sentences,
    highlight_ai_text
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from nltk.tokenize import sent_tokenize as _nltk_sent_tokenize
except Exception:
    _nltk_sent_tokenize = None


def split_sentences(text: str) -> List[str]:
    """Single NLTK entry point — avoids repeated imports inside hot paths."""
    if not text or not str(text).strip():
        return []
    if _nltk_sent_tokenize:
        return _nltk_sent_tokenize(text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


@functools.lru_cache(maxsize=8192)
def _wordnet_synonyms_cached(word_lower: str, wn_pos: str) -> Tuple[str, ...]:
    try:
        from nltk.corpus import wordnet as wn
    except Exception:
        return tuple()

    syns: List[str] = []
    for synset in wn.synsets(word_lower, pos=wn_pos)[:4]:
        for lemma in synset.lemmas():
            s = lemma.name().replace("_", " ").lower()
            if s == word_lower:
                continue
            if not s.isalpha():
                continue
            syns.append(s)
    uniq = list(dict.fromkeys(syns))
    return tuple(uniq[:12])


# Initialize Flask app
app = Flask(__name__)
CORS(app, origins="*")

def clean_final_text(text: str) -> str:
    """
    Clean the final text by:
    1. Removing spaces that appear before punctuation
    """
    if not text:
        return text
    
    cleaned_text = text

    # Remove spaces before punctuation
    result = []
    for i, char in enumerate(cleaned_text):
        if char in ',.;:!?' and i > 0 and result and result[-1] == ' ':
            result.pop()  # Remove trailing space
        result.append(char)
    cleaned_text = ''.join(result)
    
    return cleaned_text


def _text_to_pdf_bytes(text: str) -> bytes:
    """Generate a simple PDF from plain text and return raw bytes."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=11)

    # Preserve line breaks and wrap long lines automatically
    for line in text.splitlines():
        # FPDF's multi_cell handles wrapping
        pdf.multi_cell(0, 8, line)

    # Return PDF as byte string
    return pdf.output(dest="S").encode('latin-1', errors='replace')

class HumanizerService:
    """Main orchestrator service that combines paraphrasing and rewriting"""
    def __init__(self):
        load_dotenv()
        logger.info("HumanizerService initialized")

    # ---------------------------------------------------------------------
    # NEW HUMANIZATION PIPELINE (Steps 1–8 as specified by user)
    # ---------------------------------------------------------------------

    _AI_SIGNATURE_REPLACEMENTS = [
        ("it is worth noting that", ""),
        ("it is important to note", ""),
        ("utilize", "use"),
        ("leverage", "use"),
        ("delve", "explore"),
        ("furthermore", "also"),
        ("moreover", "on top of that"),
        ("in conclusion", "to wrap up"),
        ("comprehensive", "full"),
        ("crucial", "important"),
        ("notably", ""),
    ]

    _FILLER_POOL = [
        "Honestly, ",
        "To be fair, ",
        "The thing is, ",
        "In practice, ",
        "Worth noting — ",
        "Interestingly, ",
        "What's cool is that ",
        "Simply put, ",
        "Real talk — ",
    ]

    _CONTRACTIONS = [
        ("do not", "don't"),
        ("it is", "it's"),
        ("they are", "they're"),
        ("we are", "we're"),
        ("you are", "you're"),
        ("is not", "isn't"),
        ("are not", "aren't"),
        ("does not", "doesn't"),
        ("I am", "I'm"),
        ("have not", "haven't"),
        ("will not", "won't"),
        ("cannot", "can't"),
    ]

    def parse_blocks(self, text: str) -> List[Dict[str, str]]:
        """
        STEP 1 — PARSE INPUT INTO BLOCKS (exact spec)
        - Split by "\\n", strip each line
        - If line has ≤8 words AND no ending punctuation (.!?:) → heading
        - Else → paragraph
        - Return list of {type, text}
        """
        blocks: List[Dict[str, str]] = []
        for raw_line in text.split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            word_count = len(line.split())
            has_end_punct = bool(line) and line[-1] in ".!?:"
            block_type = "heading" if (word_count <= 8 and not has_end_punct) else "paragraph"
            blocks.append({"type": block_type, "text": line})
        return blocks

    def _replace_ai_signature_words(self, text: str) -> str:
        """
        STEP 3 — REMOVE AI SIGNATURE WORDS (always)
        """
        out = text
        for src, dst in self._AI_SIGNATURE_REPLACEMENTS:
            # phrase-level, case-insensitive, word-boundary where possible
            pattern = r"\b" + re.escape(src) + r"\b"
            out = re.sub(pattern, dst, out, flags=re.IGNORECASE)
        # cleanup double spaces created by removals
        out = re.sub(r"\s{2,}", " ", out).strip()
        # cleanup spaces before punctuation
        out = re.sub(r"\s+([.,!?;:])", r"\1", out)
        return out

    def _replace_transitions(self, text: str) -> str:
        """
        Replace overly-formal transitions with more casual alternatives.
        (Style improvement; randomized per occurrence.)
        """
        transition_map = {
            "However": ["That said", "But", "Still", "Even so"],
            "Therefore": ["So", "Which means", "That's why"],
            "Additionally": ["Also", "On top of that", "Plus"],
            "In addition": ["Also", "And", "Plus"],
            "Consequently": ["So", "As a result", "Which is why"],
            "Nevertheless": ["Still", "Even so", "But"],
            "Specifically": ["In particular", "Especially", "To be exact"],
            "Regarding": ["As for", "When it comes to", "About"],
            "Primarily": ["Mainly", "Mostly", "For the most part"],
            "Subsequently": ["After that", "Then", "Later"],
            "Notably": ["Interestingly", "Worth saying", ""],
            "Thus": ["So", "That's why", "Which means"],
            "Hence": ["So", "That's why"],
            "Whereas": ["While", "But"],
            "Albeit": ["Though", "Even if"],
        }

        out = text
        for formal, options in transition_map.items():
            def _repl(m):
                choice = random.choice(options)
                # Preserve capitalization if match is title-cased
                if m.group(0)[0].isupper() and choice:
                    return choice
                return choice.lower() if choice else ""

            out = re.sub(r"\b" + re.escape(formal) + r"\b", _repl, out)

        out = re.sub(r"\s{2,}", " ", out).strip()
        out = re.sub(r"\s+([.,!?;:])", r"\1", out)
        return out

    def _apply_burstiness(self, sentences: List[str]) -> List[str]:
        result: List[str] = []
        for i, sent in enumerate(sentences):
            s = sent.strip()
            if not s:
                continue
            words = s.split()

            # Every 3rd sentence: short & punchy
            if i % 3 == 2 and len(words) > 10:
                s = " ".join(words[:8]).rstrip(".!?") + "."

            # Every 4th sentence: longer with a small extension
            if i % 4 == 0 and len(s.split()) < 20:
                extensions = [
                    " — and that's something worth paying attention to",
                    ", which makes a bigger difference than most people realize",
                    ", and honestly, it changes everything about the approach",
                    " — at least in most real-world situations",
                    ", though it really depends on the context",
                ]
                s = s.rstrip(".!?") + random.choice(extensions) + "."

            result.append(s)
        # Ensure at least one short and one long sentence when possible
        if len(result) >= 3:
            lengths = [len(s.split()) for s in result]
            if not any(l <= 10 for l in lengths):
                j = min(2, len(result) - 1)
                w = result[j].split()
                if len(w) > 10:
                    result[j] = " ".join(w[:8]).rstrip(".!?") + "."
            if not any(l >= 22 for l in lengths):
                j = 0
                w = result[j].split()
                if len(w) < 22:
                    result[j] = result[j].rstrip(".!?") + ", which makes the whole thing feel a bit more real in practice."
        return result

    def _inject_human_voice(self, sentences: List[str]) -> List[str]:
        HEDGE_STARTERS = [
            "From what I can tell, ",
            "In most cases, ",
            "Generally speaking, ",
            "More often than not, ",
            "If you think about it, ",
            "At least in my experience, ",
            "As far as I know, ",
            "Realistically, ",
        ]
        OPINION_MARKERS = [
            " — which actually makes a lot of sense",
            ", and I think that's the key point here",
            ", if you ask me",
            " — pretty straightforward when you break it down",
            ", which is easy to overlook",
        ]
        UNCERTAINTY_PHRASES = [
            "probably",
            "likely",
            "seems like",
            "appears to",
            "in most cases",
            "typically",
            "generally",
        ]

        result: List[str] = []
        for sent in sentences:
            s = sent
            if random.random() < 0.20 and not any(s.startswith(h) for h in HEDGE_STARTERS) and s:
                s = random.choice(HEDGE_STARTERS) + s[0].lower() + s[1:]

            if random.random() < 0.15 and s.endswith("."):
                s = s[:-1] + random.choice(OPINION_MARKERS) + "."

            if random.random() < 0.10 and " is " in s:
                s = s.replace(" is ", f" {random.choice(UNCERTAINTY_PHRASES)} is ", 1)

            result.append(s)
        return result

    def _add_natural_sentence_starters(self, sentences: List[str]) -> List[str]:
        HUMAN_STARTERS = ["And ", "But ", "So ", "Now, ", "Look — "]
        result: List[str] = []
        for i, sent in enumerate(sentences):
            s = sent
            if i > 0 and random.random() < 0.12 and s:
                starter = random.choice(HUMAN_STARTERS)
                s = starter + s[0].lower() + s[1:]
            result.append(s)
        # Guarantee at least one "human starter" when we have multiple sentences
        if len(result) >= 2 and not any(s.startswith(("And ", "But ", "So ", "Now,", "Look")) for s in result):
            s = result[1]
            if s:
                result[1] = "But " + s[0].lower() + s[1:]
        return result

    def _humanize_punctuation(self, text: str) -> str:
        sentences = split_sentences(text)

        result: List[str] = []
        for sent in sentences:
            s = sent
            r = random.random()

            if r < 0.15 and ", " in s:
                s = s.replace(", ", " — ", 1)
            elif r < 0.25 and len(s.split()) > 12:
                words = s.split()
                mid = len(words) // 2
                aside_options = [
                    "(which is more common than you'd think)",
                    "(and this is important)",
                    "(at least in most scenarios)",
                    "(worth keeping in mind)",
                ]
                words.insert(mid, random.choice(aside_options))
                s = " ".join(words)
            elif r < 0.33 and any(w in s.lower() for w in ["however", "although", "while"]):
                s = s.rstrip(".") + "..."

            result.append(s)
        out = " ".join(result)
        # Guarantee some punctuation variety if none was introduced
        if not any(p in out for p in ["—", "...", "("]):
            if ", " in out:
                out = out.replace(", ", " — ", 1)
            elif len(out.split()) > 14:
                out = out.rstrip(".") + " (worth keeping in mind)."
        return out

    def _disrupt_structure_paragraph(self, paragraph: str) -> str:
        sentences = split_sentences(paragraph)

        if len(sentences) >= 4:
            if random.random() < 0.30:
                last = sentences.pop()
                sentences.insert(1, last)

            afterthoughts = [
                "Then again, it really comes down to your specific situation.",
                "That said, there's no one-size-fits-all answer here.",
                "Either way, it's something to keep in mind.",
                "Of course, context matters more than anything else.",
                "But honestly, most people figure this out as they go.",
            ]
            if random.random() < 0.20:
                sentences.append(random.choice(afterthoughts))

        return " ".join(sentences)

    @staticmethod
    def _syllable_count(word: str) -> int:
        w = re.sub(r"[^a-z]", "", word.lower())
        if not w:
            return 0
        # Simple heuristic: vowel group count
        groups = re.findall(r"[aeiouy]+", w)
        count = len(groups)
        # Common silent-e adjustment
        if w.endswith("e") and count > 1:
            count -= 1
        return max(1, count)

    @staticmethod
    def _wordnet_pos_from_tag(tag: str) -> Optional[str]:
        # Only NOUN or VERB per requirements
        if tag.startswith("NN"):
            return "n"
        if tag.startswith("VB"):
            return "v"
        return None

    def _wordnet_synonyms(self, word: str, wn_pos: str) -> List[str]:
        return list(_wordnet_synonyms_cached(word.lower(), wn_pos))

    def _smart_synonym_replace_sentence(self, sentence: str) -> Tuple[str, int]:
        """
        STEP 4 — SMART SYNONYM REPLACEMENT (sentence-level)
        - POS tag with nltk
        - Replace NOUN↔NOUN or VERB↔VERB only
        - Skip proper nouns, <4 chars, numbers
        - Max 2 replacements per sentence
        - Prefer shorter/simpler synonyms (lower syllable count)
        """
        try:
            from nltk import pos_tag, word_tokenize
        except Exception:
            return sentence, 0

        ai_words = {src for (src, _dst) in self._AI_SIGNATURE_REPLACEMENTS}

        tokens = word_tokenize(sentence)
        try:
            tags = pos_tag(tokens)
        except LookupError:
            # Newer NLTK splits the tagger by language suffix.
            try:
                import nltk

                nltk.download("averaged_perceptron_tagger_eng", quiet=True)
                tags = pos_tag(tokens)
            except Exception:
                return sentence, 0

        replaced = 0
        new_tokens: List[str] = []

        for tok, tag in tags:
            if replaced >= 2:
                new_tokens.append(tok)
                continue

            lower = tok.lower()

            # Skip anything not purely alphabetic tokens (keeps punctuation intact)
            if not tok.isalpha():
                new_tokens.append(tok)
                continue

            # Skip numbers, short words
            if len(tok) < 4:
                new_tokens.append(tok)
                continue

            # Skip proper nouns
            if tag in ("NNP", "NNPS"):
                new_tokens.append(tok)
                continue

            # Skip AI signature list words (already handled in Step 3)
            if lower in ai_words:
                new_tokens.append(tok)
                continue

            wn_pos = self._wordnet_pos_from_tag(tag)
            if wn_pos not in ("n", "v"):
                new_tokens.append(tok)
                continue

            candidates = self._wordnet_synonyms(lower, wn_pos)
            if not candidates:
                new_tokens.append(tok)
                continue

            # prefer fewer syllables then shorter length
            candidates = sorted(
                candidates,
                key=lambda w: (self._syllable_count(w), len(w)),
            )
            best = candidates[0]

            # Preserve capitalization
            if tok[0].isupper():
                best = best.capitalize()

            if best != tok:
                new_tokens.append(best)
                replaced += 1
            else:
                new_tokens.append(tok)

        # Detokenize with minimal spacing fixes
        out = " ".join(new_tokens)
        out = re.sub(r"\s+([.,!?;:])", r"\1", out)
        out = re.sub(r"\s+'", "'", out)
        out = re.sub(r"'\s+", "'", out)
        return out, replaced

    def _inject_fillers_paragraph(self, paragraph: str) -> Tuple[str, int]:
        """
        STEP 5 — FILLER PHRASE INJECTION (paragraphs only)
        """
        sentences = split_sentences(paragraph)

        out_sents: List[str] = []
        last_injected = False
        injected_count = 0

        for s in sentences:
            s2 = s.strip()
            if not s2:
                continue
            should_inject = (random.random() < 0.25) and (not last_injected)
            if should_inject:
                filler = random.choice(self._FILLER_POOL)
                s2 = filler + (s2[0].lower() + s2[1:] if len(s2) > 1 else s2)
                injected_count += 1
                last_injected = True
            else:
                last_injected = False
            out_sents.append(s2)

        return " ".join(out_sents), injected_count

    def _add_contractions_text(self, text: str) -> str:
        """
        STEP 6 — ADD CONTRACTIONS (paragraphs only)
        """
        out = text
        for src, dst in self._CONTRACTIONS:
            out = re.sub(r"\b" + re.escape(src) + r"\b", dst, out, flags=re.IGNORECASE)
        out = re.sub(r"\s{2,}", " ", out).strip()
        return out

    def _vary_sentence_length_paragraph(self, paragraph: str) -> str:
        """
        STEP 7 — SENTENCE LENGTH VARIATION
        """
        sents = split_sentences(paragraph)

        # Pass 1: split long sentences
        split_sents: List[str] = []
        for s in sents:
            words = s.split()
            if len(words) > 30:
                for marker in [", and ", ", but ", ", so "]:
                    if marker in s:
                        left, right = s.split(marker, 1)
                        left = left.strip().rstrip(".!?")
                        right = right.strip()
                        if left and right:
                            split_sents.append(left + ".")
                            split_sents.append(right[0].upper() + right[1:] if right else right)
                            break
                else:
                    split_sents.append(s)
            else:
                split_sents.append(s)

        # Pass 2: merge ultra-short sentences with next
        merged: List[str] = []
        i = 0
        while i < len(split_sents):
            s = split_sents[i].strip()
            if len(s.split()) < 5 and i < len(split_sents) - 1:
                nxt = split_sents[i + 1].strip()
                if nxt:
                    merged_sent = s.rstrip(".!?") + ", " + (nxt[0].lower() + nxt[1:] if len(nxt) > 1 else nxt)
                    merged.append(merged_sent)
                    i += 2
                    continue
            merged.append(s)
            i += 1

        out = " ".join(merged)
        out = re.sub(r"\s{2,}", " ", out).strip()
        return out

    def _t5_paraphrase_paragraph_sentence_by_sentence(
        self, paragraph: str, model_name: Optional[str]
    ) -> Tuple[str, Optional[str]]:
        """
        STEP 2 — T5 PARAPHRASE (paragraphs only). Uses batched generation for throughput.
        """
        sentences = split_sentences(paragraph)
        if not sentences:
            return paragraph.strip(), None

        # Balanced quality vs speed (batched path merges these; sequential fallback uses same intent)
        gen_kwargs = {
            "max_length": 256,
            "num_beams": 4,
            "do_sample": True,
            "temperature": 0.88,
            "top_k": 50,
            "top_p": 0.92,
            "repetition_penalty": 2.5,
            "no_repeat_ngram_size": 3,
            "early_stopping": True,
            "length_penalty": 1.15,
        }

        out_sents, _err = paraphrase_sentences_batched(
            sentences, model_name_param=model_name, generation_kwargs=gen_kwargs
        )
        merged: List[str] = []
        for orig, par in zip(sentences, out_sents):
            p = (par or "").strip()
            merged.append(p if p else orig.strip())
        return " ".join(merged).strip(), None

    def _humanize_blocks(
        self, text: str, model_name: Optional[str], use_paraphrasing: bool = True
    ) -> Tuple[str, str, Dict]:
        """
        Returns (step1_output, step2_output, stats)
        """
        blocks = self.parse_blocks(text)

        # Step 2 (paragraphs only) -> Step 1 output (skip T5 when paraphrasing off — big win)
        step1_blocks: List[Dict[str, str]] = []
        for b in blocks:
            if b["type"] == "heading":
                step1_blocks.append(b)  # headings unchanged
                continue
            if use_paraphrasing:
                paraphrased, _err = self._t5_paraphrase_paragraph_sentence_by_sentence(b["text"], model_name)
            else:
                paraphrased = b["text"]
            step1_blocks.append({"type": "paragraph", "text": paraphrased})

        step1_output = "\n\n".join(b["text"] for b in step1_blocks)

        # Steps 3+ apply to paragraphs only
        synonym_replacements_total = 0
        fillers_injected_total = 0

        step2_blocks: List[Dict[str, str]] = []
        for b in step1_blocks:
            if b["type"] == "heading":
                # Headings: exactly unchanged (from original parsed heading)
                step2_blocks.append(b)
                continue

            p = b["text"]

            # Step 3: remove AI signature words
            p = self._replace_ai_signature_words(p)

            # Step 4: replace transitions
            p = self._replace_transitions(p)

            # Step 5: smart synonym replacement (sentence-by-sentence)
            sents = split_sentences(p)

            new_sents: List[str] = []
            for s in sents:
                s2, replaced = self._smart_synonym_replace_sentence(s)
                synonym_replacements_total += replaced
                new_sents.append(s2)
            sents = new_sents

            # Step 6: contractions
            sents = [self._add_contractions_text(s) for s in sents]

            # Step 7: burstiness
            sents = self._apply_burstiness(sents)

            # Step 8: human voice injection
            sents = self._inject_human_voice(sents)

            # Step 9: natural sentence starters
            sents = self._add_natural_sentence_starters(sents)

            p = " ".join(sents).strip()

            # Step 10: punctuation humanizer
            p = self._humanize_punctuation(p)

            # Step 11: structural disruption (paragraph-level)
            p = self._disrupt_structure_paragraph(p)

            # Step 12: filler injection (no consecutive)
            p, injected = self._inject_fillers_paragraph(p)
            fillers_injected_total += injected

            # Keep a light sentence-length variation pass (helps rhythm)
            p = self._vary_sentence_length_paragraph(p)

            step2_blocks.append({"type": "paragraph", "text": p})

        step2_output = "\n\n".join(b["text"] for b in step2_blocks)

        stats = {
            "original_length": len(text),
            "paraphrased_length": len(step1_output),
            "final_length": len(step2_output),
            "step1_length": len(step1_output),
            "step2_length": len(step2_output),
            "step1_output": step1_output,
            "step2_output": step2_output,
            "fillers_injected": fillers_injected_total,
            "synonyms_replaced": synonym_replacements_total,
            "paraphrasing_used": use_paraphrasing,
            "blocks": {
                "total": len(blocks),
                "headings": sum(1 for b in blocks if b["type"] == "heading"),
                "paragraphs": sum(1 for b in blocks if b["type"] == "paragraph"),
            },
        }

        return step1_output, step2_output, stats
    def humanize_text(
        self, 
        text: str, 
        use_paraphrasing: bool = False,
        use_enhanced_rewriting: bool = True,
        paraphrase_model: str = None,
        add_variations: bool = True,
        variation_intensity: float = 0.85,
        add_mistakes: bool = False,
        mistakes_intensity: float = 0.2
    ) -> Tuple[str, Dict]:
        try:
            # New required behavior: always produce a distinct step1_output and step2_output
            model_to_use = paraphrase_model or get_current_model()

            step1_output, step2_output, stats = self._humanize_blocks(
                text, model_to_use, use_paraphrasing=use_paraphrasing
            )

            # Final cleanup (keeps headings intact, only normalizes spacing/punctuation)
            final_text = clean_final_text(step2_output)
            stats["final_length"] = len(final_text)
            stats["length_change"] = stats["final_length"] - stats["original_length"]
            stats["model_used"] = model_to_use or get_current_model()

            return final_text, stats

        except Exception as e:
            logger.error(f"❌ Error in humanization pipeline: {str(e)}")
            return text, {"original_length": len(text), "final_length": len(text), "error": str(e)}

# Initialize services
humanizer_service = HumanizerService()
ai_detector = AITextDetector()

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    current_model = get_current_model()
    return jsonify({
        "status": "healthy",
        "message": "🚀 Humanize AI Server is running!",
        "features": {
            "paraphrasing": current_model is not None,
            "current_model": current_model,
            "available_models": get_available_models(),
            "local_refinement": True,
            "synonym_support": True,
            "device": get_device_info()
        }
    })

@app.route('/health', methods=['GET'])
def detailed_health():
    """Detailed health check with system information - matches frontend expectations"""
    current_model = get_current_model()
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "features": {
            "paraphrasing_available": current_model is not None,
            "current_paraphrase_model": current_model,
            "local_processing": True,
            "device": get_device_info()
        },
        "version": "3.0.0"
    })

@app.route('/models', methods=['GET'])
def get_models():
    """Get available paraphrasing models - matches frontend expectations"""
    return jsonify({
        "available_models": get_available_models(),
        "current_model": get_current_model(),
        "device": get_device_info()
    })

@app.route('/load_model', methods=['POST'])
def load_model_endpoint():
    """Load a specific paraphrasing model - matches frontend expectations"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        model_name = data.get('model_name', '').strip()
        
        if not model_name:
            return jsonify({"error": "No model_name provided"}), 400
        
        available_models = get_available_models()
        if model_name not in available_models:
            return jsonify({
                "error": f"Model {model_name} not supported",
                "available_models": available_models
            }), 400
        
        success, error = load_model(model_name)
        if success:
            return jsonify({
                "message": f"Successfully loaded {model_name}",
                "current_model": get_current_model(),
                "success": True
            })
        else:
            return jsonify({"error": error or f"Failed to load model {model_name}"}), 500
        
    except Exception as e:
        logger.error(f"Error in /load_model: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/humanize', methods=['POST'])
def humanize_handler():
    """Main endpoint for humanizing AI-generated text using T5 models with human variations"""
    try:
        logger.info("Humanize request received")
        
        # Validate request
        if not request.is_json:
            logger.error("Invalid content type")
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        data = request.get_json()
        if not data or "text" not in data:
            logger.error("Missing text field in request")
            return jsonify({"error": "Text field is required"}), 400
        
        text = data.get("text", "").strip()
        if not text:
            logger.error("Empty text received")
            return jsonify({"error": "Text cannot be empty"}), 400
        
        # Validate text length
        if len(text) < 10:
            return jsonify({"error": "Text must be at least 10 characters long"}), 400
        
        if len(text) > 50000:
            return jsonify({"error": "Text must be less than 50000 characters"}), 400
        
        # Extract options - match frontend parameter names
        use_paraphrasing = data.get("paraphrasing", False)  # Default to False for speed
        use_enhanced = data.get("enhanced", True)  # Default to True for better results
        paraphrase_model = data.get("model", None)
        
        # Get variation settings
        add_variations = data.get("add_variations", True)
        variation_intensity = data.get("variation_intensity", 0.85)

        # Mistake settings
        add_mistakes = data.get("add_mistakes", False)
        mistakes_intensity = data.get("mistakes_intensity", 0.2)
        
        # Validate variation intensity
        try:
            variation_intensity = float(variation_intensity)
            variation_intensity = max(0.0, min(1.0, variation_intensity))
        except (ValueError, TypeError):
            variation_intensity = 0.5

        # Validate mistakes intensity
        try:
            mistakes_intensity = float(mistakes_intensity)
            mistakes_intensity = max(0.0, min(1.0, mistakes_intensity))
        except (ValueError, TypeError):
            mistakes_intensity = 0.2
        
        logger.info(f"Using T5 model: {paraphrase_model}, paraphrasing: {use_paraphrasing}, enhanced: {use_enhanced}, variations: {add_variations}, intensity: {variation_intensity}")
        
        # Process text through humanization pipeline
        humanized_text, stats = humanizer_service.humanize_text(
            text=text,
            use_paraphrasing=use_paraphrasing,
            use_enhanced_rewriting=use_enhanced,
            paraphrase_model=paraphrase_model,
            add_variations=add_variations,
            variation_intensity=variation_intensity,
            add_mistakes=add_mistakes,
            mistakes_intensity=mistakes_intensity
        )
        
        # Ensure we return something
        if not humanized_text or not humanized_text.strip():
            humanized_text = text
        
        response = {
            "humanized_text": humanized_text,
            "step1_output": stats.get("step1_output", ""),
            "step2_output": stats.get("step2_output", humanized_text),
            "step1_char_count": len(stats.get("step1_output", "")),
            "step2_char_count": len(stats.get("step2_output", humanized_text)),
            "success": True,
            "statistics": stats,
        }
        
        logger.info(f"Successfully processed text: {stats['original_length']} -> {stats.get('final_length', len(humanized_text))} chars")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "success": False
        }), 500


@app.route('/humanize_file', methods=['POST'])
def humanize_file_handler():
    """Endpoint to upload a .txt file, humanize it, and return a PDF."""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "File is required"}), 400

        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Only accept plain text files
        content_type = file.content_type or ''
        if 'text' not in content_type and not file.filename.lower().endswith('.txt'):
            return jsonify({"error": "Only plain text (.txt) files are supported"}), 400

        raw_text = file.read().decode('utf-8', errors='replace')
        text = raw_text.strip()
        if not text:
            return jsonify({"error": "Uploaded file is empty"}), 400

        # Extract options (similar to /humanize)
        use_paraphrasing = request.form.get('paraphrasing', 'true').lower() in ('1', 'true', 'yes')
        use_enhanced = request.form.get('enhanced', 'false').lower() in ('1', 'true', 'yes')
        paraphrase_model = request.form.get('model', None)

        humanized_text, stats = humanizer_service.humanize_text(
            text=text,
            use_paraphrasing=use_paraphrasing,
            use_enhanced_rewriting=use_enhanced,
            paraphrase_model=paraphrase_model
        )

        if not humanized_text or not humanized_text.strip():
            humanized_text = text

        pdf_bytes = _text_to_pdf_bytes(humanized_text)
        pdf_stream = io.BytesIO(pdf_bytes)
        pdf_stream.seek(0)

        filename = f"humanized_{os.path.splitext(file.filename)[0]}.pdf"
        return send_file(
            pdf_stream,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error in /humanize_file: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


# Additional endpoints for direct access
@app.route('/paraphrase', methods=['POST'])
def paraphrase_handler():
    """Direct paraphrasing endpoint"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        model_name = data.get('model_name', None)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        paraphrased_text, error = paraphrase_text(text, model_name)
        
        if error:
            return jsonify({"error": error}), 500
        
        return jsonify({
            'paraphrased': paraphrased_text,
            'success': True,
            'model_used': get_current_model(),
            'original_text': text
        })

    except Exception as e:
        logger.error(f"Error in /paraphrase: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/synonym', methods=['POST'])
def synonym_handler():
    """Get synonym for a word"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        word = data.get('word', '').strip()
        
        if not word:
            return jsonify({"error": "No word provided"}), 400
        
        synonym, error = get_synonym(word)
        
        if error:
            return jsonify({"error": error}), 400
        
        return jsonify({
            'synonym': synonym,
            'original_word': word,
            'success': True
        })

    except Exception as e:
        logger.error(f"Error in /synonym: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/refine', methods=['POST'])
def refine_handler():
    """Refine text using NLP tools"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        refined_text, error = refine_text(text)
        
        if error:
            return jsonify({"error": error}), 500
        
        return jsonify({
            'refined_text': refined_text,
            'original_text': text,
            'success': True
        })

    except Exception as e:
        logger.error(f"Error in /refine: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/paraphrase_only', methods=['POST'])
def paraphrase_only_handler():
    """Paraphrase text without rewriting - for step-by-step processing"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        model_name = data.get('model', None)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 10:
            return jsonify({"error": "Text must be at least 10 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 5000 to 50000
            return jsonify({"error": "Text must be less than 50000 characters"}), 400
        
        paraphrased_text, error = paraphrase_text(text, model_name)
        
        if error:
            return jsonify({"error": error}), 500
        
        # Clean up common formatting issues
        if paraphrased_text and paraphrased_text.startswith(": "):
            paraphrased_text = paraphrased_text[2:]
        
        return jsonify({
            'paraphrased_text': paraphrased_text or text,
            'success': True,
            'model_used': get_current_model(),
            'original_text': text,
            'statistics': {
                'original_length': len(text),
                'paraphrased_length': len(paraphrased_text) if paraphrased_text else len(text),
                'length_change': (len(paraphrased_text) if paraphrased_text else len(text)) - len(text),
                'model_used': get_current_model(),
                'paraphrasing_used': True
            }
        })

    except Exception as e:
        logger.error(f"Error in /paraphrase_only: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/rewrite_only', methods=['POST'])
def rewrite_only_handler():
    """Rewrite text without paraphrasing - for step-by-step processing"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        enhanced = data.get('enhanced', False)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        rewritten_text, error = rewrite_text(text, enhanced=enhanced)
        
        if error:
            return jsonify({"error": error}), 500
        
        # Clean the final rewritten text
        rewritten_text = clean_final_text(rewritten_text or text)
        
        return jsonify({
            'rewritten_text': rewritten_text,
            'success': True,
            'original_text': text,
            'statistics': {
                'original_length': len(text),
                'rewritten_length': len(rewritten_text),
                'length_change': len(rewritten_text) - len(text),
                'enhanced_rewriting_used': enhanced,
                'text_cleaning_applied': True
            }
        })

    except Exception as e:
        logger.error(f"Error in /rewrite_only: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/paraphrase_multi', methods=['POST'])
def paraphrase_multi_handler():
    """Paraphrase text through 2 best models in PIPELINE (each model processes previous output)"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 10:
            return jsonify({"error": "Text must be at least 10 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 5000 to 50000
            return jsonify({"error": "Text must be less than 50000 characters"}), 400
        
        # Define the 2 best models (prioritize specialized paraphrasing models)
        best_models = [
            "humarin/chatgpt_paraphraser_on_T5_base",
            "Vamsi/T5_Paraphrase_Paws"
        ]
        
        # Filter available models
        available_models = get_available_models()
        models_to_use = [model for model in best_models if model in available_models]
        
        # Fallback to first 2 available models if best models aren't available
        if len(models_to_use) < 2:
            models_to_use = available_models[:2]
        
        if not models_to_use:
            return jsonify({"error": "No models available for paraphrasing"}), 500
        
        results = []
        errors = []
        current_text = text  # Start with original text
        
        for i, model_name in enumerate(models_to_use):
            try:
                logger.info(f"Pipeline step {i+1}: Paraphrasing with model {model_name}")
                paraphrased_text, error = paraphrase_text(current_text, model_name)
                
                if error:
                    errors.append(f"Step {i+1} ({model_name}): {error}")
                    # On error, continue with current text (don't break the pipeline)
                    paraphrased_text = current_text
                
                # Clean up common formatting issues
                if paraphrased_text and paraphrased_text.startswith(": "):
                    paraphrased_text = paraphrased_text[2:]
                
                # If paraphrasing failed, use current text
                if not paraphrased_text or not paraphrased_text.strip():
                    paraphrased_text = current_text
                
                results.append({
                    "step": i + 1,
                    "model": model_name,
                    "input_text": current_text,
                    "output_text": paraphrased_text,
                    "input_length": len(current_text),
                    "output_length": len(paraphrased_text),
                    "length_change": len(paraphrased_text) - len(current_text),
                    "success": not error
                })
                
                # Update current_text for next iteration (PIPELINE EFFECT)
                current_text = paraphrased_text
                
            except Exception as e:
                logger.error(f"Error with model {model_name}: {str(e)}")
                errors.append(f"Step {i+1} ({model_name}): {str(e)}")
                # Continue with current text on error
                results.append({
                    "step": i + 1,
                    "model": model_name,
                    "input_text": current_text,
                    "output_text": current_text,  # No change on error
                    "input_length": len(current_text),
                    "output_length": len(current_text),
                    "length_change": 0,
                    "success": False,
                    "error": str(e)
                })
        
        return jsonify({
            "pipeline_results": results,
            "success": True,
            "original_text": text,
            "final_text": current_text,  # Final output after all pipeline steps
            "models_used": [r["model"] for r in results],
            "errors": errors if errors else None,
            "statistics": {
                "pipeline_steps": len(results),
                "successful_steps": len([r for r in results if r.get("success", False)]),
                "failed_steps": len([r for r in results if not r.get("success", False)]),
                "original_length": len(text),
                "final_length": len(current_text),
                "total_length_change": len(current_text) - len(text),
                "pipeline_mode": "sequential"
            }
        })

    except Exception as e:
        logger.error(f"Error in /paraphrase_multi: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/paraphrase_all', methods=['POST'])
def paraphrase_all_handler():
    """Paraphrase text through ALL available models in PIPELINE (each model processes previous output)"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 10:
            return jsonify({"error": "Text must be at least 10 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 5000 to 50000
            return jsonify({"error": "Text must be less than 50000 characters"}), 400
        
        available_models = get_available_models()
        
        if not available_models:
            return jsonify({"error": "No models available for paraphrasing"}), 500
        
        results = []
        errors = []
        current_text = text  # Start with original text
        processing_time_start = time.time()
        
        for i, model_name in enumerate(available_models):
            model_start_time = time.time()
            try:
                logger.info(f"Pipeline step {i+1}/{len(available_models)}: Paraphrasing with model {model_name}")
                paraphrased_text, error = paraphrase_text(current_text, model_name)
                
                model_time = time.time() - model_start_time
                
                if error:
                    errors.append(f"Step {i+1} ({model_name}): {error}")
                    # On error, continue with current text (don't break the pipeline)
                    paraphrased_text = current_text
                
                # Clean up common formatting issues
                if paraphrased_text and paraphrased_text.startswith(": "):
                    paraphrased_text = paraphrased_text[2:]
                
                # If paraphrasing failed, use current text
                if not paraphrased_text or not paraphrased_text.strip():
                    paraphrased_text = current_text
                
                results.append({
                    "step": i + 1,
                    "model": model_name,
                    "input_text": current_text,
                    "output_text": paraphrased_text,
                    "input_length": len(current_text),
                    "output_length": len(paraphrased_text),
                    "length_change": len(paraphrased_text) - len(current_text),
                    "processing_time": round(model_time, 2),
                    "success": not error
                })
                
                # Update current_text for next iteration (PIPELINE EFFECT)
                current_text = paraphrased_text
                
            except Exception as e:
                model_time = time.time() - model_start_time
                logger.error(f"Error with model {model_name}: {str(e)}")
                errors.append(f"Step {i+1} ({model_name}): {str(e)}")
                
                # Continue with current text on error
                results.append({
                    "step": i + 1,
                    "model": model_name,
                    "input_text": current_text,
                    "output_text": current_text,  # No change on error
                    "input_length": len(current_text),
                    "output_length": len(current_text),
                    "length_change": 0,
                    "processing_time": round(model_time, 2),
                    "success": False,
                    "error": str(e)
                })
        
        total_processing_time = time.time() - processing_time_start
        successful_steps = [r for r in results if r.get("success", False)]
        
        return jsonify({
            "pipeline_results": results,
            "successful_steps": successful_steps,
            "success": len(successful_steps) > 0,
            "original_text": text,
            "final_text": current_text,  # Final output after all pipeline steps
            "models_attempted": available_models,
            "errors": errors if errors else None,
            "statistics": {
                "pipeline_steps": len(results),
                "successful_steps": len(successful_steps),
                "failed_steps": len(results) - len(successful_steps),
                "original_length": len(text),
                "final_length": len(current_text),
                "total_length_change": len(current_text) - len(text),
                "total_processing_time": round(total_processing_time, 2),
                "average_processing_time": round(total_processing_time / len(available_models), 2) if available_models else 0,
                "pipeline_mode": "sequential"
            }
        })

    except Exception as e:
        logger.error(f"Error in /paraphrase_all: {str(e)}")
        return jsonify({"error": str(e)}), 500

# AI detection endpoints
@app.route('/detect', methods=['POST'])
def detect_ai_handler():
    """Main AI detection endpoint using ensemble method with enhanced options"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        threshold = data.get('threshold', 0.7)
        models = data.get('models', None)  # Optional specific models
        use_all_models = data.get('use_all_models', False)  # New option
        top_n = data.get('top_n', None)  # New option for top N models
        criteria = data.get('criteria', 'performance')  # New option for model selection criteria
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 20:
            return jsonify({"error": "Text must be at least 20 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 10000 to 50000
            return jsonify({"error": "Text must be less than 50,000 characters"}), 400
        
        # Get detection results based on options
        if use_all_models:
            result = detect_with_all_models(text)
        elif top_n and isinstance(top_n, int) and top_n > 0:
            result = detect_with_top_models(text, n=top_n, criteria=criteria)
        elif models and isinstance(models, list):
            result = detect_with_selected_models(text, models)
        else:
            # Default ensemble method (reuse cached global detector)
            result = ai_detector.detect_ensemble(text, models=models)
        
        # Add simple classification
        is_ai = result['ensemble_ai_probability'] > threshold
        
        response = {
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "is_ai_generated": is_ai,
            "ai_probability": result['ensemble_ai_probability'],
            "human_probability": result['ensemble_human_probability'],
            "prediction": result['prediction'],
            "confidence": result['confidence'],
            "threshold_used": threshold,
            "models_used": result['models_used'],
            "individual_results": result['individual_results'],
            "text_length": len(text),
            "detection_method": "all_models" if use_all_models else f"top_{top_n}" if top_n else "selected" if models else "default",
            "success": True
        }
        
        logger.info(f"AI detection completed: {result['prediction']} ({result['ensemble_ai_probability']:.3f})")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in AI detection: {str(e)}")
        return jsonify({
            "error": "Failed to analyze text",
            "success": False
        }), 500


@app.route('/detect_ai_text', methods=['POST', 'OPTIONS'])
def detect_ai_text_alias():
    """Alias endpoint to support frontend compatibility: delegates to /detect handler."""
    # Delegate to the existing handler which reads from `request`.
    try:
        return detect_ai_handler()
    except Exception as e:
        logger.error(f"Error in /detect_ai_text alias: {str(e)}")
        return jsonify({"error": "Detection alias failed", "success": False}), 500

@app.route('/detect_all_models', methods=['POST'])
def detect_all_models_handler():
    """Detect AI text using ALL available models"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        threshold = data.get('threshold', 0.7)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 20:
            return jsonify({"error": "Text must be at least 20 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 10000 to 50000
            return jsonify({"error": "Text must be less than 50,000 characters"}), 400
        
        # Use all available models
        result = detect_with_all_models(text)
        is_ai = result['ensemble_ai_probability'] > threshold
        
        response = {
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "is_ai_generated": is_ai,
            "ai_probability": result['ensemble_ai_probability'],
            "human_probability": result['ensemble_human_probability'],
            "prediction": result['prediction'],
            "confidence": result['confidence'],
            "threshold_used": threshold,
            "models_used": result['models_used'],
            "individual_results": result['individual_results'],
            "total_models_used": len(result['models_used']),
            "detection_method": "all_models",
            "text_length": len(text),
            "success": True
        }
        
        logger.info(f"All models detection: {result['prediction']} with {len(result['models_used'])} models")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in all models detection: {str(e)}")
        return jsonify({
            "error": "Failed to analyze text with all models",
            "success": False
        }), 500

@app.route('/detect_selected', methods=['POST'])
def detect_selected_models_handler():
    """Detect AI text using specific selected models"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        models = data.get('models', [])
        threshold = data.get('threshold', 0.7)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if not models or not isinstance(models, list):
            return jsonify({"error": "Models list is required"}), 400
        
        if len(text) < 20:
            return jsonify({"error": "Text must be at least 20 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 10000 to 50000
            return jsonify({"error": "Text must be less than 50,000 characters"}), 400
        
        # Use selected models
        result = detect_with_selected_models(text, models)
        is_ai = result['ensemble_ai_probability'] > threshold
        
        response = {
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "is_ai_generated": is_ai,
            "ai_probability": result['ensemble_ai_probability'],
            "human_probability": result['ensemble_human_probability'],
            "prediction": result['prediction'],
            "confidence": result['confidence'],
            "threshold_used": threshold,
            "models_requested": models,
            "models_used": result['models_used'],
            "individual_results": result['individual_results'],
            "detection_method": "selected_models",
            "text_length": len(text),
            "success": True
        }
        
        logger.info(f"Selected models detection: {result['prediction']} with models {result['models_used']}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in selected models detection: {str(e)}")
        return jsonify({
            "error": "Failed to analyze text with selected models",
            "success": False
        }), 500

@app.route('/detect_top_models', methods=['POST'])
def detect_top_models_handler():
    """Detect AI text using top N models based on criteria"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        n = data.get('n', 3)
        criteria = data.get('criteria', 'performance')
        threshold = data.get('threshold', 0.7)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if not isinstance(n, int) or n < 1 or n > 8:
            return jsonify({"error": "n must be an integer between 1 and 8"}), 400
        
        if criteria not in ['performance', 'speed', 'accuracy']:
            return jsonify({"error": "criteria must be 'performance', 'speed', or 'accuracy'"}), 400
        
        if len(text) < 20:
            return jsonify({"error": "Text must be at least 20 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 10000 to 50000
            return jsonify({"error": "Text must be less than 50,000 characters"}), 400
        
        # Use top N models
        result = detect_with_top_models(text, n=n, criteria=criteria)
        is_ai = result['ensemble_ai_probability'] > threshold
        
        response = {
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "is_ai_generated": is_ai,
            "ai_probability": result['ensemble_ai_probability'],
            "human_probability": result['ensemble_human_probability'],
            "prediction": result['prediction'],
            "confidence": result['confidence'],
            "threshold_used": threshold,
            "models_used": result['models_used'],
            "individual_results": result['individual_results'],
            "selection_criteria": criteria,
            "top_n": n,
            "detection_method": f"top_{n}_{criteria}",
            "text_length": len(text),
            "success": True
        }
        
        logger.info(f"Top {n} {criteria} models detection: {result['prediction']}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in top models detection: {str(e)}")
        return jsonify({
            "error": "Failed to analyze text with top models",
            "success": False
        }), 500

@app.route('/detect_lines', methods=['POST'])
def detect_lines_handler():
    """Detect which specific lines in text are AI-generated"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        threshold = data.get('threshold', 0.6)
        min_line_length = data.get('min_line_length', 20)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 50:
            return jsonify({"error": "Text must be at least 50 characters long for line detection"}), 400
        
        if len(text) > 15000:
            return jsonify({"error": "Text must be less than 15,000 characters for line detection"}), 400
        
        # Detect AI lines (reuse cached global detector)
        result = ai_detector.detect_ai_lines(text, threshold, min_line_length)
        
        response = {
            "ai_detected_lines": result['ai_detected_lines'],
            "human_lines": result['human_lines'],
            "line_analysis": result['line_analysis'],
            "statistics": result['statistics'],
            "threshold_used": result['threshold_used'],
            "min_line_length": min_line_length,
            "text_length": len(text),
            "success": True
        }
        
        logger.info(f"Line detection: {result['statistics']['ai_generated_lines']}/{result['statistics']['total_lines_analyzed']} lines detected as AI")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in line detection: {str(e)}")
        return jsonify({
            "error": "Failed to detect AI lines",
            "success": False
        }), 500

@app.route('/detect_sentences', methods=['POST'])
def detect_sentences_handler():
    """Detect which specific sentences in text are AI-generated"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        threshold = data.get('threshold', 0.6)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 50:
            return jsonify({"error": "Text must be at least 50 characters long for sentence detection"}), 400
        
        if len(text) > 15000:
            return jsonify({"error": "Text must be less than 15,000 characters for sentence detection"}), 400
        
        # Detect AI sentences (reuse cached global detector)
        result = ai_detector.detect_ai_sentences(text, threshold)
        
        response = {
            "ai_detected_sentences": result['ai_detected_sentences'],
            "human_sentences": result['human_sentences'],
            "sentence_analysis": result['sentence_analysis'],
            "statistics": result['statistics'],
            "threshold_used": result['threshold_used'],
            "text_length": len(text),
            "success": True
        }
        
        logger.info(f"Sentence detection: {result['statistics']['ai_generated_sentences']}/{result['statistics']['total_sentences_analyzed']} sentences detected as AI")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in sentence detection: {str(e)}")
        return jsonify({
            "error": "Failed to detect AI sentences",
            "success": False
        }), 500

@app.route('/highlight_ai', methods=['POST'])
def highlight_ai_handler():
    """Highlight AI-detected portions in text"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        threshold = data.get('threshold', 0.6)
        output_format = data.get('format', 'markdown')
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if output_format not in ['markdown', 'html', 'plain']:
            return jsonify({"error": "format must be 'markdown', 'html', or 'plain'"}), 400
        
        if len(text) < 50:
            return jsonify({"error": "Text must be at least 50 characters long for highlighting"}), 400
        
        if len(text) > 15000:
            return jsonify({"error": "Text must be less than 15,000 characters for highlighting"}), 400
        
        # Highlight AI text
        highlighted_text = highlight_ai_text(text, threshold, output_format)
        
        # Also get sentence analysis for additional info (reuse cached global detector)
        sentence_result = ai_detector.detect_ai_sentences(text, threshold)
        
        response = {
            "original_text": text,
            "highlighted_text": highlighted_text,
            "output_format": output_format,
            "threshold_used": threshold,
            "ai_sentences_count": len(sentence_result['ai_detected_sentences']),
            "total_sentences": len(sentence_result['sentence_analysis']),
            "ai_percentage": sentence_result['statistics']['ai_percentage'],
            "text_length": len(text),
            "success": True
        }
        
        logger.info(f"Text highlighting completed: {len(sentence_result['ai_detected_sentences'])} AI sentences highlighted")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in text highlighting: {str(e)}")
        return jsonify({
            "error": "Failed to highlight AI text",
            "success": False
        }), 500

@app.route('/get_ai_lines_simple', methods=['POST'])
def get_ai_lines_simple_handler():
    """Simple endpoint to get just the AI-detected lines with line numbers"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        threshold = data.get('threshold', 0.6)
        min_line_length = data.get('min_line_length', 20)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 50:
            return jsonify({"error": "Text must be at least 50 characters long"}), 400
        
        # Get full AI lines detection result (reuse cached global detector)
        result = ai_detector.detect_ai_lines(text, threshold, min_line_length)
        
        response = {
            "ai_lines": result['ai_detected_lines'],  # Full details with line numbers
            "ai_lines_count": len(result['ai_detected_lines']),
            "ai_lines_text_only": [line['text'] for line in result['ai_detected_lines']],
            "threshold_used": threshold,
            "min_line_length": min_line_length,
            "text_length": len(text),
            "statistics": result['statistics'],
            "success": True
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting AI lines: {str(e)}")
        return jsonify({
            "error": "Failed to get AI lines",
            "success": False
        }), 500

@app.route('/get_ai_sentences_simple', methods=['POST'])
def get_ai_sentences_simple_handler():
    """Simple endpoint to get just the AI-detected sentences"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        threshold = data.get('threshold', 0.6)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 50:
            return jsonify({"error": "Text must be at least 50 characters long"}), 400
        
        # Get AI sentences
        ai_sentences = get_ai_sentences(text, threshold)
        
        response = {
            "ai_sentences": ai_sentences,
            "ai_sentences_count": len(ai_sentences),
            "threshold_used": threshold,
            "text_length": len(text),
            "success": True
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting AI sentences: {str(e)}")
        return jsonify({
            "error": "Failed to get AI sentences",
            "success": False
        }), 500

@app.route('/detect_models', methods=['GET'])
def get_detection_models_endpoint():
    """Get available AI detection models with enhanced information"""
    try:
        available_models = get_detection_models()
        
        model_info = {
            "roberta-base-openai-detector": {
                "name": "roberta-base-openai-detector",
                "description": "OpenAI's RoBERTa base detector",
                "type": "base",
                "performance_rank": 4,
                "speed_rank": 1,
                "accuracy_rank": 4
            },
            "roberta-large-openai-detector": {
                "name": "roberta-large-openai-detector", 
                "description": "OpenAI's RoBERTa large detector",
                "type": "large",
                "performance_rank": 2,
                "speed_rank": 5,
                "accuracy_rank": 2
            },
            "chatgpt-detector": {
                "name": "chatgpt-detector",
                "description": "Specialized ChatGPT detector",
                "type": "specialized",
                "performance_rank": 3,
                "speed_rank": 3,
                "accuracy_rank": 3
            },
            "mixed-detector": {
                "name": "mixed-detector",
                "description": "Mixed AI content detector",
                "type": "general",
                "performance_rank": 1,
                "speed_rank": 4,
                "accuracy_rank": 1
            },
            "multilingual-detector": {
                "name": "multilingual-detector",
                "description": "Multilingual AI detection",
                "type": "multilingual",
                "performance_rank": 5,
                "speed_rank": 6,
                "accuracy_rank": 5
            },
            "distilbert-detector": {
                "name": "distilbert-detector",
                "description": "Fast DistilBERT-based detector",
                "type": "fast",
                "performance_rank": 6,
                "speed_rank": 2,
                "accuracy_rank": 6
            },
            "bert-detector": {
                "name": "bert-detector",
                "description": "BERT-based classification detector",
                "type": "classification",
                "performance_rank": 7,
                "speed_rank": 7,
                "accuracy_rank": 7
            }
        }
        
        detailed_models = [model_info.get(model, {"name": model, "description": "Unknown model"}) for model in available_models]
        
        return jsonify({
            "available_models": detailed_models,
            "total_models": len(available_models),
            "default_ensemble": ["chatgpt-detector", "mixed-detector"],
            "recommended_single": "mixed-detector",
            "recommended_fast": "roberta-base-openai-detector",
            "recommended_accurate": "mixed-detector",
            "selection_criteria": {
                "performance": "Best overall detection capability",
                "speed": "Fastest processing time",
                "accuracy": "Most accurate detection"
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting detection models: {str(e)}")
        return jsonify({
            "error": "Failed to get detection models",
            "success": False
        }), 500

@app.route('/humanize_and_check', methods=['POST'])
def humanize_and_check_handler():
    """Humanize text and then check if it passes AI detection"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 10:
            return jsonify({"error": "Text must be at least 10 characters long"}), 400
        
        if len(text) > 50000:  # Changed from 5000 to 50000
            return jsonify({"error": "Text must be less than 50000 characters"}), 400
        
        # Extract humanization options
        use_paraphrasing = data.get("paraphrasing", True)
        use_enhanced = data.get("enhanced", True)
        paraphrase_model = data.get("model", None)
        detection_threshold = data.get("detection_threshold", 0.7)
        
        # Step 1: Check original text
        logger.info("Checking original text for AI detection")
        original_detection = ai_detector.detect_ensemble(text)
        original_is_ai = original_detection["ensemble_ai_probability"] > detection_threshold
        original_confidence = original_detection.get("confidence", 0.0)
        
        # Step 2: Humanize the text, retrying if detection score increases
        logger.info("Humanizing text")
        # We'll keep the best result in case later attempts are worse
        best_reduction = -1.0
        best_text = text
        best_stats = {}
        humanized_text = text
        humanization_stats = {}

        # Limited retries: each attempt runs the full humanize pipeline (expensive).
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            candidate, stats = humanizer_service.humanize_text(
                text=text,
                use_paraphrasing=use_paraphrasing,
                use_enhanced_rewriting=use_enhanced,
                paraphrase_model=paraphrase_model
            )
            cand_detection = ai_detector.detect_ensemble(candidate)
            reduction = original_detection['ensemble_ai_probability'] - cand_detection['ensemble_ai_probability']

            logger.debug(f"Attempt {attempt}: ai probability reduction {reduction:.3f}")

            # keep the best candidate so far
            if reduction > best_reduction:
                best_reduction = reduction
                best_text = candidate
                best_stats = stats

            # if we already improved, break early
            if reduction >= 0:
                humanized_text = candidate
                humanization_stats = stats
                break

        else:
            # if none of the attempts improved, fall back to best candidate
            humanized_text = best_text
            humanization_stats = best_stats

        # record attempt information
        humanization_stats['attempts'] = attempt
        humanization_stats['best_ai_probability_reduction'] = best_reduction

        # Step 3: Check humanized text for AI detection
        logger.info("Checking humanized text for AI detection")
        humanized_detection = ai_detector.detect_ensemble(humanized_text)
        humanized_is_ai = humanized_detection["ensemble_ai_probability"] > detection_threshold
        humanized_confidence = humanized_detection.get("confidence", 0.0)
        
        # Calculate improvement
        ai_prob_reduction = original_detection['ensemble_ai_probability'] - humanized_detection['ensemble_ai_probability']
        detection_improved = original_is_ai and not humanized_is_ai
        
        response = {
            "original_text": text,
            "humanized_text": humanized_text,
            "humanization_stats": humanization_stats,
            "original_detection": {
                "is_ai_generated": original_is_ai,
                "ai_probability": original_detection['ensemble_ai_probability'],
                "prediction": original_detection['prediction'],
                "confidence": original_confidence
            },
            "humanized_detection": {
                "is_ai_generated": humanized_is_ai,
                "ai_probability": humanized_detection['ensemble_ai_probability'],
                "prediction": humanized_detection['prediction'],
                "confidence": humanized_confidence
            },
            "improvement": {
                "detection_improved": detection_improved,
                "ai_probability_reduction": ai_prob_reduction,
                "percentage_improvement": (ai_prob_reduction / original_detection['ensemble_ai_probability'] * 100) if original_detection['ensemble_ai_probability'] > 0 else 0
            },
            "threshold_used": detection_threshold,
            "success": True
        }
        
        logger.info(f"Humanization and detection completed. Improved: {detection_improved}, Reduction: {ai_prob_reduction:.3f}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in humanize and check: {str(e)}")
        return jsonify({
            "error": "Failed to humanize and check text",
            "success": False
        }), 500

# Legacy endpoint for backward compatibility
@app.route('/rewrite', methods=['POST'])
def rewrite_handler():
    """Legacy endpoint - redirects to humanize"""
    logger.info("Legacy /rewrite endpoint called, redirecting to /humanize")
    return humanize_handler()

@app.route('/get_ai_lines_detailed', methods=['POST'])
def get_ai_lines_detailed_handler():
    """Get detailed AI-detected lines with line numbers and probabilities"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        text = data.get('text', '').strip()
        threshold = data.get('threshold', 0.6)
        min_line_length = data.get('min_line_length', 20)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text) < 50:
            return jsonify({"error": "Text must be at least 50 characters long"}), 400
        
        # Get full AI lines detection result (reuse cached global detector)
        result = ai_detector.detect_ai_lines(text, threshold, min_line_length)
        
        # Format the AI lines with more readable structure
        formatted_ai_lines = []
        for line in result['ai_detected_lines']:
            formatted_ai_lines.append({
                "line_number": line['line_number'],
                "text": line['text'],
                "ai_probability": round(line['ai_probability'], 3),
                "confidence_level": "High" if line['ai_probability'] > 0.8 else "Medium" if line['ai_probability'] > 0.7 else "Low"
            })
        
        response = {
            "ai_detected_lines": formatted_ai_lines,
            "summary": {
                "total_lines_in_text": len(text.split('\n')),
                "lines_analyzed": result['statistics']['total_lines_analyzed'],
                "ai_lines_found": result['statistics']['ai_generated_lines'],
                "ai_percentage": round(result['statistics']['ai_percentage'], 2)
            },
            "settings": {
                "threshold_used": threshold,
                "min_line_length": min_line_length
            },
            "success": True
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting detailed AI lines: {str(e)}")
        return jsonify({
            "error": "Failed to get detailed AI lines",
            "success": False
        }), 500

if __name__ == '__main__':
    import sys

    def human_score(text: str) -> int:
        sentences = split_sentences(text)

        lengths = [len(s.split()) for s in sentences if s.strip()]
        score = 0
        total = 7

        # 1. Burstiness
        if len(lengths) > 1:
            mean = sum(lengths) / len(lengths)
            std = (sum((x - mean) ** 2 for x in lengths) / len(lengths)) ** 0.5
            if std > 8:
                score += 1

        # 2. Has contractions
        if any(c in text for c in ["don't", "it's", "they're", "isn't", "can't", "won't"]):
            score += 1

        # 3. Has casual transitions
        casual = ["That said", "But", "So", "Also", "Plus", "Which means"]
        if any(t in text for t in casual):
            score += 1

        # 4. No AI signature words remaining
        ai_words = ["utilize", "leverage", "delve", "furthermore", "moreover", "notably", "crucial", "comprehensive"]
        if not any(w in text.lower() for w in ai_words):
            score += 1

        # 5. Has punctuation variety
        if any(p in text for p in ["—", "...", "("]):
            score += 1

        # 6. Lexical diversity > 0.7
        words = [w for w in re.findall(r"[a-zA-Z']+", text.lower()) if w]
        if words and (len(set(words)) / len(words)) > 0.7:
            score += 1

        # 7. Has human starters
        if any(s.startswith(("And ", "But ", "So ", "Now,", "Look")) for s in sentences):
            score += 1

        pct = round((score / total) * 100)
        print(f"Human Score: {pct}% ({score}/{total} signals detected)")
        return pct

    def _self_test():
        sample = (
            "Project Overview\n\n"
            "This comprehensive guide explains how the system works, and it is important to note the details matter. "
            "Furthermore, the pipeline should preserve structure and not destroy headings.\n\n"
            "Key Steps\n\n"
            "We are going to test the humanize pipeline with three paragraphs. It is worth noting that the output should not utilize robotic words.\n\n"
            "Final Notes\n\n"
            "In conclusion, the system should add contractions and vary sentence lengths, so it feels more natural."
        )

        step1, step2, stats = humanizer_service._humanize_blocks(
            sample, model_name=get_current_model(), use_paraphrasing=True
        )

        # Assert headings unchanged
        blocks_in = humanizer_service.parse_blocks(sample)
        headings_in = [b["text"] for b in blocks_in if b["type"] == "heading"]
        blocks_out = humanizer_service.parse_blocks(step2)
        headings_out = [b["text"] for b in blocks_out if b["type"] == "heading"]
        assert headings_in == headings_out, "Headings changed in output"

        # Assert step1 != step2
        assert step1 != step2, "step1_output should differ from step2_output"

        # Assert same number of \\n\\n blocks as input
        assert len(sample.split("\n\n")) == len(step2.split("\n\n")), "Section count changed"

        print("SELF TEST OK")
        print("\nSCORE BEFORE (original):")
        human_score(sample)
        print("SCORE AFTER (step2_output):")
        human_score(step2)
        print("Char count before:", len(sample))
        print("Char count step1 :", len(step1))
        print("Char count step2 :", len(step2))
        print("Fillers injected :", stats.get("fillers_injected", 0))
        print("Synonyms replaced:", stats.get("synonyms_replaced", 0))

    if "--self-test" in sys.argv:
        _self_test()
        raise SystemExit(0)

    logger.info("Starting Humanize AI Server...")
    
    # Check if paraphrasing is available
    current_model = get_current_model()
    logger.info(f"Paraphrasing available: {current_model is not None}")
    if current_model:
        logger.info(f"Current model: {current_model}")
        logger.info(f"Device: {get_device_info()}")
    
    # Start Flask server with simple configuration
    print("\n" + "="*60)
    print("Starting Humanizer Server...")
    print("Backend: http://localhost:5000")
    print("="*60 + "\n")
    
    app.run(debug=False, host='localhost', port=5000, threaded=True, use_reloader=False)