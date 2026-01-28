FROM python:3.11-slim

# Install system dependencies
# texlive-latex-base: Basic LaTeX support
# texlive-fonts-recommended, texlive-fonts-extra: Fonts often used in resumes
# texlive-latex-extra: Additional LaTeX packages likely used in templates
RUN apt-get update && apt-get install -y \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
