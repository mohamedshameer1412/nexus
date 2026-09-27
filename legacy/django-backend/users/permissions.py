"""
Custom permission classes for role-based access control
"""
from rest_framework import permissions


class IsTeacher(permissions.BasePermission):
    """Permission class for teacher-only access"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'teacher'


class IsStudent(permissions.BasePermission):
    """Permission class for student-only access"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'student'




class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners to edit/delete
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for owner
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'teacher'):
            return obj.teacher == request.user
        
        return False


class IsTeacherOrReadOnly(permissions.BasePermission):
    """
    Permission to only allow teachers to create/edit/delete
    Others can only read
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.role == 'teacher'


class CanViewStudentData(permissions.BasePermission):
    """
    Permission for viewing student data
    - Student can view their own data
    - Teacher can view students in their classrooms
    """
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Get the student from the object
        if hasattr(obj, 'user'):
            student = obj.user
        elif hasattr(obj, 'student'):
            student = obj.student
        else:
            student = obj
        
        # Student can view their own data
        if user == student:
            return True
        
        # Teacher can view if student is in their classroom
        if user.role == 'teacher':
            from users.models import Classroom
            return Classroom.objects.filter(
                teacher=user,
                students=student
            ).exists()
        
        
        return False


class CanModifyQuizSession(permissions.BasePermission):
    """
    Permission for modifying quiz sessions
    - Only the student who owns the session can modify it
    """
    
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class CanAccessClassroom(permissions.BasePermission):
    """
    Permission for accessing classroom
    - Teacher who created it
    - Students enrolled in it
    """
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Teacher who created it
        if obj.teacher == user:
            return True
        
        # Students enrolled
        if user.role == 'student' and obj.students.filter(id=user.id).exists():
            return True
        
        return False
