import os
import json
import hashlib
import datetime
import time
import re
from typing import Dict
from google.api_core import exceptions
from app_config import config

# --- NEW SDK IMPORT ---
# Requires: pip install google-genai
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("CRITICAL: 'google-genai' SDK not found. Please run: pip install google-genai")
    raise

# Load paths from config
CACHE_FILE = config.get("paths", "cache_file", "genai_cache.json")
LOG_FILE = config.get("paths", "log_file", "llm_interaction.log")

# --- RATE LIMITER IMPLEMENTATION ---

class RateLimiter:
    """
    Enforces model-specific rate limits defined in config.json.
    Moved from knowledge_base.py to centralize control.
    """
    def __init__(self, model_name: str = "default"):
        self.model_name = model_name
        limits = config.get("rate_limits", model_name)
        
        # Fallback to default if model specific not found (and not explicit default)
        if not limits:
             limits = config.get("rate_limits", "default") or {"rpm": 15}

        self.rpm = limits.get("rpm", 15)
        self.delay = 60.0 / self.rpm
        self.last_call = 0

    def wait(self):
        now = time.time()
        elapsed = now - self.last_call
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_call = time.time()

# Singleton registry for rate limiters to ensure global enforcement per model
_RATE_LIMITERS: Dict[str, RateLimiter] = {}

def get_rate_limiter(model_name: str) -> RateLimiter:
    if model_name not in _RATE_LIMITERS:
        _RATE_LIMITERS[model_name] = RateLimiter(model_name)
    return _RATE_LIMITERS[model_name]


# --- CACHE & LOGGING UTILS ---

def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"   [Cache] Error: Cache file {CACHE_FILE} is corrupt. Starting with empty cache.")
            return {}
        except Exception as e:
            print(f"   [Cache] Error reading cache: {e}")
            return {}
    return {}

def _save_cache(cache):
    try:
        # Write to temp file then rename for atomic write
        temp_file = f"{CACHE_FILE}.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, sort_keys=True)
        os.replace(temp_file, CACHE_FILE)
    except Exception as e:
        print(f"   [Cache] Warning: Failed to save cache: {e}")

def _log_interaction(prompt, response_text, model_name, is_hit, thoughts=None, normalized_key=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "[CACHE HIT]" if is_hit else "[API CALL]"
    
    divider = "=" * 80
    thought_block = f"\nTHOUGHTS:\n{thoughts}\n" if thoughts else ""
    norm_msg = f"\nNORMALIZED KEY: {normalized_key}" if normalized_key else ""
    
    log_entry = (
        f"\n{divider}\n"
        f"{timestamp} {status} | Model: {model_name}"
        f"{norm_msg}\n"
        f"{divider}\n"
        f"PROMPT:\n{prompt[:2000]}...\n" 
        f"{thought_block}"
        f"\nRESPONSE:\n{response_text}\n"
    )
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"   [Warning] Failed to write to debug log: {e}")

def _normalize_prompt(text: str) -> str:
    """
    Extracts the semantic core of a prompt for caching purposes.
    """
    if not text: return ""
    norm = text.lower()
    norm = re.sub(r'[^\w\s\.\-]', ' ', norm)
    tokens = norm.split()
    stop_words = {
        "a", "an", "the", "please", "could", "would", "you", 
        "generate", "create", "write", "me", "for", "is", "are"
    }
    filtered_tokens = [t for t in tokens if t not in stop_words]
    return " ".join(filtered_tokens)

class UnifiedResponse:
    def __init__(self, text, thoughts=None):
        self.text = text
        self.thoughts = thoughts

class CachedGenAIModel:
    def __init__(self, model_name, api_key=None):
        self.model_name = model_name
        self.api_key = api_key
        self.client = None
        self.real_model = None 
        # Attach the singleton rate limiter for this model
        self.rate_limiter = get_rate_limiter(model_name)
        
    def _ensure_client(self):
        if not self.client:
            if not self.api_key:
                self.api_key = os.getenv("GOOGLE_API_KEY")
            self.client = genai.Client(api_key=self.api_key)

    def generate_content(self, prompt, response_schema=None, system_instruction=None):
        self._ensure_client()
        cache = _load_cache()
        
        # --- SEMANTIC CACHING ---
        normalized_prompt = _normalize_prompt(prompt)
        key_components = [
            f"GENERATE:{self.model_name}",
            f"PROMPT:{normalized_prompt}"
        ]
        
        if system_instruction:
            sys_hash = hashlib.md5(system_instruction.encode('utf-8')).hexdigest()
            key_components.append(f"SYS:{sys_hash}")
            
        if response_schema:
            try:
                if hasattr(response_schema, 'to_json'):
                    schema_str = response_schema.to_json()
                elif isinstance(response_schema, dict):
                    schema_str = json.dumps(response_schema, sort_keys=True)
                else:
                    schema_str = str(response_schema)
                schema_hash = hashlib.md5(schema_str.encode('utf-8')).hexdigest()
                key_components.append(f"SCHEMA:{schema_hash}")
            except:
                key_components.append("SCHEMA:UNKNOWN")

        key_content = ":".join(key_components)
        h = hashlib.md5(key_content.encode('utf-8')).hexdigest()
        
        # --- CACHE READ ---
        if h in cache:
            print(f"   [Cache] Hit ({self.model_name})")
            entry = cache[h]
            if isinstance(entry, dict):
                response_text = entry.get('response', '')
                thoughts_text = entry.get('thoughts', None)
            else:
                response_text = str(entry)
                thoughts_text = None
            
            _log_interaction(prompt, response_text, self.model_name, is_hit=True, thoughts=thoughts_text, normalized_key=normalized_prompt)
            return UnifiedResponse(response_text, thoughts_text)
            
        # --- API CALL (NEW SDK) ---
        # ENFORCE RATE LIMIT BEFORE CALL
        self.rate_limiter.wait()
        
        print(f"   [API] Calling {self.model_name} (google-genai SDK)...")
        
        retries = 5
        base_delay = 1
        
        for attempt in range(retries + 1):
            try:
                mime_type = "application/json" if response_schema else None
                
                config = types.GenerateContentConfig(
                    temperature=0.0,
                    thinking_config=types.ThinkingConfig(include_thoughts=True),
                    response_mime_type=mime_type,
                    response_schema=response_schema
                )
                
                try:
                    kwargs = {
                        "model": self.model_name,
                        "contents": prompt,
                        "config": config
                    }
                    if system_instruction:
                        kwargs["config"].system_instruction = system_instruction

                    response = self.client.models.generate_content(**kwargs)
                    
                except Exception as e:
                    if "400" in str(e) or "INVALID_ARGUMENT" in str(e):
                        print(f"   [API] Model {self.model_name} rejected ThinkingConfig. Retrying standard.")
                        standard_config = types.GenerateContentConfig(
                            temperature=0.0,
                            top_k=1,
                            response_mime_type=mime_type,
                            response_schema=response_schema
                        )
                        if system_instruction:
                            standard_config.system_instruction = system_instruction
                            
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=prompt,
                            config=standard_config
                        )
                    else:
                        raise e

                final_text = ""
                thoughts_extracted = []
                
                if response.candidates:
                    for part in response.candidates[0].content.parts:
                        if getattr(part, 'thought', False):
                            thoughts_extracted.append(part.text)
                        else:
                            final_text += part.text or ""
                
                final_thoughts = "\n".join(thoughts_extracted) if thoughts_extracted else None

                if final_text:
                    cache_entry = {
                        "model_name": self.model_name,
                        "version": "2.0-sdk-struct",
                        "prompt": prompt,
                        "normalized_prompt": normalized_prompt, 
                        "system_instruction": system_instruction,
                        "has_schema": bool(response_schema),
                        "thoughts": final_thoughts,
                        "response": final_text,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    cache[h] = cache_entry
                    _save_cache(cache)
                    _log_interaction(prompt, final_text, self.model_name, is_hit=False, thoughts=final_thoughts, normalized_key=normalized_prompt)
                    
                return UnifiedResponse(final_text, final_thoughts)
                
            except exceptions.ResourceExhausted:
                if attempt == retries:
                    print(f"   [Error] Rate limit exceeded after {retries} retries.")
                    raise
                
                sleep_time = base_delay * (2 ** attempt)
                print(f"   [Rate Limit] Quota exceeded. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"   [API Error] {e}")
                raise e

def cached_embed_content(model, content, task_type, api_key=None):
    client = genai.Client(api_key=api_key or os.getenv("GOOGLE_API_KEY"))
    
    cache = _load_cache()
    normalized_content = " ".join(content.split())
    key = f"EMBED:{model}:{normalized_content}:{task_type}"
    h = hashlib.md5(key.encode('utf-8')).hexdigest()
    
    if h in cache:
        return {'embedding': cache[h]}
    
    # Enforce Rate Limit for Embeddings too
    limiter = get_rate_limiter(model)
    limiter.wait()

    retries = 5
    base_delay = 1
    
    if isinstance(task_type, str):
        task_type = task_type.upper()

    for attempt in range(retries + 1):
        try:
            result = client.models.embed_content(
                model=model, 
                contents=content, 
                config=types.EmbedContentConfig(task_type=task_type)
            )
            embedding_values = result.embeddings[0].values
            cache[h] = embedding_values
            _save_cache(cache)
            return {'embedding': embedding_values}
            
        except exceptions.ResourceExhausted:
            if attempt == retries: raise
            time.sleep(base_delay * (2 ** attempt))
        except Exception as e:
            raise e