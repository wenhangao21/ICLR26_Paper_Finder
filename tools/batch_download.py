import os
import re
import requests

# === Configuration === 
!!!!!!CHANGE THE PATH HERE!!!!!!
input_file = "ai-paper-finder.info search results.txt"  # Path to your text file
save_dir = "pdf_downloads"  # Folder to save PDFs
os.makedirs(save_dir, exist_ok=True)

# === Read file ===
with open(input_file, "r", encoding="utf-8") as f:
    text = f.read()

# === Split into entries by the line of dashes (or other separator) ===
entries = re.split(r"-{5,}", text)

papers = []
for entry in entries:
    title_match = re.search(r"Title:\s*(.*)", entry)
    venue_match = re.search(r"Venue:\s*(.*)", entry)
    link_match = re.search(r"Link:\s*(https?://\S+\.pdf)", entry)

    if title_match and venue_match and link_match:
        title = title_match.group(1).strip()
        venue = venue_match.group(1).strip()
        link = link_match.group(1).strip()
        papers.append((title, venue, link))

print(f"Found {len(papers)} papers with PDF links.")

# === Ask once ===
choice = input(f"Download all {len(papers)} PDFs? (y/n): ").strip().lower()

if choice == "y":
    for i, (title, venue, link) in enumerate(papers, 1):
        # Clean filename: remove illegal characters
        safe_title = re.sub(r'[^a-zA-Z0-9_\- ]', '', title)
        safe_venue = re.sub(r'[^a-zA-Z0-9_\- ]', '', venue)
        filename = f"{safe_venue} - {safe_title}.pdf"
        filepath = os.path.join(save_dir, filename)

        try:
            print(f"[{i}/{len(papers)}] Downloading {filename} ...")
            response = requests.get(link)
            response.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"Saved to {filepath}")
        except Exception as e:
            print(f"Failed to download {link}: {e}")
    print("\nAll downloads completed.")
else:
    print("Download cancelled.")
