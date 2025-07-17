from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import xml.etree.ElementTree as ET
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class FAQAgent:
    """Central response generation agent with session memory"""
    
    def __init__(self, llm=None, vector_store=None, session_manager=None):
        self.llm = llm or ChatOpenAI(
            temperature=0, 
            model="gpt-4"
        )
        self.vector_store = vector_store
        self.session_manager = session_manager
        self.prompt = PromptTemplate(
            template="""
            <context>
            You are an intelligent FAQ assistant. Generate responses using ONLY 
            the provided knowledge base and conversation history.
            </context>
            
            <conversation_history>
            {conversation_context}
            </conversation_history>
            
            <knowledge_base>
            {retrieved_docs}
            </knowledge_base>
            
            <rules>
            - Answer based strictly on retrieved information
            - Consider conversation history for contextual responses
            - Avoid repeating previously provided information
            - If information is insufficient, acknowledge limitations
            - Maintain helpful and professional tone
            - Use XML output format for structured responses
            </rules>
            
            <query>{processed_query}</query>
            
            <response>
            <answer>{your_answer}</answer>
            <confidence>{high|medium|low}</confidence>
            <sources>{doc_references}</sources>
            </response>
            """,
            input_variables=["conversation_context", "retrieved_docs", "processed_query"]
        )
    
    def generate_response(self, query: str, docs: list, session_id: str | None = None) -> dict:
        """Generate context-aware FAQ responses"""
        try:
            if not query or not query.strip():
                return self._create_error_response("Empty query provided")
            
            conversation_context = self._get_conversation_context(session_id)
            formatted_docs = self._format_retrieved_docs(docs)
            
            if not docs:
                logger.warning(f"No documents provided for query: {query[:50]}...")
            
            response = self.llm.invoke(
                self.prompt.format(
                    conversation_context=conversation_context,
                    processed_query=query.strip(),
                    retrieved_docs=formatted_docs
                )
            )
            
            parsed_response = self._parse_xml_response(str(response.content))
            
            if not parsed_response.get('answer'):
                return self._create_error_response("Failed to generate response")
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"Error generating response for query '{query[:50]}...': {e}", exc_info=True)
            return self._create_error_response("An error occurred while processing your request")
    
    def _get_conversation_context(self, session_id: str | None) -> str:
        """Retrieve and format conversation context"""
        try:
            if not session_id or not self.session_manager:
                return "No previous conversation."
            
            history = self.session_manager.get_session_context(session_id, limit=5)
            return self._format_conversation_history(history)
            
        except Exception as e:
            logger.error(f"Error retrieving conversation context: {e}")
            return "No previous conversation."
    
    def _format_conversation_history(self, history: list) -> str:
        """Format conversation history for prompt context"""
        if not history:
            return "No previous conversation."
        
        try:
            formatted = []
            for i, interaction in enumerate(history):
                if interaction.get('query') and interaction.get('response'):
                    formatted.append(f"Q{i+1}: {interaction['query']}")
                    formatted.append(f"A{i+1}: {interaction['response']}")
            
            return "\n".join(formatted) if formatted else "No previous conversation."
            
        except Exception as e:
            logger.error(f"Error formatting conversation history: {e}")
            return "No previous conversation."
    
    def _format_retrieved_docs(self, docs: list) -> str:
        """Format retrieved documents with source attribution"""
        if not docs:
            return "No relevant documents found."
        
        try:
            formatted = []
            for i, doc in enumerate(docs):
                if hasattr(doc, 'page_content') and doc.page_content:
                    source = getattr(doc, 'metadata', {}).get('source', 'Unknown')
                    formatted.append(f"[Source {i+1} - {source}]: {doc.page_content}")
            
            return "\n\n".join(formatted) if formatted else "No relevant documents found."
            
        except Exception as e:
            logger.error(f"Error formatting retrieved documents: {e}")
            return "No relevant documents found."
    
    def _parse_xml_response(self, xml_string: str) -> dict:
        """Parse structured XML response from agent"""
        if not xml_string:
            return self._create_error_response("Empty response from AI model")
        
        try:
            start = xml_string.find('<response>')
            end = xml_string.find('</response>')
            
            if start == -1 or end == -1:
                logger.warning("XML response tags not found, attempting to extract content")
                return {
                    'answer': xml_string.strip(),
                    'confidence': 'low',
                    'sources': 'None'
                }
            
            xml_content = xml_string[start:end + len('</response>')]
            root = ET.fromstring(xml_content)
            
            answer_elem = root.find('answer')
            confidence_elem = root.find('confidence')
            sources_elem = root.find('sources')
            
            return {
                'answer': answer_elem.text if answer_elem is not None and answer_elem.text else 'Unable to generate response',
                'confidence': confidence_elem.text if confidence_elem is not None and confidence_elem.text else 'low',
                'sources': sources_elem.text if sources_elem is not None and sources_elem.text else 'None'
            }
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            return {
                'answer': xml_string.strip() if xml_string.strip() else 'Unable to parse response',
                'confidence': 'low',
                'sources': 'None'
            }
        except Exception as e:
            logger.error(f"Unexpected error parsing XML response: {e}")
            return self._create_error_response("Error parsing AI response")
    
    def _create_error_response(self, message: str) -> dict:
        """Create standardized error response"""
        return {
            'answer': f'I apologize, but {message.lower()}. Please try again or contact support if the issue persists.',
            'confidence': 'none',
            'sources': 'None'
        }