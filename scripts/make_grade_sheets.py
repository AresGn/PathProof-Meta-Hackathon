"""Render the fictional grade sheets of data/samples/ (E0.3 and E6.1).

Layout follows the public Bac relevé: one table for the written tests, one for
EPS, then the jury block. Coefficients come from data/coefficients_bac_benin.json.
No real name, photo, table number, stamp or signature is drawn.

Usage: python scripts/make_grade_sheets.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"
FONT_DIR = Path("C:/Windows/Fonts")
PAGE_SIZE = (1240, 1754)  # A4 at 150 dpi
BAND_COLORS = ["#e3f1ec", "#f6e7ee", "#eef3dc", "#e7eef8"]
JPEG_QUALITY = 88
GLOBAL_BLUR_RADIUS = 2.4  # still readable overall
CELL_BLUR_RADIUS = 14  # makes one note unreadable to the eye
MIN_GRADE = 0  # docs/prd.md FR-3
MAX_GRADE = 20  # docs/prd.md FR-3

# Group 1 coefficients, data/coefficients_bac_benin.json
SHEETS = {
    "releve_serie_d.jpg": {
        "serie": "D",
        "nom": "Mlle EXEMPLE Ayaba Fictive",
        "naissance": "le 01/01/2008 à Cotonou",
        "table": "000-DX0-000 (jury 000)",
        "ecrit": [
            ("ANGLAIS", 8, 2),
            ("FRANCAIS", 9.5, 2),
            ("HISTOIRE & GEOGRAPHIE", 7, 2),
            ("MATHEMATIQUES", 12, 4),
            ("PHILOSOPHIE", 8, 2),
            ("PHYSIQUE, CHIMIE ET TECHNOLOGIE", 12, 4),
            ("SCIENCES DE LA VIE ET DE LA TERRE", 15, 5),
        ],
        "eps": 10.5,
        "decision": ("Admise", "Passable"),
    },
    "releve_serie_c.jpg": {
        "serie": "C",
        "nom": "M. SPECIMEN Koffi Imaginaire",
        "naissance": "le 01/01/2008 à Porto-Novo",
        "table": "000-CX0-000 (jury 000)",
        "ecrit": [
            ("ANGLAIS", 12, 2),
            ("FRANCAIS", 11, 2),
            ("HISTOIRE & GEOGRAPHIE", 10, 2),
            ("MATHEMATIQUES", 14, 6),
            ("PHILOSOPHIE", 9, 2),
            ("PHYSIQUE, CHIMIE ET TECHNOLOGIE", 13, 5),
            ("SCIENCES DE LA VIE ET DE LA TERRE", 12, 2),
        ],
        "eps": 15,
        "decision": ("Admis", "Assez bien"),
    },
}
SHEETS["releve_serie_d_note_manquante.jpg"] = {
    **SHEETS["releve_serie_d.jpg"],
    "ecrit": [
        (name, None if name == "MATHEMATIQUES" else note, coefficient)
        for name, note, coefficient in SHEETS["releve_serie_d.jpg"]["ecrit"]
    ],
    "no_calculation": True,
    "decision": ("À confirmer", "Non déterminée"),
}
SHEETS["releve_serie_d_note_25.jpg"] = {
    **SHEETS["releve_serie_d.jpg"],
    "ecrit": [
        (name, 25 if name == "MATHEMATIQUES" else note, coefficient)
        for name, note, coefficient in SHEETS["releve_serie_d.jpg"]["ecrit"]
    ],
    "no_calculation": True,
    "decision": ("À confirmer", "Non déterminée"),
}
BLURRED_SOURCE = "releve_serie_d.jpg"
BLURRED_NAME = "releve_serie_d_flou.jpg"
BLURRED_SUBJECT = "MATHEMATIQUES"


def load_font(size: int, is_bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / ("arialbd.ttf" if is_bold else "arial.ttf")), size)


def format_number(value: float) -> str:
    """French decimal comma, no trailing ',0'."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def format_average(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def is_grade_in_range(value: float | None) -> bool:
    return value is not None and MIN_GRADE <= value <= MAX_GRADE


def draw_table(draw: ImageDraw.ImageDraw, top: int, rows: list[tuple], total_row: tuple) -> tuple[int, dict]:
    """Draw one Matière/Note/Coeff/Points/Sur table; return its bottom and note-cell boxes."""
    columns = [90, 590, 730, 850, 1060, 1150]
    row_height = 46
    header_font, body_font, bold_font = load_font(26, True), load_font(25), load_font(25, True)
    headers = ["Matière", "Note /20", "Coeff", "Points obtenus", "Sur"]
    all_rows = [headers] + rows + [total_row]
    bottom = top + row_height * len(all_rows)
    draw.rectangle([columns[0], top, columns[-1], bottom], outline="black", width=3)
    note_cells = {}
    for index, row in enumerate(all_rows):
        y = top + index * row_height
        if index:
            draw.line([columns[0], y, columns[-1], y], fill="#555", width=1)
        font = header_font if index == 0 else bold_font if row is total_row else body_font
        for column, value in enumerate(row):
            left, right = columns[column], columns[column + 1]
            text_width = draw.textlength(str(value), font=font)
            x = left + 14 if column == 0 else (left + right - text_width) / 2
            draw.text((x, y + 9), str(value), fill="black", font=font)
        if 0 < index < len(all_rows) - 1:
            # Note and points together: points / coeff would give the note back
            note_cells[row[0]] = (columns[1] + 2, y + 2, columns[4] - 2, y + row_height - 2)
    for x in columns[1:-1]:
        draw.line([x, top, x, bottom], fill="black", width=2)
    return bottom, note_cells


def render_sheet(sheet: dict) -> tuple[Image.Image, dict, float | None]:
    """Return the page, note-cell boxes and average (None when confirmation is needed)."""
    page = Image.new("RGB", PAGE_SIZE, "white")
    draw = ImageDraw.Draw(page)
    band_width = PAGE_SIZE[0] // 8
    for index in range(8):
        draw.rectangle([index * band_width, 0, (index + 1) * band_width, PAGE_SIZE[1]], fill=BAND_COLORS[index % 4])

    draw.text((90, 60), "SPÉCIMEN FICTIF — données de test PathProof", fill="#b00020", font=load_font(30, True))
    draw.text((90, 110), "Aucune valeur de ce document ne concerne un élève réel.", fill="#b00020", font=load_font(22))
    draw.rectangle([640, 170, 1150, 290], outline="black", width=2, fill="white")
    draw.text((780, 182), "Relevé de notes", fill="black", font=load_font(34, True))
    draw.text((660, 230), "Baccalauréat de l'enseignement secondaire général", fill="black", font=load_font(21))
    draw.text((90, 190), f"Série {sheet['serie']}", fill="black", font=load_font(64, True))

    identity = [("Nom et prénoms", sheet["nom"]), ("Né(e)", sheet["naissance"]), ("Numéro de table", sheet["table"])]
    for index, (label, value) in enumerate(identity):
        y = 340 + index * 44
        draw.text((90, y), label, fill="black", font=load_font(26))
        draw.text((380, y), value, fill="black", font=load_font(26, True))

    draw.text((90, 500), "Épreuves écrites du premier groupe", fill="black", font=load_font(30, True))
    known_rows = [row for row in sheet["ecrit"] if is_grade_in_range(row[1])]
    written_points = sum(note * coefficient for _, note, coefficient in known_rows)
    written_coefficients = sum(coefficient for _, _, coefficient in known_rows)
    rows = [
        (name, "—" if note is None else format_number(note), coefficient,
         format_number(note * coefficient) if is_grade_in_range(note) else "—",
         20 * coefficient)
        for name, note, coefficient in sheet["ecrit"]
    ]
    total_label = "Total des notes valides" if sheet.get("no_calculation") else "Total des épreuves écrites"
    total_average = "—" if sheet.get("no_calculation") else format_average(written_points / written_coefficients)
    total = (total_label, total_average,
             written_coefficients, format_number(written_points), 20 * written_coefficients)
    bottom, note_cells = draw_table(draw, 550, rows, total)

    group_points = written_points + sheet["eps"]
    group_coefficients = written_coefficients + 1
    average = None if sheet.get("no_calculation") else group_points / group_coefficients
    eps_rows = [("EDUCATION PHYSIQUE ET SPORTIVE", format_number(sheet["eps"]), 1, format_number(sheet["eps"]), 20)]
    group_average = "—" if average is None else format_average(average)
    eps_total = ("Total du 1er groupe", group_average, group_coefficients,
                 format_number(group_points), 20 * group_coefficients)
    bottom, _ = draw_table(draw, bottom + 50, eps_rows, eps_total)

    decision, mention = sheet["decision"]
    jury_average = "Non calculée" if average is None else f"{format_average(average)}/20"
    jury = [("Décision du jury", decision), ("Mention", mention), ("Moyenne", jury_average)]
    for index, (label, value) in enumerate(jury):
        y = bottom + 80 + index * 52
        draw.text((90, y), label, fill="black", font=load_font(30))
        draw.text((400, y), value, fill="black", font=load_font(30, True))
    draw.text((90, PAGE_SIZE[1] - 90), "Document fictif généré par scripts/make_grade_sheets.py — sans valeur officielle.",
              fill="#b00020", font=load_font(22))
    return page, note_cells, average


def blur_sheet(page: Image.Image, cell_box: tuple) -> Image.Image:
    """Blur one row's note and points until unreadable, then blur the whole photo."""
    unreadable = page.crop(cell_box).filter(ImageFilter.GaussianBlur(CELL_BLUR_RADIUS))
    page_with_hidden_note = page.copy()
    page_with_hidden_note.paste(unreadable, cell_box[:2])
    blurred = page_with_hidden_note.rotate(-1.5, resample=Image.BICUBIC, fillcolor="#777")
    return blurred.filter(ImageFilter.GaussianBlur(GLOBAL_BLUR_RADIUS))


def main() -> None:
    for file_name, sheet in SHEETS.items():
        page, note_cells, average = render_sheet(sheet)
        page.save(SAMPLES_DIR / file_name, quality=JPEG_QUALITY)
        average_text = "non calculée (note manquante)" if average is None else f"{average:.4f}"
        print(f"{file_name}: moyenne {average_text}")
        if file_name == BLURRED_SOURCE:
            blur_sheet(page, note_cells[BLURRED_SUBJECT]).save(SAMPLES_DIR / BLURRED_NAME, quality=JPEG_QUALITY)
            print(f"{BLURRED_NAME}: note {BLURRED_SUBJECT} illisible")


if __name__ == "__main__":
    main()
