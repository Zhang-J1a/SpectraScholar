"""Tool calling endpoints (V2.1)."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from ..schemas import ArxivSearchResponse
from ..settings import settings
from ..tools import ArxivSearchError, search_arxiv
from .dependencies import require_api_key

router = APIRouter(prefix="/api/v1/tools", tags=["tools"], dependencies=[Depends(require_api_key)])


@router.get("/arxiv_search", response_model=ArxivSearchResponse)
async def arxiv_search(
    query: str = Query(min_length=2, max_length=500, description="arXiv 搜索式"),
    year_from: int | None = Query(None, ge=1900, le=2100),
    year_to: int | None = Query(None, ge=1900, le=2100),
    task_topic: str | None = Query(None, max_length=200, description="任务主题过滤"),
    start: int = Query(0, ge=0, le=5000),
    max_results: int = Query(10, ge=1, le=50),
):
    current_year = datetime.now(UTC).year
    if year_from and year_from > current_year + 1:
        raise HTTPException(status_code=422, detail="year_from 超出合理范围")
    if year_to and year_to > current_year + 1:
        raise HTTPException(status_code=422, detail="year_to 超出合理范围")
    if year_from and year_to and year_from > year_to:
        raise HTTPException(status_code=422, detail="year_from 不能大于 year_to")

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                search_arxiv,
                query,
                year_from=year_from,
                year_to=year_to,
                task_topic=task_topic,
                start=start,
                max_results=max_results,
            ),
            timeout=settings.arxiv_timeout_seconds,
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="arXiv 搜索超时") from exc
    except ArxivSearchError as exc:
        if exc.code == "invalid_query":
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise HTTPException(status_code=503, detail=f"arXiv 工具不可用 ({exc.code}): {exc}") from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"arXiv 工具调用失败: {type(exc).__name__}",
        ) from exc
    return ArxivSearchResponse(**result)
