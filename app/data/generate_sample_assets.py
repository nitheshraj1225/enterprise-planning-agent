"""
app/data/generate_sample_assets.py

Module 6 prep — generates a synthetic chart image and PDF report so the
vision and PDF features have something real to demo against. Not part of
the corpus itself; built specifically as Module 6 demo inputs.
"""

import os                          # used to create the output folder and build file paths
import matplotlib.pyplot as plt    # the charting library — draws and saves the image
from fpdf import FPDF              # the PDF-writing library — builds and saves the PDF

# Where both generated files will be saved. A subfolder of app/data/, kept
# separate from synthetic_corpus/ since these aren't real corpus documents —
# they're demo assets built specifically for Module 6.
ASSETS_DIR = "app/data/synthetic_assets"


def generate_dashboard_screenshot():
    # Create the folder if it doesn't exist yet. exist_ok=True means
    # "don't error out if it's already there" — safe to call this every run.
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # The fake data for the chart — 4 Epic IDs and their story-point estimates.
    epics = ["EPIC-0213", "EPIC-0034", "EPIC-0210", "EPIC-0187"]
    points = [13, 21, 1, 8]

    # matplotlib's basic pattern: open a figure, draw on it, save it, close it.
    plt.figure(figsize=(6, 4))          # figsize is in inches (width, height)
    plt.bar(epics, points, color="#4C72B0")  # a simple bar chart
    plt.title("Q2 FY26 Epic Sizing Dashboard")
    plt.ylabel("Story Points")
    plt.tight_layout()                  # avoids labels getting cut off at the edges

    # Save the figure to disk as an actual .png file.
    plt.savefig(os.path.join(ASSETS_DIR, "dashboard_screenshot.png"))
    plt.close()                         # frees the figure from memory — good practice
    print("Generated dashboard_screenshot.png")


def generate_epic_report_pdf():
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # FPDF's basic pattern: create a PDF object, add a page, write text onto it.
    pdf = FPDF()
    pdf.add_page()

    # Set the font before writing any text — required by fpdf2.
    pdf.set_font("Helvetica", size=14)
    # cell() writes a single line; ln=True moves to the next line after.
    pdf.cell(0, 10, "Epic Sizing Report - Q2 FY26", ln=True)

    pdf.set_font("Helvetica", size=11)  # smaller font for the body text
    pdf.ln(5)                           # add a bit of vertical spacing

    # multi_cell() writes a block of text that wraps automatically —
    # unlike cell(), which is for a single line.
    pdf.multi_cell(0, 8,
        "EPIC-0213: Migrate billing engine for enterprise integration.\n"
        "Status: Prioritized. Estimated at 13 story points.\n\n"
        "EPIC-0034: Migrate billing engine for data platform.\n"
        "Status: QA. Estimated at 21 story points. Cross-team dependency "
        "must be resolved before completion.\n\n"
        "EPIC-0210: Migrate billing engine for data platform.\n"
        "Status: Open. Estimated at 1 story point."
    )

    # Write the finished PDF to disk.
    pdf.output(os.path.join(ASSETS_DIR, "epic_report.pdf"))
    print("Generated epic_report.pdf")


# Only runs when this file is executed directly (python -m app.data.generate_sample_assets),
# not when it's imported elsewhere — standard Python entry-point pattern,
# same as every other file in this project.
if __name__ == "__main__":
    generate_dashboard_screenshot()
    generate_epic_report_pdf()