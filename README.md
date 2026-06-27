# paper-read

여러 논문을 블로그 글처럼 모아 읽는 Next.js 앱. 홈(`/`)에서 논문 목록을 보고 **제목을 클릭하면** 해당 논문(`/paper/<slug>`)을 펼쳐 읽습니다. 읽는 중 우하단의 메모 아이콘을 누르면 메모장이 열리고, **저장 버튼 없이 자동 저장**됩니다 (아이폰 메모장처럼). 메모는 **논문별로 따로** 저장되고, 저장소는 Vercel Postgres(Neon)입니다.

본문은 **Marker(OCR)** 로 PDF를 변환해 **선택가능한 텍스트 + LaTeX 수식(KaTeX 렌더)** 으로 보여주고, figure는 추출 이미지로 **+Zoom** 확대, 표는 선택가능한 HTML 표(셀 안 수식도 렌더)로 보여줍니다.

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

원문 논문은 **Marker(OCR) → `marker_to_json`** 2단계로 들어갑니다. Marker는 GPU에서 빠르고(Mac MPS는 느림), 변환 결과(`marker_out/<slug>/<slug>.md` + 이미지)를 앱 JSON으로 바꾸는 건 로컬에서 합니다.

**A. 변환 (PDF → markdown+LaTeX)** — 셋 중 택1

- **RunPod GPU (가장 빠름, 권장)**: PDF를 pod `/workspace/pdfs/`에 올리고 `scripts/runpod_convert.sh` 실행 → `/workspace/marker_out/` 결과를 로컬로 내려받기. (RTX 4090에서 4편 ~5분)
- **Colab 무료 GPU**: `Marker_Colab.ipynb`를 Colab에서 열어 셀 실행 (드라이브에 PDF 넣고 → 결과 zip 다운로드).
- **로컬 Mac (느림)**: `python3 scripts/build_papers.py` — `sources/`의 새 PDF를 자동으로 Marker 변환 + 통합. 한두 편 가끔 추가할 때만 권장.

**B. 통합 (markdown → 앱)**

```bash
python3 scripts/marker_to_json.py marker_out/<slug> <slug>
```

front matter(제목/저자/소속)는 건너뛰고 초록·키워드·섹션·수식·표·그림을 `data/papers/<slug>.json`에 넣고, 이미지는 `public/figures/<slug>/`로 복사, `data/papers.index.ts`를 갱신합니다. 메타데이터(제목/저자/연도)는 기존 JSON에서 가져오며 `--title/--authors/--venue/--year`로 덮어쓸 수 있어요.

**참고자료(매뉴얼·코드)** 는 변환하지 않고 PDF 링크 카드로만 둡니다 (`kind:"pdf"`):

```bash
python scripts/extract.py "sources/<파일>.pdf" <slug> --link-only \
    --title "표시할 제목" --venue "CRAN package manual"
```

변환 후 `git push` 하면 연동된 Vercel이 자동 배포합니다.

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
  Math.tsx              KaTeX 렌더 (인라인/디스플레이 수식, 표 안 수식 auto-render)
data/
  papers/<slug>.json    논문 본문(텍스트+수식 LaTeX) + 그림/표 배치
  papers.index.ts       논문 목록 인덱스 (스크립트가 생성)
public/figures/<slug>/  논문별 추출 이미지
scripts/
  marker_to_json.py     Marker 마크다운 → papers/<slug>.json + figures
  runpod_convert.sh     RunPod(GPU)에서 Marker 일괄 변환
  build_papers.py       로컬 Marker 변환 + 통합 (sources/ 새 PDF 자동)
  extract.py            (구) PyMuPDF 추출기 — 참고자료 --link-only 등록에 사용
Marker_Colab.ipynb      무료 Colab GPU 변환 노트북
sources/                변환 대기 PDF (드롭존)
```
