# Cursor Bite — Context Intelligence Analyzer Tests
# ============================================================
# Tests for deterministic domain inference, content type detection,
# grounded technical acronyms, prompt contract, and adaptive ranking.

from domain.context_analyzer import ContextAnalyzer
from domain.models import ActionKind, ContentDomain, ContentType, UserIntent


def test_grounded_acronym_rag():
    """Verify 'RAG' is grounded to Retrieval-Augmented Generation, not generic rag cloth."""
    analysis = ContextAnalyzer.analyze("RAG")
    assert analysis.domain == ContentDomain.SOFTWARE_TECH
    assert analysis.content_type == ContentType.ACRONYM_TERM
    assert analysis.grounded_meaning is not None
    assert "Retrieval-Augmented Generation" in analysis.grounded_meaning

    prompt, system_prompt = ContextAnalyzer.build_explain_prompt("RAG", analysis)
    assert "Retrieval-Augmented Generation" in prompt
    assert "principal technical expert" in system_prompt.lower()


def test_grounded_acronym_ast_and_crud():
    """Verify AST and CRUD are grounded in Software Engineering."""
    analysis_ast = ContextAnalyzer.analyze("AST")
    assert analysis_ast.domain == ContentDomain.SOFTWARE_TECH
    assert "Abstract Syntax Tree" in analysis_ast.grounded_meaning

    analysis_crud = ContextAnalyzer.analyze("CRUD")
    assert analysis_crud.domain == ContentDomain.SOFTWARE_TECH
    assert "Create, Read, Update, Delete" in analysis_crud.grounded_meaning


def test_error_log_detection():
    """Verify stack traces are identified as ERROR_LOG."""
    trace = (
        'Traceback (most recent call last):\n'
        '  File "main.py", line 42, in process\n'
        '    result = 10 / 0\n'
        'ZeroDivisionError: division by zero'
    )
    analysis = ContextAnalyzer.analyze(trace)
    assert analysis.content_type == ContentType.ERROR_LOG
    assert analysis.domain == ContentDomain.SOFTWARE_TECH
    assert analysis.primary_intent == UserIntent.DEBUG_ERROR

    prompt, system_prompt = ContextAnalyzer.build_explain_prompt(trace, analysis)
    assert "Root Cause" in prompt
    assert "Solution" in prompt


def test_code_snippet_detection():
    """Verify code syntax triggers CODE_SNIPPET classification."""
    code = (
        "async def get_user_profile(user_id: int) -> dict:\n"
        "    async with db.transaction():\n"
        "        return await db.fetch_row(user_id)\n"
    )
    analysis = ContextAnalyzer.analyze(code)
    assert analysis.content_type == ContentType.CODE_SNIPPET
    assert analysis.domain == ContentDomain.SOFTWARE_TECH


def test_rewrite_prompt_contract():
    """Verify Rewrite prompt builder strictly forbids semantic drift and hallucinations."""
    text = "Our microservices architecture ensures 99.99% uptime during failover events."
    analysis = ContextAnalyzer.analyze(text)
    prompt, system_prompt = ContextAnalyzer.build_rewrite_prompt(text, analysis)

    assert "STRICT RULES" in system_prompt
    assert "PRESERVE" in system_prompt
    assert "DO NOT alter the user's intended meaning" in system_prompt
    assert text in prompt


def test_adaptive_action_ranking():
    """Verify context-aware action ranking returns relevant top actions."""
    # 1. No selection -> Capture text (OCR) & Ask AI
    empty_rank = ContextAnalyzer.rank_actions(None, has_selection=False)
    assert empty_rank[0] == ActionKind.CAPTURE_TEXT

    # 2. Foreign text -> Translate top
    foreign_analysis = ContextAnalyzer.analyze("Привет, мир!")
    foreign_rank = ContextAnalyzer.rank_actions(foreign_analysis, has_selection=True)
    assert foreign_rank[0] == ActionKind.TRANSLATE

    # 3. Error log -> Explain top
    error_analysis = ContextAnalyzer.analyze("TypeError: undefined is not a function at line 14")
    error_rank = ContextAnalyzer.rank_actions(error_analysis, has_selection=True)
    assert error_rank[0] == ActionKind.EXPLAIN
    assert ActionKind.SEARCH_WEB in error_rank

    # 4. Long prose -> Summarize top
    long_prose = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 30
    prose_analysis = ContextAnalyzer.analyze(long_prose)
    prose_rank = ContextAnalyzer.rank_actions(prose_analysis, has_selection=True)
    assert prose_rank[0] == ActionKind.SUMMARIZE
