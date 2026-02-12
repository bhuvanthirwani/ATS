import os
import asyncio
from celery import Celery
from src.services.llm_service import LLMService, OptimizationResult
from src.services.compiler_service import CompilerService
from src.services.file_service import FileService

# Celery Configuration
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery_app = Celery("ats_worker", broker=redis_url, backend=redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task(bind=True)
def optimize_resume_task(
    self, 
    workspace_id: str, 
    template_filename: str, 
    profile_filename: str, 
    job_description: str, 
    analysis_result: dict, 
    output_filename: str, 
    ignored_keywords: list[str]
):
    """
    Celery task to handle resume optimization in the background.
    """
    try:
        # Initialize Services
        file_service = FileService()
        llm_service = LLMService()
        compiler_service = CompilerService()

        # 1. Get Config
        config = file_service.get_config(workspace_id)
        
        # 2. Get Files
        resume_path = file_service.get_file_content(workspace_id, template_filename, "template")
        with open(resume_path, "r", encoding="utf-8") as f:
            resume_text = f.read()
            
        import pypdf
        profile_path = file_service.get_file_content(workspace_id, profile_filename, "profile")
        reader = pypdf.PdfReader(str(profile_path))
        profile_text = ""
        for page in reader.pages:
            profile_text += page.extract_text()
            
        # 3. Optimize (Async call needs to be run in sync context)
        # We use asyncio.run because Celery workers are synchronous by default
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        opt_result: OptimizationResult = loop.run_until_complete(
            llm_service.optimize_resume(
                config, 
                analysis_result, 
                resume_text, 
                job_description,
                ignored_keywords
            )
        )
        loop.close()
        
        # 4. Compile (New Architecture)
        import uuid
        workflow_id = str(uuid.uuid4())
        version = "v1"
        
        # Sanitize Latex (Remove null bytes that might come from LLM)
        sanitized_latex = opt_result.new_latex_code.replace("\x00", "").replace("\u0000", "")
        
        compile_result = compiler_service.compile_resume(
            workspace_id, 
            sanitized_latex, 
            output_filename, # e.g. "Resume_Optimized_v1"
            workflow_id=workflow_id,
            version=version
        )
        
        return {
            "status": "completed",
            "optimization": opt_result.model_dump(),
            "compilation": compile_result,
            "workflow_id": workflow_id,
            "version": version
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "failed",
            "error": str(e)
        }
