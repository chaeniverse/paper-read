# paper-read

논문을 웹에서 읽으면서 바로 메모하는 Next.js 앱. 우하단의 메모 아이콘을 누르면 메모장이 열리고, **저장 버튼 없이 자동 저장**됩니다 (아이폰 메모장처럼). 메모는 Vercel Postgres(Neon)에 저장됩니다.

본문 텍스트는 `sources/`의 PDF에서 추출했고, figure·table은 고해상도 이미지로 렌더링해 각각 **+Zoom** 버튼으로 확대할 수 있습니다.

## 로컬 실행

```bash
npm install
npm run dev        # http://localhost:3000
```

메모를 저장하려면 데이터베이스 연결 문자열이 필요합니다 (`.env.local`):

```
DATABASE_URL=postgres://...   # Neon/Vercel Postgres connection string
```

DB가 없어도 논문 읽기·확대는 그대로 동작하고, 메모 저장만 비활성화됩니다.

## Vercel 배포

1. 이 폴더를 GitHub에 push 한 뒤 [Vercel](https://vercel.com/new)에서 import.
2. **Storage → Create Database → Postgres (Neon)** 로 DB 생성 후 프로젝트에 연결.
   - 연결하면 `DATABASE_URL`(및 `POSTGRES_URL`) 환경변수가 자동 주입됩니다.
   - 앱은 첫 요청 시 `notes` 테이블을 자동으로 생성하므로 별도 마이그레이션이 필요 없습니다.
3. Deploy. 끝.

## 메모 동작

- 단일 연속 메모 (`notes` 테이블의 `id = 'paper-read-main'` 한 행).
- 입력할 때마다 600ms 디바운스로 자동 저장(`PUT /api/note`), 탭을 닫을 때도 마지막 내용을 flush.
- 헤더의 점 색으로 상태 표시: 노랑=저장 중, 초록=저장됨.
- ✕ 를 누르면 메모장이 다시 아이콘으로 접힙니다.

## 다른 논문 추가하기

본문/그림은 `sources/`의 PDF에서 `scripts/extract.py`로 추출해 `data/paper.json` + `public/figures/`로 만듭니다.

```bash
pip install pymupdf
python scripts/extract.py "sources/<파일>.pdf"
```

캡션 인식(`FIGURE n` 아래 그림 / `TABLE n` 위 표) 기준으로 영역을 잘라 3배 해상도 PNG로 저장하고, 본문에서 처음 언급되는 위치에 자동 삽입합니다.

## 구조

```
app/
  page.tsx          논문 읽기 화면 (data/paper.json 렌더)
  layout.tsx        전역 레이아웃 + 메모 위젯
  api/note/route.ts 메모 GET / PUT (자동 저장)
components/
  Figure.tsx        +Zoom 라이트박스 (휠/드래그 확대·이동)
  NotesWidget.tsx   우하단 플로팅 자동저장 메모
lib/
  db.ts             Neon Postgres 연결 + notes 테이블
  paper.ts          paper.json 타입/로더
data/paper.json     추출된 본문 + 그림/표 배치
public/figures/     figure·table 이미지 (PNG)
scripts/extract.py  PDF → paper.json + figures 추출기
sources/            원본 PDF
```
