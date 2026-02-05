import os
import subprocess
import pathlib
from fastapi import HTTPException

class CompilerService:
    def __init__(self, output_dir: str = "/app/data"):
        self.output_base = pathlib.Path(output_dir)

    def compile_resume(self, user_id: str, tex_content: str, filename_base: str, workflow_id: str = None, version: str = None):
        # Determine paths
        # Architecture Change: If workflow_id provided, use structured path:
        # /app/data/users/{user_id}/output/{workflow_id}/{version}/
        
        if workflow_id and version:
            output_dir = self.output_base / "users" / user_id / "output" / workflow_id / version
        else:
            # Fallback for legacy calls (if any)
            output_dir = self.output_base / "users" / user_id / "output"
            
        output_dir.mkdir(parents=True, exist_ok=True)
        
        tex_file = output_dir / f"{filename_base}.tex"
        pdf_file = output_dir / f"{filename_base}.pdf"
        log_file = output_dir / f"{filename_base}.log"
        
        # Write .tex file
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(tex_content)
            
        # Compile
        # We run pdflatex twice for proper formatting sometimes
        # We also capture all auxiliary files in the same dir
        cmd = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-output-directory", str(output_dir),
            str(tex_file)
        ]
        
        try:
            # First pass
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            
            # Simple check, if simple resume one pass might be enough. 
            # If complex referencing, might need second pass. For now, doing one pass for speed unless requested.
            
            if result.returncode != 0:
                # Capture log content for debugging
                log_content = ""
                if log_file.exists():
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        log_content = f.read()[-2000:] # Last 2000 chars
                
                return {
                    "success": False, 
                    "error": result.stdout.decode('utf-8', errors='ignore')[-500:],
                    "log_tail": log_content
                }
                
            return {
                "success": True, 
                "pdf_path": str(pdf_file),
                "tex_path": str(tex_file),
                "log_path": str(log_file)
            }
        except Exception as e:
             return {"success": False, "error": str(e)}
