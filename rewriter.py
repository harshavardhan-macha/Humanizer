import os
import json
import random
import string
import time
from typing import List, Dict, Optional, Tuple
import logging
import re
from dotenv import load_dotenv
import requests
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.stem import SnowballStemmer
from nltk.corpus import wordnet

# spaCy imports with fallback
try:
    from textblob import TextBlob
    ADVANCED_NLP_AVAILABLE = True
except ImportError:
    ADVANCED_NLP_AVAILABLE = False
    logging.warning("TextBlob not available. Install with: pip install textblob")

# Download required NLTK data with better error handling
def download_nltk_data():
    required_nltk_data = [
        ('punkt', 'tokenizers/punkt'),
        ('punkt_tab', 'tokenizers/punkt_tab'), 
        ('wordnet', 'corpora/wordnet'),
        ('averaged_perceptron_tagger', 'taggers/averaged_perceptron_tagger'),
        ('omw-1.4', 'corpora/omw-1.4')
    ]
    
    for data_package, path in required_nltk_data:
        try:
            nltk.data.find(path)
        except LookupError:
            print(f"Downloading {data_package}...")
            try:
                nltk.download(data_package, quiet=True)
            except Exception as e:
                print(f"Error downloading {data_package}: {e}")
                # Try alternative approach
                if data_package == 'punkt_tab':
                    try:
                        nltk.download('punkt', quiet=True)
                    except:
                        pass
        except Exception as e:
            print(f"Error with {data_package}: {e}")
            try:
                nltk.download(data_package, quiet=True)
            except:
                pass

# Call the function
download_nltk_data()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize stemmer
stemmer = SnowballStemmer('english')

class LocalRefinementRepository:
    """Advanced local text refinement using TextBlob and NLTK"""
    
    def __init__(self):
        self.advanced_features = ADVANCED_NLP_AVAILABLE
        
        if not self.advanced_features:
            logger.info("Using NLTK-based text refinement")
        else:
            logger.info("Using TextBlob and NLTK for advanced text refinement")
    
    def refine_text(self, text: str) -> Tuple[str, Optional[str]]:
        """Refine text using best available local NLP tools"""
        try:
            if self.advanced_features:
                return self._advanced_refinement(text), None
            else:
                return self._nltk_refinement(text), None
                
        except Exception as e:
            logger.error(f"Error in text refinement: {str(e)}")
            return self._basic_refinement(text), None
    
    def _advanced_refinement(self, text: str) -> str:
        """Advanced refinement using TextBlob and NLTK (preserves paragraph structure)"""
        try:
            # Split by paragraphs first to preserve structure
            paragraphs = re.split(r'\n\n+', text)
            refined_paragraphs = []
            
            for paragraph in paragraphs:
                if not paragraph.strip():
                    continue
                    
                # Grammar correction with TextBlob
                blob = TextBlob(paragraph)
                corrected_text = paragraph
                
                # Split sentences using NLTK
                sentences = sent_tokenize(corrected_text)
                
                refined_sentences = []
                for sentence in sentences:
                    refined = self._improve_sentence_advanced(sentence)
                    refined_sentences.append(refined)
                
                refined_paragraphs.append(" ".join(refined_sentences))
            
            # Join with double newlines to preserve paragraph structure
            return "\n\n".join(refined_paragraphs)
            
        except Exception as e:
            logger.warning(f"Advanced refinement failed, falling back to NLTK: {str(e)}")
            return self._nltk_refinement(text)
    
    def _improve_sentence_advanced(self, sentence: str) -> str:
        """Improve sentence using advanced NLP with academic tone"""
        if not sentence.strip():
            return sentence
        
        # Ensure proper capitalization
        sentence = sentence.strip()
        if sentence:
            sentence = sentence[0].upper() + sentence[1:]
        
        # Academic-appropriate transition words
        transition_words = {
            "Also": ["Furthermore", "Additionally", "Moreover", "In addition"],
            "But": ["However", "Nevertheless", "Nonetheless", "Conversely"],
            "So": ["Therefore", "Consequently", "Thus", "Hence"],
            "And": ["Furthermore", "Additionally", "Moreover"],
            "First": ["Initially", "Primarily", "To begin with"],
            "Finally": ["In conclusion", "Ultimately", "Lastly"]
        }
        
        for original, alternatives in transition_words.items():
            if sentence.startswith(original + " ") and random.random() < 0.25:
                replacement = random.choice(alternatives)
                sentence = sentence.replace(original, replacement, 1)
                break
        
        return sentence
    
    def _nltk_refinement(self, text: str) -> str:
        """Refinement using NLTK (preserves paragraph structure)"""
        try:
            # Split by paragraphs first to preserve structure
            paragraphs = re.split(r'\n\n+', text)
            refined_paragraphs = []
            
            for paragraph in paragraphs:
                if not paragraph.strip():
                    continue
                    
                sentences = sent_tokenize(paragraph)
                refined_sentences = []
                
                for sentence in sentences:
                    refined = self._improve_sentence_nltk(sentence)
                    refined_sentences.append(refined)
                
                refined_paragraphs.append(" ".join(refined_sentences))
            
            # Join with double newlines to preserve paragraph structure
            return "\n\n".join(refined_paragraphs)
            
        except Exception as e:
            logger.warning(f"NLTK refinement failed, using basic refinement: {str(e)}")
            return self._basic_refinement(text)
    
    def _improve_sentence_nltk(self, sentence: str) -> str:
        """Improve sentence using NLTK"""
        if not sentence.strip():
            return sentence
        
        # Basic improvements
        sentence = sentence.strip()
        if sentence:
            sentence = sentence[0].upper() + sentence[1:]
        
        # Word-level improvements using WordNet
        words = word_tokenize(sentence)
        improved_words = []
        
        for word in words:
            if word.isalpha() and len(word) > 4 and random.random() < 0.1:
                synonym = self._get_wordnet_synonym(word)
                if synonym and synonym != word.lower():
                    # Preserve original capitalization
                    if word[0].isupper():
                        synonym = synonym.capitalize()
                    improved_words.append(synonym)
                else:
                    improved_words.append(word)
            else:
                improved_words.append(word)
        
        # Reconstruct sentence with proper spacing using NLTK's detokenizer approach
        from nltk.tokenize.treebank import TreebankWordDetokenizer
        detokenizer = TreebankWordDetokenizer()
        return detokenizer.detokenize(improved_words)
    
    def _get_wordnet_synonym(self, word: str) -> Optional[str]:
        """Get synonym from WordNet"""
        try:
            synsets = wordnet.synsets(word.lower())
            if synsets:
                synonyms = []
                for syn in synsets[:2]:  # Check first 2 synsets
                    for lemma in syn.lemmas():
                        synonym = lemma.name().replace('_', ' ')
                        if (synonym != word.lower() and 
                            len(synonym.split()) == 1 and  # Single word only
                            synonym.isalpha()):
                            synonyms.append(synonym)
                
                if synonyms:
                    return random.choice(synonyms)
            return None
        except Exception:
            return None
    
    def _basic_refinement(self, text: str) -> str:
        """Basic text refinement without external libraries"""
        # Clean up text
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Fix common formatting issues - MORE COMPREHENSIVE
        replacements = {
            r'[\s\r\n]+([,.!?;:])': r'\1',  # Remove space before punctuation
            r'([.!?])\s*([a-z])': r'\1 \2',  # Ensure space after sentence endings
            r'\bi\b': 'I',  # Capitalize standalone 'i'
            r'\s+([)\]}])': r'\1',  # Remove space before closing brackets
            r'([(\[{])\s+': r'\1',  # Remove space after opening brackets
            r'\s{2,}': ' ',  # Replace multiple spaces with single space
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)
        
        # Ensure sentences start with capital letters
        sentences = re.split(r'([.!?]+)', text)
        result = []
        
        for i, part in enumerate(sentences):
            if i % 2 == 0 and part.strip():  # Sentence content
                part = part.strip()
                if part:
                    part = part[0].upper() + part[1:]
                result.append(part)
            else:  # Punctuation
                result.append(part)
        
        # Join and apply final cleanup passes
        final_text = ''.join(result)
        
        # Multiple cleanup passes to ensure all spacing issues are fixed
        final_text = re.sub(r'\s+([,.!?;:])', r'\1', final_text)  # Remove spaces before punctuation
        # Apply multiple passes to ensure no spaces are left before punctuation
        for _ in range(2):  # Multiple passes to catch nested cases
            final_text = re.sub(r'\s+([,.!?;:])', r'\1', final_text)
        final_text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', final_text)  # Ensure space after sentence endings
        final_text = re.sub(r'\s{2,}', ' ', final_text)  # Replace multiple spaces with single space
        final_text = re.sub(r'\s+$', '', final_text)  # Remove trailing spaces
        final_text = re.sub(r'^\s+', '', final_text)  # Remove leading spaces 
        return final_text
class LocalSynonymRepository:
    """Enhanced local synonym repository using NLTK WordNet and Oxford Dictionary API"""
    
    def __init__(self):
        load_dotenv()
        self.synonym_cache = {}

        self.app_id = os.getenv("OXFORD_APP_ID")
        self.app_key = os.getenv("OXFORD_APP_KEY")

        if self.app_id and self.app_key:
            logger.info("Oxford Dictionary API credentials loaded from .env")
        else:
            logger.warning("Oxford API keys missing from .env, will use WordNet only")

    def _try_oxford_synonym(self, clean_word: str) -> Optional[str]:
        """Try to fetch a synonym from the Oxford Dictionaries API.

        Returns a synonym string, or None if no synonym is available.
        If authentication fails (401/403), disables Oxford lookups going forward.
        """
        if not self.app_id or not self.app_key:
            return None

        headers = {
            "app_id": self.app_id,
            "app_key": self.app_key,
        }

        # Try both British and US variants to increase coverage
        for lang in ["en-gb", "en-us"]:
            try:
                url = f"https://od-api.oxforddictionaries.com/api/v2/thesaurus/{lang}/{clean_word}"
                resp = requests.get(url, headers=headers, timeout=4)

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = []

                    for result in data.get("results", []):
                        for lex in result.get("lexicalEntries", []):
                            for entry in lex.get("entries", []):
                                for sense in entry.get("senses", []):
                                    for syn in sense.get("synonyms", []):
                                        txt = syn.get("text")
                                        if (
                                            txt
                                            and txt.isalpha()
                                            and txt.lower() != clean_word
                                        ):
                                            candidates.append(txt)

                    if candidates:
                        return random.choice(candidates)

                    # If we got a 200 but no synonyms, no need to try other locales
                    return None

                if resp.status_code in (401, 403):
                    # Disable future Oxford lookups (invalid keys / access denied)
                    logger.warning(
                        "Oxford API authentication failed (401/403). "
                        "Disabling Oxford lookups and falling back to WordNet."
                    )
                    self.app_id = None
                    self.app_key = None
                    return None

                # Continue trying other locales for 404 or other non-fatal statuses
                logger.debug(
                    f"Oxford API returned {resp.status_code} for '{clean_word}' (lang={lang})"
                )

            except Exception as e:
                logger.debug(f"Oxford API error for '{clean_word}': {e}")
                # Don't disable keys on transient network errors

        return None

    def get_synonym(self, word: str) -> Tuple[str, Optional[str]]:
        clean_word = word.lower().strip()

        # Cache check first
        if clean_word in self.synonym_cache:
            return self.synonym_cache[clean_word], None

        if len(clean_word) < 3:
            self.synonym_cache[clean_word] = ""
            return "", "Word too short"

        # 1) Try Oxford thesaurus endpoint if keys exist
        oxford_synonym = self._try_oxford_synonym(clean_word)
        if oxford_synonym:
            self.synonym_cache[clean_word] = oxford_synonym
            return oxford_synonym, None

        # 2) Fallback to existing WordNet logic
        try:
            synsets = wordnet.synsets(clean_word)
            if not synsets:
                self.synonym_cache[clean_word] = ""
                return "", "No synonyms found for the word"

            all_synonyms = []
            # Check multiple synsets to improve coverage while keeping performance acceptable
            for synset in synsets[:3]:
                for lemma in synset.lemmas():
                    synonym = lemma.name().replace("_", " ")
                    if (
                        synonym != clean_word
                        and len(synonym.split()) == 1
                        and synonym.isalpha()
                        and len(synonym) >= 3
                    ):
                        all_synonyms.append(synonym)

            if not all_synonyms:
                self.synonym_cache[clean_word] = ""
                return "", "No suitable synonyms found"

            word_len = len(clean_word)
            filtered_synonyms = [
                syn for syn in all_synonyms if abs(len(syn) - word_len) <= 3
            ]

            result = random.choice(filtered_synonyms or all_synonyms)
            self.synonym_cache[clean_word] = result
            return result, None

        except Exception as e:
            self.synonym_cache[clean_word] = ""
            return "", f"Error fetching synonym: {str(e)}"



class TextRewriteService:
    """Enhanced service for rewriting and humanizing text"""
    
    def __init__(self):
        self.refinement_repo = LocalRefinementRepository()
        self.synonym_repo = LocalSynonymRepository()
        self.filler_sentences = self._load_fillers()
        random.seed(time.time())
        logger.info("TextRewriteService initialized with local refinement")
    
    def rewrite_text(self, text: str) -> Tuple[str, Optional[str]]:
        """Main rewriting function using local refinement"""
        try:
            # Apply local refinement
            refined, err = self.refinement_repo.refine_text(text)
            return refined if refined else text, err
        except Exception as e:
            logger.error(f"Error in text rewriting: {str(e)}")
            return text, f"Rewriting error: {str(e)}"
    
    def rewrite_text_with_modifications(self, text: str) -> Tuple[str, Optional[str]]:
        """Enhanced rewriting with comprehensive modifications (preserves paragraph structure)"""
        try:
            # Start with base rewriting
            base_result, err = self.rewrite_text(text)
            if err:
                return text, err
            
            # Split by paragraphs to preserve structure
            paragraphs = self._split_paragraphs(base_result)
            transformed_paragraphs = []
            
            for paragraph in paragraphs:
                # Apply transformations within each paragraph
                sentences = self._split_sentences(paragraph)
                transformed = []
                
                for sentence in sentences:
                    # Apply various transformations with REDUCED probability for speed
                    if random.random() < 0.2:  # Reduced from 0.8
                        sentence = self._vary_sentence_structure(sentence)
                    if random.random() < 0.1:  # Reduced from 0.6
                        sentence = self._replace_synonyms(sentence)
                    # Skip natural noise - too slow
                    
                    transformed.append(sentence)
                
                # Reduced sentence reordering (within paragraph)
                if len(transformed) > 2 and random.random() < 0.1:  # Reduced from 0.4
                    if len(transformed) > 3:
                        middle = transformed[1:-1]
                        random.shuffle(middle)
                        transformed = [transformed[0]] + middle + [transformed[-1]]
                
                # Reduced filler addition (within paragraph)
                if len(transformed) > 1 and random.random() < 0.1:  # Reduced from 0.4
                    filler = self._get_contextual_filler(transformed)
                    if filler:
                        # Insert at random position (not just end)
                        insert_pos = random.randint(1, len(transformed))
                        transformed.insert(insert_pos, filler)
                
                # Join sentences within paragraph
                paragraph_text = " ".join(transformed)
                # Collapse any pathological repeated phrases
                paragraph_text = self._collapse_repeated_phrases(paragraph_text)
                transformed_paragraphs.append(paragraph_text)
            
            # Join paragraphs with double newlines to preserve structure
            result_text = "\n\n".join(transformed_paragraphs)
            # Apply human errors while preserving paragraph structure
            result_text = self._inject_human_errors(result_text)

            return result_text, None
            
        except Exception as e:
            logger.error(f"Error in enhanced rewriting: {str(e)}")
            return text, f"Enhanced rewriting error: {str(e)}"
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs (preserving double newlines)"""
        # Split by double newlines or more to preserve paragraph structure
        paragraphs = re.split(r'\n\n+', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using NLTK"""
        try:
            return [s.strip() for s in sent_tokenize(text) if s.strip()]
        except Exception:
            return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    
    def _vary_sentence_structure(self, sentence: str) -> str:
        """Intelligently vary sentence structure"""
        if len(sentence.split()) < 4:
            return sentence
        
        transformations = [
            self._add_transition_word,
            self._rearrange_clauses,
            self._convert_contractions,
        ]
        
        transformation = random.choice(transformations)
        return transformation(sentence)
    
    def _add_transition_word(self, sentence: str) -> str:
        """Add academic transition words to sentences"""
        transitions = [
            "Furthermore, ", "Additionally, ", "Moreover, ", "Notably, ",
            "Significantly, ", "Importantly, ", "Specifically, ", "Indeed, ",
            "Particularly, ", "Evidently, ", "Consequently, ", "Subsequently, ",
            "Interestingly, ", "Remarkably, ", "Essentially, ", "Ultimately, ",
            "Clearly, ", "Obviously, ", "Undoubtedly, ", "Certainly, "
        ]
        
        if not sentence[0].isupper():
            return sentence
        
        # Reduced probability from 0.5 to 0.15 for speed
        if random.random() < 0.15:
            transition = random.choice(transitions)
            return transition + sentence.lower()
        
        return sentence
    
    def _rearrange_clauses(self, sentence: str) -> str:
        """Simple clause rearrangement"""
        if ', ' in sentence and sentence.count(',') == 1:
            parts = sentence.split(', ', 1)
            if len(parts) == 2 and random.random() < 0.3:
                part1, part2 = parts
                return f"{part2}, {part1.lower()}"
        
        return sentence
    
    def _convert_contractions(self, sentence: str) -> str:
        """Expand contractions for academic formality"""
        contractions = {
            "don't": "do not", "won't": "will not", "can't": "cannot",
            "isn't": "is not", "aren't": "are not", "wasn't": "was not",
            "weren't": "were not", "hasn't": "has not", "haven't": "have not",
            "wouldn't": "would not", "couldn't": "could not", "shouldn't": "should not",
            "it's": "it is", "that's": "that is", "there's": "there is",
            "what's": "what is", "you're": "you are", "we're": "we are",
            "they're": "they are"
        }
        
        # Reduced probability from 0.8 to 0.2 for speed
        if random.random() < 0.2:
            for contraction, expansion in contractions.items():
                # Case-insensitive replacement
                lower_sentence = sentence.lower()
                if contraction in lower_sentence:
                    # Find and replace while preserving case
                    idx = lower_sentence.find(contraction)
                    if idx != -1:
                        sentence = sentence[:idx] + expansion + sentence[idx + len(contraction):]
                    break
        
        return sentence
    
    def _replace_synonyms(self, sentence: str) -> str:
        """Intelligently replace words with synonyms"""
        words = sentence.split()
        modifications = 0
        max_modifications = max(1, len(words) // 8)  # Reduced frequency
        
        for i, word in enumerate(words):
            if modifications >= max_modifications:
                break

            # Extract clean word - remove non-alphanumeric characters
            clean_word = ''.join(c for c in word if c.isalnum()).lower()

            # Skip if too short or too common
            if (len(clean_word) < 4 or  
                self._is_common_word(clean_word)):
                continue

            # Do not replace proper nouns or capitalized words (preserve nouns)
            # If the original token starts with uppercase (likely a proper noun), skip
            if word and word[0].isupper():
                continue

            # Reduced probability from 0.4 to 0.2
            if random.random() < 0.2:
                synonym, err = self.synonym_repo.get_synonym(clean_word)
                if not err and synonym:
                    # Preserve original word formatting
                    new_word = self._preserve_word_format(word, synonym)
                    words[i] = new_word
                    modifications += 1
        
        return " ".join(words)

    def _collapse_repeated_phrases(self, text: str) -> str:
        """Collapse pathological repeated words/phrases (e.g. 'any stuffs good any stuffs good ...').
        Reduces any immediate repetition of the same word sequence to a single occurrence.
        """
        try:
            # Collapse repeated single words repeated 3 or more times into one
            text = re.sub(r"\b(\w+)(?:\s+\1){2,}\b", r"\1", text, flags=re.IGNORECASE)

            # Collapse repeated short phrases (2-4 words) repeated 2+ times
            # Example: '(any stuffs good) (any stuffs good) ...' -> single occurrence
            for n in range(4, 1, -1):
                pattern = r"\b((?:\w+\s+){%d}\w+)(?:\s+\1){1,}\b" % (n-1)
                text = re.sub(pattern, r"\1", text, flags=re.IGNORECASE)

            # Remove excessive trailing repeated tokens like 'good good good' -> 'good'
            text = re.sub(r"(\b\w+\b)(?:\s+\1){2,}", r"\1", text, flags=re.IGNORECASE)
            return text
        except Exception:
            return text
    def _inject_human_errors(self, text: str) -> str:
        """
        Inject realistic grammar mistakes to make text more human-like while preserving paragraph structure:
        - article confusion (a/an/the)
        - subject–verb agreement slips
        - preposition mixups
        - tense mistakes
        - plural/singular errors
        - homophone confusion
        - word order issues
        - missing/extra words
        """
        try:
            # Split by paragraphs to preserve structure
            paragraphs = self._split_paragraphs(text)
            processed_paragraphs = []
            
            for paragraph in paragraphs:
                # Split paragraph into sentences
                sentences = self._split_sentences(paragraph)
                noisy = []

                for sent in sentences:
                    s = sent

                    # Apply multiple types of errors with higher probability
                    error_types = [
                        (self._article_errors, 0.6),      # 60% chance
                        (self._subject_verb_errors, 0.6), # 60% chance
                        (self._preposition_errors, 0.6),  # 60% chance
                        (self._tense_errors, 0.4),        # 40% chance
                        (self._plural_errors, 0.4),       # 40% chance
                        (self._homophone_errors, 0.3),    # 30% chance
                        (self._word_order_errors, 0.3),   # 30% chance
                        (self._missing_words, 0.2),       # 20% chance
                    ]

                    for error_func, probability in error_types:
                        if random.random() < probability:
                            s = error_func(s)

                    noisy.append(s)

                # Join sentences within paragraph with spaces
                processed_paragraph = " ".join(noisy)
                processed_paragraphs.append(processed_paragraph)
            
            # Join paragraphs with double newlines to preserve structure
            return "\n\n".join(processed_paragraphs)
        except Exception:
            return text

    def _preserve_word_format(self, original: str, replacement: str) -> str:
        """Preserve capitalization and punctuation of original word"""
        # Extract prefix and suffix punctuation
        prefix = ""
        suffix = ""
        core_word = original
        
        # Get leading punctuation
        start = 0
        while start < len(original) and not original[start].isalpha():
            prefix += original[start]
            start += 1
        
        # Get trailing punctuation
        end = len(original) - 1
        while end >= 0 and not original[end].isalpha():
            suffix = original[end] + suffix
            end -= 1
        
        if start <= end:
            core_word = original[start:end+1]
        
        # Apply capitalization pattern
        if core_word and core_word[0].isupper():
            replacement = replacement.capitalize()
        elif core_word.isupper():
            replacement = replacement.upper()
        elif core_word.islower():
            replacement = replacement.lower()
        
        return prefix + replacement + suffix
    
    def _add_natural_noise(self, sentence: str) -> str:
        """Add natural linguistic variations - MORE AGGRESSIVE"""
        # More comprehensive academic-appropriate replacements
        replacements = {
            " and ": [" as well as ", " along with ", " in addition to ", " together with "],
            " but ": [" however, ", " nevertheless, ", " nonetheless, ", " conversely, "],
            " because ": [" due to the fact that ", " given that ", " since ", " as "],
            " so ": [" therefore, ", " consequently, ", " thus, ", " hence, "],
            " also ": [" furthermore, ", " additionally, ", " moreover, ", " likewise, "],
            " use ": [" utilize ", " employ ", " implement ", " apply "],
            " show ": [" demonstrate ", " illustrate ", " reveal ", " display "],
            " help ": [" facilitate ", " assist ", " aid ", " support "],
            " get ": [" obtain ", " acquire ", " achieve ", " secure "],
            " make ": [" create ", " establish ", " generate ", " produce "],
            " find ": [" discover ", " identify ", " determine ", " locate "],
            " think ": [" consider ", " believe ", " suggest ", " propose "],
            " very ": [" significantly ", " considerably ", " substantially ", " remarkably "],
            " big ": [" substantial ", " significant ", " considerable ", " extensive "],
            " small ": [" minimal ", " limited ", " modest ", " slight "],
            " good ": [" excellent ", " effective ", " beneficial ", " advantageous "],
            " bad ": [" detrimental ", " problematic ", " unfavorable ", " adverse "],
            " new ": [" novel ", " innovative ", " contemporary ", " recent "],
            " old ": [" traditional ", " established ", " conventional ", " previous "],
            " many ": [" numerous ", " multiple ", " various ", " several "],
            " few ": [" limited ", " minimal ", " sparse ", " scarce "]
        }
        
        # Apply multiple replacements per sentence with higher probability
        replacements_made = 0
        max_replacements = 3  # Allow up to 3 replacements per sentence
        
        for old, new_options in replacements.items():
            if replacements_made >= max_replacements:
                break
                
            lower_sentence = sentence.lower()
            if old in lower_sentence and random.random() < 0.3:  # Increased from 0.15
                new_phrase = random.choice(new_options)
                # Case-insensitive replacement - find and replace once
                idx = lower_sentence.find(old)
                if idx != -1:
                    sentence = sentence[:idx] + new_phrase + sentence[idx + len(old):]
                    replacements_made += 1
        
        return sentence
    
    def _get_contextual_filler(self, sentences: List[str]) -> str:
        """Generate academic contextual filler sentence"""
        if not sentences:
            return ""
        
        # Extract themes from the text
        all_text = " ".join(sentences)
        keywords = self._extract_keywords(all_text)
        
        if keywords and len(keywords) > 0:
            # Academic templates
            templates = [
                "This analysis underscores the significance of {keyword}.",
                "The examination of {keyword} reveals important insights.",
                "Such findings regarding {keyword} warrant further consideration.",
                "The implications of {keyword} are particularly noteworthy.",
                "This investigation into {keyword} provides valuable understanding.",
                "The study of {keyword} demonstrates considerable importance.",
                "These observations concerning {keyword} merit attention."
            ]
            
            template = random.choice(templates)
            keyword = random.choice(keywords[:3])  # Use top 3 keywords
            return template.format(keyword=keyword)
        
        # Fallback to academic transitions
        return random.choice(self.filler_sentences)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        # Simple keyword extraction - get words with 5+ letters
        words = text.lower().split()
        extracted = []
        for word in words:
            # Remove punctuation and check length
            clean_word = ''.join(c for c in word if c.isalpha())
            if len(clean_word) >= 5:
                extracted.append(clean_word)
        
        # Filter out common words
        filtered_words = [
            word for word in extracted 
            if not self._is_common_word(word)
        ]
        
        # Return unique keywords
        return list(dict.fromkeys(filtered_words))
    
    def _is_common_word(self, word: str) -> bool:
        """Check if word is too common for replacement in academic context"""
        # Expanded list including academic terms to preserve
        common_words = {
            "the", "and", "that", "this", "with", "have", "will", "been", 
            "from", "they", "know", "want", "been", "good", "much", "some",
            "time", "very", "when", "come", "here", "just", "like", "long",
            "make", "many", "over", "such", "take", "than", "them", "well",
            "were", "work", "about", "could", "would", "there", "their",
            "which", "should", "think", "where", "through", "because",
            "between", "important", "different", "following", "around",
            "though", "without", "another", "example", "however", "therefore",
            # Academic terms to preserve
            "research", "study", "analysis", "data", "method", "result",
            "conclusion", "evidence", "theory", "hypothesis", "findings",
            "literature", "methodology", "framework", "approach", "concept",
            "significant", "substantial", "considerable", "demonstrate",
            "indicate", "suggest", "reveal", "establish", "examine", "AI", "IoT", "ML", "NLP", 
            "deep learning", "blockchain", "cloud computing", "big data", "cybersecurity", "data science", 
            "augmented reality", "virtual reality", "edge computing", "quantum computing", "natural language processing",
            "machine learning", "artificial intelligence", "internet of things", "data analytics", "digital transformation",
            "automation", "smart technology", "sustainability", "innovation", "disruption", "technology"
        }
        return word.lower() in common_words
    
    def _article_errors(self, sentence: str) -> str:
        """Introduce realistic article mistakes (a/an/the confusion)"""
        words = sentence.split()
        if len(words) < 3:
            return sentence
        
        # Common article mistakes
        article_fixes = {
            "a": ["an", "the"],
            "an": ["a", "the"], 
            "the": ["a", "an"]
        }
        
        for i, word in enumerate(words):
            lower_word = word.lower()
            if lower_word in article_fixes and random.random() < 0.4:  # 40% chance
                # Check if next word starts with vowel/consonant for a/an
                if i + 1 < len(words):
                    next_word = words[i + 1].lower().strip('.,!?;:')
                    next_starts_vowel = next_word and next_word[0] in 'aeiou'
                    
                    if lower_word == "a" and next_starts_vowel:
                        # Should be "an" but sometimes people write "a"
                        words[i] = "an"
                    elif lower_word == "an" and not next_starts_vowel:
                        # Should be "a" but sometimes people write "an"
                        words[i] = "a"
                    elif lower_word == "the":
                        # Sometimes omit "the" or replace with "a/an"
                        if random.random() < 0.3:
                            replacement = random.choice(["a", "an"])
                            words[i] = replacement
                        else:
                            # Remove "the" entirely
                            words.pop(i)
                            break
                break
        
        return " ".join(words)
    
    def _subject_verb_errors(self, sentence: str) -> str:
        """Introduce subject-verb agreement mistakes"""
        words = sentence.split()
        if len(words) < 3:
            return sentence
        
        # Look for common subject-verb patterns to mess up
        for i, word in enumerate(words):
            lower_word = word.lower()
            
            # Common mistakes: is/are, has/have, was/were
            if lower_word in ["is", "are"] and random.random() < 0.3:
                words[i] = "are" if lower_word == "is" else "is"
                break
            elif lower_word in ["has", "have"] and random.random() < 0.3:
                words[i] = "have" if lower_word == "has" else "has"
                break
            elif lower_word in ["was", "were"] and random.random() < 0.3:
                words[i] = "were" if lower_word == "was" else "was"
                break
        
        return " ".join(words)
    
    def _preposition_errors(self, sentence: str) -> str:
        """Introduce preposition mistakes and unwanted prepositions"""
        words = sentence.split()
        if len(words) < 4:
            return sentence
        
        # Common preposition mistakes and additions
        preposition_replacements = {
            "in": ["on", "at", "with", "by"],
            "on": ["in", "at", "with", "by"],
            "at": ["in", "on", "with", "by"],
            "with": ["in", "on", "at", "by"],
            "by": ["in", "on", "at", "with"],
            "for": ["to", "at", "with", "by"],
            "to": ["for", "at", "with", "by"],
            "from": ["of", "with", "by", "at"]
        }
        
        # Unwanted prepositions to sometimes add
        unwanted_preps = ["in", "on", "at", "with", "by", "for", "to", "from", "of"]
        
        modifications = 0
        max_mods = 1  # Only one modification per sentence
        
        # First, try to replace existing prepositions
        for i, word in enumerate(words):
            if modifications >= max_mods:
                break
                
            lower_word = word.lower()
            if lower_word in preposition_replacements and random.random() < 0.3:
                replacement = random.choice(preposition_replacements[lower_word])
                words[i] = replacement
                modifications += 1
                break
        
        # Sometimes add unwanted prepositions before nouns
        if modifications == 0 and len(words) > 3 and random.random() < 0.2:
            # Find a noun position (roughly after articles or adjectives)
            for i in range(1, len(words) - 1):
                if random.random() < 0.1:  # Low chance per position
                    # Add preposition before this word
                    prep = random.choice(unwanted_preps)
                    words.insert(i, prep)
                    modifications += 1
                    break
        
        return " ".join(words)
    
    def _tense_errors(self, sentence: str) -> str:
        """Introduce tense mistakes (present/past/future confusion)"""
        words = sentence.split()
        if len(words) < 3:
            return sentence
        
        # Common tense mistakes
        tense_fixes = {
            # Present to past
            "is": ["was", "were"],
            "are": ["were", "was"],
            "has": ["had"],
            "have": ["had"],
            "does": ["did"],
            "do": ["did"],
            "goes": ["went"],
            "says": ["said"],
            "makes": ["made"],
            "takes": ["took"],
            "gets": ["got"],
            "sees": ["saw"],
            "knows": ["knew"],
            "thinks": ["thought"],
            "finds": ["found"],
            "comes": ["came"],
            "gives": ["gave"],
            "runs": ["ran"],
            # Past to present (less common but happens)
            "was": ["is"],
            "were": ["are"],
            "had": ["has", "have"],
            "did": ["does", "do"],
        }
        
        for i, word in enumerate(words):
            lower_word = word.lower()
            if lower_word in tense_fixes and random.random() < 0.5:
                replacement = random.choice(tense_fixes[lower_word])
                # Preserve capitalization
                if word[0].isupper():
                    replacement = replacement.capitalize()
                words[i] = replacement
                break
        
        return " ".join(words)
    
    def _plural_errors(self, sentence: str) -> str:
        """Introduce plural/singular mistakes"""
        words = sentence.split()
        if len(words) < 3:
            return sentence
        
        # Common plural/singular mistakes
        plural_fixes = {
            # Singular to plural
            "is": "are", "was": "were", "has": "have",
            "this": "these", "that": "those", "it": "they",
            "its": "their", "my": "our", "your": "your",  # your stays the same
            "his": "their", "her": "their",
            # Plural to singular
            "are": "is", "were": "was", "have": "has",
            "these": "this", "those": "that", "they": "it",
            "their": "its", "our": "my", "your": "your",
        }
        
        for i, word in enumerate(words):
            lower_word = word.lower()
            if lower_word in plural_fixes and random.random() < 0.4:
                replacement = plural_fixes[lower_word]
                # Preserve capitalization
                if word[0].isupper():
                    replacement = replacement.capitalize()
                words[i] = replacement
                break
        
        return " ".join(words)
    
    def _homophone_errors(self, sentence: str) -> str:
        """Introduce homophone mistakes (their/there/they're, etc.)"""
        words = sentence.split()
        if len(words) < 2:
            return sentence
        
        # Common homophone mistakes
        homophone_fixes = {
            "their": ["there", "they're"],
            "there": ["their", "they're"],
            "they're": ["their", "there"],
            "its": ["it's"],
            "it's": ["its"],
            "your": ["you're"],
            "you're": ["your"],
            "to": ["too", "two"],
            "too": ["to", "two"],
            "two": ["to", "too"],
            "then": ["than"],
            "than": ["then"],
            "affect": ["effect"],
            "effect": ["affect"],
            "accept": ["except"],
            "except": ["accept"],
            "principal": ["principle"],
            "principle": ["principal"],
            "compliment": ["complement"],
            "complement": ["compliment"],
        }
        
        for i, word in enumerate(words):
            lower_word = word.lower()
            if lower_word in homophone_fixes and random.random() < 0.6:
                replacement = random.choice(homophone_fixes[lower_word])
                # Preserve capitalization
                if word[0].isupper():
                    replacement = replacement.capitalize()
                words[i] = replacement
                break
        
        return " ".join(words)
    
    def _word_order_errors(self, sentence: str) -> str:
        """Introduce word order mistakes"""
        words = sentence.split()
        if len(words) < 4:
            return sentence
        
        # Simple word order swaps
        if random.random() < 0.4:
            # Swap two adjacent words
            swap_idx = random.randint(0, len(words) - 2)
            words[swap_idx], words[swap_idx + 1] = words[swap_idx + 1], words[swap_idx]
        
        return " ".join(words)
    
    def _missing_words(self, sentence: str) -> str:
        """Occasionally omit words or add extra ones"""
        words = sentence.split()
        if len(words) < 4:
            return sentence
        
        # Small chance to omit a word
        if random.random() < 0.3 and len(words) > 3:
            omit_idx = random.randint(1, len(words) - 2)  # Don't omit first or last word
            words.pop(omit_idx)
        
        return " ".join(words)
    
    def _load_fillers(self) -> List[str]:
        """Load academic-appropriate filler sentences"""
        return [
            "This analysis provides valuable insights into the subject matter.",
            "Such examination proves particularly enlightening for understanding the topic.", 
            "These considerations merit further scholarly attention.",
            "The implications of this research become increasingly evident.",
            "This methodological approach yields meaningful academic results.",
            "The findings contribute significantly to the existing body of knowledge.",
            "This investigation enhances our understanding of the phenomenon.",
            "The research demonstrates the complexity of the underlying issues."
        ]


# Public functions for external use
def rewrite_text(text: str, enhanced: bool = False) -> Tuple[str, Optional[str]]:
    """
    Main function to rewrite text
    
    Args:
        text: Input text to rewrite
        enhanced: Whether to use enhanced modifications
        
    Returns:
        Tuple of (rewritten_text, error_message)
    """
    service = TextRewriteService()
    if enhanced:
        return service.rewrite_text_with_modifications(text)
    else:
        return service.rewrite_text(text)

def get_synonym(word: str) -> Tuple[str, Optional[str]]:
    """
    Get synonym for a word
    
    Args:
        word: Word to find synonym for
        
    Returns:
        Tuple of (synonym, error_message)
    """
    repo = LocalSynonymRepository()
    return repo.get_synonym(word)

def refine_text(text: str) -> Tuple[str, Optional[str]]:
    """
    Refine text using NLP tools
    
    Args:
        text: Text to refine
        
    Returns:
        Tuple of (refined_text, error_message)
    """
    repo = LocalRefinementRepository()
    return repo.refine_text(text)