import pdfplumber

pdf_path = "Vystar_General_0pt.pdf"
output_path = "results.txt"

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]

    words = page.extract_words()

    with open(output_path, "w", encoding="utf-8") as f:
        for word in words:
            line = (f"{word['text']:>20}  -->  "
                    f"x0: {word['x0']:.2f}, top: {word['top']:.2f}, "
                    f"x1: {word['x1']:.2f}, bottom: {word['bottom']:.2f}\n")
            f.write(line)

    print(f"✅ Coordinates saved to: {output_path}")

    # Visual aid (optional)
    page.to_image(resolution=150).draw_rects(words).show()

input("Press Enter to exit...")
