from flask import Flask, render_template, request, jsonify, send_file
# NEW IMPORTS for pyspellchecker
from spellchecker import SpellChecker
import re
from collections import Counter
from datetime import datetime, timedelta
from io import BytesIO
from xhtml2pdf import pisa
import logging

# Import your database models
from models import db, Essay 

# --- APP CONFIGURATION ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logging.info("Essay platform starting up...")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///essays.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- DATABASE INITIALIZATION ---
db.init_app(app)
with app.app_context():
    db.create_all()

# --- TOOL INITIALIZATION (MODIFIED) ---
# Initialize the spell checker once. It's very lightweight.
spell = SpellChecker()
logging.info("pyspellchecker initialized.")

# --- ROUTES ---

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Handles the main page. Now finds misspelled words and creates a 
    single corrected text string to send to the template.
    """
    if request.method == 'POST':
        original_text = request.form.get('text')
        if not original_text:
            # For a POST request, returning JSON might be better if called via JS,
            # but for a simple form, rendering the template is fine.
            return render_template('index.html', original_text="", corrected_text="Error: No text provided.")

        # Perform a simple word-by-word correction.
        # This logic is now consistent with the /save route.
        words = original_text.split()
        misspelled = spell.unknown(words)
        
        corrected_words = []
        for word in words:
            # Clean the word of punctuation for checking, but keep original for appending
            clean_word = re.sub(r'[^\w\s]', '', word)
            if clean_word.lower() in misspelled:
                correction = spell.correction(clean_word.lower())
                # Try to preserve original capitalization
                if clean_word.istitle():
                    corrected_words.append(correction.title())
                else:
                    corrected_words.append(correction)
            else:
                corrected_words.append(word)
        
        corrected_text = " ".join(corrected_words)

        # Pass the original and corrected text to the template
        return render_template('index.html', 
                               original_text=original_text, 
                               corrected_text=corrected_text)

    # For a GET request, just show the main page
    return render_template('index.html')

@app.route('/save', methods=['POST'])
def save_essay():
    """
    Saves the essay. Performs a simple word-by-word correction for the database.
    """
    original_text = request.form.get('text')
    word_count = request.form.get('wordCount', 0, type=int)
    paragraph_count = request.form.get('paragraphCount', 0, type=int)
    backspace_count = request.form.get('backspaceCount', 0, type=int)

    if not original_text:
        return jsonify({'error': 'No text provided'}), 400

    # Perform a simple word-by-word correction.
    words = original_text.split()
    misspelled = spell.unknown(words)
    
    corrected_words = []
    for word in words:
        clean_word = re.sub(r'[^\w\s]', '', word)
        if clean_word.lower() in misspelled:
            correction = spell.correction(clean_word.lower())
            if clean_word.istitle():
                corrected_words.append(correction.title())
            else:
                corrected_words.append(correction)
        else:
            corrected_words.append(word)
            
    corrected_text = " ".join(corrected_words)
    
    try:
        new_essay = Essay(
            original_text=original_text, 
            corrected_text=corrected_text,
            word_count=word_count,
            paragraph_count=paragraph_count,
            backspace_count=backspace_count
        )
        db.session.add(new_essay)
        db.session.commit()
        return jsonify({'message': 'Essay saved successfully'}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving to database: {e}")
        return jsonify({'error': 'Could not save essay to the database.'}), 500

# --- ANALYSIS ROUTE (RESTORED) ---
@app.route('/analyze/<int:essay_id>')
def analyze_essay(essay_id):
    """
    Analyzes an essay for common spelling mistakes using pyspellchecker.
    """
    essay = Essay.query.get_or_404(essay_id)
    
    # Find misspelled words and count their frequency
    words = re.findall(r'\b\w+\b', essay.original_text.lower())
    misspelled_words = spell.unknown(words)
    error_counts = Counter(misspelled_words)
    
    # Sort by most common errors
    most_common_errors = error_counts.most_common()

    return render_template('analysis.html', essay=essay, errors=most_common_errors)


@app.route('/history')
def history():
    # This route remains the same
    try:
        minutes_str = request.args.get('minutes', '60')
        minutes = int(minutes_str)
    except ValueError:
        minutes = 60

    if minutes == -1:
        cutoff_time = datetime.utcnow() - timedelta(minutes=60)
        essays = Essay.query.filter(Essay.timestamp < cutoff_time).order_by(Essay.timestamp.desc()).all()
    else:
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        essays = Essay.query.filter(Essay.timestamp >= cutoff_time).order_by(Essay.timestamp.desc()).all()

    return render_template('history.html', essays=essays, selected_minutes=minutes)


@app.route('/download/<int:essay_id>')
def download_pdf(essay_id):
    # This route remains the same
    essay = Essay.query.get_or_404(essay_id)
    html_content = f"""
    <!DOCTYPE html><html><head><title>Corrected Essay</title>
    <style>body {{ font-family: sans-serif; }}</style></head>
    <body><h2>Corrected Essay</h2><p>{essay.corrected_text}</p><hr>
    <p><strong>Original Text:</strong></p><p>{essay.original_text}</p>
    </body></html>
    """
    pdf_buffer = BytesIO()
    pisa.CreatePDF(html_content, dest=pdf_buffer)
    pdf_buffer.seek(0)
    return send_file(pdf_buffer, download_name=f"essay_{essay_id}.pdf", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
