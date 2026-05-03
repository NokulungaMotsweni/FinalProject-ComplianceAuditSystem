from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


class TFIDFDetector:

    @staticmethod
    def analyse(messages):
        """
        messages = queryset or list of Message objects
        """

        texts = [m.message_text for m in messages]

        if not texts:
            return []

        vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
        )

        tfidf_matrix = vectorizer.fit_transform(texts)

        # Convert to array
        scores = np.asarray(tfidf_matrix.max(axis=1).todense()).flatten()

        return scores