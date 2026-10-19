from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from exam_portal.models import Student, Test, Question, Option, TestCase as TestCaseModel, TestAttempt, Submission
from exam_portal.sandbox import execute_sandboxed_code, validate_python_code, evaluate_coding_question
from exam_portal.certificate import generate_certificate_pdf


class SandboxSecurityTests(TestCase):
    def test_safe_python_code_execution(self):
        code = "import sys\nline = sys.stdin.read().strip()\nprint(f'Hello {line}')"
        res = execute_sandboxed_code(code, input_data="World", time_limit=2.0)
        self.assertEqual(res['status'], 'SUCCESS')
        self.assertEqual(res['output'].strip(), "Hello World")
        self.assertTrue(res['passed'])

    def test_security_violation_blocked_imports(self):
        dangerous_snippets = [
            "import os\nos.system('echo hacked')",
            "import subprocess\nsubprocess.run(['dir'])",
            "import socket\ns = socket.socket()",
            "import shutil\nshutil.rmtree('.')",
            "f = open('secret.txt', 'w')",
            "eval('2 + 2')",
            "exec('x = 10')",
        ]
        for snippet in dangerous_snippets:
            is_safe, msg = validate_python_code(snippet)
            self.assertFalse(is_safe, f"Should have blocked: {snippet}")
            res = execute_sandboxed_code(snippet, time_limit=1.0)
            self.assertEqual(res['status'], 'SECURITY_VIOLATION')

    def test_timeout_protection_infinite_loop(self):
        code = "while True: pass"
        res = execute_sandboxed_code(code, time_limit=1.0)
        self.assertEqual(res['status'], 'TIME_LIMIT_EXCEEDED')


class PlatformFlowIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin = User.objects.create_superuser('admin_tester', 'admin@test.com', 'adminpass123')

        # Student user
        self.student_user = User.objects.create_user('student_tester', 'student@test.com', 'studentpass123', first_name='John', last_name='Doe')
        self.student = Student.objects.create(
            user=self.student_user, roll_number='2026TEST01', college='Test Institute'
        )

        # Test
        self.test = Test.objects.create(
            title="Automated Test Suite Exam",
            duration_minutes=20,
            total_marks=20,
            pass_marks=10,
            negative_marking=True,
            negative_mark_value=Decimal('0.50'),
            allow_multiple_attempts=False,
            is_active=True
        )

        # MCQ Question (5 marks)
        self.mcq = Question.objects.create(
            test=self.test, order=1, question_type='MCQ',
            title="Sample MCQ Question", prompt="What is 2 + 2?", marks=5
        )
        self.opt_correct = Option.objects.create(question=self.mcq, text="4", is_correct=True)
        self.opt_wrong = Option.objects.create(question=self.mcq, text="5", is_correct=False)

        # Coding Question (15 marks)
        self.code_q = Question.objects.create(
            test=self.test, order=2, question_type='CODING',
            title="Sample Square Calculator", prompt="Read number from stdin and print square",
            marks=15, sample_input="3", sample_output="9",
            starter_code="import sys\nx = int(sys.stdin.read().strip())\nprint(x * x)"
        )
        TestCaseModel.objects.create(question=self.code_q, input_data="3", expected_output="9", is_sample=True)
        TestCaseModel.objects.create(question=self.code_q, input_data="5", expected_output="25", is_sample=False)

    def test_student_login_and_dashboard(self):
        login_res = self.client.login(username='student_tester', password='studentpass123')
        self.assertTrue(login_res)
        dash_res = self.client.get(reverse('student_dashboard'))
        self.assertEqual(dash_res.status_code, 200)
        self.assertContains(dash_res, "Automated Test Suite Exam")

    def test_admin_dashboard_access_control(self):
        # Non-staff cannot access admin portal
        self.client.login(username='student_tester', password='studentpass123')
        res = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(res.status_code, 302) # Redirects to login

        # Staff can access
        self.client.login(username='admin_tester', password='adminpass123')
        res_admin = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(res_admin.status_code, 200)
        self.assertContains(res_admin, "Administrative Overview")

    def test_complete_exam_flow_and_scoring(self):
        self.client.login(username='student_tester', password='studentpass123')

        # 1. Start test
        start_res = self.client.get(reverse('start_test', args=[self.test.id]), follow=True)
        self.assertEqual(start_res.status_code, 200)

        attempt = TestAttempt.objects.get(student=self.student, test=self.test)
        self.assertEqual(attempt.status, 'IN_PROGRESS')

        # 2. Save MCQ Answer via AJAX
        save_mcq = self.client.post(
            reverse('save_answer_ajax', args=[attempt.id]),
            data={'question_id': self.mcq.id, 'option_id': self.opt_correct.id},
            content_type='application/json'
        )
        self.assertEqual(save_mcq.status_code, 200)

        # 3. Save Code Answer via AJAX
        correct_code = "import sys\nx = int(sys.stdin.read().strip())\nprint(x * x)"
        save_code = self.client.post(
            reverse('save_answer_ajax', args=[attempt.id]),
            data={'question_id': self.code_q.id, 'code': correct_code},
            content_type='application/json'
        )
        self.assertEqual(save_code.status_code, 200)

        # 4. Submit test
        submit_res = self.client.post(reverse('submit_test', args=[attempt.id]), follow=True)
        self.assertEqual(submit_res.status_code, 200)

        # Refresh attempt
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, 'COMPLETED')
        self.assertEqual(attempt.score, Decimal('20.00')) # 5 (MCQ) + 15 (Coding) = 20
        self.assertEqual(attempt.percentage, Decimal('100.00'))
        self.assertTrue(attempt.is_passed)

        # 5. Verify single submission enforcement
        repeat_start = self.client.get(reverse('start_test', args=[self.test.id]), follow=True)
        # Should redirect to scorecard because multiple attempts are false
        self.assertContains(repeat_start, "Official Examination Scorecard")

        # 6. Verify PDF Certificate generation
        cert_res = self.client.get(reverse('download_certificate', args=[attempt.id]))
        self.assertEqual(cert_res.status_code, 200)
        self.assertEqual(cert_res['Content-Type'], 'application/pdf')
        self.assertGreater(len(cert_res.content), 1000)

    def test_leaderboard_rankings_and_tie_breaking(self):
        # Create second student
        u2 = User.objects.create_user('alice', 'alice@test.com', 'pass123')
        s2 = Student.objects.create(user=u2, roll_number='2026TEST02', college='NIT')

        # Attempt 1: score 20, time 300s
        att1 = TestAttempt.objects.create(
            student=self.student, test=self.test, status='COMPLETED',
            score=Decimal('20.00'), total_possible=20, percentage=Decimal('100.00'),
            is_passed=True, time_taken_seconds=300
        )

        # Attempt 2: score 20, time 150s (Faster -> should rank #1!)
        att2 = TestAttempt.objects.create(
            student=s2, test=self.test, status='COMPLETED',
            score=Decimal('20.00'), total_possible=20, percentage=Decimal('100.00'),
            is_passed=True, time_taken_seconds=150
        )

        lead_res = self.client.get(reverse('leaderboard') + f"?test_id={self.test.id}")
        self.assertEqual(lead_res.status_code, 200)
        data = lead_res.context['leaderboard_data']
        self.assertEqual(len(data), 2)
        # S2 (Alice) must be rank 1 due to tie-break on time taken
        self.assertEqual(data[0]['student'].roll_number, '2026TEST02')
        self.assertEqual(data[1]['student'].roll_number, '2026TEST01')
