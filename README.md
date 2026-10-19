# 🏆 CodeGen &mdash; Online Coding & Assessment Platform (Dasara Special Task 2026)

**CodeGen** is an enterprise-grade, full-stack **Coding & Examination Platform** built with **Python**, **Django**, **MySQL / SQLite**, **HTML5/Bootstrap 5**, and **JavaScript**.

The platform enables administrators to create timed Python exams comprising multiple-choice questions (MCQs) and algorithmic coding problems, while students attend timed tests, run code against sample inputs in real time, receive automatic scoring via an **isolated sandboxed execution runner**, view detailed scorecards with question-by-question explanations, download official certificates, and compete on a live leaderboard.

---

## 🚀 Key Modules & Features

### 1. 🛡️ Admin Module
- **Admin Dashboard**: Real-time stats on active tests, registered students, total submissions, and overall pass rates.
- **Test Management**: Full CRUD (Create, Read, Update, Delete) for exams, duration configuration, total/pass marks, and status toggles (Active vs. Draft).
- **Python MCQ Authoring**: Add questions with variable marks, custom negative marking, multiple choices, and explanatory notes.
- **Coding Question Authoring**: Add algorithmic problems with problem statements, starter boilerplate code, sample inputs/outputs, execution time limits, and hidden/sample test cases.
- **Submission & Score Auditing**: View all student attempts, time taken, marks scored, and exact code submissions.

### 2. 👨‍🎓 Student Module
- **Registration & Authentication**: Student onboarding with roll number, college name, and department tracking.
- **Student Dashboard**: Overview of available tests, completion metrics, and **Performance Analytics** chart (powered by Chart.js).
- **Timed Test Taking Interface**:
  - Live, non-pausable countdown timer with warning animations and automatic submission when expired.
  - Interactive **Question Palette** with color-coded tracking (Answered, Unanswered, Marked for Review).
  - In-browser Python code editor with live syntax styling and keyboard indentation.
  - **Run Code (Sample Cases)**: Instant test runner using AJAX to test solutions before submitting.
  - **Custom Input Stdin Runner**: Allows students to execute edge cases directly in the browser console.
- **Automatic Scoring & Instant Results**:
  - Instant automatic evaluation of MCQs and execution of coding solutions against all test cases.
  - Detailed scorecard featuring score, percentage, leaderboard standing, and time taken.
  - Comprehensive question-by-question review showing correct choices, explanations, and test case pass/fail verdicts.

### 3. 🥇 Leaderboard Module
- **Top 10 Performers**: Highlights top achievers with Gold, Silver, and Bronze podium cards.
- **Consistent Tie-Breaking**:
  1. Higher total marks
  2. Lesser time taken to complete the exam
  3. Earliest submission timestamp
- **Filters**: View overall platform standings or filter by specific examination.

### 4. ⚡ Advanced Features (Extra Credit Implemented)
- **Negative Marking**: Configurable per test or question (e.g. -0.25, -0.50) for wrong MCQ selections.
- **Randomized Questions**: Shuffles question sequences uniquely per student attempt while caching the order for session persistence.
- **Prevent Multiple Submissions**: Enforces strict single-attempt policies when enabled by the administrator.
- **Performance Analytics**: Visual score trends over time displayed on the student dashboard.
- **Official PDF Certificate Generation**: Top performers and passing candidates can download an official, cryptographic-UUID-verified **Certificate of Merit** generated on the fly via ReportLab.
- **Secure Code-Execution Sandbox**:
  > **Security Requirement Fulfilled**: Submitted Python code is **NEVER executed directly on the Django server**.
  - Code is analyzed using Python's Abstract Syntax Tree (`ast`) to block dangerous calls (`os`, `subprocess`, `shutil`, `socket`, `eval`, `open`, `__import__`).
  - Code is executed in an isolated subprocess inside a disposable temporary directory with Python's isolated mode (`-I`), bytecode inhibition (`-B`), and stripped environment variables.
  - Strict subprocess timeouts (e.g. 2.0s) prevent infinite loops and denial-of-service attempts.

---

## 🗄️ Database Architecture (Django Models)

- **`Student`**: Extends Django's `User` with `roll_number`, `college`, `department`, `phone`, and `avatar`.
- **`Test`**: Contains title, slug, duration, total marks, pass marks, negative marking rules, randomization flags, and active status.
- **`Question`**: Linked to `Test`; supports `MCQ` and `CODING` types, difficulty, marks, negative marks, sample inputs/outputs, starter code, and time limits.
- **`Option`**: Linked to `Question` (for MCQs); stores choice text, `is_correct` boolean, and answer explanations.
- **`TestCase`**: Linked to `Question` (for Coding); stores stdin `input_data`, stdout `expected_output`, and `is_sample` flag.
- **`TestAttempt`**: Linked to `Student` and `Test`; tracks `started_at`, `completed_at`, `time_taken_seconds`, `score`, `percentage`, `is_passed`, and saved randomized question sequence.
- **`Submission`**: Linked to `TestAttempt` and `Question`; stores selected option (MCQ) or submitted code (Coding), pass/fail status, test cases passed, and execution logs.

---

## 🛠️ Installation & Quickstart

### Prerequisites
- Python 3.11+
- pip
- MySQL 8.0+ (optional; SQLite works out-of-the-box by default)

### 1. Clone & Setup Environment
```bash
cd online_coding_platform
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Database
By default, the platform uses **SQLite** for instant zero-config startup.

To connect to **MySQL** as required by the specification:
1. Ensure your MySQL server is running.
2. Create the database:
   ```sql
   CREATE DATABASE coding_test_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. Set environment variables (or create a `.env` file from `.env.example`):
   ```bash
   # Windows PowerShell:
   $env:USE_MYSQL="True"
   $env:DB_NAME="coding_test_db"
   $env:DB_USER="root"
   $env:DB_PASSWORD="your_password"
   ```

### 3. Apply Migrations & Seed Sample Data
```bash
python manage.py migrate
python seed_data.py
```

### 4. Run Development Server
```bash
python manage.py runserver
```
Visit **http://127.0.0.1:8000/** in your web browser.

---

## 🔑 Default Credentials (Seed Data)

| Role | Username | Password | Notes |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `adminpassword123` | Full access to Admin Portal & Django Admin |
| **Student 1** | `rahul_s` | `student123` | Rank #1 on Leaderboard (IIT Hyderabad) |
| **Student 2** | `priya_p` | `student123` | Rank #2 on Leaderboard (NIT Warangal) |
| **Student 3** | `amit_v` | `student123` | Rank #3 on Leaderboard (BITS Pilani) |

---

## 🧪 Running Automated Tests

Run the complete test suite:
```bash
python manage.py test
```
The suite verifies:
- Sandboxed Python execution & stdout capturing
- Security violation blocking for forbidden modules and AST calls
- Timeout enforcement for infinite loops
- Student registration, login, and authorization guards
- End-to-end exam taking, auto-scoring, and negative marking
- Single submission policy enforcement
- Leaderboard tie-breaking logic
- ReportLab PDF certificate generation

---

## 📢 LinkedIn Post Template

> 🚀 Excited to share that I have built and deployed the **Online Coding Test Platform** for the **Dasara Special Task 2026**!
>
> 💻 **Tech Stack**: Python, Django, MySQL, Bootstrap 5, JavaScript, and ReportLab.
>
> 🌟 **Key Highlights**:
> - Admin test builder with Python MCQs & algorithmic coding questions
> - Sandboxed, isolated Python execution engine with AST security inspection
> - Live student test environment with countdown timers and instant evaluation
> - Dynamic Leaderboard with consistent tie-breaking rules
> - Automated PDF certificate generation for top performers
>
> Special thanks to **@10000 Coders** for this challenging project!
> #Python #Django #WebDevelopment #CodingTest #10000Coders #Dasara2026
