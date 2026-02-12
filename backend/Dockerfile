FROM python:3.11-slim

# Install System Dependencies (including minimal TeX Live)
RUN apt-get update && apt-get install -y \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-latex-extra \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Requirements and Install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Source Code
COPY . .

# Environment Defaults
ENV PYTHONPATH=/app/src
ENV APP_ENV=production

# Healthcheck is defined in docker-compose, but good practice to have entry point
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
