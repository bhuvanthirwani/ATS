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
                "prompts": {
                    "analyze_prompt": """You are an Applicant Tracking System (ATS) used by Fortune-500 companies.

Your task is to score how well a candidate’s resume matches a job description using the same logic as modern ATS platforms (Workday, Greenhouse, Lever, iCIMS).

You must analyze the resume exactly like an ATS parser would — keyword matching, semantic matching, experience relevance, and role fit — not like a human recruiter.

--------------------------------
SCORING METHODOLOGY (must follow strictly)

Total Score = 100 points
A. Keyword Match (40 points)
B. Skill Coverage Depth (20 points)
C. Job Title & Role Match (10 points)
D. Experience Relevance (15 points)
E. Education & Domain Fit (5 points)
F. ATS Parsability (10 points)

--------------------------------
OUTPUT FORMAT (STRICT JSON — NO EXTRA TEXT)

{
  "ats_score": number between 0 and 100,
  "missing_keywords": [
     list of important skills or phrases in JOB_DESCRIPTION that are missing or weak in the resume
  ],
  "matched_keywords": [
     list of important skills that were successfully matched
  ],
  "justification": {
     "keyword_match": "...",
     "skill_depth": "...",
     "role_fit": "...",
     "experience_relevance": "...",
     "education_fit": "...",
     "parsing_quality": "..."
  }
}

--------------------------------
INPUTS

RESUME_CODE (LaTeX):
{resume_text}

JOB_DESCRIPTION:
{job_description}""",
                    "optimize_prompt": """You are an ATS-optimization engine used by Big Tech recruiting platforms.

Your task is to rewrite a LaTeX resume so that its ATS score becomes at least 90% for a given job description, while preserving structure, honesty, and formatting.

--------------------------------
STRICT RULES
1) DO NOT: change section structure, remove existing sections, or rename headers.
2) YOU MUST: Add missing keywords to Skills, Experience, and Projects.
3) If a core skill is missing, enhance bullets with relevant frameworks (e.g., Java -> Spring Boot).
4) If & or % is written in latex code, replace with \\&  and \\% as these punctuations throws error in Latex.

--------------------------------
REQUIRED OUTPUT (JSON — NO EXTRA TEXT)
{
  "final_score": number between 0 and 100,
  "new_latex_code": "FULL optimized LaTeX resume",
  "summary": [
     "Added 'Next.js' to skills",
     "Updated project description"
  ]
}

--------------------------------
INPUTS
initial_ats_score: {initial_ats_score}
missing_keywords: {missing_keywords}
matched_keywords: {matched_keywords}
justification: {justification}
job_description: {job_description}
old_resume_code (LaTeX): {resume_text}"""
                },
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
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
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
        from src.services.db_service import DatabaseService
        db = DatabaseService()
        return db.get_config(user_id)

    def update_config(self, user_id: str, new_config: dict):
        from src.services.db_service import DatabaseService
        db = DatabaseService()
        return db.update_config(user_id, new_config)

    def get_llm_catalog(self):
        # Assumes llms.json is in src/llms.json, same level as main.py/deps.py
        # Current file is src/services/file_service.py -> parent=services, parent.parent=src
        catalog_path = pathlib.Path(__file__).parent.parent / "llms.json"
        if not catalog_path.exists():
             return []
        with open(catalog_path, "r") as f:
            return json.load(f)
