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
