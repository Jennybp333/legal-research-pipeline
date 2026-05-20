"""Stage 3: parallel drafting for internal vs. external audiences.

Two writer calls run concurrently. Both consume the same `verified_claims.md`,
but each is paired with a different tone guide:
  - internal_memo.md     — concise, conclusion-first
  - external_opinion.md  — formal, polite, expanded

Sonnet-4.6 is used here (faster + cheaper, plenty of capability for drafting),
in contrast to Opus-4.7 in Stages 1–2 where reasoning matters more.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from lib import claude_client, prompt_loader


def _build_writer_prompt(audience: str, tone_guide: str, verified_claims: str, case_input: str) -> str:
    return f"""당신은 법률 문서를 작성하는 writer입니다.
아래 검증된 자료(verified_claims.md)만 사용해 **{audience}** 산출물을 작성하세요.

## 톤 가이드 (반드시 준수)
{tone_guide}

## 케이스 (참고용 — 사실관계 확인)
{case_input}

## 검증된 자료 (출처)
{verified_claims}

## 작성 규칙
1. **검증된 자료에 없는 주장 사용 금지** — Critic 노트의 누락된 반대 논거는 "추가 검토 필요" 섹션에 별도 표시.
2. **모든 법률 결론에 출처 인용** — `(대법원 2020. 3. 26. 선고 2019다12345 판결)` 형식.
3. **사실관계 변경 금지** — input.md의 사실만 사용.
4. **변호사 검수 필요** 면책 문구를 마지막에 포함.

## 절대 하지 말 것
- 출처 없는 법률 단정
- 사실관계 추가/변경
- 의뢰자에 대한 가정 (input.md에 없는 동기·의도 추측)

지금 바로 Markdown으로 문서를 작성하세요. 메타 설명 없이 본문만."""


async def _run_one_writer(
    audience: str,
    tone_guide_path: str,
    verified_claims: str,
    case_input: str,
    out_path: Path,
) -> Path:
    tone_guide = prompt_loader.load(tone_guide_path)
    prompt = _build_writer_prompt(audience, tone_guide, verified_claims, case_input)
    # Cache the tone guide on the system side — it's stable across all cases.
    system = f"법률 문서를 {audience} 톤에 맞게 작성하세요.\n\n톤 가이드:\n{tone_guide}"
    result = await claude_client.call(
        system=system,
        user=prompt,
        model=claude_client.WRITER_MODEL,
        max_tokens=16000,
        effort="medium",
    )
    out_path.write_text(result, encoding="utf-8")
    return out_path


async def run(case_dir: Path) -> tuple[Path, Path]:
    verified_claims = (case_dir / "verified_claims.md").read_text(encoding="utf-8")
    case_input = (case_dir / "input.md").read_text(encoding="utf-8")

    output_dir = case_dir / "output"
    output_dir.mkdir(exist_ok=True)

    print("[stage3] Running internal + external writers in parallel...")
    internal_task = _run_one_writer(
        "사내용 (내부 법률팀 메모)",
        "config/tone_guide_internal.md",
        verified_claims,
        case_input,
        output_dir / "internal_memo.md",
    )
    external_task = _run_one_writer(
        "외부용 (클라이언트 의견서)",
        "config/tone_guide_external.md",
        verified_claims,
        case_input,
        output_dir / "external_opinion.md",
    )
    internal_path, external_path = await asyncio.gather(internal_task, external_task)
    print(f"[stage3]   wrote {internal_path.relative_to(case_dir)}")
    print(f"[stage3]   wrote {external_path.relative_to(case_dir)}")
    return internal_path, external_path
