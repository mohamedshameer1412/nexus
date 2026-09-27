from django.shortcuts import get_object_or_404
from rest_framework import status, generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
    NotificationSerializer
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    User registration endpoint.
    POST /api/auth/register/
    """
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        try:
            # print("Received registration data:", request.data)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserProfileSerializer(user, context={'request': request}).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'message': 'User registered successfully'
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            # Re-raise validation errors so DRF handles them as 400
            from rest_framework.exceptions import ValidationError
            if isinstance(e, ValidationError):
                raise e
            
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginView(APIView):
    """
    User login endpoint.
    POST /api/auth/login/
    """
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        user = None
        try:
            user_obj = User.objects.get(email=email)
            print(f"LoginView: Found user object for email {email}. ID: {user_obj.id}, Active: {user_obj.is_active}")
            # Authenticate using the retrieved username and providing password
            user = authenticate(username=user_obj.username, password=password)
            if user:
                 print(f"LoginView: Authenticated user {user.username}. ID: {user.id}")
            else:
                 print(f"LoginView: Authentication failed for {user_obj.username}")
        except User.DoesNotExist:
            print(f"LoginView: No user found for email {email}")
            pass # User remains None
        
        if user is None:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        print(f"LoginView: Generated tokens for user ID: {user.id}")
        print(f"LoginView: Access Token (first 20 chars): {access_token[:20]}...")
        
        return Response({
            'user': UserProfileSerializer(user, context={'request': request}).data,
            'tokens': {
                'refresh': str(refresh),
                'access': access_token,
            },
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    User logout endpoint.
    POST /api/auth/logout/
    """
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    Get and update user profile.
    GET /api/auth/profile/
    PUT /api/auth/profile/
    """
    permission_classes = (permissions.IsAuthenticated,)
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return UserProfileSerializer
        return UserUpdateSerializer


from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Classroom, ClassroomInvitation, Notification, Achievement
from .serializers import ClassroomSerializer, ClassroomInvitationSerializer, AchievementSerializer

class ClassroomViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            from .serializers import ClassroomDetailSerializer
            return ClassroomDetailSerializer
        return ClassroomSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'teacher':
            return Classroom.objects.filter(teacher=user)
        elif user.role == 'student':
            return user.enrolled_classes.all()
        return Classroom.objects.none()
        return Classroom.objects.none()

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # print(f"DEBUG: Classroom list for {request.user.email}: {response.data}")
        return response

    def perform_create(self, serializer):
        if self.request.user.role != 'teacher':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only teachers can create classrooms.")
        # Default to enabling join by code for better UX
        serializer.save(teacher=self.request.user, is_join_by_code_enabled=True)

    @action(detail=False, methods=['post'])
    def join(self, request):
        code = request.data.get('access_code', '').replace(' ', '').upper()
        if not code:
            return Response({'error': 'Access code is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            classroom = Classroom.objects.get(access_code=code.upper())
            if not classroom.is_join_by_code_enabled:
                return Response({'error': 'Joining by code is disabled for this class'}, status=status.HTTP_403_FORBIDDEN)

            if request.user.role != 'student':
                 return Response({'error': 'Only students can join classes'}, status=status.HTTP_403_FORBIDDEN)
            
            if classroom.students.filter(id=request.user.id).exists():
                return Response({'message': 'Already enrolled'}, status=status.HTTP_200_OK)
            
            classroom.students.add(request.user)
            return Response({
                'message': f'Successfully joined {classroom.name}',
                'classroom': {
                    'id': classroom.id,
                    'name': classroom.name,
                    'teacher_name': classroom.teacher.full_name
                }
            }, status=status.HTTP_200_OK)
        except Classroom.DoesNotExist:
            return Response({'error': 'Invalid access code'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def invite(self, request, pk=None):
        classroom = self.get_object()
        if request.user != classroom.teacher:
            return Response({'error': 'Only the teacher can invite students'}, status=status.HTTP_403_FORBIDDEN)
        
        emails = request.data.get('emails')
        if not emails:
            email = request.data.get('email')
            emails = [email] if email else []
            
        if not emails:
            return Response({'error': 'Email(s) are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not isinstance(emails, list):
            emails = [emails]

        results = []
        from django.contrib.auth import get_user_model
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from django.conf import settings
        
        User = get_user_model()
        
        for email in emails:
            email = email.strip()
            if not email:
                continue
                
            try:
                if not User.objects.filter(email=email).exists():
                    results.append({'email': email, 'status': 'error', 'message': 'Student is not registered'})
                    continue
                
                target_user = User.objects.get(email=email)
                
                if target_user.role == 'teacher':
                    results.append({'email': email, 'status': 'error', 'message': 'Cannot invite a teacher as a student'})
                    continue

                if classroom.students.filter(email=email).exists():
                    results.append({'email': email, 'status': 'error', 'message': 'Student already enrolled'})
                    continue
                
                invitation, created = ClassroomInvitation.objects.get_or_create(
                    classroom=classroom,
                    email=email,
                    defaults={'status': 'pending'}
                )
                
                if not created and invitation.status == 'accepted':
                    results.append({'email': email, 'status': 'error', 'message': 'Student already accepted invitation'})
                    continue
                
                # Send invitation email
                try:
                    context = {
                        'classroom_name': classroom.name,
                        'teacher_name': classroom.teacher.full_name or classroom.teacher.username,
                        'access_code': classroom.access_code,
                        'invite_url': f"{settings.FRONTEND_URL}/invite/accept/{invitation.id}",
                        'dashboard_url': f"{settings.FRONTEND_URL}/dashboard",
                        'show_access_code': classroom.is_join_by_code_enabled,
                    }
                    
                    html_message = render_to_string('emails/classroom_invite.html', context)
                    plain_message = strip_tags(html_message)
                    
                    send_mail(
                        subject=f"Invitation to join {classroom.name}",
                        message=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    results.append({'email': email, 'status': 'success', 'message': 'Invitation sent'})
                except Exception as e:
                    results.append({'email': email, 'status': 'partial_success', 'message': f'Invitation created but email failed: {str(e)}'})
            except Exception as e:
                results.append({'email': email, 'status': 'error', 'message': str(e)})
        
        return Response({'results': results}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='remove-student')
    def remove_student(self, request, pk=None):
        classroom = self.get_object()
        if request.user != classroom.teacher:
             return Response({'error': 'Only teacher can remove students'}, status=status.HTTP_403_FORBIDDEN)
        
        student_id = request.data.get('student_id')
        if not student_id:
             return Response({'error': 'Student ID required'}, status=status.HTTP_400_BAD_REQUEST)

        student = classroom.students.filter(id=student_id).first()
        if not student:
             return Response({'error': 'Student not found in this class'}, status=status.HTTP_404_NOT_FOUND)

        classroom.students.remove(student)
        return Response({'message': 'Student removed successfully'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='assign-quiz')
    def assign_quiz(self, request, pk=None):
        classroom = self.get_object()
        # Allow teacher or co-teacher
        if request.user != classroom.teacher and not classroom.co_teachers.filter(id=request.user.id).exists():
             return Response({'error': 'Only teacher can assign quizzes'}, status=status.HTTP_403_FORBIDDEN)

        quiz_id = request.data.get('quiz_id')
        if not quiz_id:
             return Response({'error': 'Quiz ID required'}, status=status.HTTP_400_BAD_REQUEST)

        from quiz.models import Quiz
        from .models import ClassroomQuizAssignment
        try:
            quiz = Quiz.objects.get(id=quiz_id)
        except Quiz.DoesNotExist:
             return Response({'error': 'Quiz not found'}, status=status.HTTP_404_NOT_FOUND)

        # Extract assignment settings from request
        def parse_int_or_none(val):
            try:
                return int(val)
            except (TypeError, ValueError):
                return None

        def sanitize_val(val):
            if val == '' or val is None:
                return None
            return val

        settings = {
            'quiz_mode': request.data.get('quiz_mode', 'practice'),
            'allow_unlimited_attempts': request.data.get('allow_unlimited_attempts', True),
            'max_attempts': parse_int_or_none(sanitize_val(request.data.get('max_attempts'))) or 1,
            'due_date': sanitize_val(request.data.get('due_date')),
            'time_limit_minutes': parse_int_or_none(sanitize_val(request.data.get('time_limit_minutes'))),
            'show_immediate_feedback': request.data.get('show_immediate_feedback', True),
            'enable_proctoring': request.data.get('enable_proctoring', False),
            'shuffle_questions': request.data.get('shuffle_questions', True),
            'shuffle_options': request.data.get('shuffle_options', True),
            'assigned_by': request.user
        }
        
        # Check for existing assignment
        assignment, created = ClassroomQuizAssignment.objects.update_or_create(
            classroom=classroom,
            quiz=quiz,
            defaults=settings
        )
        
        return Response({'message': 'Quiz assigned successfully', 'assignment_id': assignment.id}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='unassign-quiz')
    def unassign_quiz(self, request, pk=None):
        classroom = self.get_object()
        # Allow teacher or co-teacher
        if request.user != classroom.teacher and not classroom.co_teachers.filter(id=request.user.id).exists():
             return Response({'error': 'Only teacher can remove assigned quizzes'}, status=status.HTTP_403_FORBIDDEN)

        quiz_id = request.data.get('quiz_id')
        if not quiz_id:
             return Response({'error': 'Quiz ID required'}, status=status.HTTP_400_BAD_REQUEST)

        from .models import ClassroomQuizAssignment
        
        # Try finding by Assignment ID first (most likely what frontend sends)
        try:
            assignment = ClassroomQuizAssignment.objects.get(classroom=classroom, id=quiz_id)
            assignment.delete()
            return Response({'message': 'Quiz unassigned successfully'}, status=status.HTTP_200_OK)
        except (ClassroomQuizAssignment.DoesNotExist, ValueError):
            # Fallback: Try finding by Quiz ID (foreign key)
            try:
                assignment = ClassroomQuizAssignment.objects.get(classroom=classroom, quiz_id=quiz_id)
                assignment.delete()
                return Response({'message': 'Quiz unassigned successfully'}, status=status.HTTP_200_OK)
            except ClassroomQuizAssignment.DoesNotExist:
                 return Response({'error': 'Quiz assignment not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'], url_path='assigned-quizzes')
    def get_assigned_quizzes(self, request, pk=None):
        """Get all quizzes assigned to this classroom"""
        classroom = self.get_object()
        
        # Allow teacher, co-teachers, and students to view
        if (request.user != classroom.teacher and 
            not classroom.co_teachers.filter(id=request.user.id).exists() and
            not classroom.students.filter(id=request.user.id).exists()):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        from .models import ClassroomQuizAssignment
        from .serializers import ClassroomQuizAssignmentSerializer
        
        # Build queryset based on role
        queryset = ClassroomQuizAssignment.objects.filter(classroom=classroom)
        if request.user.role == 'student':
            queryset = queryset.filter(is_active=True)
            
        assignments = queryset.select_related('quiz', 'assigned_by').order_by('-assigned_at')
        
        # Use the specialized serializer which now includes all UI-needed aliases
        serializer = ClassroomQuizAssignmentSerializer(
            assignments, 
            many=True, 
            context={'request': request}
        )
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], url_path='leave')
    def leave_classroom(self, request, pk=None):
        """Student leaves classroom"""
        classroom = self.get_object()
        
        if request.user.role != 'student':
            return Response(
                {'error': 'Only students can leave classrooms'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not classroom.students.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not enrolled in this classroom'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already has pending request
        from .models import ClassroomLeaveRequest
        if ClassroomLeaveRequest.objects.filter(classroom=classroom, student=request.user, status='pending').exists():
            return Response({'message': 'Leave request is already pending approval'}, status=status.HTTP_200_OK)

        # Create leave request
        ClassroomLeaveRequest.objects.create(
            classroom=classroom,
            student=request.user,
            reason=request.data.get('reason', '')
        )
        
        # Notify teacher
        from .notifications import create_notification
        create_notification(
            user=classroom.teacher,
            title="Leave Request",
            message=f"{request.user.full_name} has requested to leave {classroom.name}",
            notification_type='general', # OR create new type 'leave_request'
            related_object_id=classroom.id,
            related_object_type='classroom_leave'
        )
        
        return Response(
            {'message': 'Leave request sent to teacher for approval'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], url_path='respond-leave')
    def respond_to_leave_request(self, request, pk=None):
        """Teacher responds to leave request"""
        classroom = self.get_object()
        
        if request.user != classroom.teacher:
            return Response({'error': 'Only teacher can approve leave requests'}, status=status.HTTP_403_FORBIDDEN)
            
        student_id = request.data.get('student_id')
        action = request.data.get('action') # 'approve' or 'reject'
        
        if not student_id or not action:
            return Response({'error': 'student_id and action required'}, status=status.HTTP_400_BAD_REQUEST)
            
        from .models import ClassroomLeaveRequest
        try:
            leave_request = ClassroomLeaveRequest.objects.get(
                classroom=classroom, 
                student_id=student_id, 
                status='pending'
            )
        except ClassroomLeaveRequest.DoesNotExist:
             return Response({'error': 'No pending leave request found for this student'}, status=status.HTTP_404_NOT_FOUND)

        from django.utils import timezone
        leave_request.responded_at = timezone.now()
        
        if action == 'approve':
            leave_request.status = 'approved'
            classroom.students.remove(leave_request.student)
            message = f"Your request to leave {classroom.name} was approved."
        else:
            leave_request.status = 'rejected'
            message = f"Your request to leave {classroom.name} was rejected."
            
        leave_request.save()
        
        # Notify student
        from .notifications import create_notification
        create_notification(
            user=leave_request.student,
            title="Leave Request Update",
            message=message,
            notification_type='general'
        )
        
        return Response({'message': f'Request {action}d successfully'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], url_path='leave-requests')
    def get_leave_requests(self, request, pk=None):
        """Get pending leave requests for a classroom"""
        classroom = self.get_object()
        if request.user != classroom.teacher:
            return Response({'error': 'Only teacher can view leave requests'}, status=status.HTTP_403_FORBIDDEN)
            
        from .models import ClassroomLeaveRequest
        from .serializers import ClassroomLeaveRequestSerializer
        
        requests = ClassroomLeaveRequest.objects.filter(classroom=classroom, status='pending')
        serializer = ClassroomLeaveRequestSerializer(requests, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='add-co-teacher')
    def add_co_teacher(self, request, pk=None):
        """Add co-teacher to classroom (owner only)"""
        classroom = self.get_object()
        
        if request.user != classroom.teacher:
            return Response(
                {'error': 'Only the classroom owner can add co-teachers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        teacher_email = request.data.get('teacher_email')
        if not teacher_email:
            return Response(
                {'error': 'teacher_email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            co_teacher = User.objects.get(email=teacher_email, role='teacher')
        except User.DoesNotExist:
            return Response(
                {'error': 'Teacher not found with this email'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if co_teacher == classroom.teacher:
            return Response(
                {'error': 'Cannot add yourself as co-teacher'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if classroom.co_teachers.filter(id=co_teacher.id).exists():
            return Response(
                {'error': 'Already a co-teacher'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        classroom.co_teachers.add(co_teacher)
        
        # Notify co-teacher
        from .notifications import create_notification
        create_notification(
            user=co_teacher,
            title="Added as Co-Teacher",
            message=f"{request.user.full_name} added you as co-teacher for {classroom.name}",
            notification_type='general',
            related_object_id=classroom.id,
            related_object_type='classroom',
            send_email=True
        )
        
        return Response(
            {'message': f'{co_teacher.full_name} added as co-teacher'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], url_path='remove-co-teacher')
    def remove_co_teacher(self, request, pk=None):
        """Remove co-teacher from classroom (owner only)"""
        classroom = self.get_object()
        
        if request.user != classroom.teacher:
            return Response(
                {'error': 'Only the classroom owner can remove co-teachers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        teacher_id = request.data.get('teacher_id')
        if not teacher_id:
            return Response(
                {'error': 'teacher_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            co_teacher = User.objects.get(id=teacher_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Teacher not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not classroom.co_teachers.filter(id=co_teacher.id).exists():
            return Response(
                {'error': 'Not a co-teacher'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        classroom.co_teachers.remove(co_teacher)
        
        return Response(
            {'message': f'{co_teacher.full_name} removed as co-teacher'},
            status=status.HTTP_200_OK
        )


class InvitationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ClassroomInvitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Students see invites sent to their email
        return ClassroomInvitation.objects.filter(email=self.request.user.email, status='pending')

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        invitation = self.get_object()
        if invitation.email != request.user.email:
            return Response({'error': 'This invitation is not for you'}, status=status.HTTP_403_FORBIDDEN)
            
        invitation.status = 'accepted'
        invitation.save()
        
        invitation.classroom.students.add(request.user)
        return Response({'message': f'You have joined {invitation.classroom.name}'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        invitation = self.get_object()
        if invitation.email != request.user.email:
            return Response({'error': 'This invitation is not for you'}, status=status.HTTP_403_FORBIDDEN)
            
        invitation.status = 'declined'
        invitation.save()
        return Response({'message': 'Invitation declined'}, status=status.HTTP_200_OK)


# ==================== CLASSROOM QUIZ ASSIGNMENT VIEWSET ====================

class ClassroomQuizAssignmentViewSet(viewsets.ModelViewSet):
    """Manage quiz assignments for classrooms"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        from .serializers import ClassroomQuizAssignmentSerializer
        return ClassroomQuizAssignmentSerializer
    
    def get_queryset(self):
        """Filter assignments based on user role and query params"""
        user = self.request.user
        from .models import ClassroomQuizAssignment
        from django.db.models import Q
        
        queryset = ClassroomQuizAssignment.objects.none()
        
        if user.role == 'teacher' or user.is_staff or user.is_superuser:
            # Teachers/Co-teachers/Admins see assignments for their classrooms (or all if admin)
            if user.is_superuser:
                queryset = ClassroomQuizAssignment.objects.all()
            else:
                queryset = ClassroomQuizAssignment.objects.filter(
                    Q(classroom__teacher=user) | Q(classroom__co_teachers=user)
                ).distinct()
        elif user.role == 'student':
            # Students see assignments for classrooms they're enrolled in
            queryset = ClassroomQuizAssignment.objects.filter(
                classroom__students=user,
                is_active=True
            )
            
        # Filter by classroom if provided
        classroom_id = self.request.query_params.get('classroom')
        if classroom_id:
            queryset = queryset.filter(classroom_id=classroom_id)
            
        return queryset.select_related('classroom', 'quiz', 'assigned_by')
    
    def perform_create(self, serializer):
        """Assign quiz to classroom"""
        if self.request.user.role != 'teacher':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only teachers can assign quizzes")
        serializer.save(assigned_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_classroom_quizzes(self, request):
        """Get all quizzes assigned to student's classrooms, grouped by classroom"""
        if request.user.role != 'student':
            return Response(
                {'error': 'Only students can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from .models import Classroom, ClassroomQuizAssignment
        
        # Get all classrooms student is enrolled in
        classrooms = Classroom.objects.filter(students=request.user).prefetch_related('assigned_quizzes')
        
        result = []
        for classroom in classrooms:
            assignments = ClassroomQuizAssignment.objects.filter(
                classroom=classroom,
                is_active=True
            ).select_related('quiz', 'assigned_by')
            
            serializer = self.get_serializer(assignments, many=True, context={'request': request})
            
            result.append({
                'classroom_id': str(classroom.id),
                'classroom_name': classroom.name,
                'teacher_name': classroom.teacher.full_name or classroom.teacher.username,
                'quizzes': serializer.data
            })
        
        return Response(result, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def start_attempt(self, request, pk=None):
        """Start a new quiz attempt for this classroom assignment"""
        assignment = self.get_object()
        
        # Check permissions: Student, Teacher, Co-teacher, or Admin
        is_student = assignment.classroom.students.filter(id=request.user.id).exists()
        is_teacher = assignment.classroom.teacher == request.user
        is_co_teacher = assignment.classroom.co_teachers.filter(id=request.user.id).exists()
        is_admin = request.user.is_staff or request.user.is_superuser
        
        if not (is_student or is_teacher or is_co_teacher or is_admin):
            return Response(
                {'error': 'You are not enrolled in this classroom'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check attempt limits (only for students)
        from quiz.models import QuizSession
        attempts_count = QuizSession.objects.filter(
            classroom_assignment=assignment,
            user=request.user
        ).count()
        
        if is_student:
            if assignment.quiz_mode == 'assessment':
                if attempts_count >= assignment.max_attempts:
                    return Response(
                        {'error': f'Maximum attempts ({assignment.max_attempts}) reached'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            elif assignment.quiz_mode == 'practice' and not assignment.allow_unlimited_attempts:
                if attempts_count >= assignment.max_attempts:
                    return Response(
                        {'error': f'Maximum attempts ({assignment.max_attempts}) reached'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        # Create new quiz session
        from django.utils import timezone
        session = QuizSession.objects.create(
            user=request.user,
            quiz=assignment.quiz,
            classroom_assignment=assignment,
            classroom_attempt_number=attempts_count + 1,
            attempt_number=attempts_count + 1,
            started_at=timezone.now()
        )
        
        return Response({
            'session_id': str(session.id),
            'quiz_id': str(assignment.quiz.id),
            'quiz_title': assignment.quiz.title,
            'quiz_mode': assignment.quiz_mode,
            'attempt_number': session.classroom_attempt_number,
            'time_limit': assignment.quiz.time_limit,
            'message': 'Quiz session started successfully'
        }, status=status.HTTP_201_CREATED)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({'status': 'read'})

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response(
            {"message": "All notifications marked as read"},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': count})


class AchievementViewSet(viewsets.ReadOnlyModelViewSet):
    """View user honors and badges"""
    serializer_class = AchievementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Achievement.objects.filter(user=self.request.user)
