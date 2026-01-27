import os
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

try:
    from mistralai import Mistral
except ImportError:
    Mistral = None

from models import AnalysisResult, OptimizationResult

class LLMAgent:
    def __init__(self, user_id: str, file_manager):
        self.user_id = user_id
        self.fm = file_manager
        self.user_config = self.fm.get_user_config(user_id)
        self.llm = self._initialize_llm()

    def _initialize_llm(self):
        selected_id = self.user_config.get("selected_llm_id")
        if not selected_id:
            raise ValueError("No Model Selected! Please go to Settings and select a model.")

        model_config = self.fm.resolve_model_path(self.user_id, selected_id)
        if not model_config:
            raise ValueError(f"Selected Model ID {selected_id} not found in inventory.")

        provider = model_config.get("provider")
        api_key = model_config.get("api_key")
        model_name = model_config.get("model_name")
        self.model_name = model_name
        base_url = model_config.get("base_url")

        if provider == "google":
            if not ChatGoogleGenerativeAI:
                raise ImportError("langchain-google-genai not installed.")

            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.1 # Lower temperature for better adherence
            )

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
                temperature=0.1,
                default_headers=extra_headers if extra_headers else None
            )

        elif provider == "mistral":
            if not Mistral:
                raise ImportError("mistralai not installed. Run `pip install mistralai`.")
            return Mistral(api_key=api_key)

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def analyze_resume(self, resume_text: str, job_description: str) -> AnalysisResult:
        """Step 1: Calculate ATS Score & Get Suggestions."""
        prompts = self.user_config.get("prompts", {})
        
        default_prompt = """You are an Applicant Tracking System (ATS) used by Fortune-500 companies.

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
        
        full_prompt_str = prompts.get("analyze_prompt") or default_prompt
        
        # Safe replacement to avoid issues with JSON/LaTeX braces
        formatted_prompt = full_prompt_str.replace("{resume_text}", resume_text)
        formatted_prompt = formatted_prompt.replace("{job_description}", job_description)
        # Also support double braces if user typed them
        formatted_prompt = formatted_prompt.replace("{{resume_text}}", resume_text)
        formatted_prompt = formatted_prompt.replace("{{job_description}}", job_description)

        prompt = ChatPromptTemplate.from_messages([
            ("user", "{user_payload}")
        ])

        # Mistral Handling
        if Mistral and isinstance(self.llm, Mistral):
             messages = [
                {
                    "content": formatted_prompt,
                    "role": "user",
                },
            ]
             resp = self.llm.chat.complete(
                model=self.model_name,
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "AnalysisResult",
                        "schema": AnalysisResult.model_json_schema(),
                        "strict": True
                    }
                },
                temperature=0.1
            )
             # Parse result
             content = resp.choices[0].message.content
             return AnalysisResult.model_validate_json(content)

        # Use structured output
        chain = prompt | self.llm.with_structured_output(AnalysisResult)
        return chain.invoke({"user_payload": formatted_prompt})

    def optimize_resume(self, analysis: AnalysisResult, resume_text: str, linkedin_text: str, job_description: str) -> OptimizationResult:
        """Step 2: Resume Tailoring & Optimization."""
        prompts = self.user_config.get("prompts", {})

        default_prompt = r"""You are an ATS-optimization engine used by Big Tech recruiting platforms.

Your task is to rewrite a LaTeX resume so that its ATS score becomes at least 90% for a given job description, while preserving structure, honesty, and formatting.

--------------------------------
STRICT RULES
1) DO NOT: change section structure, remove existing sections, or rename headers.
2) YOU MUST: Add missing keywords to Skills, Experience, and Projects.
3) If a core skill is missing, enhance bullets with relevant frameworks (e.g., Java -> Spring Boot).
4) If & or % is written in latex code, replace with \&  and \% as these punctuations throws error in Latex.
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
        full_prompt_str = prompts.get("optimize_prompt") or default_prompt
        
        # Safe replacement to avoid issues with JSON/LaTeX braces
        replacements = {
            "{initial_ats_score}": str(analysis.ats_score),
            "{missing_keywords}": ", ".join(analysis.missing_keywords),
            "{matched_keywords}": ", ".join(analysis.matched_keywords),
            "{justification}": json.dumps(analysis.justification.model_dump()),
            "{job_description}": job_description,
            "{resume_text}": resume_text,
            # Support double braces too
            "{{initial_ats_score}}": str(analysis.ats_score),
            "{{missing_keywords}}": ", ".join(analysis.missing_keywords),
            "{{matched_keywords}}": ", ".join(analysis.matched_keywords),
            "{{justification}}": json.dumps(analysis.justification.model_dump()),
            "{{job_description}}": job_description,
            "{{resume_text}}": resume_text,
        }
        
        formatted_prompt = full_prompt_str
        for key, val in replacements.items():
            formatted_prompt = formatted_prompt.replace(key, val)

        prompt = ChatPromptTemplate.from_messages([
            ("user", "{user_payload}")
        ])

        # Mistral Handling
        if Mistral and isinstance(self.llm, Mistral):
             messages = [
                {
                    "content": formatted_prompt,
                    "role": "user",
                },
            ]
             resp = self.llm.chat.complete(
                model=self.model_name,
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "OptimizationResult",
                        "schema": OptimizationResult.model_json_schema(),
                        "strict": True
                    }
                },
                temperature=0.1
            )
             # Parse result
             content = resp.choices[0].message.content
             return OptimizationResult.model_validate_json(content)

        chain = prompt | self.llm.with_structured_output(OptimizationResult)
        return chain.invoke({
            "user_payload": formatted_prompt
        })
