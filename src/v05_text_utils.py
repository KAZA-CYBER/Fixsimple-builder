import re

def normalize_text(text):
    # Strip leading and trailing whitespace
    text = text.strip()
    # Convert text to lowercase
    text = text.lower()
    # Collapse every run of internal whitespace to exactly one ASCII space
    text = re.sub(r'\s+', ' ', text)
    return text

def word_count(text):
    # Normalize the text
    normalized_text = normalize_text(text)
    # Split the text into words and count them
    words = normalized_text.split()
    return len(words)