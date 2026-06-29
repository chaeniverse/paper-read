# Brier · Calibration · C-index 비교: Austin ICI 논문 vs 스트로크 원고/보충자료

비교 대상
- **Austin 2020**: *Graphical calibration curves and the integrated calibration index (ICI) for survival models* (Stat Med 2020;39:2714–2742)
- **스트로크 연구**: `[2026-06-05] Manuscript Ischemic stroke.docx`, `[2026-06-13] Supplementary Ischemic stroke.docx`

> **결론 한 줄**: Austin 논문은 사실상 **calibration(ICI) 전용 논문**이라 Brier·c-index는 거기 등장하지 않는다. 스트로크 연구는 세 지표를 각각 **다른 출처·다른 통계 틀(경쟁위험 버전)**에서 가져왔다. 공통인 calibration도 적용 세팅이 다르다.

---

## 1. 각 지표의 출처가 다름

스트로크 manuscript(line 53) / supplementary(line 202–204)에서 세 지표는 서로 다른 논문을 인용한다.

| 지표 | 스트로크 논문에서의 정의 | 인용 출처 |
|---|---|---|
| **Discrimination (C-index)** | 경쟁위험용 time-dependent concordance index | **Wolbers 2014** (ref 34) |
| **Overall accuracy (Brier)** | 경쟁위험/중도절단 보정 integrated Brier score | **Graf 1999** (ref 35) |
| **Calibration (ICI)** | 예측 vs 관찰 누적발생률 비교, graphical calibration curve + ICI | **Austin 2020** (ref 36/38) |

- Austin 2020이 담당하는 건 **calibration 한 가지뿐**이다. 제목 그대로 ICI·E50·E90·Emax 같은 **보정 지표**만 다룬다.
- **Brier score, c-index는 Austin 논문에 정의되어 있지 않다.** 따라서 "Austin의 Brier/c-index vs 스트로크의 Brier/c-index" 비교 자체가 성립하지 않으며, 스트로크 연구가 그 둘은 다른 논문에서 별도로 가져온 것이다.

---

## 2. 공통 비교 가능한 건 "calibration" 하나 — 그것도 틀이 다름

| | Austin 2020 | 스트로크 연구 |
|---|---|---|
| 통계 틀 | **표준 생존분석 (standard survival)** | **경쟁위험 (competing risks)** |
| 예측치 | 시점 t₀까지 **생존확률** F(t₀\|X) (Cox PH, RSF) | Fine–Gray 모형의 **누적발생함수(CIF)** |
| 관찰치 | **Kaplan–Meier / hazard regression** 평활화 | **Aalen–Johansen estimator** (Figure S3 캡션 명시) |
| 사망 처리 | 경쟁위험으로 보지 않음 (사망=관심사건 또는 단순 중도절단) | **사망을 경쟁사건으로 명시 처리** |

→ Austin의 ICI 아이디어(예측−관찰 차이의 가중 평균 절대값)는 그대로 쓰되, KM/생존확률 대신 **CIF/Aalen–Johansen으로 바꿔** 경쟁위험에 맞게 변형했다.

---

## 3. ⚠️ Table S7의 "Calibration"은 ICI가 아니라 calibration slope

내부검증 표(Table S7) 보고값:

```
Traumatic SDH      Calibration  apparent 1.00000 → optimism-corrected 0.99333
Non-traumatic SDH  Calibration  apparent 1.00000 → optimism-corrected 0.98906
```

- 이상치 = **1.0** → 이것은 **calibration slope(보정 기울기)**다.
- **ICI는 "절대오차"**라서 완벽할 때 **0**에 가까운 값이며 1.00000이 될 수 없다.
- 즉 방법론 본문은 calibration을 Austin식 **ICI(=0이 이상적)**로 설명하지만, Table S7의 "Calibration" 칸은 **slope(=1이 이상적)**로, 같은 단어를 다른 양에 쓰고 있다.
- **권고**: 표 각주에 그 값이 ICI인지 calibration slope인지 명시해 혼동을 방지.

---

## 4. 왜 이렇게 다른가 (근본 이유)

**고령 뇌졸중 환자에서 SDH 발생 전 사망이 매우 흔하기 때문** — 사망이 강한 경쟁위험이다.

- 표준 생존분석(Austin 기본 틀)처럼 사망을 단순 중도절단으로 처리하면 → 1−KM이 SDH 위험을 **과대추정**한다.
- 따라서 discrimination(c-index), accuracy(Brier), calibration **세 지표 모두 경쟁위험 버전**이 필요했고, 각 지표마다 그 버전을 제공하는 다른 방법론 논문(Wolbers / Graf / Austin)을 인용했다.

---

## 5. 지표 해석 방향 (서로 다른 것을 측정)

| 지표 | 측정 대상 | 이상값 | 방향 |
|---|---|---|---|
| **C-index** | 순위 구별력 (discrimination) | 1.0 (0.5=무작위) | 높을수록 좋음 |
| **Brier score** | 전반적 정확도 (구별력+보정 결합) | 0 | 낮을수록 좋음 |
| **Calibration (ICI)** | 예측확률의 크기 정확성 (보정) | 0 | 낮을수록 좋음 |
| **Calibration slope** | 예측의 기울기 보정 | 1.0 | 1에 가까울수록 좋음 |

스트로크 Table S7 실제값 참고:

| Outcome | Brier (apparent→corrected) | C-index | Calibration(slope) |
|---|---|---|---|
| Traumatic SDH | 0.01159 → 0.01155 | 0.63858 → 0.63785 | 1.00000 → 0.99333 |
| Non-traumatic SDH | 0.00278 → 0.00277 | 0.65767 → 0.65653 | 1.00000 → 0.98906 |

(Brier가 매우 낮은 것은 사건이 드물기 때문이며, 절댓값만으로 우수성을 해석하면 안 됨.)

---

## 요약

1. Austin 논문은 **calibration(ICI) 전용** → 스트로크의 Brier·c-index와는 출처·정의가 애초에 다르다(Graf·Wolbers 차용).
2. 공통인 calibration도 Austin은 **표준 생존(KM/생존확률)**, 스트로크는 **경쟁위험(CIF/Aalen–Johansen)**으로 변형 적용.
3. 차이의 근본 이유는 **사망이라는 경쟁위험**.
4. Table S7의 "Calibration"은 ICI가 아니라 **calibration slope**이므로 용어 정리가 필요.
