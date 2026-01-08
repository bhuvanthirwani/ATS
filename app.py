import streamlit as st
import os, time, pathlib
import pandas as pd
from jinja2 import Environment, FileSystemLoader
# weasyprint removed in favor of LaTeX

# INTERNAL LIBRARIES
from file_management import *
from state_machine import ResumeOptimizerStateMachine
from llm_agent import *
import json
import subprocess

# GTK3 bin folder (weasyprint dependency) removed

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
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "job_id" not in st.session_state:
    st.session_state.job_id = None
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

# It´s easier for this variable to managed inside app.py rather than llm_agent
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

# Step 1: Initialize user session and set st.session_state.user_name for use throughout the app
if machine.state == "start":

    user_name = st.text_input("Enter an user name for this configuration:")

    # Display existing users in a table
    st.subheader("Existing Users")
    all_users = get_all_users()

    if all_users:
        # Create DataFrame with user data
        users_df = pd.DataFrame(all_users, columns=["User ID", "Last Modified"])
        # Format the datetime
        users_df["Last Modified"] = pd.to_datetime(users_df["Last Modified"]).dt.strftime('%Y-%m-%d %H:%M')

        # Display a table of existing users
        st.dataframe(
            users_df,
            column_config={
                "User ID": st.column_config.TextColumn(width="medium"),
                "Last Modified": st.column_config.DatetimeColumn(width="medium")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No existing users found in the database")

    if user_name and not st.session_state.user_checked:
        # Check only once after typing
        user_exists = check_user_exists(user_name)
        st.session_state.user_exists = user_exists
        st.session_state.user_checked = True

    if user_name:
        user_exists_count = check_user_exists(user_name) or 0
        if user_exists_count > 0:
            st.warning(f"⚠️ User '{user_name}' already exists. Continuing with existing data?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Yes, continue"):
                    st.session_state.user_name = user_name
                    st.session_state.resume_text, st.session_state.linkedin_text = get_user_info(st.session_state.user_name) # HERE
                    st.session_state.user_confirmed = True
                    message = machine.next("select_user")
                    st.success(message)
                    st.rerun()  # Refresh to show next state

            with col2:
                if st.button("❌ No, input a new user"):
                    st.session_state.user_checked = False  # Reset check
                    st.session_state.user_exists = False
                    st.rerun()

        else:

            st.info(f"User '{user_name}' selected. Please select your base template and LinkedIn profile.")

            # LinkedIn Profiles Directory
            linkedin_profiles_dir = os.path.join(project_root, "linkedin_profiles")
            if not os.path.exists(linkedin_profiles_dir):
                os.makedirs(linkedin_profiles_dir)
            
            all_linkedin_pdfs = [f for f in os.listdir(linkedin_profiles_dir) if f.endswith('.pdf')]
            all_templates = [f for f in os.listdir(template_dir) if f.endswith(('.txt', '.tex'))]

            col1, col2 = st.columns(2)
            with col1:
                selected_template = st.selectbox("Base LaTeX Template", all_templates)
            with col2:
                selected_linkedin = st.selectbox("LinkedIn Profile (PDF)", all_linkedin_pdfs)

            if selected_template and selected_linkedin and user_name:
                if st.button("🚀 Create Profile & Continue", type="primary"):
                    try:
                        template_path = os.path.join(template_dir, selected_template)
                        linkedin_path = os.path.join(linkedin_profiles_dir, selected_linkedin)
                        
                        st.session_state.resume_text = extract_text_from_file(template_path)
                        st.session_state.linkedin_text = extract_text_from_file(linkedin_path)
                        st.session_state.selected_template_path = template_path
                        st.session_state.selected_linkedin_path = linkedin_path
                        
                        create_user(user_name, template_path, linkedin_path)
                        st.session_state.user_name = user_name
                        message = machine.next("select_user")
                        st.success(message)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating user: {e}")

# Step 2: After user selection, select or create a new job
elif machine.state == "waiting_job_description":

    st.subheader("Select a Job Description for optimization:")

    # Get jobs for current user
    user_jobs = get_user_jobs(st.session_state.user_name)

    # Option 1: Create New Job (always shown)
    with st.expander("➕ Create New Job", expanded=True):
        new_job_text = st.text_area("Paste job description here:", height=200)
        if st.button("Save New Job"):
            if new_job_text.strip():
                try:
                    # Save the new job and automatically select it
                    job_id = create_new_job(st.session_state.user_name, new_job_text)
                    st.session_state.selected_job_text = new_job_text
                    st.session_state.job_id = job_id
                    message = machine.next("job_description_uploaded")
                    st.success(message)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving job: {e}")
            else:
                st.warning("Please enter a job description")

    # Option 2: Select Existing Jobs for the specific USER_ID/NAME
    st.subheader("Or select a previous Job configuration:")
    selected_id = display_jobs_with_selection(user_jobs)

    if selected_id:
        selected_job = next(job for job in user_jobs if job[0] == selected_id)
        st.session_state.job_id = selected_id
        st.session_state.selected_job_text = selected_job[1]
        
    st.divider()
    
    # Template Selection (Optional reuse/change)
    st.subheader("Final Template Selection:")
    all_templates = [f for f in os.listdir(template_dir) if f.endswith(('.html', '.txt', '.tex'))]
    
    # Default to the template selected at user creation if available
    default_index = 0
    if st.session_state.selected_template_path:
        template_name = os.path.basename(st.session_state.selected_template_path)
        if template_name in all_templates:
            default_index = all_templates.index(template_name)
            
    selected_template_file = st.selectbox("Choose a template for output:", all_templates, index=default_index)
    st.session_state.selected_template = selected_template_file

    if st.button("🚀 Start Optimization", type="primary"):
        if st.session_state.job_id and st.session_state.selected_template:
            message = machine.next("job_description_uploaded")
            st.success(f"Processing with template: {selected_template_file}. {message}")
            st.rerun()
        else:
            st.error("Please select both a job and a template.")

# Step 3: Process the input with the LLM to generate a tailored resume and render it as a PDF
elif machine.state == "processing_llm":
    st.subheader("Processing your data")
    with st.spinner("Initializing AI engine..."):
        time.sleep(1)  # Simulate setup

        show_loading_state()

        try:
            llm_agent = LLMAgent(config)
            
            template_path = os.path.join(template_dir, st.session_state.selected_template)
            is_latex = st.session_state.selected_template.endswith(('.txt', '.tex'))

            if not is_latex:
                # HTML Workflow
                result = llm_agent.generate_cv(
                    st.session_state.user_name,
                    st.session_state.resume_text,
                    st.session_state.linkedin_text,
                    st.session_state.selected_job_text
                )
                st.session_state.generated_cv = result
                save_dict_in_db(st.session_state.user_name, st.session_state.job_id, json.dumps(result))

                # PDF GENERATION PROCESS - HTML
                rendered_html = template.render(st.session_state.generated_cv)
                output_html_path = os.path.join(output_dir, 'output_cv.html')
                with open(output_html_path, 'w', encoding='utf-8') as f:
                    f.write(rendered_html)
                output_pdf_path = os.path.join(output_dir, f'Resume_{st.session_state.user_name}_{st.session_state.job_id}.PDF')
                st.warning("HTML to PDF conversion (WeasyPrint) has been disabled. Please use LaTeX templates for PDF generation.")
                # weasyprint.HTML(string=rendered_html).write_pdf(output_pdf_path)
            else:
                # LaTeX Workflow
                with open(template_path, 'r', encoding='utf-8') as f:
                    latex_template = f.read()
                
                optimized_latex = llm_agent.optimize_latex(
                    latex_template,
                    st.session_state.resume_text,
                    st.session_state.linkedin_text,
                    st.session_state.selected_job_text
                )
                
                # Cleaning up potential MD blocks if LLM still includes them
                if optimized_latex.startswith("```"):
                    optimized_latex = optimized_latex.split("\n", 1)[1].rsplit("\n", 1)[0]
                
                base_name = f'Resume_{st.session_state.user_name}_{st.session_state.job_id}'
                output_tex_path = os.path.join(output_dir, f'{base_name}.tex')
                
                with open(output_tex_path, 'w', encoding='utf-8') as f:
                    f.write(optimized_latex)
                
                # Compile LaTeX to PDF
                latex_compiler = config.get("database", {}).get("latex_compiler", "pdflatex")
                with st.spinner("Compiling LaTeX... This might take a moment."):
                    try:
                        result = subprocess.run(
                            [latex_compiler, "-interaction=nonstopmode", f"{base_name}.tex"],
                            cwd=output_dir,
                            capture_output=True,
                            text=True,
                            shell=True
                        )
                        if result.returncode != 0:
                            st.warning(f"LaTeX compilation warning (check log): {result.stderr}")
                    except Exception as e:
                        st.error(f"Failed to run pdflatex: {e}")
                        raise e

            message = machine.next("finished")
            st.success(message)
            st.rerun()

        except Exception as e:
            st.error(f"Generation failed: {str(e)}")
            machine.state = "waiting_job_description"  # Revert state

# Step 4: Final step – download resume and interact with the LLM-powered chatbot
elif machine.state == "job_exploration":

    # Create columns - most space empty, small space for button
    empty_col, button_col = st.columns([0.95, 0.05])

    with button_col:
        if st.button("↩️", help="Return to main menu"):
            st.session_state.clear()
            machine.next("menu")
            st.rerun()

    st.subheader("Download your Tailored Resume & Chat")

    # 1. Offer PDF download
    output_pdf_path = os.path.join(
        output_dir,
        f'Resume_{st.session_state.user_name}_{st.session_state.job_id}.PDF'
    )

    with open(output_pdf_path, "rb") as pdf_file:
        pdf_data = pdf_file.read()
    st.download_button(
        label="📄 Download Your Tailored Resume (PDF)",
        data=pdf_data,
        file_name=f"Tailored_Resume_{st.session_state.user_name}.pdf",
        mime="application/pdf"
    )

    st.divider()

    # 2. Chat with LLM based on the optimized resume
    st.subheader(f"💬 Chat with {config.get('default_model', 'gpt-4o')}")

    # Initialize or load chat history
    if "chat_history" not in st.session_state:
        # Try to load existing history from DB
        db_chat_history = get_chat_history(st.session_state.user_name, st.session_state.job_id)

        if db_chat_history:
            # Use existing history from DB
            st.session_state.chat_history = db_chat_history
        else:
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

        # Save upd ated chat history to database as JSON
        save_chat_history(
            user_id=st.session_state.user_name,
            job_id=st.session_state.job_id,
            chat_history=json.dumps(st.session_state.chat_history)
        )

        # Rerun to refresh the display with updated history
        st.rerun()
