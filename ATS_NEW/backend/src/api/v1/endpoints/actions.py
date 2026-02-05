from fastapi import APIRouter, Depends, HTTPException, Body
from src.deps import get_current_workspace
from src.services.file_service import FileService
from src.services.llm_service import LLMService
from src.services.compiler_service import CompilerService
from pydantic import BaseModel

router = APIRouter()

class AnalyzeRequest(BaseModel):
    template_filename: str = ""
    profile_filename: str = ""
    job_description: str

class OptimizeRequest(BaseModel):
    template_filename: str
    profile_filename: str
    job_description: str
    analysis_result: dict
    output_filename: str
    ignored_keywords: list[str] = [] # Optional list of keywords to remove

class RefineRequest(BaseModel):
    current_tex_filename: str
    user_request: str
    output_filename: str
    job_description: str # For re-analysis

@router.post("/analyze")
async def analyze_resume(
    req: AnalyzeRequest,
    workspace_id: str = Depends(get_current_workspace),
    file_service: FileService = Depends(lambda: FileService()),
    llm_service: LLMService = Depends(lambda: LLMService())
):
    # 1. Get Config
    config = file_service.get_config(workspace_id)
    
    # 2. Get File Content
    try:
        if req.profile_filename and req.profile_filename.lower().endswith(".pdf"):
             # Analyze the Profile PDF
            import pypdf
            profile_path = file_service.get_file_content(workspace_id, req.profile_filename, "profile")
            reader = pypdf.PdfReader(str(profile_path))
            resume_text = ""
            for page in reader.pages:
                resume_text += page.extract_text()
        elif req.template_filename:
            # Fallback to Template
            resume_path = file_service.get_file_content(workspace_id, req.template_filename, "template")
            with open(resume_path, "r", encoding="utf-8") as f:
                resume_text = f.read()
        else:
            raise HTTPException(status_code=400, detail="Must provide either profile_filename or template_filename")

    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File error: {str(e)}")

    # 3. Call LLM
    try:
        result = await llm_service.analyze_resume(config, resume_text, req.job_description)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")

@router.post("/optimize")
async def optimize_resume(
    req: OptimizeRequest,
    workspace_id: str = Depends(get_current_workspace),
    file_service: FileService = Depends(lambda: FileService()),
    llm_service: LLMService = Depends(lambda: LLMService()),
    compiler_service: CompilerService = Depends(lambda: CompilerService())
):
    # 1. Get Config
    config = file_service.get_config(workspace_id)
    
    # 2. Get Files
    try:
        resume_path = file_service.get_file_content(workspace_id, req.template_filename, "template")
        with open(resume_path, "r", encoding="utf-8") as f:
            resume_text = f.read()
            
        # LinkedIn profile (PDF) text extraction would go here
        # For now, we assume simple text or unimplemented PDF parse as it requires extra lib deps we added (pypdf)
        # We will add simple pypdf extraction here
        import pypdf
        profile_path = file_service.get_file_content(workspace_id, req.profile_filename, "profile")
        reader = pypdf.PdfReader(str(profile_path))
        profile_text = ""
        for page in reader.pages:
            profile_text += page.extract_text()
            
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File error: {str(e)}")
        
    # 3. Optimize
    try:
        opt_result = await llm_service.optimize_resume(
            config, 
            req.analysis_result, 
            resume_text, 
            req.job_description,
            req.ignored_keywords
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")
        
    # 4. Compile
    compile_result = compiler_service.compile_resume(workspace_id, opt_result.new_latex_code, req.output_filename)
    
    return {
        "optimization": opt_result,
        "compilation": compile_result
    }

@router.post("/refine")
async def refine_resume(
    req: RefineRequest,
    workspace_id: str = Depends(get_current_workspace),
    file_service: FileService = Depends(lambda: FileService()),
    llm_service: LLMService = Depends(lambda: LLMService()),
    compiler_service: CompilerService = Depends(lambda: CompilerService())
):
    # 1. Config
    config = file_service.get_config(workspace_id)
    
    # 2. Get Current Tex
    # The current tex is in /output not /templates usually
    try:
        tex_path = file_service.get_file_content(workspace_id, req.current_tex_filename, "output")
        # Ensure it's a .tex file
        if not str(tex_path).endswith('.tex'):
             tex_path = str(tex_path) + ".tex"
             
        with open(tex_path, "r", encoding="utf-8") as f:
            current_tex = f.read()
    except Exception as e:
        # Fallback to try without .tex extension or different path lookup? 
        # For now assume filename passed is correct
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")

    # 3. Refine (LLM)
    try:
        refine_result = await llm_service.refine_resume(config, current_tex, req.user_request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")

    # 4. Compile New Version
    compile_result = compiler_service.compile_resume(workspace_id, refine_result.new_latex_code, req.output_filename)
    
    # 5. Re-Analyze (Auto-Score)
    # We re-analyze the NEW latex against the SAME job description
    try:
        new_analysis = await llm_service.analyze_resume(config, refine_result.new_latex_code, req.job_description)
    except Exception:
        new_analysis = None # Non-blocking if analysis fails

    return {
        "refinement": refine_result,
        "compilation": compile_result,
        "analysis": new_analysis
    }
