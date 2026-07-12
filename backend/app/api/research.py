"""Research query route (TDD Section 5, Section 6): the HTTP surface over
app.agents.orchestrator.run_research_query(). The orchestrator itself and
its structured-output validation have existed since Milestone 6, but
nothing exposed it over HTTP until this route — closing that gap, not
skipping ahead into Milestone 7.

Thin per TDD Section 2: parse the request, call the orchestrator, wrap its
return dict in ResearchQueryResponse, map failure modes to HTTP status
codes. No orchestration logic lives here.
"""

import logging

import openai
from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.orchestrator import run_research_query
from app.core.tenancy import CurrentUser, get_current_user
from app.schemas.research import ResearchQueryRequest, ResearchQueryResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["research"])


@router.post("", response_model=ResearchQueryResponse)
async def submit_research_query(
    request: ResearchQueryRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ResearchQueryResponse:
    """Run one research query through the orchestrator's two-pass
    tool-calling loop and return its structured result (or a clean
    malformed_output failure) plus the full reasoning trace.

    `current_user` isn't otherwise used in the function body: the
    orchestrator doesn't touch tenant data (no persistence yet — saved
    research is Milestone 8), so nothing here needs org_id. Requiring a
    valid JWT still matters regardless, since this route calls a real,
    metered LLM provider on every request and must not be reachable
    unauthenticated (TDD Section 13).
    """
    try:
        result = await run_research_query(request.query)
    except RuntimeError as exc:
        # run_research_query raises RuntimeError only when no LLM API key
        # is configured server-side — a deployment/config problem, not
        # anything the client did. Logged in full server-side; the client
        # gets a clean, generic detail rather than internal config state.
        logger.error("Research query failed — LLM provider not configured: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured.",
        ) from exc
    except openai.OpenAIError as exc:
        # litellm normalizes every provider's SDK errors (rate limits,
        # timeouts, upstream 5xxs) onto the openai-python exception
        # hierarchy regardless of which provider is actually configured —
        # this is the single catch point for "the LLM provider itself
        # failed," per TDD Section 11's "LLM API failures/rate limits"
        # error-handling strategy. No retry-with-backoff here (that's a
        # documented Future Scope item, not silently added); this is only
        # the "fail loud with a clear state" half of that strategy.
        #
        # The provider's raw error (str(exc)) can be a large, verbose JSON
        # dump of internal error details (seen in practice with Gemini
        # rate-limit responses) — logged in full server-side for
        # debugging, but not forwarded to the client verbatim. TDD Section
        # 11 is explicit that the frontend should show "AI service
        # temporarily unavailable," not a raw provider error blob.
        logger.error("Research query failed — LLM provider error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable. Please try again shortly.",
        ) from exc
    return ResearchQueryResponse.model_validate(result)
