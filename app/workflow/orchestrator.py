from langgraph.graph import StateGraph, END
from typing import TypedDict, List
import os
from app.core.pipeline import FAQPipeline
from app.core.session_manager import SessionManager
from app.agents.grader import GraderAgent
from app.agents.faq_agent import FAQAgent
from app.agents.scrapper import ScrapperAgent
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """State management for the agent workflow"""
    query: str
    processed_query: str
    intent: str
    keywords: str
    retrieved_docs: List[str]
    response: str
    confidence: str
    session_id: str
    relevance: str
    terminate: bool

class FAQWorkflowOrchestrator:
    """LangGraph workflow orchestrator for FAQ AGENTIC FLOW"""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.faq_pipeline = None
        self.retriever = None
        self.grader_agent = None
        self.faq_agent = None
        self.scrapper_agent = None
        self.workflow_app = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all system components"""
        try:
            self.faq_pipeline = FAQPipeline()
            
            urls = ["https://your-website.com/faq"]
            docs = self.faq_pipeline.scrape_faq_content(urls)
            db = self.faq_pipeline.create_vector_store(docs)
            self.retriever = self.faq_pipeline.setup_retriever(db)
            
            self.grader_agent = GraderAgent()
            self.faq_agent = FAQAgent(
                vector_store=db, 
                session_manager=self.session_manager
            )
            self.scrapper_agent = ScrapperAgent(
                llm_config={"api_key": settings.openai_api_key}
            )
            
            self.workflow_app = self._create_workflow()
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            raise
    
    def _create_workflow(self):
        """Create the complete FAQ AGENTIC FLOW workflow using LangGraph"""
        workflow = StateGraph(AgentState)
        
        def grade_query_node(state):
            """Grade and filter query relevance"""
            result = self.grader_agent.process_query(state["query"])
            
            if result.get('terminate'):
                return {
                    "response": result["response"],
                    "confidence": "none",
                    "terminate": True,
                    "relevance": "irrelevant"
                }
            
            return {
                "processed_query": result["corrected_query"],
                "intent": result["intent"],
                "keywords": result["keywords"],
                "relevance": "relevant",
                "terminate": False
            }
        
        def retrieve_documents_node(state):
            """Retrieve relevant documents using vector similarity"""
            if state.get("terminate"):
                return state
            
            docs = self.retriever.invoke(state["processed_query"])
            return {"retrieved_docs": docs}
        
        def generate_faq_response_node(state):
            """Generate response using FAQ agent with session context"""
            if state.get("terminate"):
                return state
            
            result = self.faq_agent.generate_response(
                state["processed_query"], 
                state["retrieved_docs"],
                state.get("session_id")
            )
            
            return {
                "response": result["answer"],
                "confidence": result["confidence"]
            }
        
        async def scrapper_search_node(state):
            """Perform extended search using scrapper agent"""
            if state.get("terminate"):
                return state
            
            result = await self.scrapper_agent.extended_search(
                state["processed_query"],
                state.get("retrieved_docs", []),
                state.get("session_id")
            )
            
            return {
                "response": result["response"],
                "confidence": result["confidence"]
            }
        
        def generate_fallback_node(state):
            """Generate fallback when no documents found"""
            return {
                "response": "I don't have specific information about your question in our FAQ database. "
                           "Please contact our support team at support@your-website.com for personalized assistance.",
                "confidence": "none"
            }
        
        def check_relevance_and_quality(state):
            """Route based on query relevance and retrieval quality"""
            if state.get("terminate"):
                return "terminated"
            
            if not state.get("retrieved_docs"):
                return "no_results"
            
            docs = state["retrieved_docs"]
            if docs:
                max_score = max(
                    doc.metadata.get("score", 0) for doc in docs 
                    if hasattr(doc, 'metadata') and doc.metadata
                )
                
                if max_score >= 0.7:
                    return "sufficient"
                else:
                    return "insufficient"
            
            return "no_results"
        
        workflow.add_node("grader", grade_query_node)
        workflow.add_node("retriever", retrieve_documents_node)
        workflow.add_node("faq_agent", generate_faq_response_node)
        workflow.add_node("scrapper", scrapper_search_node)
        workflow.add_node("fallback", generate_fallback_node)
        
        workflow.add_edge("grader", "retriever")
        
        workflow.add_conditional_edges(
            "retriever",
            check_relevance_and_quality,
            {
                "terminated": END,
                "sufficient": "faq_agent",
                "insufficient": "scrapper",
                "no_results": "fallback"
            }
        )
        
        workflow.add_edge("faq_agent", END)
        workflow.add_edge("scrapper", END)
        workflow.add_edge("fallback", END)
        
        workflow.set_entry_point("grader")
        
        return workflow.compile()
    
    async def process_query(self, query, session_id=None):
        """Process a user query through the FAQ AGENTIC FLOW"""
        try:
            result = await self.workflow_app.ainvoke({
                "query": query,
                "session_id": session_id or "default_session"
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "response": "I apologize, but I encountered an error processing your request.",
                "confidence": "none"
            }