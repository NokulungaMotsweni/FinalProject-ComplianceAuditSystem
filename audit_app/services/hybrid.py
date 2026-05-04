def hybrid_score(rule_score, tfidf_score):
    score = 0

    if rule_score > 0:
        score += rule_score

    score += tfidf_score * 0.3

    if rule_score > 0 and tfidf_score > 10:
        score += 10

    return min(score, 100)