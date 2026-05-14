import calendar
import html as html_module
import re
import threading
import time
from datetime import date

import requests as http_client

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import close_old_connections
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ProjectTopicForm, ScheduleEventForm
from .models import FileReviewItem, Project, ProjectFile, ProjectReference, ScheduleEvent, TeamMember, TeamReview, TeamReviewItem

_AI_BASE = getattr(settings, 'AI_SERVICE_URL', 'http://127.0.0.1:8001')


def _normalize_content(text: str) -> str:
    """줄바꿈 정규화: CRLF→LF, 연속 3개 이상 줄바꿈→2개로 축소."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _find_hl(text: str, query: str, min_ratio: float = 0.6) -> str | None:
    """text 안에서 query 또는 그 최장 prefix를 찾아 반환. 못 찾으면 None."""
    if query in text:
        return query
    min_len = max(12, int(len(query) * min_ratio))
    for end in range(len(query) - 1, min_len - 1, -1):
        prefix = query[:end]
        if prefix in text:
            return prefix
    return None


def _ai_verify_background(project_file_id: int, text: str, topic: str) -> None:
    """백그라운드 스레드: AI 검증 요청 후 결과를 FileReviewItem으로 저장."""
    try:
        payload = {"project_file_id": project_file_id, "text": text, "topic": topic}
        resp = http_client.post(f"{_AI_BASE}/verify", json=payload, timeout=15)
        if resp.status_code != 202:
            return
        job_id = resp.json()["job_id"]
        ProjectFile.objects.filter(id=project_file_id).update(ai_job_id=job_id)

        for _ in range(72):  # 최대 6분 (5초 × 72)
            time.sleep(5)
            st = http_client.get(f"{_AI_BASE}/verify/{job_id}/status", timeout=10)
            if st.status_code != 200:
                break
            status = st.json().get("status")
            if status == "completed":
                result_resp = http_client.get(f"{_AI_BASE}/verify/{job_id}/result", timeout=15)
                if result_resp.status_code == 200:
                    data = result_resp.json()
                    issues = data.get("final_report", {}).get("issues", [])
                    final_grade = data.get("final_grade", "")
                    close_old_connections()
                    pf = ProjectFile.objects.filter(id=project_file_id).first()
                    if pf:
                        pf.review_items.all().delete()
                        pf.ai_final_grade = final_grade
                        pf.save(update_fields=['ai_final_grade'])
                        for i, issue in enumerate(issues):
                            FileReviewItem.objects.create(
                                project_file=pf,
                                highlighted_text=issue.get("highlighted_text", ""),
                                problem=issue.get("problem", ""),
                                suggestion=issue.get("suggestion", ""),
                                order=i,
                            )
                break
            elif status == "failed":
                break
    except Exception:
        pass
    finally:
        close_old_connections()


def _get_project_for_user(request):
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        active_id = request.session.get('active_project_id')
        if active_id:
            project = user.projects.filter(id=active_id).first()
            if project:
                return project
        project = user.projects.first()
        if project:
            request.session['active_project_id'] = project.id
            return project
    try:
        return Project.objects.get(id=1)
    except Project.DoesNotExist:
        return Project.objects.create(
            id=1, name='', title='', description='', join_code=Project.generate_code()
        )


def _base_context(tab='', request=None):
    project = _get_project_for_user(request)
    ctx = {'tab': tab, 'current_project': project}
    if request and request.user.is_authenticated:
        ctx['user_projects'] = request.user.projects.all()
    return ctx


# ── 인증 ─────────────────────────────────────────────────────────
def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('project_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


# ── 메인 리다이렉트 ──────────────────────────────────────────────
def index(request):
    if request.user.is_authenticated:
        return redirect('project_list')
    return redirect('login')


# ── 자료 검증 탭 ────────────────────────────────────────────────
@login_required
def review(request):
    project = _get_project_for_user(request)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'submit_text':
            content = _normalize_content(request.POST.get('content', ''))
            topic = request.POST.get('topic', '').strip()
            uploaded = request.FILES.get('file')
            ALLOWED = ('.pdf',)
            file_ok = uploaded and uploaded.name.lower().endswith(ALLOWED)
            if content or file_ok:
                name = topic or (uploaded.name if file_ok else '텍스트 입력')
                pf = ProjectFile(
                    project=project,
                    original_name=name,
                    file_size=uploaded.size if file_ok else 0,
                    content=content,
                    topic=topic,
                    status='pending',
                    resubmit_count=1,
                    uploaded_by=request.user,
                )
                if file_ok:
                    pf.file.save(uploaded.name, uploaded)
                else:
                    pf.save()
                if content:
                    threading.Thread(
                        target=_ai_verify_background,
                        args=(pf.id, content, topic or pf.original_name),
                        daemon=True,
                    ).start()
        elif action == 'verify':
            file_id = request.POST.get('file_id')
            ProjectFile.objects.filter(id=file_id, project=project).update(status='verified')
        elif action == 'reject':
            file_id = request.POST.get('file_id')
            ProjectFile.objects.filter(id=file_id, project=project).update(status='rejected')
        elif action == 'resubmit':
            file_id = request.POST.get('file_id')
            pf = ProjectFile.objects.filter(
                id=file_id, project=project, uploaded_by=request.user, status='rejected'
            ).first()
            if pf:
                new_topic = request.POST.get('topic', '').strip()
                new_content = _normalize_content(request.POST.get('content', ''))
                uploaded = request.FILES.get('file')
                file_ok = uploaded and uploaded.name.lower().endswith('.pdf')
                if new_topic:
                    pf.original_name = new_topic
                    pf.topic = new_topic
                pf.content = new_content
                pf.status = 'pending'
                pf.resubmit_count += 1
                if file_ok:
                    pf.file.delete(save=False)
                    pf.file_size = uploaded.size
                    pf.file.save(uploaded.name, uploaded)
                else:
                    pf.save()
                pf.review_items.all().delete()
                pf.team_review_items.all().delete()
                pf.team_reviews.all().delete()
                if new_content:
                    threading.Thread(
                        target=_ai_verify_background,
                        args=(pf.id, new_content, pf.topic or pf.original_name),
                        daemon=True,
                    ).start()
            return redirect(f'/review/?doc={file_id}')
        elif action == 'delete_doc':
            file_id = request.POST.get('file_id')
            pf = ProjectFile.objects.filter(id=file_id, project=project).first()
            if pf:
                pf.file.delete(save=False)
                pf.delete()
        elif action == 'submit_review':
            file_id = request.POST.get('file_id')
            vote = request.POST.get('vote')
            comment = request.POST.get('comment', '').strip()
            if file_id and vote:
                pf = ProjectFile.objects.filter(id=file_id, project=project).first()
                if pf:
                    TeamReview.objects.update_or_create(
                        project_file=pf,
                        reviewer=request.user,
                        defaults={'vote': vote, 'comment': comment},
                    )
            return redirect(f'/review/?doc={file_id}')
        elif action == 'submit_team_review':
            file_id = request.POST.get('file_id')
            hl = request.POST.get('highlighted_text', '').strip()
            problem = request.POST.get('problem', '').strip()
            suggestion = request.POST.get('suggestion', '').strip()
            if file_id and hl and problem:
                pf = ProjectFile.objects.filter(id=file_id, project=project).first()
                if pf:
                    TeamReviewItem.objects.create(
                        project_file=pf,
                        reviewer=request.user,
                        highlighted_text=hl,
                        problem=problem,
                        suggestion=suggestion,
                    )
            return redirect(f'/review/?doc={file_id}')
        elif action == 'delete_team_review':
            item_id = request.POST.get('item_id')
            file_id = request.POST.get('file_id')
            TeamReviewItem.objects.filter(id=item_id, reviewer=request.user).delete()
            return redirect(f'/review/?doc={file_id}')
        return redirect('review')

    selected_id = request.GET.get('doc')
    doc_files = project.files.all()
    selected_file = None
    if selected_id:
        selected_file = project.files.filter(id=selected_id).first()

    highlighted_content = None
    team_review_items = []
    reviewer_groups = []
    if selected_file:
        team_review_items = list(selected_file.team_review_items.select_related('reviewer').all())

        all_members = list(project.members.exclude(id=request.user.id))

        votes = {
            v.reviewer.id: v
            for v in selected_file.team_reviews.select_related('reviewer').all()
        }
        items_by_rid = {}
        for i, item in enumerate(team_review_items):
            if item.reviewer == request.user:
                continue
            rid = item.reviewer.id
            items_by_rid.setdefault(rid, []).append({'index': i, 'item': item})

        for member in all_members:
            reviewer_groups.append({
                'reviewer': member,
                'vote': votes.get(member.id),
                'items': items_by_rid.get(member.id, []),
            })
    if selected_file and selected_file.content:
        ai_items = list(selected_file.review_items.all())
        if ai_items or team_review_items:
            escaped = html_module.escape(selected_file.content)
            for i, item in enumerate(ai_items):
                hl_raw = re.sub(r'\s+', ' ', item.highlighted_text).strip()
                hl = html_module.escape(hl_raw)
                matched = _find_hl(escaped, hl)
                if matched:
                    mark = (f'<mark class="review-highlight ai-hl" data-idx="{i}" '
                            f'onclick="focusCard({i})">{matched}</mark>')
                    escaped = escaped.replace(matched, mark, 1)
            for i, item in enumerate(team_review_items):
                hl = html_module.escape(item.highlighted_text)
                mark = (f'<mark class="review-highlight team-hl" data-tidx="{i}" '
                        f'onclick="focusTeamCard({i})">{hl}</mark>')
                escaped = escaped.replace(hl, mark, 1)
            highlighted_content = escaped.replace('\n', '<br>')

    other_review_count = sum(1 for g in reviewer_groups if g['vote'] or g['items'])

    team_votes = [g['vote'].vote for g in reviewer_groups if g['vote']]
    team_vote_counts = {
        'approve': team_votes.count('approve'),
        'hold': team_votes.count('hold'),
        'reject': team_votes.count('reject'),
    } if team_votes else None
    my_team_review_items = []
    my_review_indices = []
    my_vote = None
    if selected_file:
        my_team_review_items = list(
            selected_file.team_review_items.filter(reviewer=request.user)
        )
        my_review_indices = [
            i for i, item in enumerate(team_review_items)
            if item.reviewer == request.user
        ]
        vote_obj = selected_file.team_reviews.filter(reviewer=request.user).first()
        my_vote = vote_obj.vote if vote_obj else None

    is_leader = project.members_info.filter(user=request.user, is_leader=True).exists()

    ai_status = 'none'
    if selected_file:
        has_items = selected_file.review_items.exists()
        if has_items:
            ai_status = 'completed'
        elif selected_file.ai_job_id:
            ai_status = 'processing'

    ctx = _base_context('review', request)
    ctx.update({
        'project': project,
        'doc_files': doc_files,
        'selected_file': selected_file,
        'highlighted_content': highlighted_content,
        'team_review_items': team_review_items,
        'reviewer_groups': reviewer_groups,
        'my_team_review_items': my_team_review_items,
        'my_review_indices': my_review_indices,
        'ai_status': ai_status,
        'my_vote': my_vote,
        'other_review_count': other_review_count,
        'team_vote_counts': team_vote_counts,
        'is_leader': is_leader,
    })
    return render(request, 'core/review.html', ctx)


# ── 자료 보관함 탭 ───────────────────────────────────────────────
@login_required
def archive(request):
    project = _get_project_for_user(request)

    if request.method == 'POST':
        action = request.POST.get('action')
        file_id = request.POST.get('file_id')
        if action == 'delete_doc':
            pf = ProjectFile.objects.filter(id=file_id, project=project).first()
            if pf:
                pf.file.delete(save=False)
                pf.delete()
        return redirect('archive')

    pending_files  = project.files.filter(status='pending')
    verified_files = project.files.filter(status='verified')
    rejected_files = project.files.filter(status='rejected')

    ctx = _base_context('archive', request)
    ctx.update({
        'project': project,
        'pending_files': pending_files,
        'verified_files': verified_files,
        'rejected_files': rejected_files,
    })
    return render(request, 'core/archive.html', ctx)


# ── 내보내기 탭 ─────────────────────────────────────────────────
@login_required
def export(request):
    ctx = _base_context('export', request)
    return render(request, 'core/export.html', ctx)


# ── 프로젝트 목록 ─────────────────────────────────────────────────
@login_required
def project_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_project':
            name = request.POST.get('name', '').strip()
            if name:
                project = Project.objects.create(name=name, join_code=Project.generate_code())
                project.members.add(request.user)
                request.session['active_project_id'] = project.id
        elif action == 'join_project':
            code = request.POST.get('join_code', '').strip()
            project = Project.objects.filter(join_code=code).first()
            if project:
                project.members.add(request.user)
                request.session['active_project_id'] = project.id
            else:
                ctx = _base_context('projects', request)
                ctx['all_projects'] = request.user.projects.all()
                ctx['error'] = f'입장 코드 {code}에 해당하는 프로젝트가 없습니다.'
                return render(request, 'core/project_list.html', ctx)
        elif action == 'delete_project':
            project_id = request.POST.get('project_id')
            Project.objects.filter(id=project_id).delete()
            if str(request.session.get('active_project_id')) == str(project_id):
                del request.session['active_project_id']
        return redirect('project_list')

    ctx = _base_context('projects', request)
    ctx['all_projects'] = request.user.projects.all()
    return render(request, 'core/project_list.html', ctx)


# ── 프로젝트 전환 ───────────────────────────────────────────────
@login_required
def switch_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if project.members.filter(id=request.user.id).exists():
        request.session['active_project_id'] = project_id
    return redirect('review')


# ── 프로젝트 설정: 주제 설정 ────────────────────────────────────
@login_required
def project_settings_topic(request):
    project = _get_project_for_user(request)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_project_name':
            name = request.POST.get('project_name', '').strip()
            if name:
                project.name = name
                project.save(update_fields=['name'])
            return redirect('project_settings_topic')
        elif action == 'save_topic':
            form = ProjectTopicForm(request.POST, instance=project)
            if form.is_valid():
                form.save()
                return redirect('project_settings_topic')
        elif action == 'upload_file':
            uploaded = request.FILES.get('file')
            if uploaded:
                pr = ProjectReference(
                    project=project,
                    original_name=uploaded.name,
                    file_size=uploaded.size,
                    uploaded_by=request.user,
                )
                pr.file.save(uploaded.name, uploaded)
                pr.save()
            return redirect('project_settings_topic')
    else:
        form = ProjectTopicForm(instance=project)

    ctx = _base_context('settings', request)
    ctx.update({
        'sub_tab': 'topic',
        'project': project,
        'form': form,
        'files': project.references.all(),
    })
    return render(request, 'core/project_settings_topic.html', ctx)


@require_POST
@login_required
def delete_file(request, file_id):
    pr = get_object_or_404(ProjectReference, id=file_id)
    pr.file.delete(save=False)
    pr.delete()
    return redirect('project_settings_topic')


# ── 프로젝트 설정: 역할 분담 ────────────────────────────────────
@login_required
def project_settings_role(request):
    project = _get_project_for_user(request)

    for i, user in enumerate(project.members.all()):
        TeamMember.objects.get_or_create(
            project=project, user=user,
            defaults={'name': user.username, 'role': '기타', 'order': i},
        )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_roles':
            user_ids = request.POST.getlist('user_id')
            roles = request.POST.getlist('role')
            for uid, role in zip(user_ids, roles):
                TeamMember.objects.filter(project=project, user_id=uid).update(role=role)
        elif action == 'save_leader':
            leader_user_id = request.POST.get('leader_user_id')
            project.members_info.update(is_leader=False)
            if leader_user_id:
                project.members_info.filter(user_id=leader_user_id).update(is_leader=True)
        return redirect('project_settings_role')

    members = project.members_info.select_related('user').order_by('order', 'id')
    current_leader = members.filter(is_leader=True).first()

    ctx = _base_context('settings', request)
    ctx.update({
        'sub_tab': 'role',
        'project': project,
        'members': members,
        'role_choices': TeamMember.ROLE_CHOICES,
        'current_leader': current_leader,
    })
    return render(request, 'core/project_settings_role.html', ctx)


@require_POST
@login_required
def delete_member(request, member_id):
    member = get_object_or_404(TeamMember, id=member_id)
    member.delete()
    return redirect('project_settings_role')


# ── 프로젝트 설정: 스케줄 ───────────────────────────────────────
@login_required
def project_settings_schedule(request):
    project = _get_project_for_user(request)

    year = int(request.GET.get('year', date.today().year))
    month = int(request.GET.get('month', date.today().month))

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_event':
            form = ScheduleEventForm(request.POST)
            if form.is_valid():
                event = form.save(commit=False)
                event.project = project
                event.save()
        elif action == 'delete_event':
            event_id = request.POST.get('event_id')
            ScheduleEvent.objects.filter(id=event_id, project=project).delete()
        return redirect(f'/settings/schedule/?year={year}&month={month}')

    cal = calendar.monthcalendar(year, month)
    events = project.events.filter(date__year=year, date__month=month)
    events_by_day = {}
    for e in events:
        events_by_day.setdefault(e.date.day, []).append(e)

    weeks = []
    for week in cal:
        week_days = []
        for day in week:
            week_days.append({
                'day': day,
                'events': events_by_day.get(day, []) if day != 0 else [],
                'is_today': (day != 0 and date(year, month, day) == date.today()),
                'is_sunday': False,
                'is_saturday': False,
            })
        week_days[0]['is_sunday'] = True
        week_days[6]['is_saturday'] = True
        weeks.append(week_days)

    prev_year, prev_month = (year, month - 1) if month > 1 else (year - 1, 12)
    next_year, next_month = (year, month + 1) if month < 12 else (year + 1, 1)

    ctx = _base_context('settings', request)
    ctx.update({
        'sub_tab': 'schedule',
        'project': project,
        'year': year,
        'month': month,
        'weeks': weeks,
        'form': ScheduleEventForm(),
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'all_events': project.events.all(),
    })
    return render(request, 'core/project_settings_schedule.html', ctx)
