# paper-read

여러 논문을 블로그 글처럼 모아 읽는 Next.js 앱. 홈(`/`)에서 논문 목록을 보고 **제목을 클릭하면** 해당 논문(`/paper/<slug>`)을 펼쳐 읽습니다. 읽는 중 우하단의 메모 아이콘을 누르면 메모장이 열리고, **저장 버튼 없이 자동 저장**됩니다 (아이폰 메모장처럼). 메모는 **논문별로 따로** 저장되고, 저장소는 Vercel Postgres(Neon)입니다.

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

- 논문마다 별도 메모 (`notes` 테이블에서 `id = <논문 slug>` 한 행씩).
- 입력할 때마다 600ms 디바운스로 자동 저장(`PUT /api/note`), 탭을 닫을 때도 마지막 내용을 flush.
- 헤더의 점 색으로 상태 표시: 노랑=저장 중, 초록=저장됨.
- ✕ 를 누르면 메모장이 다시 아이콘으로 접힙니다.

## 논문 추가하기

PDF를 `sources/`에 넣고 추출 스크립트를 돌리면 끝입니다. 두 가지 모드가 있어요.

**① 저널 논문 — 본문까지 재현** (홈 상단 목록에 표시, 읽기 뷰 + 메모)

```bash
pip install pymupdf
python scripts/extract.py "sources/<파일>.pdf" <slug> \
    --title "정확한 제목" --authors "저자1, 저자2" --venue "Journal" --year 2024
```

- 1단·2단 레이아웃을 자동 인식해 읽기 순서대로 본문을 재현(머리말/꼬리말 제거, 90° 회전된 가로 표 페이지는 똑바로 렌더).
- 캡션 기준(`FIGURE n` 아래 그림 / `TABLE n` 위 표)으로 영역을 잘라 3배 해상도 PNG로 `public/figures/<slug>/`에 저장, 본문 첫 언급 위치에 자동 삽입(+Zoom).
- **수식**: 컴파일된 PDF엔 LaTeX 원본이 없어 텍스트로는 깨지므로, 디스플레이 수식 구간을 감지해 이미지(`eqN.png`)로 잘라 본문에 그대로 삽입(클릭 시 확대). 원본과 100% 동일하게 보입니다.
- 제목/저자는 저널마다 형식이 달라 `--title`/`--authors`로 지정하는 걸 권장.

**② 매뉴얼·참고자료 — 목록 + PDF 보기만** (홈 하단 "참고자료" 섹션, 본문 재현 없음)

```bash
python scripts/extract.py "sources/<파일>.pdf" <slug> --link-only \
    --title "표시할 제목" --venue "CRAN package manual"
```

수백 페이지짜리 R 패키지 매뉴얼처럼 본문 재현이 무의미한 문서에 사용. 카드만 만들고 클릭하면 원본 PDF로 바로 엽니다.

두 모드 모두 PDF를 `public/pdfs/<slug>.pdf`로 복사하고 `data/papers/<slug>.json` + `data/papers.index.ts`를 갱신하므로, 다시 빌드/배포하면 홈에 자동으로 나타납니다.

## 구조

```
app/
  page.tsx              홈 — 블로그형 논문 목록
  paper/[slug]/page.tsx 논문 읽기 화면 (+Zoom, 메모 위젯)
  layout.tsx            전역 레이아웃
  api/note/route.ts     메모 GET / PUT (논문별 자동 저장)
components/
  Figure.tsx            +Zoom 라이트박스 (휠/드래그 확대·이동)
  NotesWidget.tsx       우하단 플로팅 자동저장 메모 (논문별)
lib/
  db.ts                 Neon Postgres 연결 + notes 테이블
  paper.ts              논문 타입/로더 (목록·slug 조회)
data/
  papers/<slug>.json    추출된 논문 본문 + 그림/표 배치
  papers.index.ts       논문 목록 인덱스 (스크립트가 생성)
public/figures/<slug>/  논문별 figure·table 이미지 (PNG)
scripts/extract.py      PDF → papers/<slug>.json + figures 추출기
sources/                원본 PDF
```
