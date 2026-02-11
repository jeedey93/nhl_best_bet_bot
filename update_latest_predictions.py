import os
from glob import glob

def get_latest_file(folder, prefix, ext="txt"):
    files = glob(os.path.join(folder, f"{prefix}_*.{ext}"))
    if not files:
        return None
    latest = max(files, key=os.path.getctime)
    return latest

def read_file(path):
    with open(path, "r") as f:
        return f.read()

def update_latest_predictions():
    predictions_dir = "predictions"
    images_dir = "images/generated"
    sports = ["nba", "nhl"]
    output_md = "LATEST_PREDICTIONS.md"

    content = "# Latest Predictions\n\n"
    for sport in sports:
        # Latest predictions text file
        folder = os.path.join(predictions_dir, sport)
        latest_text_file = get_latest_file(folder, f"{sport}_daily_predictions", ext="txt")
        if latest_text_file:
            date_str = os.path.basename(latest_text_file).split("_")[-1].replace(".txt", "")
            content += f"## {sport.upper()} ({date_str})\n"
            content += "```\n" + read_file(latest_text_file) + "\n```\n\n"
        else:
            content += f"## {sport.upper()}\nNo {sport.upper()} predictions found.\n\n"

        # Latest generated image for the sport (use HTML to control size/centering)
        latest_img_file = get_latest_file(images_dir, f"{sport}", ext="png")
        if latest_img_file:
            img_rel_path = latest_img_file.replace("\\", "/")
            # Center and size the image (GitHub supports HTML in Markdown)
            content += (
                f'<p align="center">\n'
                f'  <img src="{img_rel_path}" alt="{sport.upper()} Bet of the Day" width="720" />\n'
                f'</p>\n\n'
            )
        else:
            content += f"(No generated {sport.upper()} image found)\n\n"

    with open(output_md, "w") as f:
        f.write(content)

if __name__ == "__main__":
    update_latest_predictions()
