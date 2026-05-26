from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
import pathlib

import json

# Database Setup
def load_db_url():
    # Try Docker path first
    config_path = pathlib.Path("/app/configs/development.json")
    if not config_path.exists():
        # Fallback to local path relative to this file's directory (backend/configs/development.json)
        config_path = pathlib.Path(__file__).parent.parent.parent / "configs" / "development.json"
        
    if config_path.exists():
        with open(config_path, "r") as f:
            config = json.load(f)
            return config.get("postgres_url")
            
    # Try fallback SQLite in local directory instead of non-existent /app/data/ats.db
    local_data_dir = pathlib.Path(__file__).parent.parent.parent / "data"
    local_data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{local_data_dir / 'ats.db'}"

DB_PATH = load_db_url()

engine = create_engine(DB_PATH)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class UserConfig(Base):
    __tablename__ = "user_configs"

    user_id = Column(String, primary_key=True, index=True)
    selected_llm_id = Column(String, nullable=True)
    prompts = Column(JSON, default={})

class LLMInventoryItem(Base):
    __tablename__ = "llm_inventory"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("user_configs.user_id"))
    name = Column(String)
    provider = Column(String)
    model_id = Column(String)  # Actual model identifier (e.g. gpt-4)
    sdk_id = Column(String)    # Internal catalog ID
    api_key = Column(String)
    plan_type = Column(String)
    
class LLMModel(Base):
    __tablename__ = "llms"

    id = Column(String, primary_key=True, index=True)
    provider = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    daily_token_limit = Column(Integer, default=1000000)
    plans_supported = Column(JSON, default=["free", "paid"])
    supports_tool_calling = Column(Boolean, default=True)
    supports_structured_output = Column(Boolean, default=True)

class DatabaseService:
    def __init__(self):
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()

    def get_config(self, user_id: str):
        config = self.db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if not config:
            # Create default
            default_prompts = {
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
            }
            config = UserConfig(user_id=user_id, prompts=default_prompts)
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
        
        # Fetch inventory
        inventory = self.db.query(LLMInventoryItem).filter(LLMInventoryItem.user_id == user_id).all()
        inventory_list = [
            {
                "id": item.id,
                "name": item.name,
                "provider": item.provider,
                "model_id": item.model_id,
                "sdk_id": item.sdk_id,
                "api_key": item.api_key,
                "plan_type": item.plan_type
            }
            for item in inventory
        ]

        return {
            "selected_llm_id": config.selected_llm_id,
            "prompts": config.prompts,
            "llm_inventory": inventory_list
        }

    def update_config(self, user_id: str, new_config: dict):
        config = self.db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if not config:
            self.get_config(user_id) # ensure created
            config = self.db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        
        if "selected_llm_id" in new_config:
            config.selected_llm_id = new_config["selected_llm_id"]
        
        if "prompts" in new_config:
            config.prompts = new_config["prompts"]
            
        if "llm_inventory" in new_config:
            # Full sync strategy: Delete all for user and re-add
            self.db.query(LLMInventoryItem).filter(LLMInventoryItem.user_id == user_id).delete()
            for item in new_config["llm_inventory"]:
                 db_item = LLMInventoryItem(
                     id=item["id"],
                     user_id=user_id,
                     name=item["name"],
                     provider=item["provider"],
                     model_id=item["model_id"],
                     sdk_id=item.get("sdk_id", item["model_id"]),
                     api_key=item["api_key"],
                     plan_type=item["plan_type"]
                 )
                 self.db.add(db_item)

        self.db.commit()
        return self.get_config(user_id)

    def get_llm_catalog(self):
        models = self.db.query(LLMModel).all()
        return [
            {
                "id": m.id,
                "provider": m.provider,
                "model_name": m.model_name,
                "display_name": m.display_name,
                "daily_token_limit": m.daily_token_limit,
                "plans_supported": m.plans_supported,
                "supports_tool_calling": m.supports_tool_calling,
                "supports_structured_output": m.supports_structured_output
            }
            for m in models
        ]

