import json
import os
import hashlib
from bis_extractor.config import RAW_STORAGE_DIR

def save_raw_response(url: str, data: dict | str, entity_type: str) -> str:
    """Saves raw API responses or HTML to disk for resumability and audit."""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    type_dir = RAW_STORAGE_DIR / entity_type
    type_dir.mkdir(parents=True, exist_ok=True)
    
    is_json = isinstance(data, dict) or isinstance(data, list)
    extension = 'json' if is_json else 'html'
    file_path = type_dir / f"{url_hash}.{extension}"
    
    with open(file_path, 'w', encoding='utf-8') as f:
        if is_json:
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            f.write(data)
            
    return str(file_path)

def load_raw_response(file_path: str):
    """Loads a previously saved raw response."""
    if not os.path.exists(file_path):
        return None
        
    with open(file_path, 'r', encoding='utf-8') as f:
        if file_path.endswith('.json'):
            return json.load(f)
        return f.read()
