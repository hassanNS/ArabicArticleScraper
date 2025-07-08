from fpdf import FPDF
import os
import arabic_reshaper
import bidi.algorithm
import logging # Import logging

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

class ArabicPDF(FPDF):
    def __init__(self):
        super().__init__()
        # Register Noto Sans Arabic fonts for comprehensive Arabic support
        noto_regular_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts', 'NotoSansArabic-Regular.ttf')
        noto_bold_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts', 'NotoSansArabic-Bold.ttf')

        self.add_font('NotoSansArabic', '', noto_regular_path, uni=True)
        self.add_font('NotoSansArabic', 'B', noto_bold_path, uni=True)

        # Register Noto Sans (Latin) fonts for comprehensive English/Latin support
        noto_latin_regular_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts', 'NotoSans-Regular.ttf')
        noto_latin_bold_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts', 'NotoSans-Bold.ttf')

        self.add_font('NotoSans', '', noto_latin_regular_path, uni=True)
        self.add_font('NotoSans', 'B', noto_latin_bold_path, uni=True)


def generate_pdf(articles, output_path):
    """
    Generate a PDF file containing the scraped articles.

    Args:
        articles (dict): Dictionary of articles with their titles, content,
                         and English translations.
        output_path (str): Path where the PDF should be saved
    """
    # Ensure fonts directory exists (already handled by the font download commands)
    fonts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
    os.makedirs(fonts_dir, exist_ok=True)

    # Check if Noto Sans Arabic fonts exist
    if not os.path.exists(os.path.join(fonts_dir, 'NotoSansArabic-Regular.ttf')) or \
       not os.path.exists(os.path.join(fonts_dir, 'NotoSansArabic-Bold.ttf')):
        print("Noto Sans Arabic fonts not found. Please download them using the provided curl commands.")
        print(f"Fonts directory: {fonts_dir}")
        return

    # Check if Noto Sans (Latin) fonts exist
    if not os.path.exists(os.path.join(fonts_dir, 'NotoSans-Regular.ttf')) or \
       not os.path.exists(os.path.join(fonts_dir, 'NotoSans-Bold.ttf')):
        print("Noto Sans (Latin) fonts not found. Please download them using the provided curl commands.")
        print(f"Fonts directory: {fonts_dir}")
        return

    # Create PDF with adjusted margins
    pdf = ArabicPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(20, 20, 20)  # Left, Top, Right margins
    page_width = pdf.w - 40  # Total usable width (page width minus margins)

    for url, article in articles.items():
        pdf.add_page()

        # Reshape and reorder Arabic text for proper display
        reshaped_title = arabic_reshaper.reshape(article['title'])
        bidi_title = bidi.algorithm.get_display(reshaped_title)

        reshaped_content = arabic_reshaper.reshape(article['content'])
        bidi_content = bidi.algorithm.get_display(reshaped_content)

        # Arabic title - Centered
        pdf.set_font('NotoSansArabic', 'B', 24)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(page_width, 15, bidi_title, align='C')

        # English title - Centered, reduced font size, increased height
        pdf.set_font('NotoSans', 'B', 16) # Changed to NotoSans Bold
        pdf.set_x(pdf.l_margin) # Explicitly set X to the left margin before rendering the English title
        pdf.multi_cell(page_width, 15, article['title_english'], align='C')

        # Add some space
        pdf.ln(5)

        # Arabic content
        pdf.set_font('NotoSansArabic', '', 16)
        pdf.multi_cell(page_width, 10, bidi_content, align='R')

        # Add space between Arabic and English content
        pdf.ln(10)

        # English content
        pdf.set_font('NotoSans', '', 14) # Changed to NotoSans Regular
        pdf.multi_cell(page_width, 8, article['content_english'], align='L')

        # Add space between articles
        pdf.ln(15)

    # Save the PDF
    pdf.output(output_path)
    print(f"PDF generated successfully at: {output_path}")