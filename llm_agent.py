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

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def analyze_resume(self, resume_text: str, job_description: str) -> AnalysisResult:
        """Step 1: Analyze resume against JD for keyword matching and scoring."""
        system_prompt = """You are an Applicant Tracking System (ATS) used by Fortune-500 companies.
Your task is to score how well a candidate’s resume matches a job description using the same logic as modern ATS platforms.
You must analyze the resume exactly like an ATS parser would — keyword matching, semantic matching, experience relevance, and role fit — not like a human recruiter.

SCORING METHODOLOGY (must follow strictly)
Total Score = 100 points
A. Keyword Match (40 points)
B. Skill Coverage Depth (20 points)
C. Job Title & Role Match (10 points)
D. Experience Relevance (15 points)
E. Education & Domain Fit (5 points)
F. ATS Parsability (10 points)
"""
        user_prompt = """RESUME_CODE (LaTeX):
{resume_text}

JOB_DESCRIPTION:
{job_description}
"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])

        # Use structured output
        chain = prompt | self.llm.with_structured_output(AnalysisResult)
        return chain.invoke({"resume_text": resume_text, "job_description": job_description})

    def optimize_resume(self, analysis: AnalysisResult, resume_text: str, linkedin_text: str, job_description: str) -> OptimizationResult:
        """Step 2: Tailor the resume based on the analysis and additional info."""
        system_prompt = """You are an ATS-optimization engine used by Big Tech recruiting platforms.
Your task is to rewrite a LaTeX resume so that its ATS score becomes at least 90% for a given job description, while preserving structure, honesty, and formatting.

STRICT RULES
1) DO NOT change the section structure or delete existing skills.
2) YOU MUST add all missing_keywords into appropriate places (Skills, Experience, Projects).
3) The resume must remain technically believable and internally consistent.
4) Increase keyword frequency and skill coverage.

OPTIMIZATION TARGET: final_score >= 90
"""
        user_prompt = """initial_ats_score: {initial_ats_score}
missing_keywords: {missing_keywords}
matched_keywords: {matched_keywords}
justification: {justification}
job_description: {job_description}
old_resume_code (LaTeX): {resume_text}
linkedin_profile: {linkedin_text}
"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])

        chain = prompt | self.llm.with_structured_output(OptimizationResult)
        return chain.invoke({
            "initial_ats_score": analysis.ats_score,
            "missing_keywords": ", ".join(analysis.missing_keywords),
            "matched_keywords": ", ".join(analysis.matched_keywords),
            "justification": json.dumps(analysis.justification.model_dump()),
            "job_description": job_description,
            "resume_text": resume_text,
            "linkedin_text": linkedin_text
        })
