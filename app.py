import streamlit as st

st.set_page_config(
    page_title="ATS Resume Tailoring System",
    page_icon="📄",
    layout="wide"
)

# Custom CSS for full width and removing scrollbars where possible
st.markdown("""
<style>
    [data-testid="stAppViewBlockContainer"] {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 3rem;
        padding-right: 3rem;
        max-width: 100%;
    }
    .stCodeBlock pre {
        height: 70vh !important;
    }
</style>
""", unsafe_allow_html=True)

import os, time, pathlib
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
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.logs = []

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.logs.append(formatted_message)
        # Display logs in reverse order (latest first) to keep visibility
        self.placeholder.code("\n".join(self.logs[::-1]), language="text")

    def clear(self):
        self.logs = []
        self.placeholder.empty()

# Add the path to the GTK3 bin folder removed

# Initializing the state machine
if "machine" not in st.session_state:
    st.session_state.machine = ResumeOptimizerStateMachine()

st.title("ATS TAILORING SYSTEM (LLM)")

machine = st.session_state.machine

# Create output directory if not exists
project_root = pathlib.Path(__file__).parent.absolute()
output_path = project_root / "output"
output_path.mkdir(exist_ok=True)
(output_path/".gitkeep").touch(exist_ok=True)

# --- GLOBAL VARIABLES USED FOR PDF GENERATION ----------
output_dir = str(output_path)
template_dir = str(project_root / "templates")
# SETTING UP JINJA2 ENVIRONMENT
env = Environment(loader=FileSystemLoader(template_dir))
template = env.get_template('cv_template.html')                                  # Custom-made HTML template for the generated PDF Resume

# --- CONTROL STATE INITIALIZATIONS - SESSION CONTROL ---
if "user_checked" not in st.session_state:
    st.session_state.user_checked = False
if "user_exists" not in st.session_state:
    st.session_state.user_exists = False
if "user_confirmed" not in st.session_state:
    st.session_state.user_confirmed = False
if "user_name" not in st.session_state or st.session_state.user_name is None:
    st.session_state.user_name = "DefaultUser"
if "job_id" not in st.session_state:
    st.session_state.job_id = None
if "opt_summary" not in st.session_state:
    st.session_state.opt_summary = None
# Initialize Session State
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "linkedin_text" not in st.session_state:
    st.session_state.linkedin_text = ""
if "selected_template_path" not in st.session_state:
    st.session_state.selected_template_path = None
if "selected_linkedin_path" not in st.session_state:
    st.session_state.selected_linkedin_path = None
if "generated_cv" not in st.session_state:
    st.session_state.generated_cv = None
if "followup_answers" not in st.session_state:
    st.session_state.followup_answers = None

# Skip the initial start page, go straight to job description
if machine.state == "start":
    machine.state = "waiting_job_description"

# --- UI LAYOUT ---------------------------------------
main_col, log_col = st.columns([2, 1])

with log_col:
    st.subheader("📝 Process Log")
    log_placeholder = st.empty()
    if "logger" not in st.session_state:
        st.session_state.logger = AppLogger(log_placeholder)
    else:
        # Re-attach the placeholder to the existing logger instance on rerun
        st.session_state.logger.placeholder = log_placeholder
    
logger = st.session_state.logger

with main_col:
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

# --- CONFIGURATION PATH -------------------------------
CONFIG_PATH = os.path.join('configs', 'staging.json')
with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

# Initialize Database
init_db(config)

# ------------------------------------
# APP FUNCTIONS TO IMPROVE READABILITY
# ------------------------------------
def display_jobs_with_selection(user_jobs):
    """Enhanced job selection UI with DataFrame display"""
    if not user_jobs:
        st.info("No existing jobs found for this user")
        return None

    jobs_df = pd.DataFrame(user_jobs,
                           columns=["ID", "Description", "Generated CV", "Created", "Last Modified"])

    st.dataframe(
        jobs_df,
        column_config={
            "ID": st.column_config.NumberColumn(width="small"),
            "Description": st.column_config.TextColumn(width="large"),
            "Generated CV": st.column_config.JsonColumn(),
            "Created": st.column_config.DatetimeColumn(),
            "Last Modified": st.column_config.DatetimeColumn()
        },
        hide_index=True,
        use_container_width=True
    )

    selected_id = st.selectbox(
        "Select job:",
        options=jobs_df["ID"].tolist(),
        format_func=lambda x: f"Job {x} - {jobs_df[jobs_df['ID'] == x]['Description'].iloc[0][:50]}..."
    )

    if st.button("Confirm Job Selection"):
        return selected_id
    return None

def show_loading_state():
    """Displays an animated loading screen"""
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i in range(100):
        progress_bar.progress(i + 1)
        status_text.text(f"Generating optimized CV... {i + 1}%")
        time.sleep(0.03)  # Adjust speed as needed

    progress_bar.empty()
    status_text.empty()

# --- MAIN EXECUTION ----------------------------------
with main_col:
    # Step 1: Redirect 'start' to 'waiting_job_description' (already handled in session state setup)
    if machine.state == "start":
        st.rerun()

    # Step 2: Main Input Page (Job Description + Template Selection + LinkedIn Profile)
    elif machine.state == "waiting_job_description":
        logger.log("Waiting for user inputs...")
        st.subheader("ATS Optimization Configuration")
        
        # 1. Job Description
        job_description_text = st.text_area("📋 Paste Job Description here:", height=300)
        
        col1, col2 = st.columns(2)
        
        # 2. Base Template Selection
        with col1:
            all_templates = [f for f in os.listdir(template_dir) if f.endswith(('.txt', '.tex'))]
            # Default to previous selection if available
            def_idx_t = 0
            if st.session_state.selected_template_path:
                t_name = os.path.basename(st.session_state.selected_template_path)
                if t_name in all_templates: def_idx_t = all_templates.index(t_name)
            selected_template = st.selectbox("📄 Select Base LaTeX Template", all_templates, index=def_idx_t)
            
        # 3. LinkedIn Profile Selection
        with col2:
            linkedin_profiles_dir = os.path.join(project_root, "linkedin_profiles")
            if not os.path.exists(linkedin_profiles_dir): os.makedirs(linkedin_profiles_dir)
            all_linkedin_pdfs = [f for f in os.listdir(linkedin_profiles_dir) if f.endswith('.pdf')]
            
            def_idx_l = 0
            if st.session_state.selected_linkedin_path:
                l_name = os.path.basename(st.session_state.selected_linkedin_path)
                if l_name in all_linkedin_pdfs: def_idx_l = all_linkedin_pdfs.index(l_name)
            selected_linkedin = st.selectbox("🔗 Select LinkedIn Profile (PDF)", all_linkedin_pdfs, index=def_idx_l)

        if st.button("🚀 Start Optimization", type="primary"):
            if job_description_text.strip() and selected_template and selected_linkedin:
                logger.log("Inputs confirmed. Initializing optimization...")
                template_path = os.path.join(template_dir, selected_template)
                linkedin_path = os.path.join(linkedin_profiles_dir, selected_linkedin)
                
                # Extract texts
                st.session_state.resume_text = extract_text_from_file(template_path)
                st.session_state.linkedin_text = extract_text_from_file(linkedin_path)
                st.session_state.selected_job_text = job_description_text
                st.session_state.selected_template = selected_template
                st.session_state.selected_template_path = template_path
                
                # Decoupled from DB flow for debugging
                st.session_state.job_id = f"job_{int(time.time())}"
                logger.log(f"Optimization session started: {st.session_state.job_id}")
                
                machine.next("job_description_uploaded")
                st.rerun()
            else:
                st.error("Please provide all required inputs.")

    # Step 3: Process the input with the LLM to generate a tailored resume and render it as a PDF
    elif machine.state == "processing_llm":
        logger.log("AI engine is running...")
        with st.spinner("Processing your data..."):
            try:
                llm_agent = LLMAgent(config)
                template_path = os.path.join(template_dir, st.session_state.selected_template)
                
                logger.log("Optimizing CV content with LLM...")
                with open(template_path, 'r', encoding='utf-8') as f:
                    latex_template = f.read()

                optimized_latex = llm_agent.optimize_latex(
                    latex_template,
                    st.session_state.resume_text,
                    st.session_state.linkedin_text,
                    st.session_state.selected_job_text
                )
                
                # Cleaning up potential MD blocks
                if optimized_latex.strip().startswith("```"):
                    optimized_latex = optimized_latex.split("\n", 1)[1].rsplit("\n", 1)[0]
                
                base_name = f'Resume_{st.session_state.user_name}_{st.session_state.job_id}'
                output_tex_path = os.path.join(output_dir, f'{base_name}.tex')
                with open(output_tex_path, 'w', encoding='utf-8') as f: f.write(optimized_latex)
                
                logger.log("Compiling LaTeX to PDF...")
                latex_compiler = config.get("database", {}).get("latex_compiler", "pdflatex")
                
                result = subprocess.run(
                    [latex_compiler, "-interaction=nonstopmode", f"{base_name}.tex"],
                    cwd=output_dir,
                    capture_output=True,
                    text=True,
                    shell=True
                )
                
                if result.returncode != 0:
                    logger.log(f"LaTeX Warning: {result.stderr[:200]}...")
                else:
                    logger.log("PDF compiled successfully!")

                logger.log("Generating optimization summary...")
                st.session_state.opt_summary = llm_agent.get_optimization_summary(optimized_latex, st.session_state.selected_job_text)

                logger.log("Generating follow-up interview answers...")
                st.session_state.followup_answers = llm_agent.get_followup_answers(optimized_latex, st.session_state.selected_job_text)
                logger.log("Job completed!")

                machine.next("finished")
                st.rerun()

            except Exception as e:
                logger.log(f"CRITICAL ERROR: {str(e)}")
                st.error(f"Generation failed: {str(e)}")
                machine.state = "waiting_job_description"

    # Step 4: Final step – download resume and interact with the LLM-powered chatbot
    elif machine.state == "job_exploration":
        st.subheader("🎉 Your Optimized Resume is Ready!")

        base_name = f'Resume_{st.session_state.user_name}_{st.session_state.job_id}'
        pdf_path = os.path.join(output_dir, f'{base_name}.pdf')

        col_dl, col_back = st.columns([4, 1])

        with col_dl:
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📥 Download Tailored PDF Resume",
                        data=f,
                        file_name=f"{base_name}.pdf",
                        mime="application/pdf"
                    )
            else:
                st.error("PDF file not found. Check the logs on the right.")

        with col_back:
            if st.button("🔄 New Optimization"):
                # Reset relevant session state but keep logger
                st.session_state.generated_cv = None
                st.session_state.followup_answers = None
                st.session_state.chat_history = None
                machine.reset()
                st.rerun()

        # Display Follow-up Answers
        if st.session_state.followup_answers:
            st.divider()
            
            # Use columns for 3 sections
            ans_col, change_col, key_col = st.columns(3)
            
            with ans_col:
                st.subheader("💡 Interview Preparation")
                answers = st.session_state.followup_answers
                if isinstance(answers, dict):
                    st.markdown("**Best Fit:**")
                    st.info(answers.get("best_fit", "Answer not generated."))
                    st.markdown("**Why this Organization:**")
                    st.info(answers.get("why_organization", "Answer not generated."))
                else:
                    st.write(answers)
            
            with change_col:
                st.subheader("🛠️ Changes Made")
                summary = st.session_state.opt_summary
                if isinstance(summary, dict):
                    st.markdown(f"**Location:** {summary.get('location', 'Multiple sections')}")
                    for change in summary.get('changes', []):
                        st.write(f"- {change}")
                else:
                    st.write("Summary not available.")

            with key_col:
                st.subheader("🔑 Keywords Added")
                if isinstance(summary, dict):
                    keywords = summary.get('keywords', [])
                    st.write(", ".join(keywords))
                else:
                    st.write("Keywords not available.")
        st.subheader(f"💬 Chat with {config.get('default_model', 'gpt-4o')}")

        # Initialize or load chat history
        if "chat_history" not in st.session_state:
            # Initialize new chat with default system prompt
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
        for message in st.session_state.chat_history:
            if message["role"] != "system":
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # Handle chat input
        if prompt := st.chat_input("How can I help you today?"):
            # Constantly adding user message to chat history
            st.session_state.chat_history.append({"role": "user", "content": prompt})

            # Display user message while it finishes processing and rereun
            with st.chat_message("user"):
                st.markdown(prompt)

            assistant_response = llm_chat_agent.get_chat_answer(final_text_prompt=st.session_state.chat_history)

            # Constantly adding assistant response to chat history
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})

            # Skip saving updated chat history to database
            # save_chat_history(
            #     user_id=st.session_state.user_name,
            #     job_id=st.session_state.job_id,
            #     chat_history=json.dumps(st.session_state.chat_history)
            # )

            # Rerun to refresh the display with updated history
            st.rerun()
