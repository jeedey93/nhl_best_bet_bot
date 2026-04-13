import os
import sys
import time
from datetime import date
from dotenv import load_dotenv
from google import genai
import re

load_dotenv()

def read_prompt(prompt_path):
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def ensure_confidence_line(text):
    # Regex to find play headers (e.g., **Boston Bruins ML vs Philadelphia Flyers @ 1.94** or without @)
    # Updated to match headers with or without odds
    play_header_pattern = re.compile(r"^(\*\*.+?(vs|ML|over|under|\+|-).+?\*\*)$", re.MULTILINE)
    # Regex to find confidence line
    confidence_pattern = re.compile(r"Confidence Level: .+?Units: .+?Win Probability: .+?%", re.IGNORECASE)

    lines = text.split('\n')
    output_lines = []
    i = 0
    while i < len(lines):
        output_lines.append(lines[i])
        # If this is a play header, check if the next 5 lines contain a confidence line
        if play_header_pattern.match(lines[i]):
            found_conf = False
            for j in range(1, 6):
                if i + j < len(lines) and confidence_pattern.search(lines[i + j]):
                    found_conf = True
                    break
            if not found_conf:
                # Try to extract confidence info from the next lines, else add a placeholder
                output_lines.append("Confidence Level: [Unknown] Units: [Unknown] | Win Probability: [Unknown]%")
        i += 1
    return '\n'.join(output_lines)

def compare_predictions(morning_file, noon_file, output_file, prompt_path):
    """
    Compare morning (7am) and afternoon (3pm) NHL predictions and generate a combined analysis.
    """
    api_key = os.environ["GOOGLE_API_KEY"]
    client = genai.Client(api_key=api_key)

    # Read both prediction files
    try:
        with open(morning_file, "r", encoding="utf-8") as f:
            morning_predictions = f.read()
    except FileNotFoundError:
        print(f"Morning predictions file not found: {morning_file}")
        return

    try:
        with open(noon_file, "r", encoding="utf-8") as f:
            noon_predictions = f.read()
    except FileNotFoundError:
        print(f"Noon predictions file not found: {noon_file}")
        return

    # Read the comparison prompt from file
    comparison_prompt_template = read_prompt(prompt_path)
    comparison_prompt = comparison_prompt_template.format(
        morning_predictions=morning_predictions,
        noon_predictions=noon_predictions
    )

    models_to_try = [
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-2.0-flash-lite",
        "models/gemini-2.5-flash-lite",
    ]

    retry_waits = [30, 60]

    for model in models_to_try:
        max_retries = len(retry_waits) + 1
        for attempt in range(max_retries):
            try:
                print(f"🤖 Trying {model}...")
                response = client.models.generate_content(
                    model=model,
                    contents=comparison_prompt,
                )
                combined_analysis = response.text.strip()
                # Ensure confidence line is present after each play
                combined_analysis = ensure_confidence_line(combined_analysis)

                # Write combined analysis to output file
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(combined_analysis)

                print(f"✅ Combined analysis saved to: {output_file}")
                print("\n" + combined_analysis)

                return combined_analysis

            except genai.errors.ServerError as e:
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    if attempt < max_retries - 1:
                        wait_time = retry_waits[attempt]
                        print(f"⚠️ {model} 503 error. Retrying in {wait_time}s... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        print(f"⚠️ {model} still unavailable, trying next model...")
                        break
                else:
                    raise
            except genai.errors.ClientError as e:
                if "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e):
                    print(f"⚠️ {model} quota exceeded, trying next model...")
                    break
                else:
                    raise

    print("❌ All Gemini models unavailable. Cancelling workflow.")
    sys.exit(1)


def main():
    """Main function to compare morning and noon NHL predictions."""
    today_str = date.today().isoformat()
    predictions_folder = os.path.join("data", "predictions", "nhl")
    daily_runs_folder = os.path.join(predictions_folder, "daily_runs")
    prompt_path = os.path.join("prompts", "compare_prompt.txt")

    # Read from daily_runs folder
    morning_file = os.path.join(daily_runs_folder, f"nhl_daily_predictions_{today_str}_7am.txt")
    noon_file = os.path.join(daily_runs_folder, f"nhl_daily_predictions_{today_str}_3pm.txt")
    # Write final output to main predictions folder
    output_file = os.path.join(predictions_folder, f"nhl_daily_predictions_{today_str}.txt")

    # Check if both files exist
    if not os.path.exists(morning_file):
        print(f"⚠️  Morning predictions file not found: {morning_file}")
        return

    if not os.path.exists(noon_file):
        print(f"⚠️  Noon predictions file not found: {noon_file}")
        return

    # Check if output file already exists - skip if it does
    if os.path.exists(output_file):
        print(f"⚠️  Combined predictions file already exists: {output_file}")
        print("Skipping comparison to avoid overwriting existing file.")
        return

    print(f"Comparing NHL predictions from {today_str}...")
    print(f"Morning file: {morning_file}")
    print(f"Noon file: {noon_file}")

    # Run comparison
    compare_predictions(morning_file, noon_file, output_file, prompt_path)

if __name__ == "__main__":
    main()
