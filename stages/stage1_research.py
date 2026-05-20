"""Stage 1: parallel legal research.

Fans out three async calls to Claude — one per SCOPE (supreme_court / lower_court /
doctrine) — using the prompt template in `prompts/stage1_research.md`. Each call has
web search enabled so it can find real citations. Results are written to per-SCOPE
files and then merged into `research_notes.md`.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from lib import claude_client, prompt_loader

SCOPES: list[tuple[str, str]] = [
    ("supreme_court", "대법원 판례 (2014년 이후 우선)"),
    ("lower_court", "고등법원·지방법원 등 하급심 판례"),
    ("doctrine", "단행본·주석서·학술논문"),
]


def _build_prompt(scope_id: str, scope_desc: str, case_input: str, citation_policy: str) -> str:
    """Construct the per-agent prompt by inlining the template guidance directly.

    We don't reuse the human-facing `prompts/stage1_research.md` verbatim because that
    file is structured as a tutorial for a human invoking OMC agents. The runtime
    prompt below distills its instructions for direct SDK use.
    """
    return f"""당신은 한국 법률 리서치를 보조하는 document-specialist입니다.
아래 케이스에 대해 **{scope_desc}** 범위만 조사하세요.

## 케이스
{case_input}

## 담당 범위 (엄격)
- SCOPE: {scope_desc}
- 이 범위 밖의 자료는 조사 금지 — 다른 에이전트가 담당합니다.
- 중복 회피를 위해 자신의 SCOPE 안에서만 결론을 도출하세요.

## 인용 정책 (필수 — 위반 시 그 주장은 출력 금지)
{citation_policy}

## 도구 사용
- web_search 도구를 적극적으로 사용해 실제 출처를 찾으세요.
- 검색 결과로 본문 인용이 충분치 않으면 web_fetch로 원문 확인.

## 출력 형식 (엄격)

다음 Markdown 구조를 정확히 따르세요:

```markdown
## {scope_desc} 리서치 결과

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

## 절대 하지 말 것
- 본인 SCOPE 밖 자료 인용
- 출처 없이 "통설" "다수설" 같은 일반론 작성
- 케이스 input.md에 적힌 사실관계를 임의 변경
- 법률 결론 단언 ("...해야 한다", "...에 위배된다") — 자료 제시만

위 형식의 Markdown만 출력하세요. 다른 설명은 금지."""


async def _run_one_scope(scope_id: str, scope_desc: str, case_dir: Path, case_input: str, citation_policy: str) -> Path:
    prompt = _build_prompt(scope_id, scope_desc, case_input, citation_policy)
    # `system` carries the case + policy (stable across attempts for caching);
    # `user` is the short instruction. Cache hits will land on the system block.
    system = f"케이스 자료와 인용 정책을 참조해 한국 법률 리서치를 수행하세요.\n\n인용 정책:\n{citation_policy}"
    result = await claude_client.call(
        system=system,
        user=prompt,
        tools=[claude_client.WEB_SEARCH_TOOL, claude_client.WEB_FETCH_TOOL],
        max_tokens=16000,
        effort="high",
    )
    out_path = case_dir / f"research_notes_{scope_id}.md"
    out_path.write_text(result, encoding="utf-8")
    return out_path


def _merge(case_dir: Path, scope_files: list[Path]) -> Path:
    merged_path = case_dir / "research_notes.md"
    parts: list[str] = ["# 리서치 노트 (Stage 1 통합)\n"]
    for path in scope_files:
        parts.append(f"\n<!-- source: {path.name} -->\n")
        parts.append(path.read_text(encoding="utf-8"))
    merged_path.write_text("\n".join(parts), encoding="utf-8")
    return merged_path


async def run(case_dir: Path) -> Path:
    """Execute Stage 1 for the given case directory. Returns the merged notes path."""
    case_input = (case_dir / "input.md").read_text(encoding="utf-8")
    citation_policy = prompt_loader.load("config/citation_policy.md")

    print(f"[stage1] Running {len(SCOPES)} document specialists in parallel...")
    tasks = [
        _run_one_scope(scope_id, scope_desc, case_dir, case_input, citation_policy)
        for scope_id, scope_desc in SCOPES
    ]
    scope_files = await asyncio.gather(*tasks)
    for path in scope_files:
        print(f"[stage1]   wrote {path.name}")

    merged = _merge(case_dir, scope_files)
    print(f"[stage1] Merged into {merged.name}")
    return merged
