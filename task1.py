import requests
import json
from decouple import config
from typing import Dict, Tuple, List

# Configuration
API_KEY = config('OPENROUTER_API')
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-4o"

# System prompt that defines AI behavior
SYSTEM_PROMPT = """You are a helpful, harmless, and honest AI assistant. 
You provide accurate information and refuse to help with harmful, illegal, or unethical requests.
You should be polite, professional, and respectful in all interactions."""

# Moderation keywords - expand this list based on your needs
BANNED_KEYWORDS = [
    "kill", "murder", "hack", "bomb", "exploit", "steal",
    "drug", "weapon", "terror", "abuse", "scam", "fraud",
    "suicide", "self-harm", "violence", "illegal"
]

# Sensitive patterns that require careful handling
SENSITIVE_PATTERNS = [
    "how to make", "how do i", "teach me to", "help me",
    "instructions for", "guide to", "steps to"
]


class ModerationSystem:
    """Handles content moderation for AI chat interactions"""

    def __init__(self, banned_keywords: List[str]):
        self.banned_keywords = [keyword.lower() for keyword in banned_keywords]

    def check_input(self, text: str) -> Tuple[bool, str]:
        """
        Check if input contains banned content
        Returns: (is_safe, reason)
        """
        text_lower = text.lower()

        # Check for banned keywords
        for keyword in self.banned_keywords:
            if keyword in text_lower:
                return False, f"Input contains prohibited content: '{keyword}'"

        # Check for suspicious combinations
        for pattern in SENSITIVE_PATTERNS:
            if pattern in text_lower:
                for keyword in self.banned_keywords:
                    if keyword in text_lower:
                        return False, f"Input contains potentially harmful request"

        return True, "Input passed moderation"

    def moderate_output(self, text: str) -> Tuple[str, bool]:
        """
        Moderate AI output by redacting banned content
        Returns: (moderated_text, was_modified)
        """
        moderated_text = text
        was_modified = False

        # Replace banned keywords with [REDACTED]
        for keyword in self.banned_keywords:
            if keyword in moderated_text.lower():
                # Case-insensitive replacement
                import re
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                moderated_text = pattern.sub("[REDACTED]", moderated_text)
                was_modified = True

        return moderated_text, was_modified


class AIChat:
    """Handles AI chat interactions with moderation"""

    def __init__(self, api_key: str, api_url: str, model: str):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.moderator = ModerationSystem(BANNED_KEYWORDS)

    def send_message(self, user_prompt: str, system_prompt: str = SYSTEM_PROMPT) -> Dict:
        """
        Send message to AI with moderation checks
        Returns: Dictionary with status, message, and moderation info
        """

        # Step 1: Input Moderation
        print("\n🔍 Checking input moderation...")
        is_safe, reason = self.moderator.check_input(user_prompt)

        if not is_safe:
            return {
                "status": "blocked",
                "message": "Your input violated the moderation policy.",
                "reason": reason,
                "moderation": "input_blocked"
            }

        print("✅ Input passed moderation")

        # Step 2: Send to AI API
        print("🤖 Sending request to AI...")

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )

            response.raise_for_status()
            ai_response = response.json()

            # Extract AI message
            ai_message = ai_response['choices'][0]['message']['content']

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "message": f"API Error: {str(e)}",
                "moderation": "none"
            }

        # Step 3: Output Moderation
        print("🔍 Checking output moderation...")
        moderated_message, was_modified = self.moderator.moderate_output(ai_message)

        if was_modified:
            print("⚠️  Output contained restricted content - redacted")
            return {
                "status": "moderated",
                "message": moderated_message,
                "moderation": "output_redacted",
                "warning": "Response contained restricted content that was redacted"
            }

        print("✅ Output passed moderation")

        return {
            "status": "success",
            "message": moderated_message,
            "moderation": "passed"
        }


def main():
    """Main interactive function"""

    print("=" * 60)
    print("🤖 AI Chat with Content Moderation")
    print("=" * 60)
    print("\nThis chatbot includes moderation to ensure safe interactions.")
    print("Type 'exit' to quit, 'test' to run moderation tests.\n")

    # Initialize chat system
    chat = AIChat(API_KEY, API_URL, MODEL)

    while True:
        # Get user input
        user_input = input("\n💬 You: ").strip()

        if not user_input:
            print("⚠️  Please enter a message")
            continue

        if user_input.lower() == 'exit':
            print("\n👋 Goodbye!")
            break

        if user_input.lower() == 'test':
            run_tests(chat)
            continue

        # Send message with moderation
        result = chat.send_message(user_input)

        # Display result
        print("\n" + "=" * 60)
        if result["status"] == "blocked":
            print(f"🚫 BLOCKED: {result['message']}")
            print(f"   Reason: {result['reason']}")
        elif result["status"] == "moderated":
            print(f"⚠️  AI (Moderated): {result['message']}")
            print(f"   Warning: {result['warning']}")
        elif result["status"] == "success":
            print(f"🤖 AI: {result['message']}")
        else:
            print(f"❌ ERROR: {result['message']}")
        print("=" * 60)


def run_tests(chat: AIChat):
    """Run moderation test cases"""

    print("\n" + "=" * 60)
    print("🧪 Running Moderation Tests")
    print("=" * 60)

    test_cases = [
        ("What is the capital of France?", "Should pass"),
        ("How do I bake a cake?", "Should pass"),
        ("Teach me how to hack a website", "Should be blocked"),
        ("How to make a bomb", "Should be blocked"),
        ("Tell me about cybersecurity", "Should pass"),
    ]

    for i, (prompt, expected) in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {expected} ---")
        print(f"Input: {prompt}")

        result = chat.send_message(prompt)

        if result["status"] == "blocked":
            print(f"✅ Result: BLOCKED - {result['reason']}")
        elif result["status"] == "moderated":
            print(f"⚠️  Result: MODERATED - Some content redacted")
            print(f"Response: {result['message'][:100]}...")
        else:
            print(f"✅ Result: PASSED")
            print(f"Response: {result['message'][:100]}...")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()