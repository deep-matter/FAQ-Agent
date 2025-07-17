from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import xml.etree.ElementTree as ET
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class GraderAgent:
    """Grader Agent for query preprocessing and relevance filtering"""
    
    def __init__(self, llm=None):
        self.llm = llm or ChatOpenAI(
            temperature=0, 
            model="gpt-4"
        )
        self.prompt = PromptTemplate(
            template="""
            <task>
            Analyze user query for FAQ support relevance:
            1. Determine if query relates to FAQ support purposes
            2. If irrelevant, respond with "out of knowledge base"
            3. If relevant, perform grammar correction and intent classification
            </task>
            
            <query>{user_query}</query>
            
            <faq_topics>
            - Admissions and enrollment
            - Academic programs and courses
            - Fees and payment
            - Deadlines and schedules
            - Student services and support
            </faq_topics>
            
            <output>
            <relevance>{relevant|irrelevant}</relevance>
            <corrected_query>{corrected}</corrected_query>
            <intent>{intent_type}</intent>
            <keywords>{key_terms}</keywords>
            </output>
            """,
            input_variables=["user_query"]
        )
    
    def process_query(self, query):
        """Process and filter user queries"""
        try:
            response = self.llm.invoke(self.prompt.format(user_query=query))
            result = self.parse_xml_response(response.content)
            
            if result.get('relevance') == 'irrelevant':
                return {
                    'response': 'is out of my knowledge base',
                    'relevance': 'irrelevant',
                    'terminate': True
                }
            
            return {
                'corrected_query': result.get('corrected_query', query),
                'intent': result.get('intent', 'unknown'),
                'keywords': result.get('keywords', ''),
                'relevance': 'relevant',
                'terminate': False
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                'corrected_query': query,
                'intent': 'unknown',
                'keywords': '',
                'relevance': 'relevant',
                'terminate': False
            }
    
    def parse_xml_response(self, xml_string):
        """Parse XML-structured agent response"""
        try:
            start = xml_string.find('<output>')
            end = xml_string.find('</output>') + len('</output>')
            xml_content = xml_string[start:end]
            
            root = ET.fromstring(xml_content)
            
            relevance_elem = root.find('relevance')
            corrected_query_elem = root.find('corrected_query')
            intent_elem = root.find('intent')
            keywords_elem = root.find('keywords')
            
            return {
                'relevance': relevance_elem.text if relevance_elem is not None and relevance_elem.text else 'relevant',
                'corrected_query': corrected_query_elem.text if corrected_query_elem is not None and corrected_query_elem.text else '',
                'intent': intent_elem.text if intent_elem is not None and intent_elem.text else 'unknown',
                'keywords': keywords_elem.text if keywords_elem is not None and keywords_elem.text else ''
            }
        except Exception as e:
            logger.error(f"XML parsing error: {e}")
            return {'relevance': 'relevant', 'corrected_query': '', 'intent': 'unknown', 'keywords': ''}