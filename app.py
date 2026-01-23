import streamlit as st
import time
import os
import pathlib
import json
import uuid
from file_management import FileManager, extract_text_from_file
from state_machine import ResumeOptimizerStateMachine
from llm_agent import LLMAgent, LLM_Chat

# --- PAGE CONFIG -------------------------------------
st.set_page_config(
    page_title="ATS Resume Tailoring System",
    page_icon="📄",
    layout="wide"
)

# --- GLOBAL STYLES -----------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap');
    
    html, body, [data-testid="stAppViewBlockContainer"] {
        font-family: 'Outfit', sans-serif;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
    }
    
    .main { background: transparent; }
    
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
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
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
    
    /* Animation */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .fade-in {
        animation: fadeIn 0.8s ease-out;
    }
    
    /* Native Container Styling to replace glass-card */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        padding: 1rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- DIALOGS -----------------------------------------
@st.dialog("➕ Add New Model")
def add_model_dialog(catalog, inventory, user_config):
    with st.form("add_model_form"):
        catalog_opts = {c['id']: f"{c['display_name']} ({c['provider']})" for c in catalog}
        chosen_sdk_id = st.selectbox("Choose Base Model", options=catalog_opts.keys(), format_func=lambda x: catalog_opts[x])
        
        chosen_cat_item = next((c for c in catalog if c['id'] == chosen_sdk_id), {})
        
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("Friendly Name", value=chosen_cat_item.get('display_name', ''))
        with c2:
            plan_type = st.selectbox("Plan Type", ["free", "paid"])
        
        api_key_input = st.text_input("API Key (Required for all plans)", type="password")
        
        if st.form_submit_button("Save Model"):
            duplicate = any(item['name'].lower() == new_name.lower().strip() for item in inventory)
            
            if not new_name.strip():
                st.error("Please provide a name.")
            elif duplicate:
                st.error(f"Name '{new_name}' already exists.")
            elif not api_key_input.strip():
                st.error("API Key is required.")
            else:
                new_item = {
                    "id": str(uuid.uuid4()),
                    "sdk_id": chosen_sdk_id,
                    "plan_type": plan_type,
                    "name": new_name.strip(),
                    "api_key": api_key_input.strip(),
                    "tokens_used_today": 0,
                    "last_used_at": None
                }
                inventory.append(new_item)
                user_config['llm_inventory'] = inventory
                if len(inventory) == 1:
                    user_config['selected_llm_id'] = new_item['id']
                
                fm.save_user_config(st.session_state.user_id, user_config)
                st.success(f"Added {new_name}!")
                time.sleep(1)
                st.rerun()

# --- INITIALIZATION ----------------------------------
project_root = pathlib.Path(__file__).parent.absolute()
fm = FileManager(project_root)

if "user_id" not in st.session_state:
    st.session_state.user_id = None

# --- LOGGER CLASS ------------------------------------
class AppLogger:
    def __init__(self, placeholder=None):
        self.placeholder = placeholder
        self.logs = []

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.logs.append(formatted_message)
        if self.placeholder:
            self.placeholder.code("\n".join(self.logs[::-1]), language="text")

    def clear(self):
        self.logs = []
        if self.placeholder:
            self.placeholder.empty()

if "logger" not in st.session_state:
    st.session_state.logger = AppLogger()

# --- LOGIN SCREEN ------------------------------------
if not st.session_state.user_id:
    
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.title("🔐 ATS Access Portal")
        st.markdown("Enter your User ID to load your workspace.")
        
        uid_input = st.text_input("User ID", placeholder="e.g. jdoe")
        
        if st.button("🚀 Enter Workspace"):
            if uid_input.strip():
                st.session_state.user_id = uid_input.strip()
                fm.ensure_user_structure(st.session_state.user_id)
                st.success(f"Welcome, {st.session_state.user_id}!")
                st.rerun()
            else:
                st.error("Please enter a User ID.")
    st.stop()

# --- MAIN APP LOGIC ----------------------------------

# Helper: Get current user config
user_config = fm.get_user_config(st.session_state.user_id)
user_dir = fm.get_user_dir(st.session_state.user_id)

# Initialize State Machine if new session
if "machine" not in st.session_state:
    st.session_state.machine = ResumeOptimizerStateMachine()

machine = st.session_state.machine

# Sidebar Navigation
with st.sidebar:
    st.image("https://img.icons8.com/?size=100&id=12150&format=png&color=000000", width=80)
    st.title(f"ATS Agent")
    st.caption(f"User: {st.session_state.user_id}")
    
    page = st.radio("Navigation", ["Dashboard", "Profiles", "Settings", "History"], index=0)
    
    st.divider()
    if st.button("🚪 Logout"):
        st.session_state.user_id = None
        st.session_state.machine = ResumeOptimizerStateMachine() # Reset machine
        st.rerun()

# --- PAGE: SETTINGS ----------------------------------
if page == "Settings":
    st.header("⚙️ Configuration")
    
    tab1, tab2, tab3 = st.tabs(["🧠 AI Models", "📦 LLM Inventory", "📝 Prompts"])
    
    # TAB 1: MODEL SELECTION
    with tab1:
        st.subheader("Select Active Model")
        inventory = user_config.get("llm_inventory", [])
        
        if not inventory:
            st.warning("No models found in inventory. Please add one in the 'LLM Inventory' tab.")
        else:
            # Selection Dropdown
            options = {item['id']: f"{item.get('name', 'Unnamed')} ({item.get('plan_type', 'Unknown')})" for item in inventory}
            current_selection = user_config.get("selected_llm_id")
            
            selected_id = st.selectbox(
                "Choose Model for Optimization", 
                options=options.keys(), 
                format_func=lambda x: options[x],
                index=list(options.keys()).index(current_selection) if current_selection in options else 0,
                key="active_model_select"
            )
            
            if st.button("💾 Set as Active Model"):
                user_config['selected_llm_id'] = selected_id
                fm.save_user_config(st.session_state.user_id, user_config)
                st.success("Active model updated!")

    # TAB 2: INVENTORY MANAGEMENT
    with tab2:
        st.subheader("Manage Inventory")
        
        if st.button("➕ Add New Model"):
            add_model_dialog(fm.get_global_catalog(), inventory, user_config)
            
        st.divider()
        
        if not inventory:
            st.info("Inventory is empty.")
        else:
            for i, item in enumerate(inventory):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{item.get('name')}**")
                with col2:
                     st.caption(f"{item.get('plan_type')} | {item.get('sdk_id')}")
                with col3:
                    if st.button("🗑️", key=f"del_model_{i}", help="Delete Model"):
                        inventory.pop(i)
                        user_config['llm_inventory'] = inventory
                        if user_config.get('selected_llm_id') == item['id']:
                            user_config['selected_llm_id'] = None
                        fm.save_user_config(st.session_state.user_id, user_config)
                        st.success(f"Deleted {item.get('name')}")
                        time.sleep(1)
                        st.rerun()
                st.divider()

    # TAB 3: PROMPT ENGINEERING
    with tab3:
        st.subheader("Customize System Prompts")
        
        prompts = user_config.get("prompts", {})
        
        # Define Known Prompt Keys with Defaults
        DEFAULT_PROMPTS = {
            "optimize_system": "You are a professional career assistant and LaTeX expert...",
            "optimize_user": "Optimize this LaTeX template for the following Job Description...",
            "chat_system": "You are a helpful assistant specialized in career assistance...",
        }
        
        placeholders = ["{resume_text}", "{linkedin_text}", "{job_description}", "{latex_template}"]
        
        for key, default_val in DEFAULT_PROMPTS.items():
            st.markdown(f"**{key.replace('_', ' ').title()}**")
            
            # Placeholder Buttons Row
            cols = st.columns(len(placeholders))
            for idx, ph in enumerate(placeholders):
                if cols[idx].button(f"➕ {ph}", key=f"btn_{key}_{idx}"):
                    prompts[key] = prompts.get(key, default_val) + " " + ph
                    # No need to rerun, text area will pick up updated dict value if rerendered, 
                    # strictly speaking we might need to rerun to refresh the text_area value if it uses value=...
                    # Let's verify: Streamlit text_area with `value` doesn't auto-update if key exists unless we wipe it?
                    # Better approach: We update the prompt in config and st.rerun() to reflect change in text_area
                    user_config['prompts'] = prompts
                    fm.save_user_config(st.session_state.user_id, user_config)
                    st.rerun()

            current_val = prompts.get(key, default_val)
            new_val = st.text_area(f"Edit {key}", value=current_val, height=150, key=f"prompt_{key}")
            prompts[key] = new_val
            st.divider()
            
        if st.button("💾 Save All Prompts"):
            user_config['prompts'] = prompts
            fm.save_user_config(st.session_state.user_id, user_config)
            st.success("Prompts saved!")

        


# --- PAGE: PROFILES (MANAGE FILES) --------------------
elif page == "Profiles":
    st.header("📂 File Management")
    
    templates_dir = user_dir / "templates"
    profiles_dir = user_dir / "linkedin_profiles"
    
    tab1, tab2 = st.tabs(["📄 Resume Templates (.tex)", "🔗 LinkedIn Profiles (.pdf)"])
    
    # RESUME TEMPLATES SECTION
    with tab1:
        st.subheader("Resume Templates")
        
        # List Existing
        temps = [f for f in templates_dir.glob("*.tex")] + [f for f in templates_dir.glob("*.txt")]
        if temps:
            for t in temps:
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"📄 **{t.name}**")
                with c2:
                    if st.button("🗑️", key=f"del_temp_{t.name}", help="Delete Template"):
                        os.remove(t)
                        st.rerun()
                st.divider()
        else:
            st.info("No templates found.")
            
        # Upload New
        st.caption("Upload New Template")
        uploaded_temp = st.file_uploader("Select .tex file", type=["tex", "txt"], key="uploader_temp")
        if uploaded_temp:
            if st.button("📤 Upload Template"):
                with open(templates_dir / uploaded_temp.name, "wb") as f:
                    f.write(uploaded_temp.getbuffer())
                st.success(f"Uploaded {uploaded_temp.name}")
                time.sleep(1)
                st.rerun()

    # LINKEDIN PROFILES SECTION
    with tab2:
        st.subheader("LinkedIn Profiles")
        
        # List Existing
        profs = [f for f in profiles_dir.glob("*.pdf")]
        if profs:
            for p in profs:
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"🔗 **{p.name}**")
                with c2:
                    if st.button("🗑️", key=f"del_prof_{p.name}", help="Delete Profile"):
                        os.remove(p)
                        st.rerun()
                st.divider()
        else:
            st.info("No profiles found.")
            
        # Upload New
        st.caption("Upload New Profile")
        uploaded_prof = st.file_uploader("Select .pdf file", type=["pdf"], key="uploader_prof")
        if uploaded_prof:
            if st.button("📤 Upload Profile"):
                with open(profiles_dir / uploaded_prof.name, "wb") as f:
                    f.write(uploaded_prof.getbuffer())
                st.success(f"Uploaded {uploaded_prof.name}")
                time.sleep(1)
                st.rerun()

# --- PAGE: DASHBOARD (MAIN APP) ----------------------
elif page == "Dashboard":
    # Ensure directories
    templates_dir = user_dir / "templates"
    profiles_dir = user_dir / "linkedin_profiles"
    output_dir = user_dir / "output"
    
    # State Init
    states_to_init = {
        "resume_text": "",
        "linkedin_text": "",
        "custom_resume_name": "",
        "job_description_text": "",
        "chat_history": []
    }
    for k, v in states_to_init.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if machine.state == "start":
        machine.state = "waiting_job_description"
        st.rerun()

    elif machine.state == "waiting_job_description":
        with st.container(border=True):
            st.subheader("🚀 Create New Resume")
            
            job_desc = st.text_area("Job Description", height=200, placeholder="Paste JD here...", value=st.session_state.job_description_text)
            st.session_state.job_description_text = job_desc
            
            c1, c2 = st.columns(2)
            with c1:
                # LIST TEMPLATES
                temps = [f.name for f in templates_dir.glob("*.tex")] + [f.name for f in templates_dir.glob("*.txt")]
                if not temps:
                    st.warning("No templates found!")
                    st.markdown("👉 [Manage Templates in Profile Page](/)", unsafe_allow_html=True)
                    sel_temp = None
                else:
                    sel_temp = st.selectbox("Select Template", temps)
            
            with c2:
                # LIST PROFILES
                profs = [f.name for f in profiles_dir.glob("*.pdf")]
                if not profs:
                    st.warning("No profiles found!")
                    st.markdown("👉 [Manage Profiles in Profile Page](/)", unsafe_allow_html=True)
                    sel_prof = None
                else:
                    sel_prof = st.selectbox("Select LinkedIn Profile", profs)
            
            # Logic to update custom_resume_name if selection changes
            if "last_selected_template" not in st.session_state:
                st.session_state.last_selected_template = None
            
            if sel_temp and sel_temp != st.session_state.last_selected_template:
                # Update default name
                base_name = os.path.splitext(sel_temp)[0]
                st.session_state.custom_resume_name = base_name
                st.session_state.last_selected_template = sel_temp

            resume_name = st.text_input("Output Filename", value=st.session_state.custom_resume_name, help="Defaults to template name. Change if desired.")
            st.session_state.custom_resume_name = resume_name
        
        if st.button("✨ Generate Optimized Resume"):
            if not job_desc or not sel_temp or not sel_prof:
                st.error("Please ensure you have a Job Description, a Template, and a LinkedIn Profile selected.")
            else:
                st.session_state.selected_template_path = templates_dir / sel_temp
                st.session_state.selected_linkedin_path = profiles_dir / sel_prof
                machine.next("processing_llm")
                st.rerun()

    elif machine.state == "processing_llm":
        with st.status("🤖 AI Agent Working...", expanded=True):
            st.write("Initializing Agent with User Config...")
            
            # --- AGENT INIT ---
            try:
                agent = LLMAgent(st.session_state.user_id, fm)
                
                st.write("Reading inputs...")
                resume_txt = extract_text_from_file(st.session_state.selected_template_path)
                linkedin_txt = extract_text_from_file(st.session_state.selected_linkedin_path)
                
                st.write("Optimizing Resume (this may take a minute)...")
                optimized_latex = agent.optimize_latex(
                    resume_txt, 
                    resume_txt, # Passing resume twice as template and text for now, 
                    linkedin_txt, 
                    st.session_state.job_description_text
                )
                
                # SAVE OUTPUT
                out_path = output_dir / f"{st.session_state.custom_resume_name}.tex"
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(optimized_latex)
                
                st.write("Compiling PDF...")
                # Note: Compiler path is hardcoded in original config, 
                # we might need to assume it's in path or add to user config.
                # using pdflatex from path for now.
                import subprocess
                cmd = ["pdflatex", "-interaction=nonstopmode", f"{st.session_state.custom_resume_name}.tex"]
                subprocess.run(cmd, cwd=str(output_dir), capture_output=True)
                
                # GET METRICS
                st.write("Calculating Scores...")
                metrics = agent.get_ats_score(optimized_latex, st.session_state.job_description_text)
                st.session_state.final_metrics = metrics
                
                st.write("Done!")
                time.sleep(1)
                machine.next("finished")
                st.rerun()
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
                # st.exception(e) # Debugging
                if st.button("Back"):
                    machine.state = "waiting_job_description"
                    st.rerun()

                if st.button("Back"):
                    machine.state = "waiting_job_description"
                    st.rerun()

    elif machine.state == "job_exploration": # Final state
        st.header("📝 Resume Editor & Preview")
        
        # Load current files
        tex_path = output_dir / f"{st.session_state.custom_resume_name}.tex"
        pdf_path = output_dir / f"{st.session_state.custom_resume_name}.pdf"
        
        # Ensure TeX exists in session for editing if not already
        if "current_latex" not in st.session_state:
            if tex_path.exists():
                with open(tex_path, "r", encoding="utf-8") as f:
                    st.session_state.current_latex = f.read()
            else:
                st.session_state.current_latex = ""
        
        col_preview, col_edit = st.columns([1, 1])
        
        # --- LEFT: PDF PREVIEW ---
        with col_preview:
            st.subheader("📄 Live Preview")
            if pdf_path.exists():
                import base64
                with open(pdf_path, "rb") as f:
                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)
            else:
                st.error("PDF not found. Try compiling.")
        
        # --- RIGHT: EDITOR & CHAT ---
        with col_edit:
            tab_edit, tab_chat = st.tabs(["✏️ Editor", "💬 AI Refinement"])
            
            # 1. MANUAL EDITOR
            with tab_edit:
                new_latex = st.text_area("LaTeX Source", value=st.session_state.current_latex, height=600)
                st.session_state.current_latex = new_latex
                
                if st.button("⚡ Re-Compile PDF"):
                    # Save TeX
                    with open(tex_path, "w", encoding="utf-8") as f:
                        f.write(st.session_state.current_latex)
                    
                    # Compile
                    with st.spinner("Compiling..."):
                        import subprocess
                        subprocess.run(["pdflatex", "-interaction=nonstopmode", f"{st.session_state.custom_resume_name}.tex"], cwd=str(output_dir))
                    st.success("Compiled!")
                    st.rerun()
                
                # Download Buttons
                with open(tex_path, "r", encoding="utf-8") as f:
                    st.download_button("📥 Download TeX", f, file_name=f"{st.session_state.custom_resume_name}.tex")
                if pdf_path.exists():
                    with open(pdf_path, "rb") as f:
                        st.download_button("📥 Download PDF", f, file_name=f"{st.session_state.custom_resume_name}.pdf")

            # 2. CHAT REFINEMENT
            with tab_chat:
                st.warning("Chat with AI to refine your resume.")
                
                # Chat History Display
                if "refinement_chat" not in st.session_state:
                    st.session_state.refinement_chat = []
                
                for msg in st.session_state.refinement_chat:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
                
                # Input
                if prompt := st.chat_input("E.g., 'Make the summary shorter'"):
                    # User Msg
                    st.session_state.refinement_chat.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.write(prompt)
                    
                    # AI Processing
                    try:
                        agent = LLMAgent(st.session_state.user_id, fm)
                        with st.status("Refining Resume..."):
                            updated_latex = agent.refine_latex(st.session_state.current_latex, prompt)
                            
                        # Update State
                        # Clean markdown if LLM adds it
                        updated_latex = updated_latex.replace("```latex", "").replace("```", "").strip()
                        st.session_state.current_latex = updated_latex
                        
                        # Auto-save & Compile
                        with open(tex_path, "w", encoding="utf-8") as f:
                            f.write(updated_latex)
                        import subprocess
                        subprocess.run(["pdflatex", "-interaction=nonstopmode", f"{st.session_state.custom_resume_name}.tex"], cwd=str(output_dir))
                        
                        st.session_state.refinement_chat.append({"role": "assistant", "content": "I've updated the resume and re-compiled it for you!"})
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error refining: {e}")
            
        if st.button("🔄 Start Over (New Job)"):
            machine.reset()
            # Clear specific keys
            keys = ["refinement_chat", "current_latex", "last_selected_template"]
            for k in keys:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

# --- PAGE: HISTORY -----------------------------------
elif page == "History":
    st.header("📜 Resume History")
    output_dir = user_dir / "output"
    files = list(output_dir.glob("*.pdf"))
    
    if not files:
        st.info("No generated resumes found.")
    else:
        for f in files:
            c1, c2 = st.columns([4, 1])
            with c1:
                st.write(f"**{f.name}**")
                st.caption(f"Created: {time.ctime(f.stat().st_ctime)}")
            with c2:
                with open(f, "rb") as pdf_file:
                    st.download_button("📥", pdf_file, key=f.name, file_name=f.name)
            st.divider()
