from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from fastapi import APIRouter, HTTPException

from backend.api.schemas.ai import AiChatRequest, AiChatResponse


router = APIRouter(prefix="/ai", tags=["ai"])

DEFAULT_ENDPOINT = "https://ai.nscc-cs.cn/external/api/v1/chat/completions"
DEFAULT_MODEL = "Qwen3-32B-128k"


@router.post("/chat", response_model=AiChatResponse)
def chat(request: AiChatRequest) -> AiChatResponse:
    api_key = os.getenv("OMICS_LLM_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OMICS_LLM_API_KEY is not configured.")

    endpoint = os.getenv("OMICS_LLM_ENDPOINT", DEFAULT_ENDPOINT)
    model = os.getenv("OMICS_LLM_MODEL", DEFAULT_MODEL)
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是单细胞 RNA-seq 智能分析平台的科研助手。"
                    "回答必须基于提供的项目上下文，区分数据观察、统计结论、风险提示和建议。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": request.question,
                        "context": request.context,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "stream": False,
    }
    http_request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(http_request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=exc.code, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    answer = extract_answer(data)
    return AiChatResponse(answer=answer, model=model)


def extract_answer(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        return json.dumps(data, ensure_ascii=False)
    message = choices[0].get("message") or {}
    return str(message.get("content") or "")

