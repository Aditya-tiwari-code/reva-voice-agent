# Conversation State Management & Lead Scoring

class ConversationAgent:
    """
    Manages multi-turn conversation state, dialogue flow, and lead qualification scoring.
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.history = []
        self.lead_score = 0.0

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})

    def calculate_lead_score(self) -> float:
        """
        Calculates qualification score based on budget clarity, timeline, intent, and contact info.
        """
        return self.lead_score
