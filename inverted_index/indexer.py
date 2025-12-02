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
        self.dictionary = defaultdict(list)
        self.block_count = 0
        self.doc_lengths = {}

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def add_document(self, doc_id: int, tokens: List[str]):
        term_freqs = defaultdict(int)
        for token in tokens:
            term_freqs[token] += 1

        for term, tf in term_freqs.items():
            self.dictionary[term].append((doc_id, tf))

        if len(self.dictionary) >= self.block_size_limit:
            self.write_block_to_disk()

    def write_block_to_disk(self):
        if not self.dictionary:
            return

        sorted_terms = sorted(self.dictionary.keys())

        block_path = os.path.join(self.output_dir, f"block_{self.block_count}.dat")
        with open(block_path, 'wb') as f:
            block_data = []
            for term in sorted_terms:
                block_data.append((term, self.dictionary[term]))
            pickle.dump(block_data, f)

        print(f"Block {self.block_count} written to {block_path}")
        self.block_count += 1
        self.dictionary.clear()

    def merge_blocks(self):
        print("Merging blocks hierarchically...")

        MAX_OPEN_FILES = 10

        pending_blocks = [
            os.path.join(self.output_dir, f"block_{i}.dat")
            for i in range(self.block_count)
            if os.path.exists(os.path.join(self.output_dir, f"block_{i}.dat"))
        ]

        level = 0

        while len(pending_blocks) > MAX_OPEN_FILES:
            print(f"--- Merge Level {level} (Blocks: {len(pending_blocks)}) ---")
            next_level_blocks = []
            batch_counter = 0

            for i in range(0, len(pending_blocks), MAX_OPEN_FILES):
                batch_files = pending_blocks[i: i + MAX_OPEN_FILES]

                merged_filename = os.path.join(self.output_dir, f"merged_lvl{level}_{batch_counter}.dat")
                self._merge_batch(batch_files, merged_filename, is_final=False)

                next_level_blocks.append(merged_filename)
                batch_counter += 1

            pending_blocks = next_level_blocks
            level += 1

        print(f"--- Final Merge (Blocks: {len(pending_blocks)}) ---")
        final_index_path = os.path.join(self.output_dir, "inverted_index.dat")
        self._merge_batch(pending_blocks, final_index_path, is_final=True)
        print("Merge completed.")

    def _merge_batch(self, input_files: List[str], output_file: str, is_final: bool):
        open_files = []
        iterators = []
        heap = []

        for i, filepath in enumerate(input_files):
            try:
                f = open(filepath, 'rb')
                open_files.append(f)
                data = pickle.load(f)
                it = iter(data)

                first_term, first_postings = next(it)
                heapq.heappush(heap, (first_term, first_postings, i))
                iterators.append(it)
            except (EOFError, StopIteration, FileNotFoundError):
                pass

        output_data = []

        current_term = None
        current_postings = []

        while heap:
            term, postings, idx = heapq.heappop(heap)

            if current_term is None:
                current_term = term

            if term != current_term:
                output_data.append((current_term, current_postings))
                current_term = term
                current_postings = []

            current_postings.extend(postings)

            try:
                next_term, next_postings = next(iterators[idx])
                heapq.heappush(heap, (next_term, next_postings, idx))
            except StopIteration:
                pass

        if current_term:
            output_data.append((current_term, current_postings))

        with open(output_file, 'wb') as out_f:
            if is_final:
                for item in output_data:
                    pickle.dump(item, out_f)
            else:
                pickle.dump(output_data, out_f)

        for f in open_files:
            f.close()

    def compute_tfidf_and_norms(self, total_docs: int):
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

        doc_norms = {k: math.sqrt(v) for k, v in doc_norms.items()}
        with open(norms_path, 'wb') as f_norms:
            pickle.dump(doc_norms, f_norms)

        print("TF-IDF and Norms computed.")
