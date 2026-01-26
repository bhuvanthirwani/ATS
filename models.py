from pydantic import BaseModel, Field
from typing import List, Dict

class Justification(BaseModel):
    keyword_match: str = Field(description="Evaluation of exact and semantic keyword overlap")
    skill_depth: str = Field(description="Assessment of skill frequency and coverage across sections")
    role_fit: str = Field(description="Comparison of job titles and role relevance")
    experience_relevance: str = Field(description="Evaluation of years of experience and recency")
    education_fit: str = Field(description="Assessment of degree and field relevance")
    parsing_quality: str = Field(description="Evaluation of LaTeX formatting and ATS parsability")

class AnalysisResult(BaseModel):
    ats_score: int = Field(ge=0, le=100, description="The ATS match score between 0 and 100")
    missing_keywords: List[str] = Field(description="Skills or phrases in JD missing from resume")
    matched_keywords: List[str] = Field(description="Skills successfully matched")
    justification: Justification = Field(description="Detailed scoring breakdown")

class OptimizationResult(BaseModel):
    final_score: int = Field(ge=0, le=100, description="The simulated ATS score after optimization (target >= 90)")
    new_latex_code: str = Field(description="The full optimized LaTeX resume code")
    summary: List[str] = Field(description="Detailed list of specific changes made during optimization")
