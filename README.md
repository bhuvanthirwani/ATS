
<div align="center">

# 🚀 ATS Resume Optimzer & Tailor Agent

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Powered by LangChain](https://img.shields.io/badge/Powered%20by-LangChain-orange)](https://langchain.com/)

**The Ultimate AI-Powered Career Assistant**  
*Tailor your resume to any job description in seconds using State-of-the-Art LLMs.*

[Features](#-key-features) • [Quick Start](#-quick-start) • [Configuration](#-configuration) • [Models](#-supported-models)

</div>

---

## 🌟 Overview

**ATS Resume Optimizer** is a next-generation agentic application that transforms your generic resume into a **highly tailored, ATS-compliant PDF** targeting a specific job description. 

Built with **Streamlit** and **LangChain**, it leverages powerful models like **Google Gemini Pro** and **GPT-4o** to re-write content, optimize keywords, and generate professional LaTeX documents automatically.

## ✨ Key Features

### 🧠 Intelligent Optimization
- **Multi-Model Support**: Use Google Gemini (Flash/Pro), GPT-4o, Claude 3.5 Sonnet, and more.
- **Context-Aware Rewriting**: The AI understands your experience and the job requirements to highlight the *right* skills.
- **ATS Scoring**: Get instant feedback on how well your resume matches the job.

### 🎨 Premium User Experience
- **Multi-User Workspace**: Personal login separates your profiles, templates, and history.
- **Visual Dashboard**: Glassmorphism UI for a modern, focused usage.
- **History Tracking**: Never lose a tailored resume; access all your past generations in one place.

### 🛠️ Total Control
- **Prompt Engineering UI**: Edit the exact system prompts used by the AI directly from the settings.
- **Model Inventory**: Manage your own API keys and choose from a vast catalog of supported models.
- **Template Management**: Upload your own LaTeX templates or use built-in ones.

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/bhuvanthirwani/ATS.git
cd ATS
pip install -r requirements.txt
pip install langchain-google-genai langchain-openai
```

### 2. Run the App

```bash
streamlit run app.py
```

### 3. Login
Enter any unique **User ID** (e.g., `jdoe`) to create your private workspace.

---

## 📸 Architecture

### File-Based Persistence
All user data is stored locally for privacy and portability:

```text
users/
├── jdoe/
│   ├── config.json         # Your preferences & model keys
│   ├── linkedin_profiles/  # Uploaded PDF profiles
│   ├── templates/          # LaTeX templates
│   └── output/             # Generated Resumes
```

### Dynamic Model Catalog
Connect to **Google Gemini**, **OpenAI**, or **OpenRouter** seamlessly through the `configs/llms.json` catalog.

---

## 💎 Supported Models

| Provider | Model | Special Features |
|:---|:---|:---|
| **Google** | Gemini 2.0 Flash | Fast, long context, multimodal |
| **Google** | Gemini 2.5 Pro | High reasoning capability |
| **OpenRouter** | GPT-4o | Best-in-class instruction following |
| **OpenRouter** | Claude 3.5 Sonnet | Natural writing style |
| **OpenRouter** | Llama 3.1 405B | Open source giant |

---

<div align="center">
    <h3>Ready to land your dream job?</h3>
    <p><i>Start optimizing today.</i></p>
</div>
