import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer
import ssl
import os

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Setup local NLTK data path
# We use a relative path 'nltk_data' inside the current working directory or a specific data dir
# For now, let's keep it relative to CWD, assuming the app runs from root
nltk_data_dir = os.path.join(os.getcwd(), "nltk_data")
if not os.path.exists(nltk_data_dir):
    os.makedirs(nltk_data_dir)
nltk.data.path.append(nltk_data_dir)

# Ensure necessary NLTK data is downloaded to local dir
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Downloading punkt to local dir...")
    nltk.download('punkt', download_dir=nltk_data_dir)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    print("Downloading stopwords to local dir...")
    nltk.download('stopwords', download_dir=nltk_data_dir)

class TextPreprocessor:
    def __init__(self, language='spanish'):
        self.stop_words = set(stopwords.words(language))
        self.stemmer = SnowballStemmer(language)
        
    def preprocess(self, text: str) -> list[str]:
        """
        Applies the full preprocessing pipeline:
        1. Lowercase
        2. Remove non-alphanumeric characters
        3. Tokenize
        4. Remove stopwords
        5. Stemming
        """
        if not text:
            return []
            
        # 1. Lowercase
        text = text.lower()
        
        # 2. Remove non-alphanumeric characters (keep spaces)
        # This regex keeps letters, numbers and spaces. 
        # Adjust if you need to keep specific punctuation.
        text = re.sub(r'[^a-záéíóúñ0-9\s]', '', text)
        
        # 3. Tokenize
        tokens = nltk.word_tokenize(text)
        
        # 4. Filter Stopwords & 5. Stemming
        processed_tokens = [
            self.stemmer.stem(token) 
            for token in tokens 
            if token not in self.stop_words and len(token) > 1
        ]
        
        return processed_tokens
