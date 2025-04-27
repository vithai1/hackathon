import os
from typing import List, Dict
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path

class TaxGuideRAG:
    def __init__(self):
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Initialize ChromaDB
        self.persist_directory = "tax_guides_db"
        self.vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def download_irs_guides(self) -> List[Dict]:
        """Download and parse IRS tax guides."""
        # IRS Publication URLs for relevant guides
        guides = [
            {
                "url": "https://www.irs.gov/pub/irs-pdf/p15.pdf",
                "title": "Employer's Tax Guide"
            },
            {
                "url": "https://www.irs.gov/pub/irs-pdf/i1040gi.pdf",
                "title": "IRS Tax Guide for Individuals"
            },
            {
                "url": "https://www.irs.gov/pub/irs-pdf/p17.pdf",
                "title": "Your Federal Income Tax"
            },
            {
                "url": "https://www.irs.gov/pub/irs-pdf/p334.pdf",
                "title": "Tax Guide for Small Business"
            },
            {
                "url": "https://www.irs.gov/pub/irs-pdf/p525.pdf",
                "title": "Taxable and Nontaxable Income"
            }
        ]
        
        documents = []
        for guide in guides:
            try:
                response = requests.get(guide["url"])
                if response.status_code == 200:
                    # Save the PDF temporarily
                    temp_path = f"temp_{guide['title']}.pdf"
                    with open(temp_path, "wb") as f:
                        f.write(response.content)
                    
                    # Convert PDF to text
                    text = self._pdf_to_text(temp_path)
                    
                    # Split text into chunks
                    chunks = self.text_splitter.split_text(text)
                    
                    # Add metadata and chunks to documents
                    for i, chunk in enumerate(chunks):
                        documents.append({
                            "text": chunk,
                            "metadata": {
                                "source": guide["url"],
                                "title": guide["title"],
                                "chunk": i
                            }
                        })
                    
                    # Clean up
                    os.remove(temp_path)
            except Exception as e:
                print(f"Error processing {guide['title']}: {str(e)}")
        
        return documents
    
    def _pdf_to_text(self, pdf_path: str) -> str:
        """Convert PDF to text using pdf2image and pytesseract."""
        from pdf2image import convert_from_path
        import pytesseract
        
        text = ""
        images = convert_from_path(pdf_path)
        for image in images:
            text += pytesseract.image_to_string(image)
        return text
    
    def build_vector_store(self):
        """Build the vector store from IRS guides."""
        # Check if vector store already exists
        if os.path.exists(self.persist_directory):
            print("Vector store already exists. Skipping rebuild.")
            return
        
        # Download and process IRS guides
        documents = self.download_irs_guides()
        
        # Add documents to vector store
        texts = [doc["text"] for doc in documents]
        metadatas = [doc["metadata"] for doc in documents]
        
        self.vectorstore.add_texts(
            texts=texts,
            metadatas=metadatas
        )
        
        # Persist the vector store
        self.vectorstore.persist()
    
    def get_relevant_context(self, query: str, k: int = 3) -> str:
        """Retrieve relevant context from IRS guides."""
        docs = self.vectorstore.similarity_search(query, k=k)
        
        # Format the context
        context = "Relevant IRS Tax Guide Information:\n\n"
        for i, doc in enumerate(docs, 1):
            context += f"Source {i} ({doc.metadata['title']}):\n"
            context += doc.page_content + "\n\n"
        
        return context

# Initialize RAG handler
rag_handler = TaxGuideRAG() 