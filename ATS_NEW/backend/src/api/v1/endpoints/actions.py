from fastapi import APIRouter, Depends, HTTPException, Body
from src.deps import get_current_workspace
from src.services.file_service import FileService
from src.services.llm_service import LLMService
from src.services.compiler_service import CompilerService
from pydantic import BaseModel

router = APIRouter()

import uuid
import re

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
    workflow_id: str
    current_version: str # e.g. "v1"
    current_tex_filename: str # "Resume_Optimized_v1" (without extension)
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
        import traceback
        print(traceback.format_exc())
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
        
    # 4. Compile (New Architecture)
    workflow_id = str(uuid.uuid4())
    version = "v1"
    
    compile_result = compiler_service.compile_resume(
        workspace_id, 
        opt_result.new_latex_code, 
        req.output_filename, # e.g. "Resume_Optimized_v1"
        workflow_id=workflow_id,
        version=version
    )
    
    return {
        "optimization": opt_result,
        "compilation": compile_result,
        "workflow_id": workflow_id,
        "version": version
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
    
    # 2. Get Current Tex from Workflow Storage
    try:
        # We need the tex file from the previous version
        tex_path = file_service.get_file_content(
            workspace_id, 
            req.current_tex_filename + ".tex", 
            "workflow_output", 
            workflow_id=req.workflow_id, 
            version=req.current_version
        )
             
        with open(tex_path, "r", encoding="utf-8") as f:
            current_tex = f.read()
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")

    # 3. Refine (LLM)
    try:
        refine_result = await llm_service.refine_resume(config, current_tex, req.user_request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")

    # 4. Determine New Version
    # e.g. "v1" -> "v2"
    match = re.search(r"v(\d+)", req.current_version)
    if match:
        v_num = int(match.group(1)) + 1
        new_version = f"v{v_num}"
    else:
        new_version = "v2" # Fallback

    # 5. Compile New Version
    compile_result = compiler_service.compile_resume(
        workspace_id, 
        refine_result.new_latex_code, 
        req.output_filename,
        workflow_id=req.workflow_id,
        version=new_version
    )
    
    # 6. Re-Analyze (Auto-Score)
    # We re-analyze the NEW latex against the SAME job description
    try:
        new_analysis = await llm_service.analyze_resume(config, refine_result.new_latex_code, req.job_description)
    except Exception:
        new_analysis = None

    return {
        "refinement": refine_result,
        "compilation": compile_result,
        "analysis": new_analysis,
        "workflow_id": req.workflow_id,
        "version": new_version
    }
