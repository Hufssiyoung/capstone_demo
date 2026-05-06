# 종합설계 구현 - 프로젝트 문서

## 개요

**팀프로젝트 자료조사 검증 서비스** — AI 기반 팀 프로젝트 자료 검증 웹앱.  
Django MTV 패턴으로 구현. 가상환경: `myvenv` (Python 3.13.4, Django 6.0.4)

---

## 실행 방법

```bash
source myvenv/Scripts/activate          # 가상환경 활성화 (Windows)
cp .env.example .env                    # 최초 1회: 환경변수 설정
python manage.py migrate                # 최초 1회: DB 마이그레이션
python manage.py runserver              # 개발 서버 → http://127.0.0.1:8000
```

환경변수 (`.env`):

- `SECRET_KEY` — Django 시크릿 키
- `DEBUG` — True/False

---

## 시스템 플로우

```
[Block 1] 회원가입 → 로그인 → 프로젝트 목록
              ├─ 프로젝트 생성 → 초대코드 발급 → 팀원 초대
              └─ 프로젝트 참여 → 초대코드 입력

[Block 2] 자료 제출 → AI 검증 → 팀원 리뷰
              ├─ 드래그 리뷰 작성 → 승인/보류/거절 투표
              └─ 검증 완료 → 자료 보관함 등록

[Block 3] 자료 보관함 관리
              ├─ 리뷰 중 / 검증 완료 / 거절됨 구분
              └─ 내보내기 (추후: 요약/PPT 자동화)
```

---

## 리다이렉트 규칙

- `/` → 로그인 O: `/projects/` / 로그인 X: `/accounts/login/`
- `/accounts/login/` → 이미 로그인 O: `/projects/` (redirect_authenticated_user=True)
- 로그인 완료 후 → `/projects/`
- 회원가입 완료 후 → `/projects/`

---

## 화면 레이아웃

```
┌──────────────────────────────────────────────────────┐
│  프로젝트명 ∨                          사용자명 ∨      │  ← 최상단 헤더
├──────────────────────────────────────────────────────┤
│  자료 검증  자료 보관함  팀 관리  내보내기              │  ← 메인 탭 (4개, 좌측 정렬)
├──────────────────────────────────────────────────────┤
│  (서브탭: 프로젝트 개요 / 역할 분담 / 일정 관리)      │  ← 팀 관리 탭만 (가운데 정렬)
└──────────────────────────────────────────────────────┘
```

---

## 탭 구조

| 순서 | 탭            | URL                | 상태                  |
| ---- | ------------- | ------------------ | --------------------- |
| 0    | 프로젝트 목록 | `/projects/`       | 구현됨 (메인 탭 외부) |
| 1    | 자료 검증     | `/review/`         | 구현됨                |
| 2    | 자료 보관함   | `/archive/`        | 구현됨                |
| 3    | 팀 관리       | `/settings/topic/` | 구현됨                |
| 4    | 내보내기      | `/export/`         | UI만                  |

### 팀 관리 서브탭

| 서브탭        | URL                   | 기능                                                               |
| ------------- | --------------------- | ------------------------------------------------------------------ |
| 프로젝트 개요 | `/settings/topic/`    | 프로젝트 이름·주제·상세설명 인라인 수정, 참고자료(PDF) 업로드/삭제 |
| 역할 분담     | `/settings/role/`     | 팀원 역할 변경                                                     |
| 일정 관리     | `/settings/schedule/` | 월별 달력, 일정 추가/삭제                                          |

---

## 자료 검증 상세 (`/review/`)

3패널 레이아웃 (`1.5fr 3fr 1.5fr`):

**왼쪽 사이드바**

- 자료 제출하기 버튼 → 중앙 편집창 이동
- 제출 폼: 제목 + 줄 글 + PDF 첨부 (선택)
- 현재 자료 목록: 전체 상태(리뷰중/검증완료/거절됨) 표시

**가운데 뷰어**

- 자료 미선택: 줄 글 입력 에디터
- 자료 선택: 제목·메타·본문 표시, AI/팀원 하이라이트 표시
- 상단: 상태 뱃지 + 자료명 + "리뷰 남기기" 버튼

**오른쪽 패널 (3탭)**

- `AI 리뷰`: AI가 분석한 리뷰 카드 (해당내용·문제점·제안), 클릭 시 텍스트 하이라이트 연동
- `팀원 리뷰`: 본인 제외 팀원 리뷰, 리뷰어별 토글 아코디언
- `리뷰 남기기`: 드래그→자동 채움, 내 리뷰 목록, 승인/보류/거절 투표

하이라이트 규칙:

- AI 리뷰 탭: AI 하이라이트(노랑)만 표시
- 팀원 리뷰 탭: 리뷰어 토글 열 때 해당 팀원 하이라이트(파랑)만 표시
- 다른 탭: 하이라이트 없음

---

## 자료 보관함 (`/archive/`)

세 섹션으로 구분:

- **리뷰 중** (노란 뱃지): 검증/거절 버튼 + 삭제
- **검증 완료** (초록 뱃지): 다운로드(PDF) + 삭제
- **거절됨** (빨간 뱃지): 삭제
- 자료명 클릭 → `/review/?doc=id`로 이동

---

## 디렉토리 구조

```
종합설계 구현/
├── config/
│   ├── settings.py          # .env 기반 설정 (python-dotenv)
│   └── urls.py
├── core/
│   ├── models.py            # 전체 모델
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   ├── admin.py
│   └── management/commands/seed.py
├── templates/
│   ├── base.html
│   ├── registration/
│   │   ├── login.html
│   │   └── signup.html
│   └── core/
│       ├── review.html
│       ├── archive.html
│       ├── export.html
│       ├── project_list.html
│       ├── project_settings_topic.html
│       ├── project_settings_role.html
│       └── project_settings_schedule.html
├── static/
│   ├── css/main.css
│   └── js/main.js
├── media/                   # gitignore
├── .env                     # gitignore
├── .env.example
├── .gitignore
├── README.md
└── manage.py
```

---

## 모델

| 모델               | 주요 필드                                                                                                                |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| `Project`          | name, join_code(6자리), members(M2M→User), title, description, created_at, updated_at                                    |
| `ProjectFile`      | project(FK), file, original_name, file_size, content, topic, status(pending/verified/rejected), uploaded_by, uploaded_at |
| `ProjectReference` | project(FK), file(PDF), original_name, file_size, uploaded_by, uploaded_at — 팀 관리 참고자료 전용                       |
| `FileReviewItem`   | project_file(FK), highlighted_text, problem, suggestion, order — AI 리뷰                                                 |
| `TeamReviewItem`   | project_file(FK), reviewer(FK), highlighted_text, problem, suggestion, created_at — 팀원 드래그 리뷰                     |
| `TeamReview`       | project_file(FK), reviewer(FK), vote(approve/reject/hold), comment, created_at, updated_at — unique_together 제약        |
| `TeamMember`       | project(FK), user(FK), name, role, order — related_name: members_info                                                    |
| `ScheduleEvent`    | project(FK), title, date                                                                                                 |

> `Project.members` (M2M) ↔ User.projects (related_name)
> `TeamMember` (역할 정보) ↔ project.members_info (related_name)

모델 메서드:

- `ProjectFile.ext()` — 파일 확장자 반환
- `ProjectFile.size_display()` / `ProjectReference.size_display()` — 파일 크기 포맷 (KB/MB)
- `TeamMember.avatar_char()` — 아바타용 이름 첫 글자 반환

---

## 주요 URL

| name                        | URL                             | 설명                         |
| --------------------------- | ------------------------------- | ---------------------------- |
| `login`                     | `/accounts/login/`              | 로그인                       |
| `logout`                    | `/accounts/logout/`             | 로그아웃 (POST)              |
| `signup`                    | `/accounts/signup/`             | 회원가입                     |
| `project_list`              | `/projects/`                    | 프로젝트 목록·생성·삭제·입장 |
| `review`                    | `/review/`                      | 자료 검증                    |
| `archive`                   | `/archive/`                     | 자료 보관함                  |
| `export`                    | `/export/`                      | 내보내기                     |
| `project_settings_topic`    | `/settings/topic/`              | 프로젝트 개요 설정           |
| `project_settings_role`     | `/settings/role/`               | 역할 분담                    |
| `project_settings_schedule` | `/settings/schedule/`           | 스케줄                       |
| `delete_file`               | `/settings/file/<id>/delete/`   | 참고자료 삭제                |
| `delete_member`             | `/settings/member/<id>/delete/` | 팀원 삭제                    |

---

## 설계 기준

- **인증** — Django 기본 auth (회원가입/로그인/로그아웃)
- **환경변수** — python-dotenv, `.env` 파일 (gitignore)
- **프로젝트 연결** — 유저의 첫 번째 프로젝트 (`user.projects.first()`)
- **프로젝트 없을 때** — id=1 임시 프로젝트 fallback (목록에는 미노출)
- **파일 업로드** — PDF만 허용 (자료검증, 팀관리 참고자료 모두)
- **DB** — SQLite (`db.sqlite3`, gitignore)
- **미디어** — `MEDIA_ROOT = media/` (gitignore)
- **언어/시간대** — `ko-kr` / `Asia/Seoul`

---

## 구현 현황 (2026-05-06 기준)

| 항목        | 상태         | 비고                              |
| ----------- | ------------ | --------------------------------- |
| 모델        | ✅ 완전 구현 | 8개 모델 전체                     |
| 뷰/URL      | ✅ 완전 구현 | 10개 뷰 전체                      |
| 템플릿      | ✅ 완전 구현 | 11개 파일                         |
| CSS         | ✅ 완전 구현 | main.css (~2968줄)                |
| JS          | ⚠️ 부분      | main.js 12줄 + 템플릿 인라인 위주 |
| 인증        | ✅ 완전 구현 | signup/login/logout               |
| 자료 검증   | ✅ 완전 구현 | 3패널, 드래그 리뷰, 투표          |
| 자료 보관함 | ✅ 완전 구현 | 상태별 3섹션                      |
| 팀 관리     | ✅ 완전 구현 | 프로젝트 개요, 역할, 일정         |
| AI 연동     | ❌ 미구현    | `FileReviewItem` 수동 입력만 가능 |
| 내보내기    | ⚠️ UI만      | export.html 뼈대만 존재           |

---

## 미구현 (추후 작업)

### 핵심 기능

- [ ] **AI 연동** — 자료 제출 시 LLM 호출 → `FileReviewItem` 자동 생성 (API 키 관리, 프롬프트 설계, 비동기 처리)
- [x] **최종 승인 처리** — 자료 검증 탭에서 팀장이 최종 검증 완료/거절 처리 (팀장 역할 추가, review.html 헤더 버튼)
- [x] **자료 수정 및 재 재출** - 거절된 자료의 경우 제출자가 수정 및 재 재출 가능

### 보조 기능

- [x] **팀장 역할 추가** — `TeamMember.ROLE_CHOICES`에 추가, 역할 분담 탭에서 지정 가능
- [x] **프로젝트 전환** — 헤더 드롭다운 프로젝트 전환 미동작 (현재 `user.projects.first()` 고정)

### 데모 준비

- [ ] **Seed 데이터** — `management/commands/seed.py` 내용 확인 및 완성
- [ ] **AI 리뷰 더미 데이터** — AI 연동 전 시연용 `FileReviewItem` 수동 입력

### MVP에 미반영

- [ ] **3일 자동 삭제** — pending 자료 타임아웃 (Django cron 또는 Celery 필요)
- [ ] **내보내기 기능**
