"""
TravelBuddy Agent — Tích hợp từ Lab 4 (LangGraph ReAct Agent).

Sử dụng GPT-4o-mini + 3 tools (search_flights, search_hotels, calculate_budget)
để tư vấn du lịch Việt Nam.

Fallback về mock_llm nếu không cài LangGraph hoặc thiếu OPENAI_API_KEY.
"""
import os
import logging

logger = logging.getLogger(__name__)

# System prompt gốc từ Lab 4
SYSTEM_PROMPT = """Bạn là TravelBuddy — một trợ lý du lịch thông minh, thân thiện và hiểu biết về du lịch Việt Nam.

Bạn nói chuyện tự nhiên như một người bạn đã đi du lịch nhiều nơi, luôn đưa ra lời khuyên thực tế và phù hợp với ngân sách của người dùng.

Quy tắc:
1. Luôn trả lời bằng tiếng Việt.
2. Nếu người dùng chưa cung cấp đủ thông tin (điểm đi, điểm đến, ngân sách, số ngày), hãy hỏi lại trước khi gọi tool.
3. Ưu tiên sử dụng tool khi cần dữ liệu cụ thể (vé máy bay, khách sạn, ngân sách).
4. Khi có nhiều lựa chọn, ưu tiên phương án tối ưu chi phí nhất.
5. Không được tự bịa thông tin — chỉ sử dụng dữ liệu từ tool.
6. Có thể gọi nhiều tool liên tiếp để hoàn thành yêu cầu (multi-step reasoning).
7. Sau khi dùng tool, phải tổng hợp kết quả thành câu trả lời rõ ràng cho người dùng.

Bạn có 3 công cụ: search_flights, search_hotels, calculate_budget.
Hướng dẫn: Tìm chuyến bay trước → Chọn khách sạn → Dùng calculate_budget để kiểm tra tổng chi phí.

Chỉ hỗ trợ các yêu cầu liên quan đến du lịch. Từ chối lịch sự các yêu cầu ngoài phạm vi."""


def _build_langgraph_agent():
    """Khởi tạo LangGraph agent (chỉ gọi 1 lần khi import)."""
    from langchain_core.messages import SystemMessage
    from langchain_openai import ChatOpenAI
    from langgraph.graph import StateGraph, START
    from langgraph.graph.message import add_messages
    from langgraph.prebuilt import ToolNode, tools_condition
    from typing import Annotated
    from typing_extensions import TypedDict

    from app.travel_tools import search_flights, search_hotels, calculate_budget

    class AgentState(TypedDict):
        messages: Annotated[list, add_messages]

    tools_list = [search_flights, search_hotels, calculate_budget]
    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    llm_with_tools = llm.bind_tools(tools_list)

    def agent_node(state: AgentState):
        messages = state["messages"]
        if not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(tools_list))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")

    return builder.compile()


# Khởi tạo agent hoặc fallback
_graph = None
_use_real_agent = False

try:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and not api_key.startswith("sk-fake"):
        _graph = _build_langgraph_agent()
        _use_real_agent = True
        logger.info("✅ TravelBuddy LangGraph agent initialized (GPT-4o-mini)")
    else:
        logger.warning("⚠️ OPENAI_API_KEY not set — using mock LLM fallback")
except ImportError as e:
    logger.warning(f"⚠️ LangGraph/LangChain not installed — using mock LLM fallback: {e}")
except Exception as e:
    logger.warning(f"⚠️ Failed to init LangGraph agent — using mock LLM fallback: {e}")


def ask(question: str) -> str:
    """
    Gọi TravelBuddy agent (LangGraph + GPT-4o-mini) hoặc fallback mock.
    Đây là hàm duy nhất mà main.py cần gọi.
    """
    if _use_real_agent and _graph is not None:
        try:
            result = _graph.invoke({"messages": [("human", question)]})
            final_message = result["messages"][-1]
            return final_message.content
        except Exception as e:
            logger.error(f"LangGraph agent error: {e}")
            return f"Xin lỗi, TravelBuddy đang gặp sự cố kỹ thuật. Vui lòng thử lại sau. (Lỗi: {str(e)[:100]})"
    else:
        # Fallback: mock response
        from utils.mock_llm import ask as mock_ask
        return mock_ask(question)
