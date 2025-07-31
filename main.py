from flask import Flask, request, jsonify, send_from_directory
import openai
import os
from docx import Document
import PyPDF2
from werkzeug.utils import secure_filename
from flask_cors import CORS

app = Flask(__name__)

CORS(app)  # This allows requests from any domain

# FEW SHOT EXAMPLES

FEW_SHOT_EXAMPLES = """
Example 1:

Resume:
Rami Zidan
rami.zidan@unitechmail.com | (456) 222-1098 | Canton, MI | github.com/ramiz | linkedin.com/in/ramizidan

OBJECTIVE
Highly motivated Computer Science student seeking an internship in software development to apply academic knowledge in real-world applications.

EDUCATION
Michigan Tech University — B.S. in Computer Science
Expected Graduation: May 2026 | GPA: 3.84

SKILLS
Python, Java, C++, Git, HTML/CSS/JS, MongoDB, SQL, Excel
Written and oral communication, problem-solving, Agile collaboration

PROJECTS
Smart Parking App (Spring 2025)
• Built a prototype Android app that uses GPS to help drivers locate empty parking spots
• Integrated Firebase for real-time updates and data storage
• Collaborated with 2 peers and presented project at Campus Tech Fair

Coursework Analysis Tool (Fall 2024)
• Used Python and pandas to analyze student grade trends across departments
• Created visualizations using Matplotlib

EXPERIENCE
Peer Tutor - Tech Learning Center
• Tutored students in Java and data structures
• Facilitated group sessions, improved public speaking confidence

ACTIVITIES & INTERESTS
• Arabic Culture Club, Hackathons, Coding Chess Club
• Enjoys digital painting and strategy games

Feedback:
✅ GPA is clearly listed.

✅ Academic projects are detailed and relevant to major.

✅ Work experience is closely tied to technical skill development.

✅ Tools and technical skills are clearly listed.

✅ Hobbies/activities show personality and tech engagement.

✅ Communication and teamwork are well-demonstrated.

Overall Rating: ✅ Strong Resume

---

Example 2:

Resume:
Dev Patel
dev.patelbio@gmail.com | (313) 999-1080 | Sterling Heights, MI

OBJECTIVE
Biology major looking for research or clinical shadowing opportunities to gain lab experience.

EDUCATION
Lakeside State University - B.S. Biology
Expected Graduation: May 2025 | GPA: 3.77

SKILLS
Biology terminology, critical thinking, academic writing

EXPERIENCE
Cashier - Speedway Gas Station (2022-2023)
• Handled cash and credit transactions
• Refilled inventory and cleaned equipment

Waiter - Bombay Palace Restaurant (2021-2022)
• Served customers during peak hours
• Memorized menu specials and ensured cleanliness

Feedback:
✅ GPA is included.

❌ No relevant academic or lab experience included.

❌ Work experience is unrelated to biology or scientific skills.

❌ No technical tools (e.g., SPSS, Excel, lab techniques) are listed.

❌ No extracurriculars or personal interest indicators.

⚠️ Needs more biology-related experiences (even class labs or volunteer work).

Overall Rating: ❌ Weak Resume - Irrelevant experience, missing core content

---
Example 3:

Resume:
Leah Park
leah.park@stargmail.com | (517) 732-6601 | Grand Rapids, MI

OBJECTIVE
I want to find an internship in the data science field to use my data knowledge and be part of big projects.

EDUCATION
Northern Metro University – B.S. in Data Science
Expected Graduation: 2026

SKILLS
Python, R, Excel, Tableau, pandas, scikit-learn

PROJECTS
COVID-19 Dashboard (2024)
• Built interactive charts with real-time case updates
• Visualized trends using matplotlib and seaborn

EXPERIENCE
Cashier – Kroger (2021–2022)
• Handled money and gave change to customers
• Restocked shelves

ACTIVITIES
• Book Club, Boba Enthusiasts Group

Feedback:

❌ GPA is missing — important for internship-stage students.

❌ No coursework or academic context to support major.

⚠️ Work experience is unrelated, with no link to data or tech.

✅ Tools and languages are listed clearly.

⚠️ Objective is vague and informal (“I want to…”).

✅ Projects are present but need clearer academic tie-ins.

⚠️ Book Club & Boba Club are not clearly connected to the major.

Overall Rating: ❌ Weak Resume - Missing GPA and academic grounding

---

Now, analyze the following resume and provide constructive feedback.
"""


def extract_text_from_file(file):
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".txt":
        return file.read().decode("utf-8")
    elif ext == ".docx":
        doc = Document(file)
        return "\n".join([p.text for p in doc.paragraphs])
    elif ext == ".pdf":
        reader = PyPDF2.PdfReader(file)
        return "\n".join([
            page.extract_text() for page in reader.pages
            if page.extract_text()
        ])
    else:
        raise ValueError("Unsupported file type.")


def chat_with_gpt(prompt):
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role":
            "system",
            "content":
            "You are an expert career advisor helping college students improve their resumes for internship applications. "
            "When given a resume, review it and make sure it includes the following key areas: "
            "1) Objective statement, "
            "2) Education and GPA, "
            "3) Relevant coursework, "
            "4) Academic or personal projects, "
            "5) Work or volunteer experience, "
            "6) Technical tools and software used, try to remind students of relevent tools they might have used"
            "dont just tell them you dont have enough technical skills because that might be all they learned since they can "
            "7) Communication and teamwork skills, "
            "8) Relevant activities and hobbies (especially if there is not enough coursework or job experience), "
            "9) Grammar and writing quality. "
            "Your goal is to identify what's strong and what's missing. "
            "Focus on whether the resume demonstrates internship-level readiness. Use bullet points to list strengths and weaknesses. "
            "At the end, give an Overall Rating as one of: ✅ Strong Resume, ⚠️ Adequate Resume, or ❌ Weak Resume. "
            "Be honest and specific. Don't sugarcoat. Mention irrelevant or vague sections "
            "(like hobbies that don't support the major) and call out grammar/spelling issues if present."
        }, {
            "role": "user",
            "content": prompt
        }])
    return response.choices[0].message.content.strip()


@app.route("/evaluate", methods=["POST"])
def evaluate():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    try:
        resume_text = extract_text_from_file(file)
        final_prompt = FEW_SHOT_EXAMPLES + "\nResume:\n" + resume_text + "\n\nFeedback:"
        feedback = chat_with_gpt(final_prompt)

        # Optional: Basic tag splitter
        tagged = {}
        current_section = "General"
        tagged[current_section] = ""

        for line in feedback.splitlines():
            if line.strip().startswith("✅") or line.strip().startswith(
                    "❌") or line.strip().startswith("⚠️"):
                tagged[current_section] += line + "\n"
            elif line.strip().lower().startswith("overall rating:"):
                tagged["Overall"] = line
            elif line.strip().endswith(":"):
                current_section = line.strip().replace(":", "")
                tagged[current_section] = ""
            else:
                tagged[current_section] += line + "\n"

        return jsonify(tagged)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Serve the HTML file
@app.route('/')
def index():
    return send_from_directory('.', 'test2.html')


# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
