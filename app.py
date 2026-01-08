import streamlit as st

st.set_page_config(
    page_title="ATS Resume Tailoring System",
    page_icon="📄",
    layout="wide"
)

# Premium UI Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap');
    
    html, body, [data-testid="stAppViewBlockContainer"] {
        font-family: 'Outfit', sans-serif;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
    }
    
    .main {
        background: transparent;
    }
    
    [data-testid="stHeader"] {
        background: rgba(15, 23, 42, 0.8);
        backdrop-filter: blur(10px);
    }
    
    .stButton>button {
        border-radius: 12px;
        background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%) !important;
        color: white !important;
        border: none !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
        width: 100%;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.4) !important;
    }
    
    .glass-card {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    
    [data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        background: linear-gradient(90deg, #3b82f6, #60a5fa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Animation */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .fade-in {
        animation: fadeIn 0.8s ease-out;
    }
</style>
""", unsafe_allow_html=True)

import os, time, pathlib, json
import pandas as pd
from jinja2 import Environment, FileSystemLoader
# weasyprint removed in favor of LaTeX

# INTERNAL LIBRARIES
from file_management import *
from state_machine import ResumeOptimizerStateMachine
from llm_agent import *
import subprocess

# --- LOGGER CLASS ------------------------------------
class AppLogger:
    def __init__(self, placeholder=None):
        self.placeholder = placeholder
        self.logs = []

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.logs.append(formatted_message)
        # Display logs only if placeholder is available
        if self.placeholder:
            self.placeholder.code("\n".join(self.logs[::-1]), language="text")

    def clear(self):
        self.logs = []
        if self.placeholder:
            self.placeholder.empty()

# Add the path to the GTK3 bin folder removed

# --- AGENT & STATE INITIALIZATION ---------------------
if "logger" not in st.session_state:
    st.session_state.logger = AppLogger()

if "machine" not in st.session_state:
    st.session_state.machine = ResumeOptimizerStateMachine()

machine = st.session_state.machine

# Paths and Directories
project_root = pathlib.Path(__file__).parent.absolute()
output_path = project_root / "output"
output_path.mkdir(exist_ok=True)
output_dir = str(output_path)
template_dir = str(project_root / "templates")

# Config Loading
CONFIG_PATH = os.path.join('configs', 'staging.json')
with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

# Initialize Database
init_db(config)

# Chat Model Prompt
starting_chat_prompt_model = """You are a helpful assistant specialized in career assistance.Your goal is to provide clear,
actionable, and practical advice to help users present themselves at their best,
land interviews, and succeed in their career transitions.
Take the following information as reference for the candidate and opportunity.

--- Candidate Resume ---
{resume_text}

--- Linkedin Export ---
{linkedin_text}

--- Job Description ---
{job_description}
"""

# Session State defaults
states_to_init = {
    "user_name": "DefaultUser",
    "job_id": None,
    "opt_summary": None,
    "resume_text": "",
    "linkedin_text": "",
    "selected_template_path": None,
    "selected_linkedin_path": None,
    "generated_cv": None,
    "followup_answers": None,
    "initial_ats_score": None,
    "final_ats_score": None,
    "chat_history": []
}
for key, val in states_to_init.items():
    if key not in st.session_state or st.session_state[key] is None:
        st.session_state[key] = val

# --- UI LAYOUT & MODERNIZATION -------------------------
if "show_log" not in st.session_state:
    st.session_state.show_log = False

@st.dialog("📋 System Activity Log")
def show_log_dialog():
    st.code("\n".join(st.session_state.logger.logs[::-1]), language="text")

# Sidebar for auxiliary controls
with st.sidebar:
    st.image("https://img.icons8.com/?size=100&id=12150&format=png&color=000000", width=100)
    st.title("ATS Agent")
    st.markdown("---")
    if st.button("🔍 View Technical Logs"):
        show_log_dialog()
    st.markdown("---")
    st.info("Tailor your professional presence with AI-driven precision.")

# Main content area
st.markdown('<div class="fade-in">', unsafe_allow_html=True)

# Step 1: Initialization logic
if machine.state == "start":
    machine.state = "waiting_job_description"
    st.rerun()

# Step 2: Main Input Page
elif machine.state == "waiting_job_description":
    st.subheader("ATS Optimization Configuration")
    
    with st.container():
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        job_description_text = st.text_area("📋 Paste Job Description here:", height=300, 
                                         placeholder="Enter the full job description to optimize your resume against...")
        
        col1, col2 = st.columns(2)
        with col1:
            all_templates = [f for f in os.listdir(template_dir) if f.endswith(('.txt', '.tex'))]
            selected_template = st.selectbox("📄 Select Base LaTeX Template", all_templates)
        with col2:
            linkedin_profiles_dir = os.path.join(project_root, "linkedin_profiles")
            all_linkedin_pdfs = [f for f in os.listdir(linkedin_profiles_dir) if f.endswith('.pdf')]
            selected_linkedin = st.selectbox("🔗 Select LinkedIn Profile (PDF)", all_linkedin_pdfs)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🚀 Optimize My Resume"):
        if job_description_text.strip():
            st.session_state.selected_job_text = job_description_text
            st.session_state.selected_template = selected_template
            st.session_state.selected_template_path = os.path.join(template_dir, selected_template)
            st.session_state.selected_linkedin_path = os.path.join(linkedin_profiles_dir, selected_linkedin)
            st.session_state.job_id = f"job_{int(time.time())}"
            st.session_state.logger.log(f"Optimization session initialized for {st.session_state.user_name} (Job ID: {st.session_state.job_id})")
            machine.next("job_description_uploaded")
            st.rerun()
        else:
            st.error("Please provide a job description!")

# Step 3: LLM Optimization Process
elif machine.state == "processing_llm":
    with st.status("🔮 AI Resume Agent at work...", expanded=True) as status:
        msg = "Initializing AI Optimized Pipeline..."
        st.write(msg)
        st.session_state.logger.log(msg)
        llm_agent = LLMAgent(config)
        
        # Scoring Initial
        msg = "Evaluating current resume alignment..."
        st.write(msg)
        st.session_state.logger.log(msg)
        if not st.session_state.resume_text:
            st.session_state.resume_text = extract_text_from_file(st.session_state.selected_template_path)
        st.session_state.initial_ats_score = llm_agent.get_ats_score(st.session_state.resume_text, st.session_state.selected_job_text)
        st.session_state.logger.log(f"Initial ATS Match: {st.session_state.initial_ats_score.get('score', 0)}%")
        
        # Optimization
        msg = "Re-engineering CV content for maximum impact..."
        st.write(msg)
        st.session_state.logger.log(msg)
        if not st.session_state.linkedin_text:
            st.session_state.linkedin_text = extract_text_from_pdf(st.session_state.selected_linkedin_path)
            
        optimized_latex = llm_agent.optimize_latex(
            st.session_state.resume_text,
            st.session_state.resume_text,
            st.session_state.linkedin_text,
            st.session_state.selected_job_text
        )
        st.session_state.logger.log("LaTeX optimization complete.")
        
        # Cleaning up potential MD blocks
        if optimized_latex.strip().startswith("```"):
            optimized_latex = optimized_latex.split("\n", 1)[1].rsplit("\n", 1)[0]
        
        # Compilation
        msg = "Generating high-fidelity PDF asset..."
        st.write(msg)
        st.session_state.logger.log(msg)
        base_name = f'Resume_{st.session_state.user_name}_{st.session_state.job_id}'
        output_tex_path = os.path.join(output_dir, f'{base_name}.tex')
        with open(output_tex_path, 'w', encoding='utf-8') as f: f.write(optimized_latex)
        
        latex_compiler = config.get("database", {}).get("latex_compiler", "pdflatex")
        st.session_state.logger.log(f"Running LaTeX compiler: {latex_compiler}")
        result = subprocess.run([latex_compiler, "-interaction=nonstopmode", f"{base_name}.tex"],
                               cwd=output_dir, capture_output=True, text=True, shell=True)
        
        if result.returncode != 0:
            st.session_state.logger.log(f"LaTeX Warning: {result.stderr[:200]}...")
        else:
            st.session_state.logger.log("PDF compiled successfully.")
        
        # Metrics
        msg = "Finalizing career metrics and coaching insights..."
        st.write(msg)
        st.session_state.logger.log(msg)
        st.session_state.opt_summary = llm_agent.get_optimization_summary(optimized_latex, st.session_state.selected_job_text)
        st.session_state.final_ats_score = llm_agent.get_ats_score(optimized_latex, st.session_state.selected_job_text)
        st.session_state.followup_answers = llm_agent.get_followup_answers(optimized_latex, st.session_state.selected_job_text)
        st.session_state.logger.log(f"Final ATS Match: {st.session_state.final_ats_score.get('score', 0)}%")
        
        status.update(label="✅ Optimization Complete!", state="complete", expanded=False)
        st.session_state.logger.log("Pipeline finished successfully.")
        time.sleep(1)
        machine.next("finished")
        st.rerun()

# Step 4: Finished Results
elif machine.state == "job_exploration":
    st.header("✨ Your Tailored Career Assets")
    
    base_name = f'Resume_{st.session_state.user_name}_{st.session_state.job_id}'
    pdf_path = os.path.join(output_dir, f'{base_name}.pdf')

    # Metrics Section
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    m1, m2 = st.columns(2)
    with m1:
        if st.session_state.initial_ats_score:
            st.metric("📊 Initial Match", f"{st.session_state.initial_ats_score.get('score', 0)}%")
            st.caption(f"_{st.session_state.initial_ats_score.get('justification', '')}_")
    with m2:
        if st.session_state.final_ats_score:
            score = st.session_state.final_ats_score.get("score", 0)
            delta = score - st.session_state.initial_ats_score.get("score", 0) if st.session_state.initial_ats_score else 0
            st.metric("🚀 Post-Optimization", f"{score}%", delta=f"+{delta}%")
            st.caption(f"_{st.session_state.final_ats_score.get('justification', '')}_")
    st.markdown('</div>', unsafe_allow_html=True)

    # Actions Section
    c1, c2 = st.columns([3, 1])
    with c1:
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.download_button(label="📥 Download Tailored PDF Resume", data=f, 
                                 file_name="Optimized_Resume.pdf", mime="application/pdf")
    with c2:
        if st.button("🔄 New Optimization"):
            machine.reset()
            st.rerun()

    # Insights Section
    st.divider()
    ans_col, change_col, key_col = st.columns(3)
    
    with ans_col:
        st.markdown('<div class="glass-card" style="height: 100%;">', unsafe_allow_html=True)
        st.subheader("💡 Coaching Insights")
        answers = st.session_state.followup_answers
        if isinstance(answers, dict):
            st.markdown("**Best Fit:**")
            st.info(answers.get("best_fit", "Pending..."))
            st.markdown("**Motivation:**")
            st.info(answers.get("why_organization", "Pending..."))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with change_col:
        st.markdown('<div class="glass-card" style="height: 100%;">', unsafe_allow_html=True)
        st.subheader("🛠️ Changes")
        summary = st.session_state.opt_summary
        if isinstance(summary, dict):
            st.markdown(f"**Focus:** {summary.get('location', 'Global Match')}")
            for change in summary.get('changes', []):
                st.write(f"• {change}")
        st.markdown('</div>', unsafe_allow_html=True)

    with key_col:
        st.markdown('<div class="glass-card" style="height: 100%;">', unsafe_allow_html=True)
        st.subheader("🔑 Keywords")
        if isinstance(summary, dict):
            for kw in summary.get('keywords', []):
                st.markdown(f"`{kw}`")
        st.markdown('</div>', unsafe_allow_html=True)

    # Chat Section - Full Width
    st.divider()
    st.subheader(f"💬 Chat with {config.get('default_model', 'gpt-4o')}")

    # Initialize or load chat history
    if "chat_history" not in st.session_state or not st.session_state.chat_history:
        st.session_state.chat_history = [
            {
                "role": "system",
                "content": starting_chat_prompt_model.format(
                    resume_text=st.session_state.resume_text,
                    linkedin_text=st.session_state.linkedin_text,
                    job_description=st.session_state.selected_job_text
                )
            }
        ]

    # Initialize the LLM Chat Agent
    llm_chat_agent = LLM_Chat(config)

    # Display chat messages (skip system prompt in display)
    if st.session_state.chat_history:
        for message in st.session_state.chat_history:
            if message["role"] != "system":
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

    # Handle chat input
    if prompt := st.chat_input("Ask me anything about your career path..."):
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        # Display user message and rerun
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Assistant is thinking..."):
            assistant_response = llm_chat_agent.get_chat_answer(final_text_prompt=st.session_state.chat_history)

        # Add assistant response to chat history
        st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})
        st.rerun()
