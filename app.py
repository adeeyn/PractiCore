import os
import re
import spacy
import pdfplumber
import docx
from spacy.matcher import PhraseMatcher
from flask import Flask, render_template,Blueprint ,request, redirect, url_for, session, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import random

app = Flask(__name__, template_folder='templates')

employer_bp = Blueprint(
    'employer', 
    __name__, 
    template_folder='templates_employer',
    static_folder='static_employer',         
    static_url_path='/static_employer',      
    url_prefix='/employer'
)

app.secret_key = "nyek"



# File Upload Configuration
UPLOAD_FOLDER = 'uploads/resumes'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

# Load SpaCy model once at application startup
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    raise RuntimeError("SpaCy model 'en_core_web_sm' not found. Run: python -m spacy download en_core_web_sm")

# MySQL Configuration
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'practicore'
}

def get_db():
    """Helper function to obtain a fresh MySQL connection."""
    return mysql.connector.connect(**DB_CONFIG)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- SPA CY PARSER HELPERS ---

def extract_text_from_pdf(file_stream):
    text = ""
    with pdfplumber.open(file_stream) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text

def extract_text_from_docx(file_stream):
    doc = docx.Document(file_stream)
    return "\n".join([p.text for p in doc.paragraphs if p.text])

# Mapped Skills Taxonomy aligned with the 6 Core Job Categories
SKILL_CATEGORY_MAP = {
    "Software & Application Development": [
        "Python", "Java", "C++", "VB.NET", "JavaScript", "HTML", "CSS", 
        "React", "Node.js", "Flask", "Django", "UI/UX", "Git"
    ],
    "Systems, Infrastructure & Networks": [
        "Networking", "Cisco", "TCP/IP", "VLAN", "Linux", "Windows Server", 
        "Cloud", "AWS", "Docker", "Cybersecurity"
    ],
    "IT Service Management & Operations": [
        "ITIL", "Service Desk", "Incident Management", "Agile", "Scrum", 
        "Jira", "Technical Support"
    ],
    "Data, AI & Analytics": [
        "SQL", "PostgreSQL", "MongoDB", "Machine Learning", "Data Analysis", 
        "NLP", "Pandas", "Power BI", "Tableau"
    ],
    "Cybersecurity & Risk Management": [
        "Network Security", "Ethical Hacking", "NIST", "OWASP", "Penetration Testing", 
        "Risk Assessment", "Information Security"
    ],
    "Business Systems & Project Management": [
        "Business Analysis", "Requirements Gathering", "BPMN", "Project Management", 
        "SDLC", "System Analysis"
    ]
}


def parse_resume_stream(file_stream, filename):
    # 1. Extract plain text
    if filename.endswith('.pdf'):
        text = extract_text_from_pdf(file_stream)
    elif filename.endswith('.docx'):
        text = extract_text_from_docx(file_stream)
    else:
        raise ValueError("Unsupported format")

    doc = nlp(text)

    # 2. Extract Regex Data (Email & Phone)
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    
    email_match = re.search(email_pattern, text)
    phone_match = re.search(phone_pattern, text)

    # 3. Extract Name using SpaCy NER
    extracted_name = None
    first_few_lines = "\n".join(text.split("\n")[:5])
    top_doc = nlp(first_few_lines)
    for ent in top_doc.ents:
        if ent.label_ == "PERSON":
            extracted_name = ent.text.strip()
            break

    # 4. Extract Skills using PhraseMatcher
    all_skills = list({skill for sublist in SKILL_CATEGORY_MAP.values() for skill in sublist})

    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp.make_doc(skill) for skill in all_skills]
    matcher.add("SKILLS", patterns)

    matches = matcher(doc)
    found_skills = set()
    for match_id, start, end in matches:
        found_skills.add(doc[start:end].text)

    # 5. Group extracted skills into their respective categories
    categorized_skills = {}
    for skill in found_skills:
        for category, skills_list in SKILL_CATEGORY_MAP.items():
            if any(s.lower() == skill.lower() for s in skills_list):
                if category not in categorized_skills:
                    categorized_skills[category] = []
                if skill not in categorized_skills[category]:
                    categorized_skills[category].append(skill)

    return {
        "name": extracted_name,
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0) if phone_match else None,
        "skills": list(found_skills),
        "categorized_skills": categorized_skills
    }


# --- ROUTES ---

@app.route("/student_login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM students WHERE username = %s",
            (username,)
        )
        record = cursor.fetchone()
        cursor.close()
        db.close()

        if record:
            stored_password = record.get("password_hash") or record.get("password")
            is_valid = False
            
            if stored_password:
                if stored_password.startswith("pbkdf2:") or stored_password.startswith("scrypt:"):
                    is_valid = check_password_hash(stored_password, password)
                else:
                    is_valid = (stored_password == password)

            if is_valid:
                session["loggedin"] = True
                session["username"] = record.get("username")
                session["studentNo"] = record.get("student_no") or record.get("studentNo")

                return redirect(url_for("student_dashboard"))

        failed_username = request.args.get("username", "")
        return render_template("student_login.html", failed=1, username=failed_username)

    return render_template("student_login.html", failed=0, username="")


@app.route('/student_register', methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        student_no = request.form.get('studentNo', '').strip()
        phone = request.form.get('phone', '').strip()
        year_level = request.form.get('year_level', '4th Year').strip()
        course = request.form.get('course', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirmPassword', '').strip()

        if not all([name, email, username, student_no, course, password, confirm_password]):
            return render_template('student_register.html', error="Please fill out all required fields.")

        if password != confirm_password:
            return render_template('student_register.html', error="Passwords do not match.")

        hashed_password = generate_password_hash(password)

        try:
            db = get_db()
            cursor = db.cursor(dictionary=True)

            cursor.execute(
                "SELECT id FROM students WHERE student_no = %s OR username = %s OR email = %s",
                (student_no, username, email)
            )
            existing = cursor.fetchone()

            if existing:
                cursor.close()
                db.close()
                return render_template('student_register.html', error="Student Number, Username, or Email already exists.")

            cursor.execute("""
                INSERT INTO students (name, email, username, student_no, phone, year_level, course, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, email, username, student_no, phone, year_level, course, hashed_password))

            db.commit()
            cursor.close()
            db.close()

            return redirect(url_for('student_login'))

        except mysql.connector.Error as err:
            return render_template('student_register.html', error=f"Database error: {err}")

    return render_template('student_register.html')

@app.route("/student_dashboard")
def student_dashboard():
    if 'loggedin' not in session:
        return redirect(url_for("student_login"))

    student_username = session.get('username')
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # 1. Fetch Student Profile, Assessment Stats, and Resume Skills
    cursor.execute("""
        SELECT id, name, skills, assessment_score, total_questions 
        FROM students 
        WHERE username = %s
    """, (student_username,))
    student = cursor.fetchone()

    student_id = student['id'] if student else None
    student_skills_str = student.get('skills', '') if student else ''
    student_skills_set = set([s.strip().lower() for s in student_skills_str.split(',') if s.strip()])

    # --- METRIC 1: ASSESSMENT SCORE ---
    assessment_percentage = 0
    if student and student.get('total_questions') and student['total_questions'] > 0:
        assessment_percentage = round((student['assessment_score'] / student['total_questions']) * 100)

    # --- METRIC 2: APPLICATIONS IN PROGRESS ---
    applications_count = 0
    if student_id:
        try:
            cursor.execute("SELECT COUNT(*) AS total FROM applications WHERE student_id = %s", (student_id,))
            app_result = cursor.fetchone()
            applications_count = app_result['total'] if app_result else 0
        except mysql.connector.Error:
            # Fallback if applications table hasn't been created yet
            applications_count = 0

    # --- METRIC 3 & RECOMMENDATIONS: FETCH POSTINGS & CALCULATE MATCHES ---
    category_breakdown = session.get('latest_assessment_results', {}).get('category_breakdown', {})

    cursor.execute("""
        SELECT 
            p.id,
            p.title,
            p.description,
            p.is_remote,
            p.posted_date,
            e.company_name,
            e.company_logo_text,
            e.location
        FROM internship_postings p
        JOIN employers e ON p.employer_id = e.id
        ORDER BY p.posted_date DESC
    """)
    postings = cursor.fetchall()

    recommendations = []
    total_match_scores = []

    for item in postings:
        cursor.execute("SELECT skill_name FROM posting_skills WHERE posting_id = %s", (item['id'],))
        skill_records = cursor.fetchall()
        posting_skills = [s['skill_name'] for s in skill_records]

        # Calculate Resume Match percentage against required posting skills
        matched_resume_skills = []
        if posting_skills:
            for req_skill in posting_skills:
                req_lower = req_skill.strip().lower()
                if any(req_lower in user_skill or user_skill in req_lower for user_skill in student_skills_set):
                    matched_resume_skills.append(req_skill)
            
            # Resume Match % for this specific posting
            resume_match_pct = round((len(matched_resume_skills) / len(posting_skills)) * 100)
        else:
            resume_match_pct = 0

        # Category Assessment Score match
        recommended_category = map_skills_to_category(posting_skills)
        domain_stats = category_breakdown.get(recommended_category, {})
        assessment_match_pct = domain_stats.get('score_percent', assessment_percentage)

        # Combined Match Score (50% Assessment + 50% Resume Match)
        if matched_resume_skills or student_skills_set:
            combined_match = round((assessment_match_pct + resume_match_pct) / 2) if resume_match_pct > 0 else assessment_match_pct
        else:
            combined_match = assessment_match_pct

        total_match_scores.append(resume_match_pct)

        # Extract initials for logo fallback (e.g., Tech Solution Inc -> TS)
        company_logo = item['company_logo_text']
        if not company_logo and item['company_name']:
            company_logo = "".join([word[0] for word in item['company_name'].split()[:2]]).upper()

        recommendations.append({
            'id': item['id'],
            'title': item['title'],
            'company': item['company_name'],
            'location': item['location'],
            'logo': company_logo or 'IT',
            'is_remote': item['is_remote'],
            'match_score': combined_match if combined_match > 0 else 75,
            'match_color_class': 'green' if combined_match >= 85 else 'amber'
        })

    # Average Resume Match Rate across available matching positions
    avg_resume_match = round(sum(total_match_scores) / len(total_match_scores)) if total_match_scores else (85 if student_skills_set else 0)

    # Sort and slice top 3 recommendations for the main dashboard preview
    recommendations = sorted(recommendations, key=lambda x: x['match_score'], reverse=True)[:3]

    cursor.close()
    db.close()

    return render_template(
        "student_dashboard.html",
        username=student['name'] if student and student.get('name') else session.get('username'),
        assessment_score=assessment_percentage,
        resume_match=avg_resume_match,
        applications_count=applications_count,
        recommendations=recommendations,
        active_page='dashboard'
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("student_login"))


@app.route('/student_profile')
def student_profile():
    if 'loggedin' not in session:
        return redirect(url_for('student_login'))
    
    return render_template('student_profile.html', active_page='profile')


@app.route('/upload_resume', methods=['GET', 'POST'])
def upload_resume():
    if 'loggedin' not in session:
        return redirect(url_for('student_login'))
    
    student_username = session.get('username')
    
    # POST Request: Handle Upload & Parsing
    if request.method == 'POST':
        if 'resume' not in request.files:
            return jsonify({'error': 'No file submitted'}), 400
            
        file = request.files['resume']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            
            try:
                parsed_data = parse_resume_stream(file.stream, filename)
                
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.seek(0)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                
                skills_str = ", ".join(parsed_data['skills'])
                
                db = get_db()
                cursor = db.cursor()
                cursor.execute("""
                    UPDATE students 
                    SET skills = %s, resume_path = %s
                    WHERE username = %s
                """, (skills_str, filename, student_username))
                db.commit()
                cursor.close()
                db.close()

                return jsonify({
                    'status': 'success',
                    'filename': filename,
                    'parsed_data': parsed_data
                }), 200

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        return jsonify({'error': 'Invalid file extension'}), 400

    # GET Request: Fetch saved student resume details from Database
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT name, email, phone, skills, resume_path FROM students WHERE username = %s",
        (student_username,)
    )
    student = cursor.fetchone()
    cursor.close()
    db.close()

    # Parse saved skills back into a Python list
    saved_skills = []
    if student and student.get('skills'):
        saved_skills = [s.strip() for s in student['skills'].split(',') if s.strip()]

    return render_template(
        'upload_resume.html',
        active_page='resume',
        student=student,
        skills=saved_skills
    )

@app.route('/assessment', methods=['GET'])
def assessment():
    if 'loggedin' not in session:
        return redirect(url_for('student_login'))
    
    student_username = session.get('username')
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Fetch student assessment stats
    cursor.execute(
        "SELECT assessment_score, total_questions, competency_level FROM students WHERE username = %s",
        (student_username,)
    )
    student = cursor.fetchone()

    # Calculate live score percentage safely
    score_percentage = 0
    if student and student.get('total_questions') and student['total_questions'] > 0:
        score_percentage = round((student['assessment_score'] / student['total_questions']) * 100)

    cursor.close()
    db.close()

    return render_template(
        'assessment.html', 
        active_page='assessment', 
        student=student, 
        score_percentage=score_percentage
    )
@app.route('/start_assessment', methods=['GET'])
def start_assessment():
    if 'loggedin' not in session:
        return redirect(url_for('student_login'))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM assessment_questions")
    all_questions = cursor.fetchall()

    domain_buckets = {
        'Software & Application Development': [],
        'Systems, Infrastructure & Networks': [],
        'IT Service Management & Operations': [],
        'Data, AI & Analytics': [],
        'Cybersecurity & Risk Management': [],
        'Business Systems & Project Management': []
    }

    # Group questions into buckets
    for q in all_questions:
        track = q.get('course_track') or q.get('track_code') or q.get('track') or ''
        role = q.get('target_role') or q.get('job_title') or ''
        domain = map_to_6_domains(track, role)
        domain_buckets[domain].append(q)

    selected_questions = []
    grouped_questions = {}
    question_domain_map = {}  # { "question_id": "Domain Name" }

    for domain_name, q_list in domain_buckets.items():
        random.shuffle(q_list)
        chosen = q_list[:15]  # Exactly 15 questions per domain
        grouped_questions[domain_name] = chosen
        
        for q in chosen:
            question_domain_map[str(q['id'])] = domain_name
            selected_questions.append(q)

    cursor.close()
    db.close()

    # Store exact 15-question mapping in session for submission evaluation
    session['active_assessment_map'] = question_domain_map

    random.shuffle(selected_questions)

    # BOTH 'questions' AND 'grouped_questions' ARE PASSED TO TEMPLATE
    return render_template(
        'start_assessment.html',
        questions=selected_questions,
        grouped_questions=grouped_questions,
        total_questions=len(selected_questions)
    )



# The 6 standard job domains mapping dictionary
DOMAIN_LABEL_MAP = {
    'Software & Application Development': 'Software & Application Development',
    'Systems, Infrastructure & Networks': 'Systems, Infrastructure & Networks',
    'IT Service Management & Operations': 'IT Service Management & Operations',
    'Data, AI & Analytics': 'Data, AI & Analytics',
    'Cybersecurity & Risk Management': 'Cybersecurity & Risk Management',
    'Business Systems & Project Management': 'Business Systems & Project Management'
}

# Helper mapping track codes or target roles to the 6 core job categories
def map_to_6_domains(track_code, target_role=""):
    track = str(track_code or '').strip().upper()
    role = str(target_role or '').strip().lower()

    # 1. Cybersecurity & Risk Management
    if 'SEC' in track or 'CYBER' in track or any(k in role for k in ['security', 'cyber', 'risk', 'soc', 'penetration']):
        return 'Cybersecurity & Risk Management'

    # 2. Data, AI & Analytics
    elif 'DATA' in track or 'AI' in track or 'ANALYTICS' in track or any(k in role for k in ['data', 'analytics', 'ai', 'machine learning']):
        return 'Data, AI & Analytics'

    # 3. IT Service Management & Operations
    elif 'TSM' in track or 'ITSM' in track or any(k in role for k in ['service', 'support', 'helpdesk', 'itsm', 'operations']):
        return 'IT Service Management & Operations'

    # 4. Systems, Infrastructure & Networks
    elif 'NET' in track or 'NA' in track or 'INFRA' in track or any(k in role for k in ['network', 'sysadmin', 'infrastructure', 'cisco']):
        return 'Systems, Infrastructure & Networks'

    # 5. Business Systems & Project Management
    elif 'SYS' in track or 'BIZ' in track or 'PM' in track or any(k in role for k in ['project', 'business analyst', 'scrum', 'erp']):
        return 'Business Systems & Project Management'

    # 6. Software & Application Development (Explicit match or WMA)
    elif 'DEV' in track or 'WMA' in track or 'APP' in track or any(k in role for k in ['developer', 'software', 'web', 'frontend', 'backend', 'fullstack']):
        return 'Software & Application Development'

    # Fallback
    return 'Software & Application Development'

@app.route('/submit_assessment', methods=['POST'])
def submit_assessment():
    if 'loggedin' not in session:
        return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

    answers = request.get_json() or {}
    active_map = session.get('active_assessment_map', {})

    category_breakdown = {
        'Software & Application Development': {'correct': 0, 'total': 0, 'track': 'DEV'},
        'Systems, Infrastructure & Networks': {'correct': 0, 'total': 0, 'track': 'NET'},
        'IT Service Management & Operations': {'correct': 0, 'total': 0, 'track': 'TSM'},
        'Data, AI & Analytics': {'correct': 0, 'total': 0, 'track': 'DATA'},
        'Cybersecurity & Risk Management': {'correct': 0, 'total': 0, 'track': 'SEC'},
        'Business Systems & Project Management': {'correct': 0, 'total': 0, 'track': 'SYS'}
    }

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        # Parse submitted question IDs (handles "q_15" and "15" formats)
        submitted_q_ids = []
        for key in answers.keys():
            cleaned_id = str(key).replace('q_', '').strip()
            if cleaned_id.isdigit():
                submitted_q_ids.append(int(cleaned_id))

        # Query active test questions using IDs, or fallback to active session map IDs
        if submitted_q_ids:
            format_strings = ','.join(['%s'] * len(submitted_q_ids))
            cursor.execute(f"SELECT * FROM assessment_questions WHERE id IN ({format_strings})", tuple(submitted_q_ids))
            active_questions = cursor.fetchall()
        elif active_map:
            map_ids = [int(k) for k in active_map.keys() if str(k).isdigit()]
            format_strings = ','.join(['%s'] * len(map_ids))
            cursor.execute(f"SELECT * FROM assessment_questions WHERE id IN ({format_strings})", tuple(map_ids))
            active_questions = cursor.fetchall()
        else:
            cursor.execute("SELECT * FROM assessment_questions LIMIT 90")
            active_questions = cursor.fetchall()

        total_correct = 0
        total_questions = len(active_questions)

        for q in active_questions:
            q_id_str = str(q['id'])
            domain = active_map.get(q_id_str)

            if not domain:
                track = q.get('course_track') or q.get('track_code') or ''
                role = q.get('target_role') or ''
                domain = map_to_6_domains(track, role)

            if domain in category_breakdown:
                category_breakdown[domain]['total'] += 1

                # =========================================================
                # 1. TESTING BYPASS ENABLED (Marks all answers correct)
                # =========================================================
                category_breakdown[domain]['correct'] += 1
                total_correct += 1

                # =========================================================
                # 2. REAL GRADING LOGIC (COMMENTED OUT FOR NOW)
                #    Uncomment this section & comment out lines 48-49 when live
                # =========================================================
                # selected_answer = answers.get(f"q_{q_id_str}") or answers.get(q_id_str) or ""
                # correct_answer = q.get('correct_option') or q.get('correct_answer') or q.get('answer') or ""
                # if selected_answer and str(selected_answer).strip().upper() == str(correct_answer).strip().upper():
                #     category_breakdown[domain]['correct'] += 1
                #     total_correct += 1

        # Calculate percentages
        for domain, stats in category_breakdown.items():
            if stats['total'] > 0:
                stats['score_percent'] = round((stats['correct'] / stats['total']) * 100)
            else:
                stats['score_percent'] = 0

        overall_percentage = round((total_correct / total_questions) * 100) if total_questions > 0 else 0
        competency_level = "Advanced / Job-Ready" if overall_percentage >= 85 else "Intermediate / Competent"

        student_username = session.get('username')
        cursor.execute("""
            UPDATE students 
            SET assessment_score = %s, total_questions = %s, competency_level = %s 
            WHERE username = %s
        """, (total_correct, total_questions, competency_level, student_username))
        db.commit()

        session['latest_assessment_results'] = {
            'overall_percentage': overall_percentage,
            'total_correct': total_correct,
            'total_questions': total_questions,
            'competency_level': competency_level,
            'category_breakdown': category_breakdown
        }

        cursor.close()
        db.close()

        return jsonify({
            'status': 'success',
            'redirect_url': url_for('assessment_results')
        })

    except Exception as e:
        if cursor:
            cursor.close()
        if db:
            db.close()
        print(f"Error in submit_assessment: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
    
@app.route('/assessment_results')
def assessment_results():
    if 'loggedin' not in session:
        return redirect(url_for('student_login'))

    results = session.get('latest_assessment_results')
    if not results:
        return redirect(url_for('start_assessment'))

    return render_template(
        'assessment_results.html',
        active_page='assessment',
        competency_level=results['competency_level'],
        overall_percentage=results['overall_percentage'],
        total_correct=results['total_correct'],
        total_questions=results['total_questions'],
        category_breakdown=results['category_breakdown']  # <--- MUST MATCH THIS KEY NAME
    )

def map_skills_to_category(required_skills):
    """Maps a list of required posting skills to 1 of the 6 core job taxonomy categories."""
    category_scores = {cat: 0 for cat in SKILL_CATEGORY_MAP.keys()}
    
    for skill in required_skills:
        skill_clean = skill.strip().lower()
        for category, taxonomy_skills in SKILL_CATEGORY_MAP.items():
            for tax_skill in taxonomy_skills:
                tax_clean = tax_skill.lower()
                if tax_clean in skill_clean or skill_clean in tax_clean:
                    category_scores[category] += 1

    best_category = max(category_scores, key=category_scores.get)
    if category_scores[best_category] == 0:
        best_category = "Software & Application Development"
        
    return best_category

def calculate_match_score(assessment_percentage):

    if assessment_percentage is None or assessment_percentage == 0:
        return 50  # Default baseline score before taking the quiz

    # Score bounded realistically between 30% and 99%
    return max(30, min(round(float(assessment_percentage)), 99))


@app.route('/recommendation')
def recommendation():
    if 'loggedin' not in session:
        return redirect(url_for('student_login'))
        
    student_username = session.get('username')
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # 1. Fetch student's extracted resume skills
    cursor.execute("SELECT skills FROM students WHERE username = %s", (student_username,))
    student = cursor.fetchone()
    
    student_skills_str = student.get('skills', '') if student else ''
    student_skills_set = set([s.strip().lower() for s in student_skills_str.split(',') if s.strip()])

    # 2. Get category breakdown from assessment session
    assessment_results = session.get('latest_assessment_results', {})
    category_breakdown = assessment_results.get('category_breakdown', {})

    # 3. Fetch internship postings
    cursor.execute("""
        SELECT 
            p.id,
            p.title,
            p.description,
            p.is_remote,
            p.posted_date,
            e.company_name,
            e.company_logo_text,
            e.location
        FROM internship_postings p
        JOIN employers e ON p.employer_id = e.id
        ORDER BY p.posted_date DESC
    """)
    postings = cursor.fetchall()

    recommendations = []
    for item in postings:
        cursor.execute("SELECT skill_name FROM posting_skills WHERE posting_id = %s", (item['id'],))
        skill_records = cursor.fetchall()
        posting_skills = [s['skill_name'] for s in skill_records]

        # Match resume skills against required skills
        matched_resume_skills = []
        for req_skill in posting_skills:
            req_lower = req_skill.strip().lower()
            if any(req_lower in user_skill or user_skill in req_lower for user_skill in student_skills_set):
                matched_resume_skills.append(req_skill)

        # RESUME FILTER: Only display companies that match at least 1 resume skill
        if not matched_resume_skills:
            continue

        recommended_category = map_skills_to_category(posting_skills)

        # Get assessment score for this domain
        domain_stats = category_breakdown.get(recommended_category, {})
        match_score = domain_stats.get('score_percent', 50)

        if match_score >= 80:
            badge_class = "high"
        elif match_score >= 60:
            badge_class = "medium"
        else:
            badge_class = "top"

        recommendations.append({
            'id': item['id'],
            'title': item['title'],
            'company': item['company_name'],
            'location': item['location'],
            'logo': item['company_logo_text'],
            'description': item['description'],
            'is_remote': item['is_remote'],
            'skills': posting_skills,
            'matched_resume_skills': matched_resume_skills,
            'match_score': match_score,
            'match_badge_class': badge_class,
            'recommended_category': recommended_category,
            'posted': item['posted_date'].strftime('%b %d, %Y') if item['posted_date'] else 'Recently'
        })

    # Sort recommendations by highest domain assessment score
    recommendations = sorted(recommendations, key=lambda x: x['match_score'], reverse=True)

    cursor.close()
    db.close()

    return render_template('recommendation.html', active_page='recommendation', recommendations=recommendations)


@app.route('/application')
def application():
    if 'loggedin' not in session:
        return redirect(url_for('student_login'))
        
    return render_template('application.html', active_page='application')


@employer_bp.route('/dashboard')
def employer_dashboard():
    return render_template('dashboard.html')

app.register_blueprint(employer_bp)

if __name__ == "__main__":
    app.run(debug=True)