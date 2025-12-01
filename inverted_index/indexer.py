import os
import pickle
import math
from collections import defaultdict
import heapq
from typing import List, Tuple, Dict

class SPIMIIndexer:
    def __init__(self, block_size_limit: int = 10000, output_dir: str = "index_data"):
        self.block_size_limit = block_size_limit
        self.output_dir = output_dir
        self.dictionary = defaultdict(list)  # term -> [(doc_id, tf), ...]
        self.block_count = 0
        self.doc_lengths = {}  # doc_id -> norm (L2)
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def add_document(self, doc_id: int, tokens: List[str]):
        """
        Adds a document to the current in-memory block.
        """
        # Calculate term frequencies for this document locally first
        term_freqs = defaultdict(int)
        for token in tokens:
            term_freqs[token] += 1
            
        # Add to main dictionary
        for term, tf in term_freqs.items():
            self.dictionary[term].append((doc_id, tf))
            
        # Check memory constraint (simplified by number of entries)
        if len(self.dictionary) >= self.block_size_limit:
            self.write_block_to_disk()

    def write_block_to_disk(self):
        """
        Writes the current in-memory dictionary to a block file.
        """
        if not self.dictionary:
            return

        # Sort terms
        sorted_terms = sorted(self.dictionary.keys())
        
        block_path = os.path.join(self.output_dir, f"block_{self.block_count}.dat")
        with open(block_path, 'wb') as f:
            # We write term by term. 
            # Format: Term (str) | Postings (list of tuples)
            # Using pickle for simplicity in this project, but could be raw bytes for optimization
            block_data = []
            for term in sorted_terms:
                block_data.append((term, self.dictionary[term]))
            pickle.dump(block_data, f)
            
        print(f"Block {self.block_count} written to {block_path}")
        self.block_count += 1
        self.dictionary.clear()

    def merge_blocks(self):
        """
        Merges all block files into a single inverted index.
        Also computes TF-IDF and document norms.
        """
        print("Merging blocks...")
        
        # Open all block files
        block_files = []
        iterators = []
        
        for i in range(self.block_count):
            path = os.path.join(self.output_dir, f"block_{i}.dat")
            if os.path.exists(path):
                f = open(path, 'rb')
                block_files.append(f)
                try:
                    data = pickle.load(f) 
                    iterators.append(iter(data))
                except EOFError:
                    pass
            else:
                print(f"Warning: Block file {path} not found.")

        # Min-heap for k-way merge
        # Heap elements: (term, postings, block_index)
        heap = []
        
        # Initialize heap
        for i, it in enumerate(iterators):
            try:
                term, postings = next(it)
                heapq.heappush(heap, (term, postings, i))
            except StopIteration:
                pass

        final_index_path = os.path.join(self.output_dir, "inverted_index.dat")
        
        with open(final_index_path, 'wb') as out_f:
            current_term = None
            current_postings = []
            
            while heap:
                term, postings, block_idx = heapq.heappop(heap)
                
                if current_term is None:
                    current_term = term
                
                if term != current_term:
                    # Write previous term
                    self._write_term_to_index(out_f, current_term, current_postings)
                    current_term = term
                    current_postings = []
                
                current_postings.extend(postings)
                
                # Push next from same block
                try:
                    next_term, next_postings = next(iterators[block_idx])
                    heapq.heappush(heap, (next_term, next_postings, block_idx))
                except StopIteration:
                    pass
            
            # Write last term
            if current_term:
                self._write_term_to_index(out_f, current_term, current_postings)

        # Close files
        for f in block_files:
            f.close()
            
        print("Merge completed.")

    def _write_term_to_index(self, f, term, postings):
        """
        Writes a term and its postings to the final index.
        """
        pickle.dump((term, postings), f)

    def compute_tfidf_and_norms(self, total_docs: int):
        """
        Reads the raw index, computes TF-IDF, updates index, and computes norms.
        This is a second pass.
        """
        raw_path = os.path.join(self.output_dir, "inverted_index.dat")
        final_path = os.path.join(self.output_dir, "tfidf_index.dat")
        norms_path = os.path.join(self.output_dir, "doc_norms.dat")
        
        if not os.path.exists(raw_path):
            print("No inverted index found to compute TF-IDF.")
            return

        doc_norms = defaultdict(float)
        
        with open(raw_path, 'rb') as f_in, open(final_path, 'wb') as f_out:
            while True:
                try:
                    term, postings = pickle.load(f_in)
                except EOFError:
                    break
                
                # Calculate IDF
                df = len(postings)
                if df > 0:
                    idf = math.log10(total_docs / df)
                else:
                    idf = 0
                
                weighted_postings = []
                for doc_id, tf in postings:
                    weight = (1 + math.log10(tf)) * idf
                    weighted_postings.append((doc_id, weight))
                    doc_norms[doc_id] += weight ** 2
                
                pickle.dump((term, weighted_postings), f_out)
                
        # Save norms
        doc_norms = {k: math.sqrt(v) for k, v in doc_norms.items()}
        with open(norms_path, 'wb') as f_norms:
            pickle.dump(doc_norms, f_norms)
            
        print("TF-IDF and Norms computed.")
