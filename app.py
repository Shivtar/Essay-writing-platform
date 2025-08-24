from flask import Flask, render_template, request, jsonify, send_file
import language_tool_python
from datetime import datetime, timedelta
from io import BytesIO
from xhtml2pdf import pisa
from collections import Counter
import os

# Import your database models
from models import db, Essay 

# --- APP CONFIGURATION ---
app = Flask(__name__)
essay_api_key = os.getenv("essayvv")
if not essay_api_key:
    raise ValueError("Missing essayvv environment variable")
import logging
logging.basicConfig(level=logging.INFO)
logging.info("Essay platform started")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///essays.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- DATABASE INITIALIZATION ---
db.init_app(app)

with app.app_context():
    db.create_all()

# --- TOOL INITIALIZATION ---
tool = language_tool_python.LanguageTool('en-US')

# --- ROUTES ---

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Handles the main page for essay submission.
    This route NO LONGER saves to the database. It only corrects text.
    """
    if request.method == 'POST':
        original_text = request.form.get('text')
        if not original_text:
            return jsonify({'error': 'No text provided'}), 400

        # Perform the grammar check
        matches = tool.check(original_text)
        corrected_text = language_tool_python.utils.correct(original_text, matches)

        # Return the rendered template with the results
        return render_template('index.html', corrected_text=corrected_text, original_text=original_text)

    # For a GET request, just show the main page
    return render_template('index.html')

@app.route('/save', methods=['POST'])
def save_essay():
    """
    Corrects, then saves the essay and its stats to the database.
    This is triggered by the 'Save Manually' button.
    """
    original_text = request.form.get('text')
    # Get stats from the form
    word_count = request.form.get('wordCount', 0, type=int)
    paragraph_count = request.form.get('paragraphCount', 0, type=int)
    backspace_count = request.form.get('backspaceCount', 0, type=int)

    if not original_text:
        return jsonify({'error': 'No text provided'}), 400

    # Perform correction before saving
    matches = tool.check(original_text)
    corrected_text = language_tool_python.utils.correct(original_text, matches)

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
        print(f"Error saving to database: {e}")
        return jsonify({'error': 'Could not save essay to the database.'}), 500

# --- ANALYSIS ROUTE ---
@app.route('/analyze/<int:essay_id>')
def analyze_essay(essay_id):
    """
    Analyzes an essay for common spelling mistakes.
    """
    essay = Essay.query.get_or_404(essay_id)
    matches = tool.check(essay.original_text)
    
    # Filter for spelling mistakes and count them
    spelling_errors = [
        # *** FIXED: Changed match.error_length to match.errorLength ***
        match.context[match.offset:match.offset + match.errorLength]
        for match in matches
        if match.ruleId == 'MORFOLOGIK_RULE_EN_US' or 'SPELLING' in match.ruleId
    ]
    
    error_counts = Counter(spelling_errors)
    # Sort by most common errors
    most_common_errors = error_counts.most_common()

    return render_template('analysis.html', essay=essay, errors=most_common_errors)


@app.route('/history')
def history():
    """ Displays a history of essays based on the updated time filter. """
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
    """ Generates and downloads a PDF for a specific essay. """
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

@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    app.run()
