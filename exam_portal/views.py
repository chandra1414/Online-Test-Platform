import json
import random
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.utils import timezone
from django.db.models import Avg, Max, Count, Q
from django.views.decorators.csrf import csrf_exempt

from .models import Student, Test, Question, Option, TestCase, TestAttempt, Submission
from .forms import StudentRegistrationForm, TestForm, QuestionForm
from .sandbox import execute_sandboxed_code, evaluate_coding_question
from .certificate import generate_certificate_pdf


def is_admin_or_staff(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


# ==========================================
# AUTHENTICATION
# ==========================================

def user_login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            if user.is_staff:
                return redirect('admin_dashboard')
            return redirect('student_dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'exam_portal/auth/login.html', {'form': form})


def student_register_view(request):
    if request.user.is_authenticated:
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            student = form.save()
            login(request, student.user)
            messages.success(request, f"Account created successfully! Welcome to the Online Coding Platform, {student.user.first_name}!")
            return redirect('student_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = StudentRegistrationForm()

    return render(request, 'exam_portal/auth/register.html', {'form': form})


def user_logout_view(request):
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    return redirect('login')


# ==========================================
# STUDENT MODULE
# ==========================================

@login_required
def student_dashboard(request):
    # Ensure student profile exists for non-staff
    if not hasattr(request.user, 'student_profile'):
        if request.user.is_staff:
            return redirect('admin_dashboard')
        # Create student profile if not exists
        student = Student.objects.create(
            user=request.user,
            roll_number=f"USR-{request.user.id:04d}",
            college="University Campus"
        )
    else:
        student = request.user.student_profile

    # Active tests available
    available_tests = Test.objects.filter(is_active=True).order_by('-created_at')
    
    # Completed attempts by this student
    attempts = TestAttempt.objects.filter(student=student).select_related('test').order_by('-started_at')
    completed_attempts = attempts.filter(status__in=['COMPLETED', 'TIMED_OUT'])
    
    # Check which tests can be taken (respect allow_multiple_attempts)
    test_status_map = {}
    for t in available_tests:
        user_test_attempts = attempts.filter(test=t)
        has_completed = user_test_attempts.filter(status__in=['COMPLETED', 'TIMED_OUT']).exists()
        in_progress = user_test_attempts.filter(status='IN_PROGRESS').first()
        
        can_take = True
        if has_completed and not t.allow_multiple_attempts:
            can_take = False
            
        test_status_map[t.id] = {
            'has_completed': has_completed,
            'in_progress': in_progress,
            'can_take': can_take,
            'attempts_count': user_test_attempts.count(),
            'best_score': user_test_attempts.filter(status__in=['COMPLETED', 'TIMED_OUT']).aggregate(Max('score'))['score__max']
        }

    # Analytics metrics
    total_tests_taken = completed_attempts.count()
    avg_score = completed_attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0
    passed_count = completed_attempts.filter(is_passed=True).count()
    
    # Data for performance analytics chart (past attempts)
    chart_labels = []
    chart_scores = []
    for att in reversed(list(completed_attempts[:7])):
        chart_labels.append(att.test.title[:15] + ('...' if len(att.test.title) > 15 else ''))
        chart_scores.append(float(att.percentage))

    context = {
        'student': student,
        'available_tests': available_tests,
        'test_status_map': test_status_map,
        'recent_attempts': completed_attempts[:5],
        'total_tests_taken': total_tests_taken,
        'avg_score': round(avg_score, 1),
        'passed_count': passed_count,
        'chart_labels': json.dumps(chart_labels),
        'chart_scores': json.dumps(chart_scores),
    }
    return render(request, 'exam_portal/student/dashboard.html', context)


@login_required
def test_instruction(request, test_id):
    test = get_object_or_404(Test, id=test_id, is_active=True)
    student = getattr(request.user, 'student_profile', None)
    
    if not student:
        messages.error(request, "Student profile required.")
        return redirect('student_dashboard')

    # Prevent multiple submissions if not allowed
    past_completed = TestAttempt.objects.filter(
        student=student, test=test, status__in=['COMPLETED', 'TIMED_OUT']
    ).first()
    
    if past_completed and not test.allow_multiple_attempts:
        messages.warning(request, "You have already completed this test. Multiple attempts are not permitted.")
        return redirect('test_result', attempt_id=past_completed.id)

    # Check for active in-progress attempt
    active_attempt = TestAttempt.objects.filter(
        student=student, test=test, status='IN_PROGRESS'
    ).first()

    context = {
        'test': test,
        'active_attempt': active_attempt,
        'past_completed': past_completed,
    }
    return render(request, 'exam_portal/student/test_instruction.html', context)


@login_required
def start_test(request, test_id):
    test = get_object_or_404(Test, id=test_id, is_active=True)
    student = getattr(request.user, 'student_profile', None)
    if not student:
        return redirect('student_dashboard')

    # Check if multiple attempts prevented
    existing_completed = TestAttempt.objects.filter(
        student=student, test=test, status__in=['COMPLETED', 'TIMED_OUT']
    ).first()
    if existing_completed and not test.allow_multiple_attempts:
        messages.warning(request, "Multiple submissions are not allowed for this test.")
        return redirect('test_result', attempt_id=existing_completed.id)

    # Get or create active attempt
    attempt = TestAttempt.objects.filter(student=student, test=test, status='IN_PROGRESS').first()
    if not attempt:
        # Generate question sequence (randomized if enabled)
        all_q_ids = list(test.questions.values_list('id', flat=True))
        if test.randomize_questions:
            random.shuffle(all_q_ids)

        attempt = TestAttempt.objects.create(
            student=student,
            test=test,
            total_possible=test.total_marks,
            question_order=all_q_ids
        )

    return redirect('take_test', attempt_id=attempt.id)


@login_required
def take_test(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, id=attempt_id, student__user=request.user)

    # If already completed or timed out, redirect to result
    if attempt.status != 'IN_PROGRESS':
        return redirect('test_result', attempt_id=attempt.id)

    # Check server-side expiration
    if attempt.is_expired:
        attempt.status = 'TIMED_OUT'
        attempt.save()
        _finalize_attempt_scoring(attempt)
        messages.warning(request, "Time expired! Your test has been automatically submitted.")
        return redirect('test_result', attempt_id=attempt.id)

    # Fetch ordered questions
    q_ids = attempt.question_order
    if not q_ids:
        q_ids = list(attempt.test.questions.values_list('id', flat=True))
        attempt.question_order = q_ids
        attempt.save()

    # Preserve order
    questions_dict = {q.id: q for q in Question.objects.filter(id__in=q_ids).prefetch_related('options', 'test_cases')}
    ordered_questions = [questions_dict[qid] for qid in q_ids if qid in questions_dict]

    # Fetch existing submissions for this attempt
    existing_submissions = {
        s.question_id: s for s in Submission.objects.filter(attempt=attempt).select_related('selected_option')
    }

    # Time remaining in seconds
    remaining_seconds = attempt.time_remaining_seconds

    context = {
        'attempt': attempt,
        'test': attempt.test,
        'questions': ordered_questions,
        'submissions': existing_submissions,
        'remaining_seconds': remaining_seconds,
    }
    return render(request, 'exam_portal/student/take_test.html', context)


@login_required
def save_answer_ajax(request, attempt_id):
    """
    Saves an intermediate answer (MCQ option or Coding code) via AJAX while test is running.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    attempt = get_object_or_404(TestAttempt, id=attempt_id, student__user=request.user)
    if attempt.status != 'IN_PROGRESS':
        return JsonResponse({'error': 'Test is already completed'}, status=400)

    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        question = get_object_or_404(Question, id=question_id, test=attempt.test)

        sub, created = Submission.objects.get_or_create(attempt=attempt, question=question)

        if question.question_type == 'MCQ':
            opt_id = data.get('option_id')
            if opt_id:
                option = Option.objects.get(id=opt_id, question=question)
                sub.selected_option = option
            else:
                sub.selected_option = None
            sub.save()

        elif question.question_type == 'CODING':
            code = data.get('code', '')
            sub.submitted_code = code
            sub.save()

        return JsonResponse({'success': True, 'saved_at': timezone.now().strftime('%H:%M:%S')})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def run_code_ajax(request):
    """
    Evaluates student code in isolated sandbox against sample test cases (for practice run).
    Does NOT finalize test submission.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        code = data.get('code', '')
        custom_input = data.get('custom_input', None)

        question = get_object_or_404(Question, id=question_id, question_type='CODING')

        if custom_input is not None:
            # Custom input run
            res = execute_sandboxed_code(code, input_data=custom_input, time_limit=question.time_limit_seconds)
            return JsonResponse({
                'success': True,
                'is_custom': True,
                'status': res['status'],
                'output': res['output'],
                'error': res['error'],
                'execution_time': res['execution_time']
            })

        # Run against sample test cases
        sample_cases = question.test_cases.filter(is_sample=True)
        if not sample_cases.exists():
            # If no sample cases in DB, use sample_input / sample_output from Question model
            class MockTC:
                def __init__(self, in_data, out_data):
                    self.input_data = in_data
                    self.expected_output = out_data
                    self.is_sample = True
            sample_cases = [MockTC(question.sample_input, question.sample_output)]

        evaluation = evaluate_coding_question(code, sample_cases, time_limit=question.time_limit_seconds)
        return JsonResponse({
            'success': True,
            'is_custom': False,
            'evaluation': evaluation
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def submit_test(request, attempt_id):
    """
    Finalizes the student's attempt, runs sandbox evaluation for coding questions,
    grades MCQs, applies negative marking, and calculates rank.
    """
    attempt = get_object_or_404(TestAttempt, id=attempt_id, student__user=request.user)

    if attempt.status == 'IN_PROGRESS':
        # Process POST form if any submitted at final click
        if request.method == 'POST':
            # Save any remaining answers submitted via POST
            for key, val in request.POST.items():
                if key.startswith('mcq_'):
                    qid = key.split('_')[1]
                    try:
                        q = Question.objects.get(id=qid, test=attempt.test)
                        opt = Option.objects.get(id=val, question=q)
                        sub, _ = Submission.objects.get_or_create(attempt=attempt, question=q)
                        sub.selected_option = opt
                        sub.save()
                    except Exception:
                        pass
                elif key.startswith('code_'):
                    qid = key.split('_')[1]
                    try:
                        q = Question.objects.get(id=qid, test=attempt.test)
                        sub, _ = Submission.objects.get_or_create(attempt=attempt, question=q)
                        sub.submitted_code = val
                        sub.save()
                    except Exception:
                        pass

        attempt.status = 'COMPLETED'
        attempt.completed_at = timezone.now()
        attempt.time_taken_seconds = max(1, int((attempt.completed_at - attempt.started_at).total_seconds()))
        attempt.save()

        _finalize_attempt_scoring(attempt)
        messages.success(request, "Your test has been successfully submitted and evaluated!")

    return redirect('test_result', attempt_id=attempt.id)


def _finalize_attempt_scoring(attempt):
    """
    Grades all submissions inside the attempt (MCQ + Sandboxed Coding).
    Applies negative marking when configured.
    """
    test = attempt.test
    total_score = Decimal('0.00')
    questions = test.questions.all().prefetch_related('options', 'test_cases')

    for q in questions:
        sub, _ = Submission.objects.get_or_create(attempt=attempt, question=q)

        if q.question_type == 'MCQ':
            if sub.selected_option:
                if sub.selected_option.is_correct:
                    sub.is_correct = True
                    sub.marks_awarded = Decimal(str(q.marks))
                    total_score += sub.marks_awarded
                else:
                    sub.is_correct = False
                    # Negative marking check
                    neg_val = q.negative_marks if q.negative_marks > 0 else (test.negative_mark_value if test.negative_marking else Decimal('0.00'))
                    sub.marks_awarded = -Decimal(str(neg_val))
                    total_score += sub.marks_awarded
            else:
                # Unanswered: 0 marks
                sub.is_correct = False
                sub.marks_awarded = Decimal('0.00')
            sub.save()

        elif q.question_type == 'CODING':
            code = sub.submitted_code or ""
            test_cases = list(q.test_cases.all())

            # If no test cases in DB, generate one from question sample fields
            if not test_cases and (q.sample_input or q.sample_output):
                class MockTC:
                    def __init__(self, in_data, out_data):
                        self.input_data = in_data
                        self.expected_output = out_data
                        self.is_sample = True
                test_cases = [MockTC(q.sample_input, q.sample_output)]

            if not code.strip():
                sub.is_correct = False
                sub.marks_awarded = Decimal('0.00')
                sub.test_cases_passed = 0
                sub.total_test_cases = len(test_cases)
                sub.execution_output = "No code submitted."
                sub.evaluation_details = {'error': 'No code submitted.'}
            else:
                eval_res = evaluate_coding_question(code, test_cases, time_limit=q.time_limit_seconds)
                sub.test_cases_passed = eval_res['cases_passed']
                sub.total_test_cases = eval_res['total_cases']
                sub.is_correct = eval_res['passed_all']
                sub.evaluation_details = eval_res

                if eval_res['total_cases'] > 0:
                    earned_ratio = Decimal(str(eval_res['cases_passed'])) / Decimal(str(eval_res['total_cases']))
                    awarded = round(Decimal(str(q.marks)) * earned_ratio, 2)
                    sub.marks_awarded = awarded
                    total_score += awarded
                else:
                    sub.marks_awarded = Decimal('0.00')
            sub.save()

    # Floor score at 0 if negative marking exceeded total
    if total_score < Decimal('0.00'):
        total_score = Decimal('0.00')

    attempt.score = total_score
    if attempt.total_possible > 0:
        pct = (total_score / Decimal(str(attempt.total_possible))) * Decimal('100.0')
        attempt.percentage = round(pct, 2)
    else:
        attempt.percentage = Decimal('0.00')

    attempt.is_passed = (attempt.score >= Decimal(str(test.pass_marks)))
    attempt.save()


@login_required
def test_result(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, id=attempt_id)
    
    # Permission check: student who took the test or staff
    if not request.user.is_staff and attempt.student.user != request.user:
        raise Http404("You do not have permission to view this scorecard.")

    # Calculate student rank on this test
    # Consistent tie-handling: Highest score first, then least time taken, then earlier completed_at
    all_attempts = TestAttempt.objects.filter(
        test=attempt.test, status__in=['COMPLETED', 'TIMED_OUT']
    ).order_by('-score', 'time_taken_seconds', 'completed_at')
    
    rank = 1
    for idx, att in enumerate(all_attempts, start=1):
        if att.id == attempt.id:
            rank = idx
            break

    submissions = Submission.objects.filter(attempt=attempt).select_related(
        'question', 'selected_option'
    ).prefetch_related('question__options', 'question__test_cases')

    # Breakdown metrics
    correct_count = submissions.filter(is_correct=True).count()
    total_q_count = submissions.count()
    wrong_count = submissions.filter(is_correct=False).exclude(selected_option__isnull=True, submitted_code='').count()
    unanswered_count = total_q_count - (correct_count + wrong_count)

    context = {
        'attempt': attempt,
        'test': attempt.test,
        'rank': rank,
        'submissions': submissions,
        'correct_count': correct_count,
        'wrong_count': wrong_count,
        'unanswered_count': unanswered_count,
    }
    return render(request, 'exam_portal/student/test_result.html', context)


@login_required
def test_history(request):
    student = getattr(request.user, 'student_profile', None)
    if not student:
        return redirect('student_dashboard')

    attempts = TestAttempt.objects.filter(student=student).select_related('test').order_by('-started_at')
    return render(request, 'exam_portal/student/history.html', {'attempts': attempts})


# ==========================================
# LEADERBOARD MODULE
# ==========================================

def leaderboard_view(request):
    test_id = request.GET.get('test_id')
    tests = Test.objects.filter(is_active=True).order_by('title')

    selected_test = None
    if test_id:
        selected_test = get_object_or_404(Test, id=test_id)
        # Per-test ranking: pick best attempt per student for this test
        # Consistent tie-handling: score DESC, time_taken_seconds ASC, completed_at ASC
        attempts_qs = TestAttempt.objects.filter(
            test=selected_test,
            status__in=['COMPLETED', 'TIMED_OUT']
        ).select_related('student__user', 'test').order_by('-score', 'time_taken_seconds', 'completed_at')
    else:
        # Overall Leaderboard: highest scored completed attempts
        attempts_qs = TestAttempt.objects.filter(
            status__in=['COMPLETED', 'TIMED_OUT']
        ).select_related('student__user', 'test').order_by('-score', 'time_taken_seconds', 'completed_at')

    # De-duplicate to show each student once (their highest ranked attempt)
    seen_students = set()
    ranked_attempts = []
    for att in attempts_qs:
        if att.student_id not in seen_students:
            seen_students.add(att.student_id)
            ranked_attempts.append(att)

    # Top 10 performers
    top_10 = ranked_attempts[:10]
    
    # Assign ranks with consistent tie rules
    leaderboard_data = []
    for rank_idx, att in enumerate(top_10, start=1):
        leaderboard_data.append({
            'rank': rank_idx,
            'attempt': att,
            'student': att.student,
            'score': att.score,
            'percentage': att.percentage,
            'time_taken_minutes': round(att.time_taken_seconds / 60, 1),
            'completed_at': att.completed_at
        })

    context = {
        'tests': tests,
        'selected_test': selected_test,
        'leaderboard_data': leaderboard_data,
        'total_participants': len(seen_students),
    }
    return render(request, 'exam_portal/leaderboard/leaderboard.html', context)


@login_required
def download_certificate(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, id=attempt_id)

    # Permission check: only student who took it or staff
    if not request.user.is_staff and attempt.student.user != request.user:
        raise Http404("Permission denied")

    if not attempt.is_passed:
        messages.error(request, "Certificates are only issued for passing scores.")
        return redirect('test_result', attempt_id=attempt.id)

    # Calculate rank for certificate
    all_attempts = TestAttempt.objects.filter(
        test=attempt.test, status__in=['COMPLETED', 'TIMED_OUT']
    ).order_by('-score', 'time_taken_seconds', 'completed_at')
    
    rank = 1
    for idx, att in enumerate(all_attempts, start=1):
        if att.id == attempt.id:
            rank = idx
            break

    pdf_bytes = generate_certificate_pdf(attempt, rank=rank)
    filename = f"Certificate_{attempt.student.roll_number}_{attempt.test.slug}.pdf"

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ==========================================
# ADMIN MODULE
# ==========================================

@user_passes_test(is_admin_or_staff)
def admin_dashboard(request):
    tests_count = Test.objects.count()
    students_count = Student.objects.count()
    attempts_count = TestAttempt.objects.count()
    completed_count = TestAttempt.objects.filter(status__in=['COMPLETED', 'TIMED_OUT']).count()
    pass_rate = 0
    if completed_count > 0:
        passed = TestAttempt.objects.filter(status__in=['COMPLETED', 'TIMED_OUT'], is_passed=True).count()
        pass_rate = round((passed / completed_count) * 100, 1)

    recent_tests = Test.objects.all().order_by('-created_at')[:5]
    recent_attempts = TestAttempt.objects.select_related('student__user', 'test').order_by('-started_at')[:8]

    context = {
        'tests_count': tests_count,
        'students_count': students_count,
        'attempts_count': attempts_count,
        'pass_rate': pass_rate,
        'recent_tests': recent_tests,
        'recent_attempts': recent_attempts,
    }
    return render(request, 'exam_portal/admin/dashboard.html', context)


@user_passes_test(is_admin_or_staff)
def admin_tests_list(request):
    tests = Test.objects.all().order_by('-created_at')
    return render(request, 'exam_portal/admin/tests_list.html', {'tests': tests})


@user_passes_test(is_admin_or_staff)
def admin_test_create(request):
    if request.method == 'POST':
        form = TestForm(request.POST)
        if form.is_valid():
            test = form.save(commit=False)
            test.created_by = request.user
            test.save()
            messages.success(request, f"Test '{test.title}' created successfully! You can now add questions.")
            return redirect('admin_test_detail', test_id=test.id)
    else:
        form = TestForm()

    return render(request, 'exam_portal/admin/test_form.html', {'form': form, 'title': 'Create New Test'})


@user_passes_test(is_admin_or_staff)
def admin_test_detail(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    questions = test.questions.all().prefetch_related('options', 'test_cases')
    return render(request, 'exam_portal/admin/test_detail.html', {'test': test, 'questions': questions})


@user_passes_test(is_admin_or_staff)
def admin_test_edit(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if request.method == 'POST':
        form = TestForm(request.POST, instance=test)
        if form.is_valid():
            form.save()
            messages.success(request, "Test updated successfully.")
            return redirect('admin_test_detail', test_id=test.id)
    else:
        form = TestForm(instance=test)

    return render(request, 'exam_portal/admin/test_form.html', {'form': form, 'title': f"Edit: {test.title}", 'test': test})


@user_passes_test(is_admin_or_staff)
def admin_test_delete(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if request.method == 'POST':
        title = test.title
        test.delete()
        messages.success(request, f"Test '{title}' deleted.")
        return redirect('admin_tests_list')
    return render(request, 'exam_portal/admin/test_confirm_delete.html', {'test': test})


@user_passes_test(is_admin_or_staff)
def admin_question_create(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.test = test
            question.save()

            # Handle MCQ options
            if question.question_type == 'MCQ':
                options_data = request.POST.getlist('option_text[]')
                correct_idx = request.POST.get('correct_option', '0')
                for i, opt_text in enumerate(options_data):
                    if opt_text.strip():
                        is_corr = (str(i) == str(correct_idx))
                        Option.objects.create(question=question, text=opt_text.strip(), is_correct=is_corr)

            # Handle Coding test cases
            elif question.question_type == 'CODING':
                inputs = request.POST.getlist('tc_input[]')
                outputs = request.POST.getlist('tc_output[]')
                is_samples = request.POST.getlist('tc_is_sample[]')
                
                for i in range(len(inputs)):
                    in_val = inputs[i].strip()
                    out_val = outputs[i].strip() if i < len(outputs) else ''
                    sample_flag = ('1' in is_samples) if str(i) in is_samples else False
                    if in_val or out_val:
                        TestCase.objects.create(
                            question=question,
                            input_data=in_val,
                            expected_output=out_val,
                            is_sample=sample_flag
                        )

            messages.success(request, f"Question '{question.title}' added successfully!")
            return redirect('admin_test_detail', test_id=test.id)
    else:
        next_order = test.questions.count() + 1
        form = QuestionForm(initial={'order': next_order})

    return render(request, 'exam_portal/admin/question_form.html', {'form': form, 'test': test, 'title': 'Add Question'})


@user_passes_test(is_admin_or_staff)
def admin_question_edit(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    test = question.test

    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()

            if question.question_type == 'MCQ':
                question.options.all().delete()
                options_data = request.POST.getlist('option_text[]')
                correct_idx = request.POST.get('correct_option', '0')
                for i, opt_text in enumerate(options_data):
                    if opt_text.strip():
                        is_corr = (str(i) == str(correct_idx))
                        Option.objects.create(question=question, text=opt_text.strip(), is_correct=is_corr)

            elif question.question_type == 'CODING':
                question.test_cases.all().delete()
                inputs = request.POST.getlist('tc_input[]')
                outputs = request.POST.getlist('tc_output[]')
                is_samples = request.POST.getlist('tc_is_sample[]')
                for i in range(len(inputs)):
                    in_val = inputs[i].strip()
                    out_val = outputs[i].strip() if i < len(outputs) else ''
                    sample_flag = ('1' in is_samples) if str(i) in is_samples else False
                    if in_val or out_val:
                        TestCase.objects.create(
                            question=question,
                            input_data=in_val,
                            expected_output=out_val,
                            is_sample=sample_flag
                        )

            messages.success(request, f"Question '{question.title}' updated.")
            return redirect('admin_test_detail', test_id=test.id)
    else:
        form = QuestionForm(instance=question)

    return render(request, 'exam_portal/admin/question_form.html', {
        'form': form, 'test': test, 'question': question, 'title': f"Edit Question: {question.title}"
    })


@user_passes_test(is_admin_or_staff)
def admin_question_delete(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    test_id = question.test_id
    if request.method == 'POST':
        question.delete()
        messages.success(request, "Question deleted.")
        return redirect('admin_test_detail', test_id=test_id)
    return render(request, 'exam_portal/admin/question_confirm_delete.html', {'question': question})


@user_passes_test(is_admin_or_staff)
def admin_attempts_list(request):
    attempts = TestAttempt.objects.select_related('student__user', 'test').order_by('-started_at')
    return render(request, 'exam_portal/admin/attempts_list.html', {'attempts': attempts})
