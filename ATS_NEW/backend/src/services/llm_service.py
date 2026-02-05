import json
import pathlib
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_mistralai import ChatMistralAI # Using native SDK now
from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import JsonOutputParser # Removed
from pydantic import BaseModel, Field

try:
    from mistralai import Mistral
except ImportError:
    Mistral = None

# ... (Models remain unchanged, skipping for brevity in replacement if not targeted, but here we replace top block)

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
        base_url = config.get("base_url")

        if provider == "mistral":
            if not Mistral:
                print("Mistral not installed")
                raise ImportError("mistralai library not installed.")
            print("Mistral installed")
            return Mistral(api_key=api_key)

        elif provider == "google":
            return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=0.2)

        elif provider in ["openrouter", "openai"]:
            extra_headers = {}
            if provider == "openrouter":
                base_url = "https://openrouter.ai/api/v1"
                extra_headers = {
                    "HTTP-Referer": "https://github.com/bhuvanthirwani/ATS",
                    "X-Title": "ATS Resume Tailoring System"
                }

            return ChatOpenAI(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=0.2,
                default_headers=extra_headers if extra_headers else None
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def analyze_resume(self, user_config: Dict, resume_text: str, jd_text: str) -> AnalysisResult:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        
        try:
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
            
            # Safe replacement to avoid issues with JSON/LaTeX braces (Legacy Strategy)
            formatted_prompt = analyze_prompt.replace("{resume_text}", resume_text)
            formatted_prompt = formatted_prompt.replace("{job_description}", jd_text)
            
            # Support double braces too if user typed them
            formatted_prompt = formatted_prompt.replace("{{resume_text}}", resume_text)
            formatted_prompt = formatted_prompt.replace("{{job_description}}", jd_text)
            
            # MISTRAL HANDLING
            if Mistral and isinstance(llm, Mistral):
                messages = [{"role": "user", "content": formatted_prompt}]
                resp = llm.chat.complete(
                    model=model_conf.get("model_id"),
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.2
                )
                content = resp.choices[0].message.content
                return AnalysisResult.model_validate_json(content)

            # LANGCHAIN HANDLING (OpenAI / Google)
            prompt = ChatPromptTemplate.from_messages([("user", "{user_payload}")])
            chain = prompt | llm.with_structured_output(AnalysisResult)
            
            return await chain.ainvoke({"user_payload": formatted_prompt})
        except Exception as e:
            logger.error(f"Error in analyze_resume: {str(e)}\n{traceback.format_exc()}")
            raise e

    async def optimize_resume(
        self, 
        user_config: Dict, 
        analysis: Dict, 
        resume_text: str, 
        jd_text: str,
        ignored_keywords: list[str] = []
    ) -> OptimizationResult:
        import traceback
        import logging
        logger = logging.getLogger(__name__)

        try:
            model_conf = self._get_model_config(user_config)
            llm = self._init_llm(model_conf)
            
            # Filter missing keywords if any are ignored
            missing = analysis.get('missing_keywords', [])
            effective_missing = [k for k in missing if k not in ignored_keywords]
            
            optimize_prompt = user_config.get("prompts", {}).get("optimize_prompt", "")
            if not optimize_prompt:
                 optimize_prompt = """You are an expert Resume Optimizer for ATS systems.
            Your goal is to rewrite the resume to include the missing keywords naturally and improve the ATS score.
            
            INPUT DATA:
            - Initial ATS Score: {initial_ats_score}
            - Missing Keywords: {missing_keywords}
            - Matched Keywords: {matched_keywords}
            - Current Resume (LaTeX): {resume_text}
            - Job Description: {job_description}
            
            INSTRUCTIONS:
            1. Integrate the missing keywords into the Experience or Skills sections where relevant.
            2. Do not fabricate experience, but phrased existing skills to match the JD.
            3. output the FULL valid LaTeX code.
            
            OUTPUT FORMAT (Strict JSON):
            {
                "final_score": <number 0-100>,
                "new_latex_code": "<full latex string>",
                "summary": ["<change 1>", "<change 2>"]
            }
            """
    
            # Safe replacement logic (Legacy Strategy)
            replacements = {
                "{initial_ats_score}": str(analysis.get('ats_score', 0)),
                "{missing_keywords}": ", ".join(effective_missing),
                "{matched_keywords}": ", ".join(analysis.get('matched_keywords', [])),
                "{justification}": json.dumps(analysis.get('justification', {})),
                "{job_description}": jd_text,
                "{resume_text}": resume_text,
                # Support double braces
                "{{initial_ats_score}}": str(analysis.get('ats_score', 0)),
                "{{missing_keywords}}": ", ".join(effective_missing),
                "{{matched_keywords}}": ", ".join(analysis.get('matched_keywords', [])),
                "{{justification}}": json.dumps(analysis.get('justification', {})),
                "{{job_description}}": jd_text,
                "{{resume_text}}": resume_text,
            }
            
            formatted_prompt = optimize_prompt
            for key, val in replacements.items():
                formatted_prompt = formatted_prompt.replace(key, str(val))
    
            # MISTRAL HANDLING
            if Mistral and isinstance(llm, Mistral):
                messages = [{"role": "user", "content": formatted_prompt}]
                resp = llm.chat.complete(
                    model=model_conf.get("model_id"),
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.2
                )
                content = resp.choices[0].message.content
                return OptimizationResult.model_validate_json(content)

            # LANGCHAIN HANDLING
            prompt = ChatPromptTemplate.from_messages([("user", "{user_payload}")])
            chain = prompt | llm.with_structured_output(OptimizationResult)
            
            return await chain.ainvoke({"user_payload": formatted_prompt})
        except Exception as e:
            logger.error(f"Error in optimize_resume: {str(e)}\n{traceback.format_exc()}")
            raise e

    async def refine_resume(self, user_config: Dict, current_tex: str, user_request: str) -> RefineResult:
        import traceback
        import logging
        logger = logging.getLogger(__name__)

        try:
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
            
            formatted_prompt = refine_prompt.replace("{current_tex}", current_tex)
            formatted_prompt = formatted_prompt.replace("{user_request}", user_request)
            
            # MISTRAL HANDLING
            if Mistral and isinstance(llm, Mistral):
                messages = [{"role": "user", "content": formatted_prompt}]
                resp = llm.chat.complete(
                    model=model_conf.get("model_id"),
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.2
                )
                content = resp.choices[0].message.content
                return RefineResult.model_validate_json(content)

            # LANGCHAIN HANDLING
            prompt = ChatPromptTemplate.from_messages([("user", "{user_payload}")])
            chain = prompt | llm.with_structured_output(RefineResult)
            
            return await chain.ainvoke({"user_payload": formatted_prompt})
        except Exception as e:
            logger.error(f"Error in refine_resume: {str(e)}\n{traceback.format_exc()}")
            raise e
