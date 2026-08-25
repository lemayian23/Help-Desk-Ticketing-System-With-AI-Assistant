"""
RAG (Retrieval-Augmented Generation) Service for IT Helpdesk.
Provides AI-powered answers and solutions based on past tickets.
"""

import os
import json
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
from sentence_transformers import SentenceTransformer
import faiss
from sqlalchemy.orm import Session
from database import Ticket, TicketSolution, TicketMessage

class RAGService:
    """
    RAG service that uses past tickets to generate AI-powered solutions.
    """
    
    def __init__(self):
        # Initialize the embedding model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = None
        self.documents = []
        self.embeddings = None
        self.is_initialized = False
        
    def initialize(self, db: Session):
        """Load all past tickets and solutions into the vector database"""
        print("🔄 Initializing RAG service...")
        
        # Get all resolved tickets with solutions
        tickets = db.query(Ticket).filter(
            Ticket.status == "resolved"
        ).all()
        
        if not tickets:
            print("⚠️ No resolved tickets found. RAG will be empty.")
            return
        
        # Build documents from tickets
        self.documents = []
        for ticket in tickets:
            # Get the solution if available
            solution = db.query(TicketSolution).filter(
                TicketSolution.ticket_id == ticket.id
            ).first()
            
            # Create document text
            doc_text = f"""
            Title: {ticket.title}
            Category: {ticket.category.value}
            Priority: {ticket.priority.value}
            Description: {ticket.description}
            Solution: {solution.solution if solution else 'No solution recorded'}
            """
            self.documents.append({
                "text": doc_text,
                "ticket_id": ticket.id,
                "title": ticket.title,
                "category": ticket.category.value,
                "solution": solution.solution if solution else None
            })
        
        # Create embeddings
        if self.documents:
            texts = [doc["text"] for doc in self.documents]
            self.embeddings = self.model.encode(texts)
            self.index = faiss.IndexFlatL2(self.embeddings.shape[1])
            self.index.add(self.embeddings)
            self.is_initialized = True
            print(f"✅ RAG initialized with {len(self.documents)} documents")
        else:
            print("⚠️ No documents to index")
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search for similar tickets/solutions"""
        if not self.is_initialized or not self.documents:
            return []
        
        # Encode the query
        query_embedding = self.model.encode([query])
        
        # Search
        distances, indices = self.index.search(query_embedding, min(top_k, len(self.documents)))
        
        results = []
        for idx in indices[0]:
            if idx < len(self.documents):
                results.append(self.documents[idx])
        
        return results
    
    def generate_response(self, query: str, db: Session) -> Dict:
        """
        Generate an AI response based on the query.
        Uses RAG to find relevant solutions and formats a response.
        """
        # Search for relevant documents
        relevant_docs = self.search(query)
        
        if not relevant_docs:
            return {
                "answer": "I don't have enough information to answer that yet. Please ask your IT support team for assistance.",
                "sources": []
            }
        
        # Build response from relevant documents
        response = f"Based on past resolved tickets, here's what I found:\n\n"
        sources = []
        
        for i, doc in enumerate(relevant_docs[:3], 1):
            response += f"{i}. **{doc['title']}**\n"
            if doc['solution']:
                response += f"   Solution: {doc['solution'][:200]}...\n\n"
            sources.append({
                "ticket_id": doc['ticket_id'],
                "title": doc['title'],
                "category": doc['category']
            })
        
        response += "Would you like me to create a ticket with this information?"
        
        return {
            "answer": response,
            "sources": sources
        }

# Create a global instance
rag_service = RAGService()