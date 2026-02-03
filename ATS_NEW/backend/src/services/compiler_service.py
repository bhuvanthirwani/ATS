import os
import subprocess
import pathlib
from fastapi import HTTPException

class CompilerService:
    def __init__(self, output_dir: str = "/app/data"):
        self.output_base = pathlib.Path(output_dir)

    def compile_resume(self, user_id: str, tex_content: str, filename_base: str):
        # Determine paths
        user_output_dir = self.output_base / "users" / user_id / "output"
        user_output_dir.mkdir(parents=True, exist_ok=True)
        
        tex_file = user_output_dir / f"{filename_base}.tex"
        pdf_file = user_output_dir / f"{filename_base}.pdf"
        
        # Write .tex file
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(tex_content)
            
        # Compile
        # We run pdflatex twice for proper formatting sometimes, but once is usually enough for simple resume
        cmd = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-output-directory", str(user_output_dir),
            str(tex_file)
        ]
        
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            if result.returncode != 0:
                # Basic error extraction
                return {"success": False, "error": result.stdout.decode('utf-8')[-500:]}
            return {"success": True, "pdf_path": str(pdf_file)}
        except Exception as e:
             return {"success": False, "error": str(e)}
