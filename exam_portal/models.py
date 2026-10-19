import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    roll_number = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    college = models.CharField(max_length=150, blank=True, default='Engineering & Tech College')
    department = models.CharField(max_length=100, blank=True, default='Computer Science')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.roll_number})"

    @property
    def display_name(self):
        full = self.user.get_full_name()
        return full if full else self.user.username


class Test(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(help_text="Detailed instructions and topics covered")
    duration_minutes = models.PositiveIntegerField(default=30, help_text="Duration in minutes")
    total_marks = models.PositiveIntegerField(default=100)
    pass_marks = models.PositiveIntegerField(default=40)
    
    # Advanced feature configurations
    negative_marking = models.BooleanField(default=False, help_text="Enable penalty for wrong answers")
    negative_mark_value = models.DecimalField(max_digits=4, decimal_places=2, default=0.25, 
                                             help_text="Marks deducted per wrong answer")
    randomize_questions = models.BooleanField(default=True, help_text="Randomize question sequence for each student")
    allow_multiple_attempts = models.BooleanField(default=False, help_text="If false, prevents re-taking the test")
    
    is_active = models.BooleanField(default=True, help_text="Visible for students to take")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_tests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.title) or "test"
            slug = base_slug
            counter = 1
            while Test.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def mcq_count(self):
        return self.questions.filter(question_type='MCQ').count()

    @property
    def coding_count(self):
        return self.questions.filter(question_type='CODING').count()


class Question(models.Model):
    QUESTION_TYPES = (
        ('MCQ', 'Multiple Choice Question'),
        ('CODING', 'Python Coding Problem'),
    )
    DIFFICULTY_LEVELS = (
        ('EASY', 'Easy'),
        ('MEDIUM', 'Medium'),
        ('HARD', 'Hard'),
    )

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES, default='MCQ')
    title = models.CharField(max_length=255, help_text="Summary or title of the question")
    prompt = models.TextField(help_text="Full question text or problem statement (supports Markdown/code)")
    marks = models.PositiveIntegerField(default=5)
    negative_marks = models.DecimalField(max_digits=4, decimal_places=2, default=0.00,
                                        help_text="Custom negative mark for this question (0 to inherit test default)")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_LEVELS, default='MEDIUM')
    order = models.PositiveIntegerField(default=1)

    # Specific fields for Coding questions
    sample_input = models.TextField(blank=True, default='', help_text="Sample input provided to student")
    sample_output = models.TextField(blank=True, default='', help_text="Expected output for sample input")
    starter_code = models.TextField(blank=True, default="def solution():\n    # Write your Python code here\n    pass\n",
                                   help_text="Boilerplate code provided in the editor")
    time_limit_seconds = models.FloatField(default=2.0, help_text="Execution time limit in seconds")

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"[{self.get_question_type_display()}] {self.title} ({self.marks} pts)"


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    explanation = models.TextField(blank=True, default='', help_text="Explanation revealed in review")

    def __str__(self):
        return f"{self.text[:50]} ({'Correct' if self.is_correct else 'Incorrect'})"


class TestCase(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='test_cases')
    input_data = models.TextField(help_text="Input passed via stdin")
    expected_output = models.TextField(help_text="Expected stdout from code")
    is_sample = models.BooleanField(default=False, help_text="Is this visible as an example to the student?")
    weight = models.PositiveIntegerField(default=1, help_text="Relative weight for score distribution")

    def __str__(self):
        kind = "Sample" if self.is_sample else "Hidden"
        return f"TestCase {self.id} ({kind}) for Question {self.question_id}"


class TestAttempt(models.Model):
    STATUS_CHOICES = (
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('TIMED_OUT', 'Timed Out'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attempts')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')
    
    score = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    total_possible = models.PositiveIntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    is_passed = models.BooleanField(default=False)
    time_taken_seconds = models.PositiveIntegerField(default=0)
    
    # Stores randomized question IDs list to keep consistent across navigation
    question_order = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.user.username} - {self.test.title} ({self.status}) - {self.score}/{self.total_possible}"

    @property
    def time_remaining_seconds(self):
        if self.status != 'IN_PROGRESS':
            return 0
        elapsed = (timezone.now() - self.started_at).total_seconds()
        total_allowed = self.test.duration_minutes * 60
        remaining = total_allowed - elapsed
        return max(0, int(remaining))

    @property
    def is_expired(self):
        return self.time_remaining_seconds <= 0


class Submission(models.Model):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='submissions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='submissions')
    
    # For MCQ
    selected_option = models.ForeignKey(Option, on_delete=models.SET_NULL, null=True, blank=True)
    
    # For Coding
    submitted_code = models.TextField(blank=True, default='')
    
    # Evaluation Results
    is_correct = models.BooleanField(default=False)
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    test_cases_passed = models.PositiveIntegerField(default=0)
    total_test_cases = models.PositiveIntegerField(default=0)
    execution_output = models.TextField(blank=True, default='')
    evaluation_details = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('attempt', 'question')

    def __str__(self):
        return f"Submission Q{self.question_id} in Attempt {self.attempt_id} ({self.marks_awarded} pts)"
