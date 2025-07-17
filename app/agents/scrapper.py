from langchain_openai import ChatOpenAI
from scrapegraphai.graphs import SmartScraperGraph
from app.config.settings import settings
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ScrapperAgent:
    """Intelligent fallback agent with extended search capabilities"""
    
    def __init__(self, llm=None, llm_config=None):
        self.llm = llm or ChatOpenAI(
            temperature=0, 
            model="gpt-4"
        )
        self.graph_config = {
            "llm": {
                "api_key": llm_config.get("api_key", settings.openai_api_key) if llm_config else settings.openai_api_key,
                "model": "openai/gpt-4o-mini",
            },
            "verbose": False,
            "headless": True,
        }
        
    async def extended_search(self, query: str, failed_context: List[Any], session_id: str | None = None) -> Dict[str, Any]:
        """Perform extended search when primary retrieval fails"""
        try:
            if not query or not query.strip():
                return self._generate_fallback_response([], query)
            
            search_urls = self._identify_related_faq_pages(query)
            
            extended_results = []
            for url in search_urls[:3]:  # Limit to 3 URLs for performance
                try:
                    scraper = SmartScraperGraph(
                        prompt=f"""Search for information related to: '{query}'
                                  Extract any relevant FAQ content, guides, or help information
                                  that might answer this specific question.
                                  Focus on educational/academic content.""",
                        source=url,
                        config=self.graph_config
                    )
                    
                    result = scraper.run()
                    if self._assess_relevance(result, query):
                        extended_results.append(result)
                        
                except Exception as e:
                    logger.error(f"Scraping error for {url}: {e}")
                    continue
            
            return self._generate_fallback_response(extended_results, query)
            
        except Exception as e:
            logger.error(f"Error in extended search for query '{query[:50]}...': {e}", exc_info=True)
            return self._generate_fallback_response([], query)
    
    def _identify_related_faq_pages(self, query: str) -> List[str]:
        """Identify potential FAQ pages for extended search"""
        base_urls = [
            "https://your-website.com/faq",
            "https://your-website.com/help",
            "https://your-website.com/support",
            "https://your-website.com/admissions-faq",
            "https://your-website.com/academic-faq"
        ]
        
        return base_urls
    
    def _assess_relevance(self, scraped_content: Any, query: str) -> bool:
        """Check if scraped content is relevant to the query"""
        try:
            if not scraped_content or not query:
                return False
            
            query_words = set(query.lower().split())
            if not query_words:
                return False
            
            content_text = str(scraped_content).lower()
            
            matches = sum(1 for word in query_words if word in content_text)
            relevance_score = matches / len(query_words)
            
            return relevance_score >= 0.3  # 30% keyword match threshold
            
        except Exception as e:
            logger.error(f"Error assessing relevance: {e}")
            return False
    
    def _generate_fallback_response(self, extended_results: List[Any], query: str) -> Dict[str, Any]:
        """Generate three-tier fallback response"""
        try:
            if extended_results:
                # Tier 2: Alternative suggestions found
                return {
                    "response": f"I found related information that might help with your question about '{query}'. "
                               f"While I don't have a direct answer in our main FAQ database, "
                               f"here are some related resources that might be helpful.",
                    "suggestions": extended_results,
                    "confidence": "medium",
                    "type": "extended_search_results"
                }
            else:
                # Tier 3: Human escalation
                return {
                    "response": f"I couldn't find specific information about '{query}' in our FAQ database. "
                               f"For personalized assistance, please:\n"
                               f"• Contact our support team at support@your-website.com\n"
                               f"• Visit our help center for additional resources\n"
                               f"• Schedule a consultation with our advisors\n"
                               f"We're here to help with any questions you may have!",
                    "confidence": "none",
                    "type": "human_escalation"
                }
                
        except Exception as e:
            logger.error(f"Error generating fallback response: {e}")
            return {
                "response": "I apologize, but I encountered an error processing your request. "
                           "Please contact our support team for assistance.",
                "confidence": "none",
                "type": "error"
            }