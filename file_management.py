import psycopg2
import fitz  # pymupdf
import json

DB_CONFIG = None

def init_db(config_dict):
    """Initialize the database configuration and ensure tables exist."""
    global DB_CONFIG
    DB_CONFIG = config_dict.get('database')
    if not DB_CONFIG:
        raise ValueError("Database configuration not found in config file.")
    
    ensure_tables_exist()

def ensure_tables_exist():
    """Create the necessary tables if they do not exist."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    table_names = DB_CONFIG.get('table_names', {})
    users_table = table_names.get('users', 'users')
    jobs_table = table_names.get('jobs', 'jobs')
    
    try:
        # Create users table
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {users_table} (
                user_id TEXT PRIMARY KEY,
                resume_txt TEXT,
                linkedin_txt TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Create jobs table
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {jobs_table} (
                job_id SERIAL PRIMARY KEY,
                user_id TEXT REFERENCES {users_table}(user_id),
                job_description TEXT,
                generated_cv JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                last_modified TIMESTAMP DEFAULT NOW(),
                chat_history JSONB
            );
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error creating tables: {e}")
        raise
    finally:
        cur.close()
        conn.close()

# Function to connect to the PostgreSQL
def get_db_connection():
    if not DB_CONFIG:
        raise Exception("Database not initialized. Call init_db(config) first.")
        
    conn = psycopg2.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        database=DB_CONFIG['database'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password']
    )
    return conn

# Function to extract text from a file (path or Streamlit uploaded file object)
def extract_text_from_pdf(file_input):
    """Extracts text from a PDF file path or uploaded file object."""
    try:
        if isinstance(file_input, str):
            # File path
            doc = fitz.open(file_input)
        else:
            # Streamlit uploaded file
            file_input.seek(0)
            file_bytes = file_input.getvalue()
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            
        text = ""
        for page in doc:
            text += page.get_text()
        return text.encode("utf-8", errors="replace").decode("utf-8")
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        raise

def extract_text_from_file(file_path):
    """General text extraction for TXT, TEX, or PDF."""
    if file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    else:
        # Default to reading as plain text (for .tex, .txt)
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

# Function to check if the user already exists
def check_user_exists(user_name):
    users_table = DB_CONFIG['table_names']['users']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {users_table} WHERE user_id = %s;", (user_name,))
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count > 0

# Function to initialize the txt input variables from the db in the case of user_selection without cache
def get_user_info(user_name):
    users_table = DB_CONFIG['table_names']['users']
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(f"""
                SELECT resume_txt, linkedin_txt
                FROM {users_table}
                WHERE user_id = %s;
                """, (user_name,))

    result = cur.fetchone()

    cur.close()
    conn.close()

    if result:
        resume_txt, linkedin_txt = result
        return resume_txt, linkedin_txt
    return "", ""

# Function to get a list of jobs for a determined user
def get_user_jobs(user_name):
    jobs_table = DB_CONFIG['table_names']['jobs']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT job_id, job_description, generated_cv, created_at, last_modified
        FROM {jobs_table}
        WHERE user_id = %s
        ORDER BY last_modified DESC;
    """, (user_name,))
    jobs = cur.fetchall()
    cur.close()
    conn.close()
    return jobs

# Function to get the list of users
def get_all_users():
    try:
        users_table = DB_CONFIG['table_names']['users']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT user_id, created_at FROM {users_table} ORDER BY created_at DESC;")
        users = cur.fetchall()
        cur.close()
        conn.close()
        return users
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []

# Function to create a new job
def create_new_job(user_name, job_description_text):
    jobs_table = DB_CONFIG['table_names']['jobs']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO {jobs_table} (user_id, job_description)
        VALUES (%s, %s)
        RETURNING job_id;
    """, (user_name, job_description_text))
    new_id = cur.fetchone()[0] # NEW ID CREATED
    conn.commit()
    cur.close()
    conn.close()

    return new_id

# Function to input the files into the right path
def create_user(user_name, resume_path, linkedin_path):
    """Creates a user using file paths for resume (template) and linkedin profile."""
    users_table = DB_CONFIG['table_names']['users']
    user_id = user_name
    resume_text = extract_text_from_file(resume_path)
    linkedin_text = extract_text_from_file(linkedin_path)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(f"""
        INSERT INTO {users_table} (user_id, resume_txt, linkedin_txt)
        VALUES (%s, %s, %s);
        """, (user_id, resume_text, linkedin_text))

    conn.commit()
    cur.close()
    conn.close()
    return True

# Function to register the JSON used to build the HTML and PDFs
def save_dict_in_db(user_id, job_id, generated_dict_resume):
    jobs_table = DB_CONFIG['table_names']['jobs']
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(f"""
        UPDATE {jobs_table}
        SET generated_cv = %s, last_modified = NOW()
        WHERE user_id = %s AND job_id = %s;
        """, (generated_dict_resume, user_id, job_id))

    conn.commit()
    cur.close()
    conn.close()

    return True

# Function to retrieve chat history for a job
def get_chat_history(user_id, job_id):
    jobs_table = DB_CONFIG['table_names']['jobs']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT chat_history
        FROM {jobs_table}
        WHERE user_id = %s AND job_id = %s;
    """, (user_id, job_id))
    result = cur.fetchone()
    cur.close()
    conn.close()

    if result and result[0]:
        try:
            chat_history = result[0]
            if isinstance(chat_history, str):
                chat_history = json.loads(chat_history)
            # Ensure format is a list of dicts with 'role' and 'content'
            if isinstance(chat_history, list) and all('role' in m and 'content' in m for m in chat_history):
                return chat_history
        except json.JSONDecodeError:
            pass

    return []  # Return empty list if no valid history exists

# Function to append chat data to a specific job
def save_chat_history(user_id, job_id, chat_history):
    """Save complete chat history as JSON to database"""
    jobs_table = DB_CONFIG['table_names']['jobs']
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"""
            UPDATE {jobs_table}
            SET chat_history = %s::jsonb, last_modified = NOW()
            WHERE user_id = %s AND job_id = %s;
        """, (json.dumps(chat_history), user_id, job_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()