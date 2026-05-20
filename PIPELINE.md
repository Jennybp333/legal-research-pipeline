# 법률 리서치 파이프라인 (3-Stage)

```
┌──────────────────────────────────────────────────────────────────────┐
│  INPUT                                                                │
│  cases/<case-id>/input.md  (질문 + 사실관계)                          │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  STAGE 1 — 리서치 (병렬 fan-out, 3 agents)                            │
│                                                                       │
│   ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐   │
│   │ document-        │ │ document-        │ │ document-        │   │
│   │ specialist A     │ │ specialist B     │ │ specialist C     │   │
│   │  SCOPE=대법원     │ │  SCOPE=하급심     │ │  SCOPE=학설/주석  │   │
│   └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘   │
│            │                    │                    │              │
│            ▼                    ▼                    ▼              │
│   research_notes_     research_notes_     research_notes_           │
│   supreme_court.md    lower_court.md      doctrine.md               │
│            │                    │                    │              │
│            └──────────┬─────────┴────────────────────┘              │
│                       │  [메인 Claude가 병합]                        │
│                       ▼                                              │
│            cases/<case-id>/research_notes.md                         │
│            (모든 주장에 출처 + 원문 인용)                             │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  STAGE 2 — 팩트 검증 (순차)                                           │
│                                                                       │
│   ┌──────────────┐         ┌──────────────┐                          │
│   │  verifier    │ ──────► │   critic     │                          │
│   │  (출처 대조)  │         │  (논리 검토)  │                          │
│   └──────────────┘         └──────┬───────┘                          │
│                                   ▼                                   │
│                  cases/<case-id>/verified_claims.md                   │
│                  (검증 통과 주장만)                                    │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  STAGE 3 — 작성 (병렬 fan-out, 2 agents, 톤앤매너 분리)               │
│                                                                       │
│   ┌──────────────────────────┐  ┌──────────────────────────┐         │
│   │  writer A (사내용)         │  │  writer B (외부용)        │         │
│   │  + tone_guide_internal   │  │  + tone_guide_external   │         │
│   └────────────┬─────────────┘  └────────────┬─────────────┘         │
│                ▼                              ▼                       │
│   output/internal_memo.md       output/external_opinion.md           │
└──────────────────────────────────────────────────────────────────────┘
```

## 디렉토리 구조

```
legal-research-pipeline/
├── PIPELINE.md                       # 이 파일 (도식)
├── config/
│   ├── citation_policy.md            # 인용 규칙 (Stage 1·2 공통)
│   ├── tone_guide_internal.md        # 사내 톤 (Stage 3-A) — TODO
│   └── tone_guide_external.md        # 외부 톤 (Stage 3-B) — TODO
├── prompts/
│   ├── stage1_research.md            # ✅ 본 PR에 포함
│   ├── stage2_verify.md              # TODO
│   ├── stage2_critic.md              # TODO
│   ├── stage3_internal.md            # TODO
│   └── stage3_external.md            # TODO
└── cases/
    └── _template/                    # 새 케이스 시작 시 복사할 템플릿
        ├── input.md
        └── output/
```

## 핵심 설계 원칙

1. **병렬 vs 순차 분리** — Stage 1·3은 fan-out(병렬), Stage 2는 검증 체인(순차).
2. **인용 강제** — Stage 1 산출물의 모든 주장은 `config/citation_policy.md` 규칙을 통과해야 함.
3. **톤은 파일로 주입** — 에이전트 메모리가 아닌 `config/tone_guide_*.md`를 매번 첨부.
4. **케이스 격리** — `cases/<case-id>/` 안에서만 산출물이 생성·소비되어 케이스 간 오염 없음.
5. **법률 도메인 면책** — 모든 산출물은 변호사 검수가 필요한 초안임.
