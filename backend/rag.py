import json
from pathlib import Path
from typing import Any, Dict, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_PATH = Path(__file__).parent / "data" / "knowledge_base.json"

class KnowledgeRetriever:
    def __init__(self):
        self.documents = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        self.texts = [
            f"{d['title']} {d['topic']} {d['text']} {' '.join(d.get('keywords', []))}"
            for d in self.documents
        ]
        self.vectorizer = TfidfVectorizer(
            lowercase=True, stop_words="english", ngram_range=(1, 2), min_df=1
        )
        self.matrix = self.vectorizer.fit_transform(self.texts)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            return []
        q = self.vectorizer.transform([query])
        scores = cosine_similarity(q, self.matrix)[0]
        ranked = scores.argsort()[::-1][:top_k]
        results = []
        for i in ranked:
            if scores[i] <= 0:
                continue
            item = dict(self.documents[i])
            item["similarity"] = round(float(scores[i]), 4)
            results.append(item)
        return results

    def all_documents(self):
        return self.documents
