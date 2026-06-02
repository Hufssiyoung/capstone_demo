import random
from django.contrib.auth.models import User
from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=100, default='')
    join_code = models.CharField(max_length=6, unique=True, default='')
    members = models.ManyToManyField(User, related_name='projects', blank=True)
    title = models.CharField(max_length=200, default='')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or self.title

    @staticmethod
    def generate_code():
        while True:
            code = str(random.randint(100000, 999999))
            if not Project.objects.filter(join_code=code).exists():
                return code

    class Meta:
        verbose_name = '프로젝트'
        ordering = ['-created_at']


class ProjectFile(models.Model):
    STATUS_CHOICES = [
        ('pending', '대기중'),
        ('verified', '검증 완료'),
        ('rejected', '거절됨'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='project_files/', blank=True)
    original_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)
    content = models.TextField(blank=True, verbose_name='검증 내용 (텍스트)')
    topic = models.TextField(blank=True, verbose_name='문서 토픽')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    resubmit_count = models.PositiveIntegerField(default=0, verbose_name='재제출 횟수')
    ai_job_id = models.CharField(max_length=100, blank=True, default='', verbose_name='AI 검증 job ID')
    ai_final_grade = models.CharField(max_length=20, blank=True, default='', verbose_name='AI 종합 판정')
    ai_summary = models.TextField(blank=True, default='', verbose_name='AI 종합 요약')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_files')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_name

    def size_display(self):
        size = self.file_size
        if size >= 1024 * 1024:
            return f'{size / (1024 * 1024):.1f}MB'
        elif size >= 1024:
            return f'{size / 1024:.0f}KB'
        return f'{size}B'

    def ext(self):
        name = self.original_name.upper()
        for ext in ['PDF', 'DOCX', 'DOC', 'XLSX', 'XLS', 'TXT', 'CSV', 'JPEG', 'JPG', 'PNG']:
            if name.endswith(ext):
                return ext
        return 'FILE'

    class Meta:
        verbose_name = '자료'
        ordering = ['-uploaded_at']


class ProjectReference(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='references')
    file = models.FileField(upload_to='project_references/')
    original_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_name

    def size_display(self):
        size = self.file_size
        if size >= 1024 * 1024:
            return f'{size / (1024 * 1024):.1f}MB'
        elif size >= 1024:
            return f'{size / 1024:.0f}KB'
        return f'{size}B'

    def ext(self):
        name = self.original_name.upper()
        for ext in ['PDF', 'DOCX', 'DOC', 'XLSX', 'XLS', 'TXT', 'CSV', 'JPG', 'JPEG', 'PNG']:
            if name.endswith(ext):
                return ext
        return 'FILE'

    class Meta:
        verbose_name = '참고자료'
        ordering = ['-uploaded_at']


class TeamReview(models.Model):
    VOTE_CHOICES = [
        ('approve', '찬성'),
        ('reject', '반대'),
        ('hold', '보류'),
    ]
    project_file = models.ForeignKey('ProjectFile', on_delete=models.CASCADE, related_name='team_reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_reviews')
    vote = models.CharField(max_length=10, choices=VOTE_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('project_file', 'reviewer')]
        ordering = ['created_at']
        verbose_name = '팀원 리뷰'


class TeamReviewItem(models.Model):
    project_file = models.ForeignKey('ProjectFile', on_delete=models.CASCADE, related_name='team_review_items')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_review_items')
    highlighted_text = models.TextField(verbose_name='해당 내용')
    problem = models.TextField(verbose_name='문제점')
    suggestion = models.TextField(verbose_name='제안 내용')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = '팀원 리뷰 항목'


class FileReviewItem(models.Model):
    project_file = models.ForeignKey(ProjectFile, on_delete=models.CASCADE, related_name='review_items')
    highlighted_text = models.TextField(verbose_name='해당 내용')
    problem = models.TextField(verbose_name='문제점')
    suggestion = models.TextField(verbose_name='제안 내용')
    judgment = models.CharField(max_length=20, default='FAIL', verbose_name='판정')
    node = models.CharField(max_length=50, blank=True, default='', verbose_name='검증 노드')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'AI 검증 항목'
        ordering = ['order']


class TeamMember(models.Model):
    ROLE_CHOICES = [
        ('PM', 'PM'),
        ('프론트', '프론트'),
        ('백엔드', '백엔드'),
        ('AI', 'AI'),
        ('자료조사', '자료조사'),
        ('기획', '기획'),
        ('디자인', '디자인'),
        ('기타', '기타'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members_info')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='team_roles')
    name = models.CharField(max_length=50)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='기타')
    is_leader = models.BooleanField(default=False, verbose_name='팀장')
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.name} ({self.role})'

    def avatar_char(self):
        return self.name[0] if self.name else '?'

    class Meta:
        verbose_name = '팀원'
        ordering = ['order', 'id']


class ScheduleEvent(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=200)
    date = models.DateField()

    def __str__(self):
        return f'{self.date} - {self.title}'

    class Meta:
        verbose_name = '일정'
        ordering = ['date']
