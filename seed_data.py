import os
import sys
import django
from decimal import Decimal
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coding_platform.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from exam_portal.models import Student, Test, Question, Option, TestCase, TestAttempt, Submission
from exam_portal.sandbox import evaluate_coding_question


def run_seed():
    print("[*] Starting database seeding...")

    # 1. Create Admin
    admin_user, created = User.objects.get_or_create(username='admin', defaults={
        'email': 'admin@10000coders.co',
        'first_name': 'Exam',
        'last_name': 'Administrator',
        'is_staff': True,
        'is_superuser': True
    })
    if created:
        admin_user.set_password('adminpassword123')
        admin_user.save()
        print("[OK] Created Superuser/Admin: admin / adminpassword123")
    else:
        print("[OK] Superuser already exists")

    # 2. Create Students
    students_data = [
        {"username": "rahul_s", "first": "Rahul", "last": "Sharma", "roll": "2026PY001", "college": "IIT Hyderabad", "dept": "Computer Science"},
        {"username": "priya_p", "first": "Priya", "last": "Patel", "roll": "2026PY002", "college": "NIT Warangal", "dept": "Information Technology"},
        {"username": "amit_v", "first": "Amit", "last": "Verma", "roll": "2026PY003", "college": "BITS Pilani", "dept": "AI & Data Science"},
        {"username": "sneha_r", "first": "Sneha", "last": "Reddy", "roll": "2026PY004", "college": "Osmania University", "dept": "Computer Science"},
        {"username": "vikram_k", "first": "Vikram", "last": "Kumar", "roll": "2026PY005", "college": "JNTU Hyderabad", "dept": "Software Engineering"},
        {"username": "ananya_d", "first": "Ananya", "last": "Das", "roll": "2026PY006", "college": "IIIT Hyderabad", "dept": "Electronics & CS"},
        {"username": "kavita_m", "first": "Kavita", "last": "Menon", "roll": "2026PY007", "college": "Vellore Tech", "dept": "Computer Science"},
    ]

    students = []
    for s in students_data:
        u, _ = User.objects.get_or_create(username=s['username'], defaults={
            'email': f"{s['username']}@student.ac.in",
            'first_name': s['first'],
            'last_name': s['last']
        })
        u.set_password('student123')
        u.save()

        st, _ = Student.objects.get_or_create(user=u, defaults={
            'roll_number': s['roll'],
            'college': s['college'],
            'department': s['dept'],
            'phone': '+91 98765 43210'
        })
        students.append(st)

    print(f"[OK] Created {len(students)} student profiles (Password: student123)")

    # 3. Create Tests
    # Test 1: Python Core & Algorithmic Challenge 2026
    test1, _ = Test.objects.get_or_create(
        title="Python Core & Algorithmic Challenge 2026",
        defaults={
            'description': "Comprehensive Python assessment testing object-oriented concepts, mutability, decorators, generator expressions, and algorithmic problem-solving with isolated test case execution.",
            'duration_minutes': 30,
            'total_marks': 50,
            'pass_marks': 25,
            'negative_marking': True,
            'negative_mark_value': Decimal('0.50'),
            'randomize_questions': True,
            'allow_multiple_attempts': False,
            'is_active': True,
            'created_by': admin_user
        }
    )

    # MCQs for Test 1
    mcq1, _ = Question.objects.get_or_create(
        test=test1, order=1, question_type='MCQ',
        title="Python Mutability and Default Parameter Evaluation",
        defaults={
            'prompt': "What will be the output of executing the following snippet?\n\n```python\ndef append_item(val, items=[]):\n    items.append(val)\n    return items\n\nprint(append_item(1))\nprint(append_item(2))\n```",
            'marks': 5,
            'difficulty': 'MEDIUM'
        }
    )
    if not mcq1.options.exists():
        Option.objects.create(question=mcq1, text="[1] and [2]", is_correct=False, explanation="In Python, default arguments are evaluated once at function definition time, not every invocation.")
        Option.objects.create(question=mcq1, text="[1] and [1, 2]", is_correct=True, explanation="Because the list is mutable and bound at function definition time, subsequent calls append to the same list instance.")
        Option.objects.create(question=mcq1, text="[1, 2] and [1, 2]", is_correct=False)
        Option.objects.create(question=mcq1, text="TypeError: default arguments cannot be lists", is_correct=False)

    mcq2, _ = Question.objects.get_or_create(
        test=test1, order=2, question_type='MCQ',
        title="List Comprehension Variable Scope",
        defaults={
            'prompt': "In Python 3, what is printed by the following code?\n\n```python\nx = 10\nres = [x * 2 for x in range(3)]\nprint(x)\n```",
            'marks': 5,
            'difficulty': 'EASY'
        }
    )
    if not mcq2.options.exists():
        Option.objects.create(question=mcq2, text="2", is_correct=False)
        Option.objects.create(question=mcq2, text="10", is_correct=True, explanation="In Python 3, list comprehensions have their own local scope, preventing the iteration variable from leaking into the enclosing scope.")
        Option.objects.create(question=mcq2, text="4", is_correct=False)
        Option.objects.create(question=mcq2, text="NameError: name 'x' is ambiguous", is_correct=False)

    mcq3, _ = Question.objects.get_or_create(
        test=test1, order=3, question_type='MCQ',
        title="Dictionary Key Hashability",
        defaults={
            'prompt': "Which of the following data types CANNOT be used as a dictionary key in Python?",
            'marks': 5,
            'difficulty': 'EASY'
        }
    )
    if not mcq3.options.exists():
        Option.objects.create(question=mcq3, text="Tuple containing strings (e.g. ('a', 'b'))", is_correct=False)
        Option.objects.create(question=mcq3, text="Frozenset (e.g. frozenset([1, 2]))", is_correct=False)
        Option.objects.create(question=mcq3, text="List of integers (e.g. [1, 2, 3])", is_correct=True, explanation="Lists are mutable and unhashable, therefore cannot be used as dictionary keys.")
        Option.objects.create(question=mcq3, text="Integer (e.g. 42)", is_correct=False)

    mcq4, _ = Question.objects.get_or_create(
        test=test1, order=4, question_type='MCQ',
        title="Time Complexity of In-Operator on Set vs List",
        defaults={
            'prompt': "What is the average time complexity of checking membership (`x in collection`) for a Python `set` versus a Python `list` of size N?",
            'marks': 5,
            'difficulty': 'MEDIUM'
        }
    )
    if not mcq4.options.exists():
        Option.objects.create(question=mcq4, text="O(1) for set, O(N) for list", is_correct=True, explanation="Sets use hash tables offering O(1) average lookup, whereas lists require O(N) linear search.")
        Option.objects.create(question=mcq4, text="O(N) for set, O(1) for list", is_correct=False)
        Option.objects.create(question=mcq4, text="O(log N) for set, O(N) for list", is_correct=False)
        Option.objects.create(question=mcq4, text="O(1) for both", is_correct=False)

    # Coding Problem 1 for Test 1
    code_q1, _ = Question.objects.get_or_create(
        test=test1, order=5, question_type='CODING',
        title="Reverse Words in a String",
        defaults={
            'prompt': (
                "Given an input string `S` consisting of space-separated words, reverse the order of the words.\n\n"
                "**Input Format:**\n"
                "A single line containing words separated by spaces.\n\n"
                "**Output Format:**\n"
                "Print the words in reverse order on a single line separated by a single space.\n\n"
                "**Example:**\n"
                "Input: `Dasara Special Task 2026`\n"
                "Output: `2026 Task Special Dasara`"
            ),
            'marks': 15,
            'difficulty': 'MEDIUM',
            'sample_input': "Dasara Special Task 2026",
            'sample_output': "2026 Task Special Dasara",
            'starter_code': (
                "# Read input from stdin\n"
                "import sys\n\n"
                "line = sys.stdin.read().strip()\n"
                "# Write your logic to reverse words and print stdout\n"
                "words = line.split()\n"
                "print(' '.join(reversed(words)))\n"
            ),
            'time_limit_seconds': 2.0
        }
    )
    if not code_q1.test_cases.exists():
        TestCase.objects.create(question=code_q1, input_data="Dasara Special Task 2026", expected_output="2026 Task Special Dasara", is_sample=True)
        TestCase.objects.create(question=code_q1, input_data="Hello World", expected_output="World Hello", is_sample=True)
        TestCase.objects.create(question=code_q1, input_data="Python is awesome", expected_output="awesome is Python", is_sample=False)
        TestCase.objects.create(question=code_q1, input_data="singleword", expected_output="singleword", is_sample=False)

    # Coding Problem 2 for Test 1
    code_q2, _ = Question.objects.get_or_create(
        test=test1, order=6, question_type='CODING',
        title="Find Target Sum Pair Indices",
        defaults={
            'prompt': (
                "Given an integer array `nums` and an integer `target`, return the 0-based indices of the two numbers such that they add up to `target`.\n\n"
                "**Input Format:**\n"
                "Line 1: Space-separated integers representing `nums`\n"
                "Line 2: Single integer representing `target`\n\n"
                "**Output Format:**\n"
                "Two space-separated indices in ascending order.\n\n"
                "**Example:**\n"
                "Input:\n2 7 11 15\n9\n"
                "Output:\n0 1"
            ),
            'marks': 15,
            'difficulty': 'MEDIUM',
            'sample_input': "2 7 11 15\n9",
            'sample_output': "0 1",
            'starter_code': (
                "import sys\n\n"
                "data = sys.stdin.read().split()\n"
                "if data:\n"
                "    nums = [int(x) for x in data[:-1]]\n"
                "    target = int(data[-1])\n"
                "    \n"
                "    seen = {}\n"
                "    for i, num in enumerate(nums):\n"
                "        comp = target - num\n"
                "        if comp in seen:\n"
                "            print(f\"{seen[comp]} {i}\")\n"
                "            break\n"
                "        seen[num] = i\n"
            ),
            'time_limit_seconds': 2.0
        }
    )
    if not code_q2.test_cases.exists():
        TestCase.objects.create(question=code_q2, input_data="2 7 11 15\n9", expected_output="0 1", is_sample=True)
        TestCase.objects.create(question=code_q2, input_data="3 2 4\n6", expected_output="1 2", is_sample=True)
        TestCase.objects.create(question=code_q2, input_data="3 3\n6", expected_output="0 1", is_sample=False)
        TestCase.objects.create(question=code_q2, input_data="1 5 8 12 14\n20", expected_output="2 3", is_sample=False)

    print("[OK] Created Test 1: Python Core & Algorithmic Challenge 2026 with 4 MCQs and 2 Coding Challenges")

    # Test 2: Dasara Python Fundamentals Blitz
    test2, _ = Test.objects.get_or_create(
        title="Dasara Python Fundamentals Blitz",
        defaults={
            'description': "Quick-fire assessment evaluating fundamental Python syntax, string manipulation, and list slicing.",
            'duration_minutes': 15,
            'total_marks': 30,
            'pass_marks': 15,
            'negative_marking': False,
            'randomize_questions': True,
            'allow_multiple_attempts': True,
            'is_active': True,
            'created_by': admin_user
        }
    )

    t2_mcq1, _ = Question.objects.get_or_create(
        test=test2, order=1, question_type='MCQ',
        title="String Negative Slicing",
        defaults={
            'prompt': "What is the output of `s = 'Python'[::-1]`?",
            'marks': 10,
            'difficulty': 'EASY'
        }
    )
    if not t2_mcq1.options.exists():
        Option.objects.create(question=t2_mcq1, text="'nohtyP'", is_correct=True, explanation="A step of -1 reverses the string sequence.")
        Option.objects.create(question=t2_mcq1, text="'Python'", is_correct=False)
        Option.objects.create(question=t2_mcq1, text="'P'", is_correct=False)
        Option.objects.create(question=t2_mcq1, text="IndexError", is_correct=False)

    t2_code1, _ = Question.objects.get_or_create(
        test=test2, order=2, question_type='CODING',
        title="Even Fibonacci Numbers Sum",
        defaults={
            'prompt': (
                "Given an integer `N`, find the sum of all even-valued Fibonacci numbers that do not exceed `N`.\n\n"
                "**Input:** A single integer `N`\n"
                "**Output:** The sum of even Fibonacci terms <= N\n"
                "**Example:** Input `10` -> Output `10` (terms: 2, 8)"
            ),
            'marks': 20,
            'difficulty': 'MEDIUM',
            'sample_input': "10",
            'sample_output': "10",
            'starter_code': (
                "import sys\n\n"
                "raw = sys.stdin.read().strip()\n"
                "if raw:\n"
                "    N = int(raw)\n"
                "    a, b = 1, 2\n"
                "    total = 0\n"
                "    while b <= N:\n"
                "        if b % 2 == 0:\n"
                "            total += b\n"
                "        a, b = b, a + b\n"
                "    print(total)\n"
            ),
            'time_limit_seconds': 2.0
        }
    )
    if not t2_code1.test_cases.exists():
        TestCase.objects.create(question=t2_code1, input_data="10", expected_output="10", is_sample=True)
        TestCase.objects.create(question=t2_code1, input_data="50", expected_output="44", is_sample=True)
        TestCase.objects.create(question=t2_code1, input_data="100", expected_output="44", is_sample=False)

    print("[OK] Created Test 2: Dasara Python Fundamentals Blitz")

    # 4. Generate Pre-populated Completed Student Attempts to demonstrate the Leaderboard & Tie Handling
    now = timezone.now()
    
    # Pre-calculated performances for test 1 to show rankings 1 to 6
    performance_records = [
        # Student, MCQ correctness [q1, q2, q3, q4], coding correctness [c1, c2], minutes_taken
        (students[0], [True, True, True, True], [True, True], 12),     # Rahul: 50/50 (Rank 1, 12 mins)
        (students[1], [True, True, True, True], [True, True], 16),     # Priya: 50/50 (Rank 2, 16 mins - demonstrates tie-breaking by time taken!)
        (students[2], [True, True, True, False], [True, True], 19),    # Amit: 45 - 0.5 = 44.5/50
        (students[3], [True, True, False, False], [True, True], 21),   # Sneha: 40 - 1.0 = 39.0/50
        (students[4], [True, True, True, False], [True, False], 24),   # Vikram: 15 - 0.5 + 15 = 29.5/50
        (students[5], [True, False, False, False], [True, False], 26), # Ananya: 5 - 1.5 + 15 = 18.5/50
    ]

    for student, mcq_flags, code_flags, mins_taken in performance_records:
        start_t = now - timedelta(hours=2, minutes=mins_taken)
        comp_t = start_t + timedelta(minutes=mins_taken)
        
        attempt, _ = TestAttempt.objects.get_or_create(
            student=student,
            test=test1,
            defaults={
                'started_at': start_t,
                'completed_at': comp_t,
                'status': 'COMPLETED',
                'time_taken_seconds': mins_taken * 60,
                'total_possible': test1.total_marks,
                'question_order': [mcq1.id, mcq2.id, mcq3.id, mcq4.id, code_q1.id, code_q2.id]
            }
        )

        # Grade MCQs
        score = Decimal('0.00')
        qs = [mcq1, mcq2, mcq3, mcq4]
        for idx, q in enumerate(qs):
            sub, _ = Submission.objects.get_or_create(attempt=attempt, question=q)
            is_corr = mcq_flags[idx]
            correct_opt = q.options.filter(is_correct=True).first()
            wrong_opt = q.options.filter(is_correct=False).first()
            
            chosen = correct_opt if is_corr else wrong_opt
            sub.selected_option = chosen
            sub.is_correct = is_corr
            if is_corr:
                sub.marks_awarded = Decimal(str(q.marks))
            else:
                sub.marks_awarded = -Decimal(str(test1.negative_mark_value))
            score += sub.marks_awarded
            sub.save()

        # Grade Coding 1
        sub_c1, _ = Submission.objects.get_or_create(attempt=attempt, question=code_q1)
        if code_flags[0]:
            sub_c1.submitted_code = code_q1.starter_code
            sub_c1.is_correct = True
            sub_c1.test_cases_passed = 4
            sub_c1.total_test_cases = 4
            sub_c1.marks_awarded = Decimal('15.00')
            sub_c1.evaluation_details = {'passed_all': True, 'cases_passed': 4, 'total_cases': 4, 'percentage': 100}
        else:
            sub_c1.submitted_code = "print('wrong')"
            sub_c1.is_correct = False
            sub_c1.test_cases_passed = 0
            sub_c1.total_test_cases = 4
            sub_c1.marks_awarded = Decimal('0.00')
            sub_c1.evaluation_details = {'passed_all': False, 'cases_passed': 0, 'total_cases': 4, 'percentage': 0}
        score += sub_c1.marks_awarded
        sub_c1.save()

        # Grade Coding 2
        sub_c2, _ = Submission.objects.get_or_create(attempt=attempt, question=code_q2)
        if code_flags[1]:
            sub_c2.submitted_code = code_q2.starter_code
            sub_c2.is_correct = True
            sub_c2.test_cases_passed = 4
            sub_c2.total_test_cases = 4
            sub_c2.marks_awarded = Decimal('15.00')
            sub_c2.evaluation_details = {'passed_all': True, 'cases_passed': 4, 'total_cases': 4, 'percentage': 100}
        else:
            sub_c2.submitted_code = "# Incomplete"
            sub_c2.is_correct = False
            sub_c2.test_cases_passed = 0
            sub_c2.total_test_cases = 4
            sub_c2.marks_awarded = Decimal('0.00')
            sub_c2.evaluation_details = {'passed_all': False, 'cases_passed': 0, 'total_cases': 4, 'percentage': 0}
        score += sub_c2.marks_awarded
        sub_c2.save()

        attempt.score = max(Decimal('0.00'), score)
        attempt.percentage = round((attempt.score / Decimal(str(test1.total_marks))) * Decimal('100.0'), 2)
        attempt.is_passed = (attempt.score >= Decimal(str(test1.pass_marks)))
        attempt.save()

    print("[OK] Successfully populated realistic student exam submissions, scores, and rankings!")
    print("\n=======================================================")
    print("[SUCCESS] PLATFORM IS READY!")
    print("Admin Portal:   http://127.0.0.1:8000/admin-portal/")
    print("Student Portal: http://127.0.0.1:8000/dashboard/")
    print("Leaderboard:    http://127.0.0.1:8000/leaderboard/")
    print("Admin login:    admin / adminpassword123")
    print("Student logins: rahul_s / student123, priya_p / student123")
    print("=======================================================\n")


if __name__ == '__main__':
    run_seed()
