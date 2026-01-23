import os
import json
import pathlib
import fitz  # pymupdf

# --- FILE BASED ARCHITECTURE ---

class FileManager:
    def __init__(self, project_root):
        self.project_root = pathlib.Path(project_root)
        self.users_dir = self.project_root / "users"
        self.configs_dir = self.project_root / "configs"
        self.catalog_path = self.configs_dir / "llms.json"
        
        # Ensure base directories exist
        self.users_dir.mkdir(exist_ok=True)
        self.configs_dir.mkdir(exist_ok=True)

    def get_global_catalog(self):
        """Reads the global model catalog."""
        if not self.catalog_path.exists():
            return []
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_user_dir(self, user_id):
        """Returns the Path object for the user's directory."""
        return self.users_dir / user_id

    def ensure_user_structure(self, user_id):
        """Creates the necessary folder structure for a user."""
        user_path = self.get_user_dir(user_id)
        dirs = [
            user_path,
            user_path / "linkedin_profiles",
            user_path / "output",
            user_path / "templates",
            user_path / "output" / "raw_data" # Ensure raw_data exists
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            
        # Ensure config.json exists
        config_path = user_path / "config.json"
        if not config_path.exists():
            default_config = {
                "selected_llm_id": None,
                "prompts": {},  # Will be populated with defaults by logic if empty
                "llm_inventory": []
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4)
        
        return user_path

    def get_user_config(self, user_id):
        """Reads the user's config.json."""
        self.ensure_user_structure(user_id)
        config_path = self.get_user_dir(user_id) / "config.json"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"selected_llm_id": None, "prompts": {}, "llm_inventory": []}

    def save_user_config(self, user_id, config_data):
        """Writes to the user's config.json."""
        self.ensure_user_structure(user_id)
        config_path = self.get_user_dir(user_id) / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)

    def resolve_model_path(self, user_id, inventory_id):
        """Helper to find specific model details from inventory + catalog."""
        config = self.get_user_config(user_id)
        inventory = config.get("llm_inventory", [])
        
        # Find item in inventory
        item = next((i for i in inventory if i.get("id") == inventory_id), None)
        if not item:
            return None
            
        # Find definition in catalog
        catalog = self.get_global_catalog()
        catalog_def = next((c for c in catalog if c.get("id") == item.get("sdk_id")), None)
        
        if not catalog_def:
            return None
            
        # Merge: Catalog Def + Inventory Item (Inventory overrides if key conflict, e.g. api_key)
        # We want the API Key from Inventory (if present) to be available
        merged = {**catalog_def, **item} 
        return merged


# --- UTILITIES (Preserved from original) ---

def extract_text_from_pdf(file_input):
    """Extracts text from a PDF file path or uploaded file object."""
    try:
        if isinstance(file_input, (str, pathlib.Path)):
            doc = fitz.open(str(file_input))
        else:
            # Streamlit uploaded file
            file_input.seek(0)
            file_bytes = file_input.getvalue()
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            
        text = ""
        for page in doc:
            text += page.get_text()
        return text.encode("utf-8", errors="replace").decode("utf-8")
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return "" # Return empty string instead of crashing

def extract_text_from_file(file_path):
    """General text extraction for TXT, TEX, or PDF."""
    file_path = str(file_path)
    if file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    else:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""
