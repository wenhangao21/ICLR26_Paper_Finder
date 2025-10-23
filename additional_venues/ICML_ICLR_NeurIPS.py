import openreview
from openreview import tools
import json
import re
import textwrap
from collections import Counter
from datetime import datetime
import argparse
from IPython import embed
import os

def get_submissions(conf_name: str, year: int, email: str = None, 
                    password: str = None, state: str = 'Submitted'):
    """
    Retrieve all submissions for a given OpenReview conference.

    Args:
        conf_name (str): e.g. "ICLR", "NeurIPS", or "ICML"
        year (int): conference year (e.g. 2023)
        email (str, optional): your OpenReview email (for higher rate limits)
        password (str, optional): your OpenReview password

    Returns:
        list[openreview.Note]: list of submission notes
    """
    prefix = f"{conf_name}.cc"
    venue = f"{prefix}/{year}/Conference"

    # --- Try API v2 (used for 2023+ venues like ICLR 2024, 2025, etc.) ---
    try:
        client_v2 = openreview.api.OpenReviewClient(
            baseurl="https://api2.openreview.net",
            username=email,
            password=password,
        )
        v2_inv = f"{venue}/-/Submission"
        notes = list(tools.iterget_notes(client_v2, invitation=v2_inv))
        if state == 'Accepted' and conf_name == 'ICLR':
            filtered = []
            for n in notes:
                venue_str = n.content.get("venue", "")
                if venue_str['value'].find('Submi') < 0:
                    filtered.append(n)
            notes = filtered
        if notes:
            print(f"Found {len(notes)} submissions via API v2 ({v2_inv})")
            return notes
    except Exception as e:
        print(f"[API v2] Failed or no notes found: {e}")

    # --- Fallback: API v1 (used for ≤2022 or some 2023 venues) ---
    try:
        client_v1 = openreview.Client(
            baseurl="https://api.openreview.net",
            username=email,
            password=password,
        )

        possible_invitations = [
            f"{venue}/-/Blind_Submission",                # common for ICLR/NeurIPS/ICML ≤2022
            f"{prefix}/{year}/conference/-/submission",   # older lowercase form
        ]

        for inv in possible_invitations:
            try:
                notes = list(tools.iterget_notes(client_v1, invitation=inv))
                if state == 'Accepted' and conf_name == 'ICLR':
                    filtered = []
                    for n in notes:
                        venue_str = n.content.get("venue", "")
                        if venue_str.find('Submi') < 0:
                            filtered.append(n)
                    notes = filtered
                if notes:
                    print(f"Found {len(notes)} submissions via API v1 ({inv})")
                    return notes
            except Exception:
                continue

    except Exception as e:
        print(f"[API v1] Failed or no notes found: {e}")

    print("No submissions found for this venue/year.")
    return []

def main(args):

    notes = get_submissions(args.conf_name, args.year, args.email, 
                            args.password, args.state)
    
    # Check how many submissions there are
    print(f"Total submissions: {len(notes)}")
    # Get all the possible atrributes
    key_counter = Counter(k for note in notes for k in note.content.keys())
    print("\nAttribute occurrence counts:")
    for key, count in key_counter.items():
        print(f"  {key}: {count}")

    json_data = []
    for note in notes:
        # Extract title value safely
        title_val = note.content.get("title", "")
        if isinstance(title_val, dict) and "value" in title_val:
            title_val = title_val["value"]
        # Skip notes where title starts with 'Null' followed by any non-space chars (one word)
        if isinstance(title_val, str) and re.fullmatch(r"Null\S+", title_val):
            continue
        entry = {}
        for key, value in note.content.items():
            # Safely extract inner value if present
            if isinstance(value, dict) and "value" in value:
                val = str(value["value"])
            else:
                val = str(value)
            # Special handling for 'pdf' field
            if key == "pdf":
                # Prepend if it's not already a full URL
                if val and not val.startswith("https://openreview.net/"):
                    val = "https://openreview.net/" + val.lstrip("/")
                entry['link'] = val
            else:
                entry[key] = val
        json_data.append(entry)

    # Save to JSON file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") # They update the submission list, so timestamps are added
    filename = f"notes_{args.conf_name}{args.year}_{args.state}_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Openreview-based')
    parser.add_argument('--email', type=str, help='Email of your openreview profile')
    parser.add_argument('--password', type=str, help='password of your openreview profile')
    parser.add_argument('--conf_name', type=str, help='Conference Name: ICML, ICLR, NeurIPS')
    parser.add_argument('--year', type=str, help='corresponding year')
    parser.add_argument('--state', type=str, help='State of paper: Accepted/Submission')
    
    args = parser.parse_args()

    main(args)
