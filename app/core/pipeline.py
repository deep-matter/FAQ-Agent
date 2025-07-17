import os
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from scrapegraphai.graphs import SmartScraperGraph
from datetime import datetime
from app.config.settings import settings

class FAQPipeline:
    """FAQ AGENTIC FLOW pipeline for knowledge acquisition and processing"""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.openai_api_key
        )
        self.text_splitter = CharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=0
        )
        self.persistent_directory = self._get_persistent_directory()
    
    def _get_persistent_directory(self):
        """Get persistent directory for vector store"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        db_dir = os.path.join(current_dir, "..", "..", "db")
        return os.path.join(db_dir, "chroma_db_faq")
    
    def scrape_faq_content(self, urls):
        """Web scraping and content extraction"""
        loader = WebBaseLoader(urls)
        documents = loader.load()
        
        docs = self.text_splitter.split_documents(documents)
        
        print(f"Created {len(docs)} document chunks")
        return docs
    
    def create_vector_store(self, docs):
        """Embedding and vector storage with Chroma + FAISS"""
        if not os.path.exists(self.persistent_directory):
            print("Creating vector store...")
            db = Chroma.from_documents(
                docs, 
                self.embeddings, 
                persist_directory=self.persistent_directory
            )
            print("Vector store created successfully")
        else:
            print("Loading existing vector store...")
            db = Chroma(
                persist_directory=self.persistent_directory, 
                embedding_function=self.embeddings
            )
        
        return db
    
    def setup_retriever(self, db):
        """Configure similarity search with 0.7 threshold"""
        retriever = db.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )
        return retriever

class AdvancedFAQScraper:
    """Advanced FAQ scraper using ScrapeGraphAI"""
    
    def __init__(self, llm_config):
        self.graph_config = {
            "llm": {
                "api_key": llm_config["api_key"],
                "model": "openai/gpt-4o-mini",
            },
            "verbose": True,
            "headless": True,
        }
    
    def extract_faq_content(self, url):
        """Intelligent FAQ extraction using ScrapeGraphAI"""
        smart_scraper = SmartScraperGraph(
            prompt="""Extract comprehensive FAQ information:
                     - Questions and complete answers
                     - FAQ categories and sections
                     - Related links and resources
                     - Contact information
                     Format as structured Q&A pairs with metadata""",
            source=url,
            config=self.graph_config
        )
        
        result = smart_scraper.run()
        return self.process_extracted_data(result)
    
    def process_extracted_data(self, raw_data):
        """Structure extracted data for vector embedding"""
        faq_items = []
        for item in raw_data.get('faqs', []):
            faq_items.append({
                'question': item['question'],
                'answer': item['answer'],
                'category': item.get('category', 'general'),
                'metadata': {
                    'source_url': item.get('source'),
                    'last_updated': datetime.now().isoformat()
                }
            })
        return faq_items