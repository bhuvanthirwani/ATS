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
    ignored_keywords: list[str],
    manual_keywords: list[str],
    workflow_id: str # New Argument
):
    """
    Celery task to handle resume optimization in the background.
    """
    # DB Setup for Worker
    from src.db.session import SessionLocal
    from src.db.models import Job
    db = SessionLocal()
    
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
            
        # 3. Optimize
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        opt_result: OptimizationResult = loop.run_until_complete(
            llm_service.optimize_resume(
                config, 
                analysis_result, 
                resume_text, 
                job_description,
                ignored_keywords,
                manual_keywords
            )
        )
        loop.close()
        
        # 4. Compile
        import uuid
        # We reuse the workflow_id passed from API if possible, but for versioning logic we might need sub-ids
        # For now, let's keep the file structure logic
        # Architecture Note: The "Workflow" in DB tracks the session. 
        # The file system "workflow_id" was used for folder separation. 
        # Let's align them: usage of workflow_id in file path corresponds to DB workflow_id.
        
        version = "v1" # Initial optimization is always v1
        
        sanitized_latex = opt_result.new_latex_code.replace("\x00", "").replace("\u0000", "")
        
        compile_result = compiler_service.compile_resume(
            workspace_id, 
            sanitized_latex, 
            output_filename, 
            workflow_id=workflow_id,
            version=version
        )
        
        result_data = {
            "optimization": opt_result.model_dump(),
            "compilation": compile_result,
            "workflow_id": workflow_id,
            "version": version
        }
        
        # Update DB - Success
        job = db.query(Job).filter(Job.id == self.request.id).first()
        if job:
            job.status = "SUCCESS"
            job.result_data = result_data
            db.commit()
            
        return {
            "status": "completed",
            **result_data
        }

    except Exception as e:
        db.rollback() # Critical: Rollback previous failed transaction
        import traceback
        traceback.print_exc()
        
        try:
            # Update DB - Failure
            job = db.query(Job).filter(Job.id == self.request.id).first()
            if job:
                job.status = "FAILED"
                job.error_message = str(e)
                db.commit()
        except Exception as inner_e:
            print(f"Failed to update job status to FAILED: {inner_e}")
            
        return {
            "status": "failed",
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(bind=True)
def refine_resume_task(
    self,
    workspace_id: str,
    workflow_id: str,
    current_version: str,
    current_tex_filename: str,
    user_request: str,
    output_filename: str,
    job_description: str,
    target_version: str = None
):
    """
    Celery task to handle resume refinement in the background.
    """
    from src.db.session import SessionLocal
    from src.db.models import Job
    import re
    db = SessionLocal()

    try:
        file_service = FileService()
        llm_service = LLMService()
        compiler_service = CompilerService()

        # 1. Config
        config = file_service.get_config(workspace_id)

        # 2. Get current TeX
        tex_path = file_service.get_file_content(
            workspace_id,
            current_tex_filename + ".tex",
            "workflow_output",
            workflow_id=workflow_id,
            version=current_version
        )
        with open(tex_path, "r", encoding="utf-8") as f:
            current_tex = f.read()

        # 3. Refine (LLM) - run async in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        refine_result = loop.run_until_complete(
            llm_service.refine_resume(config, current_tex, user_request)
        )

        # 4. Determine new version
        if target_version:
            new_version = target_version
        else:
            match = re.search(r"v(\d+)", current_version)
            if match:
                v_num = int(match.group(1)) + 1
                new_version = f"v{v_num}"
            else:
                new_version = "v2"

        # 5. Compile
        sanitized_latex = refine_result.new_latex_code.replace("\x00", "").replace("\u0000", "")
        compile_result = compiler_service.compile_resume(
            workspace_id,
            sanitized_latex,
            output_filename,
            workflow_id=workflow_id,
            version=new_version
        )

        # 6. Re-Analyze (Auto-Score)
        try:
            new_analysis = loop.run_until_complete(
                llm_service.analyze_resume(config, refine_result.new_latex_code, job_description)
            )
        except Exception as e:
            print(f"[ERROR] Re-analysis failed: {e}")
            import traceback
            traceback.print_exc()
            new_analysis = None

        loop.close()

        result_data = {
            "refinement": refine_result.model_dump() if hasattr(refine_result, 'model_dump') else {"summary": str(refine_result), "new_latex_code": refine_result.new_latex_code},
            "compilation": compile_result,
            "analysis": new_analysis.model_dump() if new_analysis and hasattr(new_analysis, 'model_dump') else new_analysis,
            "workflow_id": workflow_id,
            "version": new_version
        }

        # Update DB - Success
        job = db.query(Job).filter(Job.id == self.request.id).first()
        if job:
            job.status = "SUCCESS"
            job.result_data = result_data
            db.commit()

        return {
            "status": "completed",
            **result_data
        }

    except Exception as e:
        db.rollback() # Critical: Rollback previous failed transaction
        import traceback
        traceback.print_exc()

        try:
            # Re-query job in clean session state
            job = db.query(Job).filter(Job.id == self.request.id).first()
            if job:
                job.status = "FAILED"
                job.error_message = str(e)
                # Workflow doesn't have status field, relying on Job status for UI
                db.commit()
        except Exception as inner_e:
            print(f"Failed to update job status to FAILED: {inner_e}")

        return {
            "status": "failed",
            "error": str(e)
        }
    finally:
        db.close()
