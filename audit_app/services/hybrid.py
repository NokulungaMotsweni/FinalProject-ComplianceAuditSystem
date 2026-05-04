def hybrid_score(rule_score, tfidf_score, tfidf_weight=1.0):
    score = 0

    if rule_score > 0:
        score += rule_score

    score += tfidf_score * tfidf_weight

    if rule_score > 0 and tfidf_score > 10:
        score += 10

    # if TF-IDF is strong enough on its own, don't suppress it
    if rule_score == 0 and tfidf_score >= 30:
        score = max(score, tfidf_score * 0.6)

    return min(score, 100)