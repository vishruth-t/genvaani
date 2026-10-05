import os

class KnowledgeBase:
    def __init__(self, knowledge_dir: str = "knowledge"):
        self.knowledge_dir = knowledge_dir
        self.documents = []
        self._load_knowledge()
        
    def _load_knowledge(self):
        if not os.path.exists(self.knowledge_dir):
            return
            
        for filename in os.listdir(self.knowledge_dir):
            if filename.endswith(".md") or filename.endswith(".txt"):
                filepath = os.path.join(self.knowledge_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    self.documents.append({
                        "name": filename,
                        "content": f.read()
                    })
                    
    def search(self, query: str) -> str:
        """
        Simple keyword-based RAG search. 
        In production, use vector embeddings + cosine similarity.
        """
        query_words = set(query.lower().split())
        best_match = None
        highest_score = 0
        
        for doc in self.documents:
            doc_words = set(doc["content"].lower().split())
            score = len(query_words.intersection(doc_words))
            if score > highest_score:
                highest_score = score
                best_match = doc
                
        if best_match and highest_score > 0:
            return f"Information from {best_match['name']}:\n{best_match['content']}"
        
        return ""

rag_db = KnowledgeBase()
