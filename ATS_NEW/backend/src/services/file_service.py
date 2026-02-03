import os
import shutil
import pathlib
import json
from fastapi import UploadFile, HTTPException
from typing import List, Dict

class FileService:
    def __init__(self, data_dir: str = "/app/data"):
        self.data_dir = pathlib.Path(data_dir)
        self.users_dir = self.data_dir / "users"
        self.users_dir.mkdir(parents=True, exist_ok=True)

    def _get_user_path(self, user_id: str) -> pathlib.Path:
        if not user_id or ".." in user_id or "/" in user_id:
            raise HTTPException(status_code=400, detail="Invalid User ID")
        return self.users_dir / user_id

    def ensure_user_workspace(self, user_id: str):
        path = self._get_user_path(user_id)
        (path / "templates").mkdir(parents=True, exist_ok=True)
        (path / "linkedin_profiles").mkdir(parents=True, exist_ok=True)
        (path / "output").mkdir(parents=True, exist_ok=True)
        
        config_path = path / "config.json"
        if not config_path.exists():
            default_config = {
                "selected_llm_id": None,
                "prompts": {},
                "llm_inventory": []
            }
            with open(config_path, "w") as f:
                json.dump(default_config, f, indent=4)
        return {"status": "workspace_ready", "path": str(path)}

    async def upload_file(self, user_id: str, file: UploadFile, category: str):
        user_path = self._get_user_path(user_id)
        if category == "template":
            target_dir = user_path / "templates"
        elif category == "profile":
            target_dir = user_path / "linkedin_profiles"
        else:
            raise HTTPException(status_code=400, detail="Invalid category")
        
        file_path = target_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {"filename": file.filename, "path": str(file_path)}

    def list_files(self, user_id: str, category: str) -> List[str]:
        user_path = self._get_user_path(user_id)
        if category == "template":
            target_dir = user_path / "templates"
            extensions = {".tex", ".txt"}
        elif category == "profile":
            target_dir = user_path / "linkedin_profiles"
            extensions = {".pdf"}
        elif category == "output":
             target_dir = user_path / "output"
             extensions = {".pdf", ".tex"}
        else:
            return []
            
        if not target_dir.exists():
            return []
            
        return [f.name for f in target_dir.iterdir() if f.suffix in extensions]

    def get_file_content(self, user_id: str, filename: str, category: str):
        user_path = self._get_user_path(user_id)
        
        if category == "template":
            target_dir = user_path / "templates"
        elif category == "profile":
             target_dir = user_path / "linkedin_profiles"
        elif category == "output":
             target_dir = user_path / "output"
        else:
             raise HTTPException(status_code=400, detail="Invalid category")

        file_path = target_dir / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return file_path

    def delete_file(self, user_id: str, filename: str, category: str):
        # reuse get logic for path resolution
        try:
             # Logic is slightly different as we just want path
             user_path = self._get_user_path(user_id)
             if category == "template": target_dir = user_path / "templates"
             elif category == "profile": target_dir = user_path / "linkedin_profiles"
             elif category == "output": target_dir = user_path / "output"
             else: raise ValueError("Invalid cat")
             
             file_path = target_dir / filename
             if file_path.exists():
                 os.remove(file_path)
             return {"status": "deleted"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def get_config(self, user_id: str):
         user_path = self._get_user_path(user_id)
         config_path = user_path / "config.json"
         if not config_path.exists():
             return {}
         with open(config_path, "r") as f:
             return json.load(f)

    def update_config(self, user_id: str, new_config: dict):
        user_path = self._get_user_path(user_id)
        config_path = user_path / "config.json"
        with open(config_path, "w") as f:
            json.dump(new_config, f, indent=4)
        return new_config
