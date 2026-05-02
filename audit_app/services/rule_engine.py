from typing import TypedDict, List

class Rule(TypedDict):
    name: str
    keywords: List[str]
    score: int
    reason: str

class RuleBasedDetector:

    RULES = [
        {
            "name": "off_channel",
            "keywords": ["whatsapp", "telegram", "personal email"],
            "score": 40,
            "reason": "Off-channel communication attempt"
        },
        {
            "name": "guarantee",
            "keywords": ["guaranteed return", "no risk", "100% safe"],
            "score": 50,
            "reason": "Potential misleading guarantee"
        },
        {
            "name": "sensitive_info",
            "keywords": ["password", "account number", "login details"],
            "score": 60,
            "reason": "Sensitive information disclosure"
        },
        {
            "name": "process_pressure",
            "keywords": [ "just approve","push this through","dont flag",
                        "skip compliance","no need to review","do it quickly"
                        ],
            "score": 40,
            "reason": "Potential internal pressure to bypass compliance"
        },
        {
            "name": "conduct",
            "keywords": ["idiot", "stupid", "shut up"],
            "score": 30,
            "reason": "Inappropriate conduct"
        },
        {
            "name": "market_manipulation",
            "keywords": ["no intent to fill", "push the price", "layering", "wash trade", "spoof"],
            "score": 70,
            "reason": "Potential market manipulation"
        },
        {
            "name": "insider_trading",
            "keywords": ["mnpi", "non-public", "before the announcement", "ahead of the report"],
            "score": 80,
            "reason": "Potential insider trading"
        },
        {
            "name": "churning",
            "keywords": ["churning", "commissions are stacking", "keep trading", "generate activity"],
            "score": 60,
            "reason": "Potential churning / excessive trading"
        },
    ]

    @classmethod
    def analyse(cls, text):
        text = text.lower()

        total_score = 0
        triggered = []

        for rule in cls.RULES:
            for keyword in rule["keywords"]:
                if keyword in text:
                    total_score += rule["score"]
                    triggered.append(f"{rule['name']}: '{keyword}'")
                    break

        return total_score, "; ".join(triggered)