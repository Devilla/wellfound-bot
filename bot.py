import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
import anthropic
import wellfound

load_dotenv()

SYSTEM_PROMPT = (
    "You are a software engineer writing a response to the Wellfound application "
    'question: "What interests you about working for this company?"\n\n'
    "Write a genuine, concise response (2-3 short paragraphs) based on the job "
    "description provided. Focus on:\n"
    "- The company's mission and what makes it compelling\n"
    "- How the role and tech stack align with your skills and growth goals\n"
    "- Specific product or technical aspects that excite you\n\n"
    "Be authentic and specific. Reference concrete details from the description. "
    "Avoid generic flattery or buzzwords.\n\n"
    "IMPORTANT: Output ONLY the response text itself. Do not include any preamble, "
    "introduction, or meta-commentary like 'Here is a response...' and do not wrap "
    "the response in --- delimiters."
)


def make_answer_fn(claude_client):
    def generate_answer(company_name, job_title, description):
        message = claude_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Company: {company_name}\n"
                        f"Job Title: {job_title}\n\n"
                        f"Job Description:\n{description}"
                    ),
                }
            ],
        )
        text = message.content[0].text
        text = re.sub(r'^.*?---\s*', '', text, count=1, flags=re.DOTALL)
        text = re.sub(r'\s*---\s*$', '', text)
        return text.strip()
    return generate_answer


def main():
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not email or not password:
        print("Error: EMAIL and PASSWORD must be set in .env")
        return
    if not api_key:
        print("Error: ANTHROPIC_API_KEY must be set in .env")
        return

    claude = anthropic.Anthropic(api_key=api_key)
    answer_fn = make_answer_fn(claude)

    client = wellfound.Wellfound()
    client.login(email=email, password=password)

    print("\nBrowsing jobs...")
    jobs = client.browse_jobs(num_scrolls=5, answer_fn=answer_fn)

    if not jobs:
        print("No jobs found.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = f"answers_{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump(jobs, f, indent=2)

    print(f"\nDone! Saved {len(jobs)} answers to {output_file}")


if __name__ == "__main__":
    main()
