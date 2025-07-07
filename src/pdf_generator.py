from fpdf import FPDF
import os
import arabic_reshaper
import bidi.algorithm

class ArabicPDF(FPDF):
    def __init__(self):
        super().__init__()
        # Register Noto Sans Arabic fonts for comprehensive Arabic support
        noto_regular_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts', 'NotoSansArabic-Regular.ttf')
        noto_bold_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts', 'NotoSansArabic-Bold.ttf')

        self.add_font('NotoSansArabic', '', noto_regular_path, uni=True)
        self.add_font('NotoSansArabic', 'B', noto_bold_path, uni=True)

def generate_pdf(articles, output_path):
    """
    Generate a PDF file containing the scraped articles.

    Args:
        articles (dict): Dictionary of articles with their titles and content
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

    # Create PDF with adjusted margins
    pdf = ArabicPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(20, 20, 20)  # Left, Top, Right margins

    for url, article in articles.items():
        pdf.add_page()

        # Reshape and reorder Arabic text for proper display
        reshaped_title = arabic_reshaper.reshape(article['title'])
        bidi_title = bidi.algorithm.get_display(reshaped_title)

        reshaped_content = arabic_reshaper.reshape(article['content'])
        bidi_content = bidi.algorithm.get_display(reshaped_content)

        # Arabic title
        pdf.set_font('NotoSansArabic', 'B', 24) # Using Noto Sans Arabic Bold for title
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(160, 15, bidi_title, align='R')

        # English title
        pdf.set_font('NotoSansArabic', 'B', 18) # Using Noto Sans Arabic Bold for English title
        pdf.multi_cell(160, 12, article['title_english'], align='L')

        # Add some space
        pdf.ln(5)

        # Arabic content
        pdf.set_font('NotoSansArabic', '', 16) # Using Noto Sans Arabic Regular for content
        pdf.multi_cell(160, 10, bidi_content, align='R')

        # Add space between articles
        pdf.ln(15)

    # Save the PDF
    pdf.output(output_path)
    print(f"PDF generated successfully at: {output_path}")