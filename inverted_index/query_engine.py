import os
import pickle
import math
import heapq
from collections import defaultdict
from typing import List, Tuple
from .preprocessing import TextPreprocessor

class QueryEngine:
    def __init__(self, index_dir: str = "index_data"):
        self.index_dir = index_dir
        self.preprocessor = TextPreprocessor()
        self.vocabulary = {} # term -> file_offset (byte position in index)
        self.doc_norms = {}
        self.index_file = os.path.join(index_dir, "tfidf_index.dat")
        self.norms_file = os.path.join(index_dir, "doc_norms.dat")
        
        self.load_metadata()

    def load_metadata(self):
        """
        Loads document norms and builds a vocabulary map for fast seek.
        """
        # print("Loading index metadata...")
        
        # Load norms
        if os.path.exists(self.norms_file):
            with open(self.norms_file, 'rb') as f:
                self.doc_norms = pickle.load(f)
        
        # Build vocabulary map (term -> offset)
        if os.path.exists(self.index_file):
            with open(self.index_file, 'rb') as f:
                while True:
                    offset = f.tell()
                    try:
                        term, _ = pickle.load(f)
                        self.vocabulary[term] = offset
                    except EOFError:
                        break
        # print(f"Metadata loaded. Vocabulary size: {len(self.vocabulary)}")

    def search(self, query: str, k: int = 10) -> List[Tuple[int, float]]:
        """
        Executes a query and returns top-k documents.
        """
        # 1. Preprocess query
        query_tokens = self.preprocessor.preprocess(query)
        if not query_tokens:
            return []
            
        # 2. Calculate Query Vector (TF-IDF)
        # Query TF: count tokens
        query_tf = defaultdict(int)
        for token in query_tokens:
            query_tf[token] += 1
            
        scores = defaultdict(float)
        
        if not os.path.exists(self.index_file):
            return []

        with open(self.index_file, 'rb') as f:
            for term, q_tf in query_tf.items():
                if term in self.vocabulary:
                    # Seek and load postings
                    f.seek(self.vocabulary[term])
                    _, postings = pickle.load(f)
                    
                    # Approximate W_q = 1 + log(q_tf)
                    w_q = 1 + math.log10(q_tf)
                    
                    for doc_id, w_d in postings:
                        scores[doc_id] += w_q * w_d
                        
        # 3. Normalize by Document Norm
        final_scores = []
        for doc_id, dot_product in scores.items():
            norm_d = self.doc_norms.get(doc_id, 1.0)
            if norm_d == 0:
                norm_d = 1.0
            score = dot_product / norm_d
            final_scores.append((doc_id, score))
            
        # 4. Top-K
        return heapq.nlargest(k, final_scores, key=lambda x: x[1])
