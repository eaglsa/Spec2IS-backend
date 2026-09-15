import httpx
import os
import aiofiles
from pathlib import Path
from bis_extractor.config import DOCUMENTS_DIR

async def download_document_async(url: str, standard_id_str: str, file_name: str) -> str:
    """Downloads a document using aiofiles and httpx."""
    standard_dir = DOCUMENTS_DIR / standard_id_str
    standard_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = standard_dir / file_name
    
    if file_path.exists():
        return str(file_path)
        
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            
            async with aiofiles.open(file_path, 'wb') as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    await f.write(chunk)
            return str(file_path)
        except Exception as e:
            if file_path.exists():
                os.remove(file_path)
            raise e

def download_document_sync(url: str, standard_id_str: str, file_name: str, client: httpx.Client = None) -> str:
    """Synchronous fallback for document downloads."""
    standard_dir = DOCUMENTS_DIR / standard_id_str
    standard_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = standard_dir / file_name
    if file_path.exists():
        return str(file_path)
        
    if not client:
        client = httpx.Client(verify=False)
        
    try:
        with client.stream('GET', url, timeout=30.0) as response:
            response.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
        return str(file_path)
    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        raise e
