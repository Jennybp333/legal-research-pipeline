# Stage 1: 법률 케이스 리서치 — Document-Specialist 프롬프트 템플릿

이 템플릿은 `oh-my-claudecode:document-specialist` 에이전트를 **병렬**로 호출할 때 사용합니다.
세 에이전트는 동일한 인풋(케이스)을 보지만, **담당 범위(SCOPE)**가 다릅니다.

---

## 1. 호출 방법 (메인 Claude에서)

세 에이전트를 **한 메시지에서 동시에** 호출하세요 (병렬). 순차 호출 금지.

```
Task(subagent_type="oh-my-claudecode:document-specialist",
     description="대법원 판례 리서치",
     prompt=<<< 아래 §3 템플릿에 SCOPE=supreme_court 채워 전달 >>>)

Task(subagent_type="oh-my-claudecode:document-specialist",
     description="하급심 판례 리서치",
     prompt=<<< SCOPE=lower_court >>>)

Task(subagent_type="oh-my-claudecode:document-specialist",
     description="학설·주석서 리서치",
     prompt=<<< SCOPE=doctrine >>>)
```

세 호출은 같은 어시스턴트 턴에서 한 번에 보내야 병렬로 실행됩니다.

---

## 2. SCOPE 정의

| SCOPE_ID | 담당 범위 |
|---|---|
| `supreme_court` | 대법원 판례 (가능하면 최근 10년 우선) |
| `lower_court` | 고등법원·지방법원 등 하급심 판례 |
| `doctrine` | 단행본·주석서·학술논문 |

새 SCOPE 추가 시 케이스 성격에 맞게 조정 (예: `constitutional_court`, `foreign_precedent`).

---

## 3. 프롬프트 템플릿 (각 에이전트에 전달)

다음 블록을 그대로 복사해서 `{{...}}` 자리만 채워 전달하세요.

```text
당신은 한국 법률 리서치를 보조하는 document-specialist입니다.
아래 케이스에 대해 **{{SCOPE}}** 범위만 조사하세요.

## 케이스
{{cases/<case-id>/input.md 전문을 여기 붙여넣기}}

## 담당 범위 (엄격)
- SCOPE: {{SCOPE}} (예: "대법원 판례 (2014년 이후 우선)")
- 이 범위 밖의 자료는 조사 금지 — 다른 에이전트가 담당합니다.
- 중복 회피를 위해 자신의 SCOPE 안에서만 결론을 도출하세요.

## 인용 정책 (필수 — 위반 시 그 주장은 출력 금지)
`config/citation_policy.md`의 규칙을 그대로 따르세요. 핵심:

1. 모든 주장은 **출처 + 원문 인용**과 1:1 (3요소 세트)
2. 원문 인용 없는 주장은 출력하지 않음 ("~로 알려져 있다" 금지)
3. URL 불확실 시 `URL_UNVERIFIED` 표시
4. 판례 인용 형식: `대법원 2020. 3. 26. 선고 2019다12345 판결`

## 출력 형식 (엄격)

다음 Markdown 구조를 정확히 따르세요:

```markdown
## {{SCOPE}} 리서치 결과

### 1. <쟁점 또는 판례명 한 줄>
- **주장:** <한 문장>
- **출처:** <판례번호 또는 서지정보>
- **URL:** <URL 또는 `URL_UNVERIFIED`>
- **원문:**
  > "출처에서 그대로 옮긴 문장. 생략·요약 금지."
- **본 케이스와의 관련성:** <한두 문장>

### 2. ...
```

## 보고 분량
- 핵심 자료 **5~10건**. 양보다 정확도.
- 관련도 낮은 자료는 생략.
- 같은 쟁점 반복 판례는 가장 권위 있는 1건만.

## 작업 종료 시 (필수)
1. 결과를 다음 파일에 저장:
   `cases/<case-id>/research_notes_{{SCOPE_ID}}.md`
   (SCOPE_ID 예: supreme_court / lower_court / doctrine)
2. 저장한 절대경로를 한 줄로 반환.
3. 추가 설명 금지 — 파일 경로만.

## 절대 하지 말 것
- 본인 SCOPE 밖 자료 인용
- 출처 없이 "통설" "다수설" 같은 일반론 작성
- 케이스 input.md에 적힌 사실관계를 임의 변경
- 법률 결론 단언 ("...해야 한다", "...에 위배된다") — 자료 제시만
```

---

## 4. 메인 Claude의 후처리

세 에이전트가 모두 끝나면 메인 Claude(또는 `executor`)가:

1. 세 파일 읽기: `research_notes_supreme_court.md`, `..._lower_court.md`, `..._doctrine.md`
2. 단일 파일로 병합 → `cases/<case-id>/research_notes.md`
   - SCOPE별 섹션으로 구분
   - 중복 인용 제거 (같은 판례가 두 곳에서 나오면 1건만)
3. Stage 2(`prompts/stage2_verify.md`)로 진행

---

## 5. 자주 발생하는 실패 모드

| 증상 | 대응 |
|---|---|
| 에이전트가 출처 없는 일반론으로 채움 | 프롬프트의 §"인용 정책" 부분을 더 강조해서 재호출 |
| 같은 판례가 세 에이전트에 모두 등장 | SCOPE 정의를 명확히 (예: "supreme_court는 헌재 결정 제외") |
| `URL_UNVERIFIED`가 80% 이상 | 도메인에 맞는 1차 소스(국가법령정보센터, 법원도서관 등)를 프롬프트에 명시 |
| 5건도 못 찾음 | SCOPE 범위를 넓히거나(연도 확장), 케이스 input.md의 쟁점이 너무 추상적인지 점검 |
