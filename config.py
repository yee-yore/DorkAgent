import os, getpass, re

import requests
from dotenv import load_dotenv
from crewai import LLM

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

def read_env_file(path: str) -> dict:
    """Load key-value pairs from the .env file."""

    data = {}

    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                        data[k.strip()] = v.strip()
        except Exception as e:
            print(f"[!] Warning: Could not read .env file: {e}")

    return data

def write_env_file(path: str, values: dict):
    """Persist environment variables to the .env file."""

    existing = read_env_file(path)
    existing.update(values)
    lines = [f"{k}={existing[k]}" for k in sorted(existing.keys())]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def ensure_provider_api_key(provider: str):
    """Ensure provider-specific API key is available."""
    
    required_keys = []

    if provider == "openai":
        required_keys.append("OPENAI_API_KEY")
    elif provider == "anthropic":
        required_keys.append("ANTHROPIC_API_KEY")
    elif provider == "gemini":
        required_keys.append("GEMINI_API_KEY")
    
    missing = [k for k in required_keys if not os.getenv(k)]
    
    if missing:
        print("[!] Missing required API keys: " + ", ".join(missing))
        provided = {}
        for key in missing:
            prompt_text = f"Enter value for {key}: "
            try:
                val = getpass.getpass(prompt_text)
            except Exception:
                val = input(prompt_text)
            provided[key] = val.strip()
        write_env_file(ENV_PATH, provided)
        load_dotenv(dotenv_path=ENV_PATH, override=True)
    
    # Return the provider-specific API key
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY")
    elif provider == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY")
    elif provider == "gemini":
        return os.getenv("GEMINI_API_KEY")

def provider_key_name(provider: str) -> str:
    """Return the .env variable name for a provider's API key."""

    return {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }[provider]

def prompt_and_persist_key(key_name: str) -> str:
    """Prompt the user for a value and persist it to .env."""

    prompt_text = f"Enter value for {key_name}: "
    try:
        val = getpass.getpass(prompt_text)
    except Exception:
        val = input(prompt_text)
    val = val.strip()
    write_env_file(ENV_PATH, {key_name: val})
    os.environ[key_name] = val
    return val

def prompt_provider_api_key(provider: str) -> str:
    """Prompt the user to (re-)enter a provider's API key and persist it."""

    return prompt_and_persist_key(provider_key_name(provider))

SEARCH_ENGINE_KEY_NAMES = {
    "serper": "SERPER_API_KEY",
    "serpapi": "SERPAPI_API_KEY",
    "serply": "SERPLY_API_KEY",
}

def select_search_engine():
    """Select Google Dorking search engine."""

    while True:
        print("\n")
        print("1. Serper (serper.dev)")
        print("2. SerpApi (serpapi.com)")
        print("3. Serply (serply.io)")
        print("\n")

        choice = input("[?] Choose Search Engine (1 - 3): ").strip()

        if choice == "1":
            return "serper"
        elif choice == "2":
            return "serpapi"
        elif choice == "3":
            return "serply"
        else:
            print("[!] Invalid choice. Please enter 1 - 3.")

def ensure_search_engine_api_key(engine: str) -> str:
    """Ensure the selected search engine's API key is available."""

    key_name = SEARCH_ENGINE_KEY_NAMES[engine]

    if not os.getenv(key_name):
        print(f"[!] Missing required API key: {key_name}")
        prompt_and_persist_key(key_name)

    return os.getenv(key_name)

def fetch_models(provider: str, api_key: str):
    """Fetch available models from provider API."""
    
    try:
        if provider == "openai":
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=10)
            
            if response.status_code == 200:
                models = response.json()["data"]
                # Filter for GPT-4 and GPT-5 models, exclude snapshot and special purpose models
                exclude_keywords = ['transcribe', 'tts', 'codex', 'preview', 'search', 'audio', 'chat']
                filtered_models = [model for model in models 
                                 if model["id"].startswith(("gpt-4", "gpt-5")) and 
                                 not re.search(r'-\d{4}-\d{2}-\d{2}', model["id"]) and
                                 not any(keyword in model["id"] for keyword in exclude_keywords)]
                return [(model["id"], model["id"]) for model in filtered_models]
            else:
                print(f"[!] Failed to fetch OpenAI models: {response.status_code}")
                return []
                
        elif provider == "anthropic":
            headers = {
                "X-Api-Key": api_key,
                "anthropic-version": "2023-06-01"
            }
            response = requests.get("https://api.anthropic.com/v1/models", headers=headers, timeout=10)
            
            if response.status_code == 200:
                models = response.json()["data"]
                # Filter for Claude models only
                filtered_models = [model for model in models if model["id"].startswith("claude-")]
                return [(model["id"], model["display_name"]) for model in filtered_models]
            else:
                print(f"[!] Failed to fetch Anthropic models: {response.status_code}")
                return []
            
        elif provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                models = response.json()["models"]
                # Filter for models that support generateContent and exclude experimental/preview models
                exclude_keywords = ['experimental', '001', 'preview', 'banana']
                gen_models = [model for model in models 
                            if "generateContent" in model.get("supportedGenerationMethods", []) and
                            not any(keyword in model["name"].lower() or keyword in model["displayName"].lower() 
                                   for keyword in exclude_keywords)]
                return [(model["name"].split("/")[-1], model["displayName"]) for model in gen_models]
            else:
                print(f"[!] Failed to fetch Gemini models: {response.status_code}")
                return []
                
    except requests.RequestException as e:
        print(f"[!] Network error while fetching models: {e}")
        return []
    except Exception as e:
        print(f"[!] Error fetching models: {e}")
        return []

def select_provider():
    """Select LLM provider."""
    
    while True:
        print("\n")
        print("1. OpenAI")
        print("2. Anthropic")
        print("3. Google (Gemini)")
        print("\n")
        
        choice = input("[?] Choose LLM Provider (1 - 3): ").strip()
        
        if choice == "1":
            return "openai"
        elif choice == "2":
            return "anthropic"
        elif choice == "3":
            return "gemini"
        else:
            print("[!] Invalid choice. Please enter 1 - 3.")

def select_model(models: list):
    """Select model from available models list."""
    
    while True:
        print("\n")
        print("Available models:")
        for i, (model_id, display_name) in enumerate(models, 1):
            print(f"{i}. {display_name}")
        print("\n")
        
        try:
            choice = int(input(f"[?] Choose model (1 - {len(models)}): ").strip())
            if 1 <= choice <= len(models):
                return models[choice - 1][0]  # Return model_id
            else:
                print(f"[!] Invalid choice. Please enter 1 - {len(models)}.")
        except ValueError:
            print("[!] Please enter a valid number.")

def select_llm():
    """Complete LLM selection workflow."""
    
    # Step 1: Select provider
    provider = select_provider()
    
    # Step 2: Ensure API key is available
    api_key = ensure_provider_api_key(provider)
    
    # Step 3: Fetch available models, retrying with a fresh API key on failure
    while True:
        print(f"\n[+] Fetching available models for {provider.title()}...")
        models = fetch_models(provider, api_key)

        if models:
            break

        print(f"[!] Could not fetch models for {provider}. Please check your API key and try again.")
        api_key = prompt_provider_api_key(provider)
    
    # Step 4: Select model
    selected_model = select_model(models)
    
    return provider, selected_model

def create_llm(provider: str, model: str):
    """Create LLM instance based on provider and model."""

    if provider == "openai":
        return LLM(
            api_key=os.getenv('OPENAI_API_KEY'),
            model=f'openai/{model}',
        )
    elif provider == "anthropic":
        return LLM(
            api_key=os.getenv('ANTHROPIC_API_KEY'),
            model=f'anthropic/{model}',
        )
    elif provider == "gemini":
        return LLM(
            api_key=os.getenv('GEMINI_API_KEY'),
            model=f'gemini/{model}',
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")