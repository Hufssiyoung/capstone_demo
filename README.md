# 팀프로젝트 자료조사 검증 서비스

AI 기반 팀 프로젝트 자료 검증 웹 서비스입니다.  
팀원이 제출한 자료를 AI가 분석하고, 팀원들이 함께 리뷰·투표하여 자료의 신뢰성을 검증합니다.

---

## 기술 스택

- **Backend** : Python 3.13, Django 6.0.4
- **Frontend** : Django Template, Vanilla JS, CSS
- **DB** : SQLite
- **Auth** : Django 기본 인증

---

## 로컬 실행

### 1. 가상환경 활성화

```bash
python -m venv myvenv

# Windows
source myvenv/Scripts/activate

# Mac/Linux
source myvenv/bin/activate
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정

```bash
cp .env.example .env
# .env 파일을 열어 SECRET_KEY 등을 설정
```

### 4. DB 마이그레이션

```bash
python manage.py migrate
```

### 5. 개발 서버 실행

```bash
python manage.py runserver
# → http://127.0.0.1:8000
```

### 6. 더미 데이터 생성 (선택)

```bash
python manage.py seed
```

기존 데이터를 초기화하고 테스트용 더미 데이터를 생성합니다.

| 항목      | 내용                                                          |
| --------- | ------------------------------------------------------------- |
| 프로젝트  | AI 강의 추천 팀 (초대코드: `247813`)                          |
| 계정      | `minjun` / `seoyeon` / `jiho` / `yuna` (비밀번호: `test1234`) |
| 역할      | PM / 프론트 / 백엔드 / AI                                     |
| 자료      | 4건 (pending 2, verified 1, rejected 1)                       |
| AI 리뷰   | 자료별 2~3개 (문제점·제안 포함)                               |
| 팀원 리뷰 | 드래그 리뷰 항목 + 승인/보류/거절 투표 혼합                   |
| 일정      | 6건 (킥오프 ~ 최종 발표, 과거·미래 분산)                      |

---

## 디렉토리 구조

```
종합설계 구현/
├── config/
│   ├── settings.py          # 환경변수(.env) 기반 설정
│   └── urls.py
├── core/
│   ├── models.py            # 전체 모델 정의
│   ├── views.py             # 뷰 함수
│   ├── urls.py
│   ├── forms.py
│   ├── admin.py
│   └── management/
│       └── commands/
│           └── seed.py      # 더미 데이터 생성 커맨드
├── templates/
│   ├── base.html                          # 공통 레이아웃 (헤더 + 메인 탭)
│   ├── registration/                      # 로그인 / 회원가입
│   └── core/
│       ├── review.html                    # 자료 검증 (3패널 레이아웃)
│       ├── archive.html                   # 자료 보관함
│       ├── export.html                    # 내보내기
│       ├── project_list.html              # 프로젝트 목록·생성·입장
│       ├── project_settings_topic.html    # 프로젝트 관리 > 프로젝트 개요
│       ├── project_settings_role.html     # 프로젝트 관리 > 역할 분담
│       └── project_settings_schedule.html # 프로젝트 관리 > 일정 관리
├── static/
│   ├── css/main.css
│   └── js/main.js
├── media/                   # 업로드 파일 (gitignore)
├── .env                     # 환경변수 (gitignore)
├── .env.example             # 환경변수 템플릿
├── .gitignore
└── manage.py
```

---

## 주요 URL

| URL                   | 설명                          |
| --------------------- | ----------------------------- |
| `/accounts/signup/`   | 회원가입                      |
| `/accounts/login/`    | 로그인                        |
| `/projects/`          | 모든 프로젝트 목록·생성·입장  |
| `/review/`            | 자료 검증                     |
| `/archive/`           | 자료 보관함                   |
| `/export/`            | 내보내기                      |
| `/settings/topic/`    | 프로젝트 관리 > 프로젝트 개요 |
| `/settings/role/`     | 프로젝트 관리 > 역할 분담     |
| `/settings/schedule/` | 프로젝트 관리 > 일정 관리     |

---

## 주요 기능

### 모든 프로젝트 목록 (`/projects/`)

- 프로젝트 생성 및 6자리 초대코드 자동 발급
- 초대코드로 기존 프로젝트 참여
- 내가 속한 프로젝트 목록 확인 및 삭제

### 자료 검증 (`/review/`)

- 왼쪽 사이드바에서 자료 제출 (줄 글 + PDF 첨부)
- 가운데 뷰어에서 내용 확인 및 텍스트 드래그로 리뷰 작성
- 오른쪽 패널 3탭:
    - **AI 리뷰** — AI가 분석한 문제점·제안 (하이라이트 연동)
    - **팀원 리뷰** — 다른 팀원의 리뷰 목록 (리뷰어별 토글)
    - **리뷰 남기기** — 내 리뷰 작성 + 승인/보류/거절 투표

### 자료 보관함 (`/archive/`)

- 리뷰 중 / 검증 완료 / 거절됨 세 섹션으로 구분
- 자료 제목 클릭 → 자료 검증 뷰어로 이동

### 프로젝트 관리 (`/settings/`)

- 프로젝트 이름·주제·상세설명 인라인 편집, 참고자료(PDF) 업로드
- 역할 분담 설정
- 월별 스케줄 관리

---

## 모델 구조

| 모델               | 설명                                            |
| ------------------ | ----------------------------------------------- |
| `Project`          | 프로젝트 (이름, 6자리 초대코드, 멤버 M2M)       |
| `ProjectFile`      | 검증 자료 (줄글/PDF, pending→verified/rejected) |
| `ProjectReference` | 프로젝트 관리 참고자료 (PDF)                    |
| `FileReviewItem`   | AI 리뷰 항목 (해당내용·문제점·제안)             |
| `TeamReviewItem`   | 팀원 리뷰 항목 (드래그 선택 기반)               |
| `TeamReview`       | 팀원 최종 투표 (승인/보류/거절)                 |
| `TeamMember`       | 역할 분담 정보 (프로젝트별 역할)                |
| `ScheduleEvent`    | 스케줄 일정                                     |

---

## 🖥️ 화면 예시

### 1. 자료 검증 (`/review/`)

**1) 자료 제출**
<img width="1883" height="936" alt="image" src="https://github.com/user-attachments/assets/2e38f20e-d47e-4460-a69d-8ee81cd053ed" />

**2) AI 리뷰**
<img width="1883" height="915" alt="image" src="https://github.com/user-attachments/assets/858b47d6-5551-4594-8bce-d1efbed42481" />

**3) 팀원 리뷰**
<img width="1884" height="937" alt="image" src="https://github.com/user-attachments/assets/f40389b9-58e5-4dd1-84a5-ccf8129ba1f6" />

**4) 내 리뷰**
<img width="1883" height="937" alt="image" src="https://github.com/user-attachments/assets/704f4a96-503e-42ee-b0f7-6cf659f36c6e" />

### 2. 자료 보관함 (`/archive/`)

<img width="1877" height="931" alt="image" src="https://github.com/user-attachments/assets/e7a0e6d5-ecef-4f0c-832b-d13c6b0c399e" />

### 3. 프로젝트 관리 (`/teams/`)

**1) 프로젝트 개요**
<img width="1894" height="938" alt="image" src="https://github.com/user-attachments/assets/50baa7e3-0222-4fac-bc6d-4c17d4fa03f9" />

**2) 팀 관리**
<img width="1887" height="936" alt="image" src="https://github.com/user-attachments/assets/7d40d6fc-0cf8-473e-b9ee-f74a2c7be9ae" />

**3) 일정 관리**
<img width="1876" height="914" alt="image" src="https://github.com/user-attachments/assets/fc68dee0-f3b7-44d1-8ba9-f1b42d7eeebc" />

### 4. 내보내기 (`/export/`)

<img width="1892" height="937" alt="image" src="https://github.com/user-attachments/assets/c89a8447-9bf5-44b2-96bd-ffaec12eda47" />

### 5. 기타

**1) 로그인**
<img width="1897" height="933" alt="image" src="https://github.com/user-attachments/assets/4d19f30c-7d11-4a31-973b-fff9e34f4e21" />

**2) 모든 프로젝트 관리**
<img width="1890" height="933" alt="image" src="https://github.com/user-attachments/assets/5e4910a9-d322-44d3-a1ef-8ed33535a8a4" />
