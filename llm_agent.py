from pydantic import BaseModel, Field, HttpUrl
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from typing import List, Optional
import os, json

# -----------------------
# Pydantic Models
# -----------------------

class Summary(BaseModel):
    description: str = Field(description= "A professional summary highlighting the candidate's years of experience, core skills, and unique value proposition. "
                   "Focus on technical expertise. "
                   "Keep it concise (1-2 sentences), use strong action verbs, and align with the job description's keywords.",
    min_length = 50,
    max_length = 200
    )

class ProfessionalExperience(BaseModel):
    role: str = Field(description= "Job title (e.g., 'Senior Data Engineer', 'Analytics Engineer')."
                   "Use standardized industry titles that match the job description when possible.")
    company: str = Field(description= "Company's name")
    achievements: List[str] = Field(description= "2-4 bullet points highlighting quantifiable results and key responsibilities. "
                   "Each should: "
                   "1) Start with a strong action verb (e.g., 'Designed', 'Led', 'Increased') "
                   "2) Include metrics/impact where possible (e.g., 'improved efficiency by 40%')",)
    start_date: str = Field(description="Start date in format: 'MMM. YYYY' (e.g., 'Jan. 2020'). Use consistent formatting throughout the resume.")
    end_date: str = Field(description="End date in format: 'MMM. YYYY' (e.g., 'Dec. 2022') or 'Present' for current roles.")
    sector: Optional[str] = Field(description="Company's niche, industry sector using standardized terms: (eg., Pharma, Retail, E-commerce, Data Platform, Cloud provider, Finance"
                                  "Align with the target job's industry when relevant.")
    location: Optional[str] = Field(None, description="Location country of the company or role (e.g., Brazil, USA, Spain)")

class Education(BaseModel):
    degree: str = Field(description= "The degree obtained (e.g., Bachelor of Science in Computer Engineering)")
    institution: str = Field(description= "Official name of the university or institution that awarded the degree (e.g., Universidade Federal de São Paulo")
    achievements: Optional[str]
    graduation_year: Optional[str] = Field(None, description="Graduation year in the format: Year (e.g., 2022)")
    location: Optional[str] = None

class Courses(BaseModel):
    course: str = Field(description= "The certification obtained or course (e.g., Advanced PySpark for Data Engineers)")
    institution: str = Field(description= "Official name of the organization or company that awarded the(e.g., IBM, Snowflake, Azure")
    graduation_year: Optional[str]

# OBSERVATION > class Projects(BaseModel)
# I don't recommend using it, if you choose to use it, remember to:
# 1. improve your PDF extractions to collect links (actually this doesn't happen)
# 2. test and validate the links until you get solid ones
# 3. adapt your cv_template.html as well (script on doc)
# 4. uncomment StructuredOutput class definition for projects
# -----------------------------------------------------------------------------------
#class Projects(BaseModel):
#    project: str = Field(description= "The project description")
#    link: Optional[HttpUrl] = Field(None, description="Provided URL of the project")

class Skills(BaseModel):
    skill: str = Field(description= "Standardized name of the technical skill or tool. "
                   "Use industry-standard terms that match the job description. "
                   "Examples: "
                   "- 'Python' (not 'Python programming') "
                   "- 'Google Cloud Platform (GCP)' "
                   "- 'Data Visualization'")
    description: str = Field(description= "Detailed description including: "
                   "1) Years of experience (if 1+ years) "
                   "2) Key technologies/libraries within the skill "
                   "3) 2-3 concrete applications or achievements",
        min_length=50,
        max_length=200)

class Volunteering(BaseModel):
    role: str = Field(description= "Relevant Volunteering experience based on the Job Description")
    organization: str = Field(description= "Full name of the organization + cause focus.")
    achievements: List[str] = Field(description= "2-3 bullet points showcasing measurable impact and relevant skills.")
    start_date: str = Field(description="Start date in format: 'MMM. YYYY' (e.g., 'Jan. 2020')")
    end_date: str = Field(description="End date in format: 'MMM. YYYY' (e.g., 'Dec. 2022') or 'Present' for current roles.")
    location: Optional[str] = Field(None, description="Location country of the company or role (e.g., Brazil, USA, Spain)")

# COMPLETE OUTPUT STRUCTURE CLASS
class StructuredOutput(BaseModel):
    name: str = Field(description= "Full name")
    email: str = Field(description= "Email address")
    phone: str = Field(description="Phone number in the format +XX XXXXX XXXX")
    linkedin: Optional[HttpUrl] = Field(None, description="LinkedIn profile URL")
    github: Optional[HttpUrl] = Field(None, description="GitHub profile URL")

    summary: Summary
    skills: List[Skills]
    experience: List[ProfessionalExperience]
    education: List[Education]
#   projects: List[Projects]
    courses: List[Courses]
    volunteering: List[Volunteering]

# ------------------------------------
# AGENT CLASS FOR RESUME OPTIMIZATION
# ------------------------------------

class LLMAgent:
    def __init__(self, config: dict):
        self.config = config
        self.llm = self._initialize_llm()
        self.parser = JsonOutputParser(pydantic_object=StructuredOutput)  # Uses your existing StructuredOutput
        self.chain = self._build_chain()

    def _initialize_llm(self):
        # Use default enterprise and model from config
        default_enterprise = self.config.get("default_enterprise", "openai")
        default_model = self.config.get("default_model", "gpt-4o")
        
        # Priority 1: Match BOTH enterprise and model
        # Priority 2: Match just enterprise
        # Priority 3: Fallback to first resource
        resources = self.config.get("resources", [])
        resource = next(
            (r for r in resources if r.get("enterprise") == default_enterprise and r.get("model") == default_model),
            next(
                (r for r in resources if r.get("enterprise") == default_enterprise),
                resources[0] if resources else {}
            )
        )
        
        base_url = resource.get("base_url", "https://api.openai.com/v1")
        api_key = resource.get("api_key")
        
        # OpenRouter specific headers
        default_headers = {
            "HTTP-Referer": "https://github.com/bhuvanthirwani/ATS",
            "X-Title": "ATS Resume Tailoring System"
        }
        
        return ChatOpenAI(
            model=default_model,
            temperature=0.5,
            base_url=base_url,
            api_key=api_key,
            default_headers=default_headers if "openrouter.ai" in base_url else None
        )

    # BUILDING CHAIN STRUCTURE [ PROMPT (system+user) | LLM (GROQ OBJECT) | PARSER (STRUCTURED OUTPUT) ]
    def _build_chain(self):
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            ("user", self._get_user_prompt())
        ])
        return prompt_template.partial(
            format_instructions=self.parser.get_format_instructions()
        ) | self.llm | self.parser

    def _get_system_prompt(self):
        return """"
        You are a professional career assistant helping me prepare for job applications.
        I will provide my personal documents (Resume and LinkedIn Export).
        Your task is to build a complete and well-structured Professional Profile Configuration based on the provided documents.

        Write in a neutral, professional tone. Do not invent any information that is not found in the reference documents.
        
        --- Resume Export ---
        {resume_text}
        
        --- Linkedin Export ---
        {linkedin_text}
        """

    def _get_user_prompt(self):
        return """"
        Please generate An Updated CV Version based on the information provided previously the following outputs based on the provided job description.
        Follow this schema exactly: {format_instructions}
        Ensure that **all experiences** and courses listed in the input are included in the output. **Preserve the full content**, but adjust the wording to 
        better fit the job description by focusing on keywords, descriptions, and required skills. Ensure nothing is omitted. If necessary, prioritize essential 
        information but retain all experiences. Adjust technical jargon, responsibilities, and achievements to align with the role's requirements and the company’s values.
        
        --- JOB DESCRIPTION ---
        {job_description}
        """

    def optimize_latex(self, latex_template: str, resume_text: str, linkedin_text: str, job_description: str):
        system_prompt = """
        You are a professional career assistant and LaTeX expert.
        I will provide a LaTeX template and information from a Resume and LinkedIn Export.
        Your task is to take the provided LaTeX template and rewrite it COMPLETELY to be optimized for the provided Job Description.
        
        Rules:
        1. Keep the EXACT LaTeX structure and packages from the template.
        2. Replace all the content (Experience, Projects, Skills) with optimized versions based on the Resume/LinkedIn data and the Job Description.
        3. Do NOT use placeholders. Fill in all information.
        4. Return ONLY the raw LaTeX code. Do not include any markdown formatting like ```latex ... ```.
        5. Ensure the LaTeX code is valid and compiles without errors.
        6. Do not invent information; only use what is provided in the documents.
        
        --- Resume Export ---
        {resume_text}
        
        --- LinkedIn Export ---
        {linkedin_text}
        """
        
        user_prompt = """
        Optimize this LaTeX template for the following Job Description:
        
        --- JOB DESCRIPTION ---
        {job_description}
        
        --- LATEX TEMPLATE ---
        {latex_template}
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({
            "resume_text": resume_text,
            "linkedin_text": linkedin_text,
            "job_description": job_description,
            "latex_template": latex_template
        })

    def get_ats_score(self, resume_text: str, job_description: str):
        """Calculates an ATS score (0-100) based on the Job Description."""
        system_prompt = """
        You are an ATS (Applicant Tracking System) expert. 
        Evaluate the provided Resume against the Job Description and provide:
        1. A score from 0 to 100 based on keyword match, skill alignment, and experience relevance.
        2. A brief 1-sentence justification for the score.
        
        Return the result as a JSON object with keys {{ "score": 85, "justification": "..." }}.
        """
        
        user_prompt = """
        Resume: {resume_text}
        Job Description: {job_description}
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        response = chain.invoke({
            "resume_text": resume_text,
            "job_description": job_description
        })
        
        try:
            cleaned_response = response.strip().replace('```json', '').replace('```', '')
            return json.loads(cleaned_response)
        except:
            # Fallback parser for numeric score if JSON fails
            import re
            match = re.search(r'"score":\s*(\d+)', response)
            score = int(match.group(1)) if match else 50
            return {"score": score, "justification": "Score calculated via fallback parser."}

    def generate_cv(self, user_name: str, resume_text: str, linkedin_text: str, job_description: str):
        return self.chain.invoke({
            "user": user_name,
            "resume_text": resume_text,
            "linkedin_text": linkedin_text,
            "job_description": job_description
        })

    def get_followup_answers(self, optimized_resume: str, job_description: str):
        """Generates answers for 'Best Fit' and 'Why work here' based on the CV."""
        system_prompt = """
        You are a professional interview coach. 
        Based on the provided optimized Resume and Job Description, provide persuasive and authentic answers to two critical interview questions.
        
        Question 1: Why am I the best fit for this position?
        Question 2: Why do you want to work for this organization?
        
        Rules:
        1. Use the candidate's achievements and skills from the optimized resume.
        2. Align with the company's needs described in the job description.
        3. Be concise (max 3-4 sentences per answer).
        4. Return the answers as a JSON-like object with keys {{ "best_fit": "...", "why_organization": "..." }}.
        """
        
        user_prompt = """
        Job Description: {job_description}
        Optimized Resume: {optimized_resume}
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])
        
        # Use simple string parser and then handle potentially as json
        chain = prompt | self.llm | StrOutputParser()
        response = chain.invoke({
            "job_description": job_description,
            "optimized_resume": optimized_resume
        })
        
        try:
            # Attempt to strip md if it's there and parse
            cleaned_response = response.strip().replace('```json', '').replace('```', '')
            return json.loads(cleaned_response)
        except:
            return response # Fallback to raw text if parsing fails

    def get_optimization_summary(self, optimized_resume: str, job_description: str):
        """Generates a brief summary of changes made and keywords added."""
        system_prompt = """
        You are a resume expert. 
        Compare an optimized resume with a job description and identify:
        1. 3-4 key changes made to the content (be brief, e.g., 'Enhanced quantified achievements in Experience').
        2. Where these changes were primarily made (e.g., 'Professional Experience section').
        3. 5-7 key industry keywords that were integrated into the resume to match the job.
        
        Return the result as a JSON-like object with keys:
        {{
          "changes": ["brief change 1", "brief change 2", ...],
          "location": "where changes happened",
          "keywords": ["keyword1", "keyword2", ...]
        }}
        """
        
        user_prompt = """
        Job Description: {job_description}
        Optimized Resume: {optimized_resume}
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        response = chain.invoke({
            "job_description": job_description,
            "optimized_resume": optimized_resume
        })
        
        try:
            cleaned_response = response.strip().replace('```json', '').replace('```', '')
            return json.loads(cleaned_response)
        except:
            return response

# -----------------------
# AGENT CLASS FOR CHATBOT
# -----------------------

class LLM_Chat:
    def __init__(self, config: dict):
        self.config = config
        self.llm = self._initialize_llm()

    def _initialize_llm(self):
        # Use default enterprise and model from config
        default_enterprise = self.config.get("default_enterprise", "openai")
        default_model = self.config.get("default_model", "gpt-4o")

        # Priority 1: Match BOTH enterprise and model
        # Priority 2: Match just enterprise
        # Priority 3: Fallback to first resource
        resources = self.config.get("resources", [])
        resource = next(
            (r for r in resources if r.get("enterprise") == default_enterprise and r.get("model") == default_model),
            next(
                (r for r in resources if r.get("enterprise") == default_enterprise),
                resources[0] if resources else {}
            )
        )
        
        base_url = resource.get("base_url", "https://api.openai.com/v1")
        api_key = resource.get("api_key")

        # OpenRouter specific headers
        default_headers = {
            "HTTP-Referer": "https://github.com/bhuvanthirwani/ATS",
            "X-Title": "ATS Resume Tailoring System"
        }

        return ChatOpenAI(
            model=default_model,
            temperature=0.5,
            base_url=base_url,
            api_key=api_key,
            default_headers=default_headers if "openrouter.ai" in base_url else None
        )

    def get_chat_answer(self, final_text_prompt: list) -> list:

        prompt = ChatPromptTemplate.from_messages(final_text_prompt)
        chain = prompt | self.llm | StrOutputParser()

        return chain.invoke({})
