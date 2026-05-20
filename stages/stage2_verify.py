"""Stage 2: sequential fact verification.

Two passes:
  1. verifier — for each claim, confirm the cited source supports it.
  2. critic   — look for missing counter-arguments and weak inferences.

The output is `verified_claims.md` — only claims that survived both passes,
ready for Stage 3.
"""

from __future__ import annotations

from pathlib import Path

from lib import claude_client, prompt_loader


VERIFIER_INSTRUCTION = """당신은 법률 리서치 결과의 출처 검증을 담당하는 verifier입니다.
입력으로 받은 research_notes.md의 모든 주장에 대해 다음을 1:1로 검증하세요.

## 검증 항목 (각 주장마다)
1. **출처가 실제로 그 주장을 뒷받침하는가?** 원문 인용이 주장과 일치하는지 확인.
2. **URL이 유효한가?** `URL_UNVERIFIED`로 표시된 출처는 web_fetch로 직접 확인 시도.
3. **인용 정책 준수?** `config/citation_policy.md`의 3요소(주장+출처+원문) 갖춤 여부.

## 출력 형식

다음 구조의 Markdown을 출력:

```markdown
# 검증 결과

## ✅ PASSED (검증 통과)

### 1. <원본 주장>
- **출처:** ...
- **검증 메모:** <왜 통과했는지 한 줄>

### 2. ...

## ❌ FAILED (검증 실패)

### 1. <원본 주장>
- **출처:** ...
- **실패 사유:** <원문이 다른 사실을 말한다 / URL 깨짐 / 인용 누락 / 등>
```

## 절대 하지 말 것
- 검증 없이 통과 표시
- 원본에 없는 새 주장 추가
- 추측성 보강 (없는 사실 채워넣기 금지)

위 Markdown만 출력. 다른 설명 금지."""


CRITIC_INSTRUCTION = """당신은 법률 리서치를 다각도로 검토하는 critic입니다.
입력으로 받은 verified_claims.md의 PASSED 주장들에 대해 다음을 검토하세요.

## 검토 관점
1. **반대 논거 누락** — 통과한 주장에 대한 유력한 반대 견해/판례가 빠졌는가?
2. **약한 추론** — 출처가 일반론을 말하는데 본 케이스에 무리하게 적용하고 있는가?
3. **과장된 결론** — "...이 명백하다" 같은 단언이 출처보다 강한가?

## 출력 형식

원본 verified_claims.md의 PASSED 섹션은 그대로 두고, 끝에 **검토 노트**를 추가:

```markdown
<원본 verified_claims.md 내용 그대로 복사>

## 🔍 Critic 검토 노트

### 누락된 반대 논거
- 주장 #N에 대해: <어떤 반대 견해가 있는지, 가능하면 인용 단서>

### 약한 추론
- 주장 #N: <어떤 부분이 무리한 적용인지>

### 과장된 결론
- 주장 #N: <원문이 말하는 강도 vs. 표현된 강도 비교>
```

## 절대 하지 말 것
- PASSED 주장을 임의로 FAILED로 변경 (검증은 verifier의 책임)
- 출처 없이 반대 논거 만들어내기
- Stage 3의 작성 톤에 대해 코멘트 (그건 다음 단계)

위 Markdown만 출력. 다른 설명 금지."""


async def run(case_dir: Path) -> Path:
    """Execute Stage 2: verifier → critic, sequentially."""
    research_notes = (case_dir / "research_notes.md").read_text(encoding="utf-8")
    citation_policy = prompt_loader.load("config/citation_policy.md")

    print("[stage2] Running verifier...")
    verifier_system = (
        "한국 법률 리서치 결과의 출처 정합성을 검증하세요.\n\n"
        f"인용 정책:\n{citation_policy}"
    )
    verifier_user = f"{VERIFIER_INSTRUCTION}\n\n## 입력 (research_notes.md)\n\n{research_notes}"
    verifier_output = await claude_client.call(
        system=verifier_system,
        user=verifier_user,
        tools=[claude_client.WEB_FETCH_TOOL],
        max_tokens=16000,
        effort="high",
    )
    verified_path = case_dir / "verified_claims.md"
    verified_path.write_text(verifier_output, encoding="utf-8")
    print(f"[stage2]   wrote {verified_path.name}")

    print("[stage2] Running critic...")
    critic_system = "한국 법률 리서치를 다각도로 검토하세요. 누락된 반대 논거와 약한 추론을 찾으세요."
    critic_user = f"{CRITIC_INSTRUCTION}\n\n## 입력 (verified_claims.md)\n\n{verifier_output}"
    critic_output = await claude_client.call(
        system=critic_system,
        user=critic_user,
        tools=[claude_client.WEB_SEARCH_TOOL],
        max_tokens=16000,
        effort="high",
    )
    verified_path.write_text(critic_output, encoding="utf-8")
    print(f"[stage2]   updated {verified_path.name} (with critic notes)")
    return verified_path
