from django.contrib import admin
from .models import (
    Topic, Subtopic, Question, Quiz, QuizSession, 
    Response
)


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(Subtopic)
class SubtopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'topic', 'created_at']
    list_filter = ['topic']
    search_fields = ['name', 'description']
    filter_horizontal = ['prerequisite_subtopics']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'topic', 'subtopic', 'difficulty_level', 'success_rate', 'times_asked']
    list_filter = ['topic', 'difficulty_level']
    search_fields = ['question_text']
    readonly_fields = ['times_asked', 'times_correct', 'success_rate']
    
    fieldsets = (
        ('Question Content', {
            'fields': ('topic', 'subtopic', 'question_text', 'explanation')
        }),
        ('Answer Options', {
            'fields': ('option_a', 'option_b', 'option_c', 'option_d', 'correct_answer')
        }),
        ('Difficulty & IRT', {
            'fields': ('difficulty_level', 'irt_difficulty', 'irt_discrimination')
        }),
        ('Statistics', {
            'fields': ('times_asked', 'times_correct', 'success_rate'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at', 'times_asked', 'times_correct']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'total_questions', 'is_adaptive', 'created_by', 'created_at']
    list_filter = ['is_adaptive', 'created_at']
    search_fields = ['title', 'description']
    filter_horizontal = ['topics']


@admin.register(QuizSession)
class QuizSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'quiz', 'total_score', 'accuracy', 'detected_mindset', 'is_active', 'started_at']
    list_filter = ['is_active', 'detected_mindset', 'started_at']
    search_fields = ['user__username', 'quiz__title']
    readonly_fields = ['started_at', 'completed_at', 'accuracy']
    
    fieldsets = (
        ('Session Info', {
            'fields': ('user', 'quiz', 'is_active', 'started_at', 'completed_at')
        }),
        ('Progress', {
            'fields': ('current_question_index', 'current_difficulty_level', 'student_ability')
        }),
        ('Scores', {
            'fields': ('total_score', 'behavior_score', 'correct_answers', 'incorrect_answers', 'accuracy')
        }),
        ('Behavior', {
            'fields': ('total_tab_switches', 'total_hesitations', 'avg_response_time', 'detected_mindset')
        }),
    )


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'question', 'selected_answer', 'is_correct', 'response_time', 'timestamp']
    list_filter = ['is_correct', 'timestamp']
    search_fields = ['session__user__username', 'question__question_text']
    readonly_fields = ['timestamp', 'is_correct', 'confidence_level']



