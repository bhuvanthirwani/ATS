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
                 analyze_prompt = r"""You are an Applicant Tracking System (ATS) used by Fortune-500 companies.

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
                    {job_description}
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
        ignored_keywords: list[str] = [],
        manual_keywords: list[str] = []
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
            
            # Combine suggested keywords with manual keywords
            target_keywords = list(set(effective_missing + manual_keywords))
            
            optimize_prompt = user_config.get("prompts", {}).get("optimize_prompt", "")
            if not optimize_prompt:

                optimize_prompt = r"""You are an ATS-optimization engine used by Big Tech recruiting platforms.

                    Your task is to rewrite a LaTeX resume so that its ATS score becomes at least 90% for a given job description, while preserving structure, honesty, and formatting.

                    --------------------------------
                    STRICT RULES
                    1) DO NOT: change section structure, remove existing sections, or rename headers.
                    2) YOU MUST: Add missing keywords to Skills, Experience, and Projects.
                    3) If a core skill is missing, enhance bullets with relevant frameworks (e.g., Java -> Spring Boot).
                    4) If & or % is written in latex code, replace with \&  and \% as these punctuations throws error in Latex.
                    5) Make sure, You are not making syntactical errors in the latex code.
                    6) Latex tags should have \tagname instead of \\tagname.
                    7) \\ is used for Next Line.

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
                    old_resume_code (LaTeX): {resume_text}
                """
    
            # Safe replacement logic (Legacy Strategy)
            replacements = {
                "{initial_ats_score}": str(analysis.get('ats_score', 0)),
                "{missing_keywords}": ", ".join(target_keywords),
                "{matched_keywords}": ", ".join(analysis.get('matched_keywords', [])),
                "{justification}": json.dumps(analysis.get('justification', {})),
                "{job_description}": jd_text,
                "{resume_text}": resume_text,
                # Support double braces
                "{{initial_ats_score}}": str(analysis.get('ats_score', 0)),
                "{{missing_keywords}}": ", ".join(target_keywords),
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
            
            refine_prompt = r"""You are a LaTeX Resume Editor.
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
