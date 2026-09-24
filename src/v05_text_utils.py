def normalize_text(text):
    return text.strip().lower().replace("\n", " ").replace("\t", " ").replace(" ", "")

def word_count(text):
    normalized_text = normalize_text(text)
    return len(normalized_text.split()) if normalized_text else 0