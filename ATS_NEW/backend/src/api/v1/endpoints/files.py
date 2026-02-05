from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from typing import List
from src.deps import get_current_workspace
from src.services.file_service import FileService
from fastapi.responses import FileResponse

router = APIRouter()

@router.get("/templates")
async def list_templates(workspace_id: str = Depends(get_current_workspace), service: FileService = Depends(lambda: FileService())):
    return service.list_files(workspace_id, "template")

@router.post("/templates")
async def upload_template(
    file: UploadFile = File(...), 
    workspace_id: str = Depends(get_current_workspace), 
    service: FileService = Depends(lambda: FileService())
):
    return await service.upload_file(workspace_id, file, "template")

@router.delete("/templates/{filename}")
async def delete_template(filename: str, workspace_id: str = Depends(get_current_workspace), service: FileService = Depends(lambda: FileService())):
    return service.delete_file(workspace_id, filename, "template")

@router.get("/workflows/{workflow_id}/{version}/{filename}")
async def get_workflow_file(
    workflow_id: str, 
    version: str, 
    filename: str, 
    workspace_id: str = Depends(get_current_workspace), 
    service: FileService = Depends(lambda: FileService())
):
    """
    Retrieve a file (pdf, tex, log) for a specific workflow version.
    """
    file_path = service.get_file_content(workspace_id, filename, "workflow_output", workflow_id=workflow_id, version=version)
    return FileResponse(file_path)

@router.get("/profiles")
async def list_profiles(workspace_id: str = Depends(get_current_workspace), service: FileService = Depends(lambda: FileService())):
    return service.list_files(workspace_id, "profile")

@router.post("/profiles")
async def upload_profile(
    file: UploadFile = File(...), 
    workspace_id: str = Depends(get_current_workspace), 
    service: FileService = Depends(lambda: FileService())
):
    return await service.upload_file(workspace_id, file, "profile")

@router.delete("/profiles/{filename}")
async def delete_profile(filename: str, workspace_id: str = Depends(get_current_workspace), service: FileService = Depends(lambda: FileService())):
    return service.delete_file(workspace_id, filename, "profile")

@router.get("/config")
async def get_config(workspace_id: str = Depends(get_current_workspace), service: FileService = Depends(lambda: FileService())):
    return service.get_config(workspace_id)

@router.post("/config")
async def update_config(config: dict, workspace_id: str = Depends(get_current_workspace), service: FileService = Depends(lambda: FileService())):
    return service.update_config(workspace_id, config)

@router.get("/llm-catalog")
async def get_llm_catalog(service: FileService = Depends(lambda: FileService())):
    return service.get_llm_catalog()

@router.get("/history")
async def get_history(
    workspace_id: str = Depends(get_current_workspace), 
    service: FileService = Depends(lambda: FileService())
):
    return service.list_workflow_history(workspace_id)
