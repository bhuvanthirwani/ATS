import streamlit as st
import time
import os
import pathlib
import json
import uuid
from file_management import FileManager, extract_text_from_file
from state_machine import ResumeOptimizerStateMachine
from llm_agent import LLMAgent

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
    
    :root {
        --primary: #06b6d4;
        --secondary: #8b5cf6;
        --background: #0f172a;
        --surface: rgba(30, 41, 59, 0.5);
        --text: #f8fafc;
    }

    html, body, [data-testid="stAppViewBlockContainer"] {
        font-family: 'Outfit', sans-serif;
        background: radial-gradient(circle at top right, #1e1b4b 0%, #0f172a 100%);
        color: var(--text);
        font-size: 0.85rem !important; /* Global Font Size Reduction */
    }
    
    .main { background: transparent; }
    
    [data-testid="stHeader"] {
        background: rgba(15, 23, 42, 0.4);
        backdrop-filter: blur(12px);
    }
    
    /* Global Heading Scale Down */
    h1 { font-size: 1.8rem !important; }
    h2 { font-size: 1.4rem !important; }
    h3 { font-size: 1.1rem !important; }
    
    .stButton>button {
        border-radius: 10px;
        background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%) !important;
        color: white !important;
        border: none !important;
        padding: 0.4rem 1rem !important; /* Tighter Padding */
        font-weight: 600 !important;
        font-size: 0.8rem !important; /* Smaller Button Font */
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 10px rgba(6, 182, 212, 0.15);
        width: 100%;
        text-transform: none;
        letter-spacing: 0.2px;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(139, 92, 246, 0.3) !important;
    }
    
    /* Specific styling for placeholder buttons */
    section[data-testid="stVerticalBlock"] div[data-testid="stColumn"] button {
        font-size: 0.7rem !important;
        padding: 0.2rem 0.6rem !important;
    }

    /* Glass Cards */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--surface);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px; /* Smaller radius */
        padding: 1rem !important; /* Less padding */
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
        transition: transform 0.3s ease;
        margin-bottom: 0.75rem;
    }
    
    /* Metric Styling */
    [data-testid="stMetricValue"] {
        background: linear-gradient(90deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        font-size: 2rem !important; /* Smaller Metric */
    }
    
    /* Animations */
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .stVerticalBlock {
        animation: slideUp 0.6s ease-out;
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
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("""
                <div style='text-align: center;'>
                    <h1 style='background: linear-gradient(90deg, #06b6d4, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3rem;'>ATS AGENT</h1>
                    <p style='color: #94a3b8; font-size: 1.1rem;'>The Ultimate Resume Tailoring Engine</p>
                </div>
            """, unsafe_allow_html=True)
            
            uid_input = st.text_input("User ID", placeholder="Enter your unique workspace ID...")
            
            if st.button("✨ Initialize Workspace"):
                if uid_input.strip():
                    st.session_state.user_id = uid_input.strip()
                    fm.ensure_user_structure(st.session_state.user_id)
                    st.success(f"Workspace {st.session_state.user_id} Ready!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Please provide a User ID to continue.")
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
    st.markdown("""
        <div style='text-align: center; padding: 1rem;'>
            <h2 style='background: linear-gradient(90deg, #06b6d4, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>CORE NAVIGATION</h2>
        </div>
    """, unsafe_allow_html=True)
    
    page = st.radio("Access Portals", ["📊 Dashboard", "📂 Profiles", "⚙️ Settings", "📜 History"], index=0)
    
    st.divider()
    st.caption(f"Logged in as: **{st.session_state.user_id}**")
    if st.button("🚪 Leave Workspace"):
        st.session_state.user_id = None
        st.session_state.machine = ResumeOptimizerStateMachine() # Reset machine
        st.rerun()

# --- PAGE: SETTINGS ----------------------------------
if "Settings" in page:
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
        
        # Define Simplified Prompt Keys with Defaults
        DEFAULT_PROMPTS = {
            "analyze_prompt": """You are an Applicant Tracking System (ATS) used by Fortune-500 companies.

Your task is to score how well a candidate’s resume matches a job description using the same logic as modern ATS platforms (Workday, Greenhouse, Lever, iCIMS).

You must analyze the resume exactly like an ATS parser would — keyword matching, semantic matching, experience relevance, and role fit — not like a human recruiter.

--------------------------------
SCORING METHODOLOGY (must follow strictly)

Total Score = 100 points
A. Keyword Match (40 points)
B. Skill Coverage Depth (20 points)
C. Job Title & Role Match (10 points)
D. Experience Relevance (15 points)
E. Education & Domain Fit (5 points)
F. ATS Parsability (10 points)

--------------------------------
OUTPUT FORMAT (STRICT JSON — NO EXTRA TEXT)

{
  "ats_score": number between 0 and 100,
  "missing_keywords": [
     list of important skills or phrases in JOB_DESCRIPTION that are missing or weak in the resume
  ],
  "matched_keywords": [
     list of important skills that were successfully matched
  ],
  "justification": {
     "keyword_match": "...",
     "skill_depth": "...",
     "role_fit": "...",
     "experience_relevance": "...",
     "education_fit": "...",
     "parsing_quality": "..."
  }
}

--------------------------------
INPUTS

RESUME_CODE (LaTeX):
{resume_text}

JOB_DESCRIPTION:
{job_description}""",
            "optimize_prompt": """You are an ATS-optimization engine used by Big Tech recruiting platforms.

Your task is to rewrite a LaTeX resume so that its ATS score becomes at least 90% for a given job description, while preserving structure, honesty, and formatting.

--------------------------------
STRICT RULES
1) DO NOT: change section structure, remove existing sections, or rename headers.
2) YOU MUST: Add missing keywords to Skills, Experience, and Projects.
3) If a core skill is missing, enhance bullets with relevant frameworks (e.g., Java -> Spring Boot).

--------------------------------
REQUIRED OUTPUT (JSON — NO EXTRA TEXT)
{
  "final_score": number between 0 and 100,
  "new_latex_code": "FULL optimized LaTeX resume",
  "summary": [
     "Added 'Next.js' to skills",
     "Updated project description"
  ]
}

--------------------------------
INPUTS
initial_ats_score: {initial_ats_score}
missing_keywords: {missing_keywords}
matched_keywords: {matched_keywords}
justification: {justification}
job_description: {job_description}
old_resume_code (LaTeX): {resume_text}"""
        }
        
        prompt_metadata = {
            "analyze_prompt": {
                "title": "📊 Step 1: Calculate ATS Score & Recommendations",
                "description": "Analyze the Resume against the Job Description. Requires valid JSON output.",
                "placeholders": ["{resume_text}", "{job_description}"]
            },
            "optimize_prompt": {
                "title": "🛠️ Step 2: Resume Tailoring & Optimization",
                "description": "Rewrite the LaTeX code to optimize for keywords and score. Requires JSON with new LaTeX.",
                "placeholders": [
                    "{resume_text}", "{job_description}", "{initial_ats_score}", 
                    "{missing_keywords}", "{matched_keywords}", "{justification}"
                ]
            }
        }
        
        for key, meta in prompt_metadata.items():
            st.markdown(f"## {meta['title']}")
            st.info(meta['description'])
            
            # Compact Placeholder Buttons
            st.caption("Available Variables (Click to insert):")
            # Use small chunks for columns to keep buttons tight
            ph_cols = st.columns(min(len(meta['placeholders']), 4))
            for idx, ph in enumerate(meta['placeholders']):
                col_idx = idx % len(ph_cols)
                if ph_cols[col_idx].button(f" {ph} ", key=f"btn_{key}_{idx}"):
                    current = prompts.get(key, DEFAULT_PROMPTS[key])
                    prompts[key] = current + " " + ph
                    user_config['prompts'] = prompts
                    fm.save_user_config(st.session_state.user_id, user_config)
                    st.rerun()

            current_val = prompts.get(key, DEFAULT_PROMPTS[key])
            new_val = st.text_area("Template Editor", value=current_val, height=350, key=f"prompt_input_{key}")
            if new_val != current_val:
                prompts[key] = new_val
                user_config['prompts'] = prompts
            st.divider()
            
        if st.button("💎 Save All Prompt Configurations"):
            user_config['prompts'] = prompts
            fm.save_user_config(st.session_state.user_id, user_config)
            st.success("All configurations saved successfully!")
            time.sleep(1)
            st.rerun()

        


# --- PAGE: PROFILES (MANAGE FILES) --------------------
elif "Profiles" in page:
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
elif "Dashboard" in page:
    from compiler import LaTeXCompiler
    
    # Ensure directories
    templates_dir = user_dir / "templates"
    profiles_dir = user_dir / "linkedin_profiles"
    output_dir = user_dir / "output"
    
    # State Init
    states_to_init = {
        "job_description_text": "",
        "analysis_result": None,
        "optimization_result": None,
        "selected_template": None,
        "selected_profile": None,
        "custom_resume_name": ""
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
                temps = [f.name for f in templates_dir.glob("*.tex")] + [f.name for f in templates_dir.glob("*.txt")]
                if not temps:
                    st.warning("No templates found!")
                    sel_temp = None
                else:
                    sel_temp = st.selectbox("Select Template", temps)
                    st.session_state.selected_template = sel_temp
            
            with c2:
                profs = [f.name for f in profiles_dir.glob("*.pdf")]
                if not profs:
                    st.warning("No profiles found!")
                    sel_prof = None
                else:
                    sel_prof = st.selectbox("Select LinkedIn Profile", profs)
                    st.session_state.selected_profile = sel_prof

            if sel_temp:
                base_name = os.path.splitext(sel_temp)[0]
                resume_name = st.text_input("Output Filename", value=base_name)
                st.session_state.custom_resume_name = resume_name
        
        if st.button("🔍 Analyze Match"):
            if not job_desc or not sel_temp or not sel_prof:
                st.error("Please provide JD, Template, and LinkedIn Profile.")
            else:
                machine.next("submit_jd")
                st.rerun()

    elif machine.state == "analyzing":
        with st.status("🔍 Analyzing Resume...", expanded=True):
            try:
                agent = LLMAgent(st.session_state.user_id, fm)
                
                st.write("Reading files...")
                resume_path = templates_dir / st.session_state.selected_template
                resume_text = extract_text_from_file(resume_path)
                
                st.write("Running ATS Analysis...")
                analysis = agent.analyze_resume(resume_text, st.session_state.job_description_text)
                st.session_state.analysis_result = analysis
                
                machine.next("analysis_complete")
                st.success("Analysis complete!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                if st.button("Retry"):
                    st.rerun()
                if st.button("Back"):
                    machine.state = "waiting_job_description"
                    st.rerun()

    elif machine.state == "reviewing_analysis":
        analysis = st.session_state.analysis_result
        
        st.header("📊 ATS Analysis Results")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("Initial ATS Score", f"{analysis.ats_score}%")
            
        with col2:
            st.subheader("Key Findings")
            st.write(f"**Matched Keywords:** {', '.join(analysis.matched_keywords)}")
            st.warning(f"**Missing Keywords:** {', '.join(analysis.missing_keywords)}")

        with st.expander("Detailed Justification"):
            st.write(analysis.justification.model_dump())

        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ Back"):
                machine.next("back")
                st.rerun()
        with c2:
            if st.button("✨ Tailor & Optimize"):
                machine.next("start_optimization")
                st.rerun()

    elif machine.state == "optimizing":
        with st.status("🛠️ Optimizing Resume...", expanded=True):
            try:
                agent = LLMAgent(st.session_state.user_id, fm)
                
                st.write("Extracting Info...")
                resume_path = templates_dir / st.session_state.selected_template
                resume_text = extract_text_from_file(resume_path)
                linkedin_path = profiles_dir / st.session_state.selected_profile
                linkedin_text = extract_text_from_file(linkedin_path)
                
                st.write("Running Optimization Engine...")
                opt_result = agent.optimize_resume(
                    st.session_state.analysis_result,
                    resume_text,
                    linkedin_text,
                    st.session_state.job_description_text
                )
                st.session_state.optimization_result = opt_result
                
                st.write("Compiling LaTeX...")
                tex_filename = f"{st.session_state.custom_resume_name}.tex"
                tex_path = output_dir / tex_filename
                with open(tex_path, "w", encoding="utf-8") as f:
                    f.write(opt_result.new_latex_code)
                
                compiler = LaTeXCompiler(output_dir)
                success = compiler.compile(tex_filename)
                
                if success:
                    machine.next("finished")
                    st.success("Optimization finished successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("LaTeX compilation failed. You can edit the code manually in the next step.")
                    machine.next("finished") # Still proceed so they can fix LaTeX
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Optimization failed: {e}")
                if st.button("Back to Analysis"):
                    machine.state = "reviewing_analysis"
                    st.rerun()

    elif machine.state == "job_exploration":
        st.header("📝 Final Optimized Resume")
        
        opt_result = st.session_state.optimization_result
        if opt_result:
            st.success(f"Target ATS Score Reached: {opt_result.final_score}%")
            with st.expander("Summary of Changes"):
                for change in opt_result.summary:
                    st.write(f"- {change}")

        # Editor and Preview logic (simplified for here)
        tex_path = output_dir / f"{st.session_state.custom_resume_name}.tex"
        pdf_path = output_dir / f"{st.session_state.custom_resume_name}.pdf"

        col_p, col_e = st.columns([1, 1])
        with col_p:
            if pdf_path.exists():
                import base64
                with open(pdf_path, "rb") as f:
                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800"></iframe>', unsafe_allow_html=True)
            else:
                st.info("PDF preview unavailable.")

        with col_e:
            with open(tex_path, "r", encoding="utf-8") as f:
                content = f.read()
            edited_tex = st.text_area("LaTeX Source", value=content, height=600)
            
            if st.button("💾 Re-compile"):
                with open(tex_path, "w", encoding="utf-8") as f:
                    f.write(edited_tex)
                compiler = LaTeXCompiler(output_dir)
                if compiler.compile(f"{st.session_state.custom_resume_name}.tex"):
                    st.success("Re-compiled!")
                    st.rerun()
                else:
                    st.error("Compilation failed.")

        if st.button("🔄 Start New"):
            machine.next("reset")
            st.rerun()

# --- PAGE: HISTORY -----------------------------------
elif "History" in page:
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
