from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from src.deps import get_current_workspace, get_current_user
from src.db.session import get_db
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
    manual_keywords: list[str] = [] # Optional list of keywords to add manually

from typing import Optional

class RefineRequest(BaseModel):
    workflow_id: str
    current_version: str # e.g. "v1"
    current_tex_filename: str # "Resume_Optimized_v1" (without extension)
    user_request: str
    output_filename: str
    job_description: str # For re-analysis
    target_version: Optional[str] = None # NEW: Explicit version control

class CompileRequest(BaseModel):
    workflow_id: str
    latex_code: str
    target_version: str
    output_filename: str

# ... imports ...

# ... Models (AnalyzeRequest, OptimizeRequest) ...

# ... (RefineRequest, CompileRequest) ...

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
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 1. Create Workflow in DB
    from src.db.models import Workflow, Job
    import uuid
    
    workflow = Workflow(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        job_description=req.job_description,
        profile_filename=req.profile_filename,
        template_filename=req.template_filename
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    
    # 2. Enqueue Task
    from src.worker import optimize_resume_task
    import redis
    import os
    
    task = optimize_resume_task.delay(
        workspace_id=workspace_id,
        template_filename=req.template_filename,
        profile_filename=req.profile_filename,
        job_description=req.job_description,
        analysis_result=req.analysis_result,
        output_filename=req.output_filename,
        ignored_keywords=req.ignored_keywords,
        manual_keywords=req.manual_keywords,
        workflow_id=workflow.id # Pass DB ID
    )
    
    # 3. Create Job Record in DB
    job = Job(
        id=task.id,
        workflow_id=workflow.id,
        status="PENDING"
    )
    db.add(job)
    db.commit()
    
    return {
        "job_id": task.id,
        "workflow_id": workflow.id,
        "status": "processing"
    }

@router.get("/workflows")
def list_workflows(
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    from src.db.models import Workflow
    from sqlalchemy.orm import joinedload
    
    workflows = db.query(Workflow)\
        .options(joinedload(Workflow.jobs))\
        .filter(Workflow.user_id == current_user.id)\
        .order_by(Workflow.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    return workflows

@router.get("/workflows/{workflow_id}")
def get_workflow_details(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    from src.db.models import Workflow, Job
    from sqlalchemy.orm import joinedload
    
    workflow = db.query(Workflow)\
        .options(joinedload(Workflow.jobs))\
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)\
        .first()
        
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    return workflow

@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: str, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    from src.db.models import Job
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
         raise HTTPException(status_code=404, detail="Job not found")
         
    # Optional: Verify user ownership via workflow->user if strict security needed
    
    return {
        "job_id": job.id,
        "status": job.status,
        "result": job.result_data,
        "error": job.error_message,
        "workflow_id": job.workflow_id
    }

@router.post("/refine")
async def refine_resume(
    req: RefineRequest,
    workspace_id: str = Depends(get_current_workspace),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    from src.db.models import Job
    from src.worker import refine_resume_task

    # Determine target version
    if req.target_version:
        new_version = req.target_version
    else:
        match = re.search(r"v(\d+)", req.current_version)
        if match:
            v_num = int(match.group(1)) + 1
            new_version = f"v{v_num}"
        else:
            new_version = "v2"

    # Enqueue Celery Task
    task = refine_resume_task.delay(
        workspace_id=workspace_id,
        workflow_id=req.workflow_id,
        current_version=req.current_version,
        current_tex_filename=req.current_tex_filename,
        user_request=req.user_request,
        output_filename=req.output_filename,
        job_description=req.job_description,
        target_version=new_version
    )

    # Create Job Record in DB
    job = Job(
        id=task.id,
        workflow_id=req.workflow_id,
        status="PENDING"
    )
    db.add(job)
    db.commit()

    return {
        "job_id": task.id,
        "workflow_id": req.workflow_id,
        "version": new_version,
        "status": "processing"
    }

@router.post("/compile_new_version")
async def compile_manual_version(
    req: CompileRequest,
    workspace_id: str = Depends(get_current_workspace),
    compiler_service: CompilerService = Depends(lambda: CompilerService())
):
    """
    Manually compile a new version from provided LaTeX code (e.g. user edited).
    """
    # Sanitize
    sanitized_latex = req.latex_code.replace("\x00", "").replace("\u0000", "")
    
    compile_result = compiler_service.compile_resume(
        workspace_id, 
        sanitized_latex, 
        req.output_filename,
        workflow_id=req.workflow_id,
        version=req.target_version
    )
    
    return {
        "compilation": compile_result,
        "workflow_id": req.workflow_id,
        "version": req.target_version
    }

