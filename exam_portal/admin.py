from django.contrib import admin
from .models import Student, Test, Question, Option, TestCase, TestAttempt, Submission


class OptionInline(admin.TabularInline):
    model = Option
    extra = 4


class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 2


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'roll_number', 'college', 'department', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'roll_number', 'college')
    list_filter = ('department', 'college')


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'duration_minutes', 'total_marks', 'pass_marks', 'negative_marking', 'is_active', 'created_at')
    list_filter = ('is_active', 'negative_marking', 'randomize_questions')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'test', 'question_type', 'marks', 'difficulty', 'order')
    list_filter = ('test', 'question_type', 'difficulty')
    search_fields = ('title', 'prompt')
    inlines = [OptionInline, TestCaseInline]


@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'test', 'status', 'score', 'total_possible', 'percentage', 'is_passed', 'started_at')
    list_filter = ('status', 'is_passed', 'test')
    search_fields = ('student__user__username', 'student__roll_number', 'test__title')


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'question', 'is_correct', 'marks_awarded', 'test_cases_passed', 'total_test_cases')
    list_filter = ('is_correct', 'question__test')
    search_fields = ('attempt__student__user__username', 'question__title')


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'is_sample', 'weight')
    list_filter = ('is_sample', 'question__test')
