import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from inverted_index.preprocessing import TextPreprocessor
from inverted_index.indexer import SPIMIIndexer

def test_components():
    print("Testing TextPreprocessor...")
    try:
        p = TextPreprocessor()
        text = "El aprendizaje automático es una rama de la inteligencia artificial."
        tokens = p.preprocess(text)
        print(f"Text: '{text}'")
        print(f"Tokens: {tokens}")
        
        if not tokens:
            print("[ERROR] Tokens are empty!")
        else:
            print("[OK] Preprocessing works.")
            
    except Exception as e:
        print(f"[ERROR] Preprocessor failed: {e}")
        return

    print("\nTesting SPIMIIndexer...")
    output_dir = "debug_bow_output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    try:
        indexer = SPIMIIndexer(output_dir=output_dir)
        indexer.add_document(1, tokens)
        print(f"Dictionary size: {len(indexer.dictionary)}")
        
        indexer.write_block_to_disk()
        print("Block written.")
        
        indexer.merge_blocks()
        print("Blocks merged.")
        
        indexer.compute_tfidf_and_norms(total_docs=1)
        print("TF-IDF computed.")
        
        files = os.listdir(output_dir)
        print(f"Files in {output_dir}: {files}")
        
        if "tfidf_index.dat" in files:
            print("[OK] Indexer works.")
        else:
            print("[ERROR] tfidf_index.dat missing.")
            
    except Exception as e:
        print(f"[ERROR] Indexer failed: {e}")

if __name__ == "__main__":
    test_components()
