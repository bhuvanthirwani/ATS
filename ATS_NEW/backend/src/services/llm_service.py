import json
import pathlib
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# Define Models (copied from models.py)
class Justification(BaseModel):
    keyword_match: str = Field(description="Evaluation of exact and semantic keyword overlap")
    skill_depth: str = Field(description="Assessment of skill frequency and coverage across sections")
    role_fit: str = Field(description="Comparison of job titles and role relevance")
    experience_relevance: str = Field(description="Evaluation of years of experience and recency")
    education_fit: str = Field(description="Assessment of degree and field relevance")
    parsing_quality: str = Field(description="Evaluation of LaTeX formatting and ATS parsability")

class AnalysisResult(BaseModel):
    ats_score: int = Field(ge=0, le=100, description="The ATS match score between 0 and 100")
    missing_keywords: list[str] = Field(description="Skills or phrases in JD missing from resume")
    matched_keywords: list[str] = Field(description="Skills successfully matched")
    justification: Justification = Field(description="Detailed scoring breakdown")

class OptimizationResult(BaseModel):
    final_score: int = Field(ge=0, le=100, description="The simulated ATS score after optimization (target >= 90)")
    new_latex_code: str = Field(description="The full optimized LaTeX resume code")
    summary: list[str] = Field(description="Detailed list of specific changes made during optimization")

class RefineResult(BaseModel):
    new_latex_code: str = Field(description="The updated LaTeX code after refinement")
    summary: str = Field(description="Brief summary of the change applied")


class LLMService:
    def __init__(self):
        self.catalog_path = pathlib.Path(__file__).parent.parent / "llms.json"

    def _get_model_config(self, user_config: Dict):
        selected_id = user_config.get("selected_llm_id")
        if not selected_id:
            raise ValueError("No LLM model selected in configuration")
            
        inventory = user_config.get("llm_inventory", [])
        item = next((i for i in inventory if i["id"] == selected_id), None)
        if not item:
             raise ValueError("Selected model not found in inventory")
             
        # Resolve from catalog
        with open(self.catalog_path, "r") as f:
            catalog = json.load(f)
            
        catalog_def = next((c for c in catalog if c["id"] == item["sdk_id"]), None)
        if not catalog_def:
             raise ValueError("Model definition not found in catalog")
             
        return {**catalog_def, **item} # Merge (Api key in item overrides)

    def _init_llm(self, config: Dict):
        provider = config.get("provider")
        api_key = config.get("api_key")
        model_name = config.get("model_id") # e.g. gpt-4 or gemini-pro
        
        if provider == "openai":
            return ChatOpenAI(model=model_name, api_key=api_key, temperature=0.2)
        elif provider == "google":
            return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=0.2)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def analyze_resume(self, user_config: Dict, resume_text: str, jd_text: str) -> AnalysisResult:
        model_conf = self._get_model_config(user_config)
        llm = self._init_llm(model_conf)
        
        # Get custom prompt or default
        analyze_prompt = user_config.get("prompts", {}).get("analyze_prompt", "")
        if not analyze_prompt:
             # Fallback default from original app.py
             analyze_prompt = """You are an Applicant Tracking System (ATS)... (Truncated for brevity, using truncated version)
             OUTPUT FORMAT (STRICT JSON):
             {
               "ats_score": number,
               "missing_keywords": [],
               "matched_keywords": [],
               "justification": { ... }
             }
             INPUTS:
             RESUME_CODE: {resume_text}
             JOB_DESCRIPTION: {job_description}
             """
        
        parser = JsonOutputParser(pydantic_object=AnalysisResult)
        prompt = ChatPromptTemplate.from_template(analyze_prompt)
        chain = prompt | llm | parser
        
        return chain.invoke({"resume_text": resume_text, "job_description": jd_text})

    async def optimize_resume(
        self, 
        user_config: Dict, 
        analysis: Dict, 
        resume_text: str, 
        jd_text: str,
        ignored_keywords: list[str] = []
    ) -> OptimizationResult:
        model_conf = self._get_model_config(user_config)
        llm = self._init_llm(model_conf)
        
        # Filter missing keywords if any are ignored
        missing = analysis.get('missing_keywords', [])
        effective_missing = [k for k in missing if k not in ignored_keywords]
        
        optimize_prompt = user_config.get("prompts", {}).get("optimize_prompt", "")
        if not optimize_prompt:
             optimize_prompt = "You are an ATS-optimization engine... (Default)"

        parser = JsonOutputParser(pydantic_object=OptimizationResult)
        prompt = ChatPromptTemplate.from_template(optimize_prompt)
        chain = prompt | llm | parser
        
        return chain.invoke({
            "initial_ats_score": analysis.get('ats_score'),
            "missing_keywords": effective_missing,
            "matched_keywords": analysis.get('matched_keywords'),
            "justification": analysis.get('justification'),
            "resume_text": resume_text,
            "job_description": jd_text
        })

    async def refine_resume(self, user_config: Dict, current_tex: str, user_request: str) -> RefineResult:
        model_conf = self._get_model_config(user_config)
        llm = self._init_llm(model_conf)
        
        refine_prompt = """You are a LaTeX Resume Editor.
        Task: Update the resume code based on the user's request.
        
        CURRENT LATEX:
        {current_tex}
        
        USER REQUEST:
        {user_request}
        
        OUTPUT FORMAT (JSON):
        {{
            "new_latex_code": "Updated full latex code",
            "summary": "Updated summary section to include..."
        }}
        """
        
        parser = JsonOutputParser(pydantic_object=RefineResult)
        prompt = ChatPromptTemplate.from_template(refine_prompt)
        chain = prompt | llm | parser
        
        return chain.invoke({"current_tex": current_tex, "user_request": user_request})
