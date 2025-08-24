from flask import Flask, render_template, request, jsonify, send_file
# NEW IMPORTS for Gramformer
from gramformer import Gramformer
import torch
from datetime import datetime, timedelta
from io import BytesIO
from xhtml2pdf import pisa
from collections import Counter
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
def instantiate_gramformer():
    # This function loads the model. It's slow and memory-intensive.
    logging.info("Instantiating Gramformer model...")
    gf = Gramformer(models=1, use_gpu=False) # models=1 is for correction
    logging.info("Gramformer model loaded successfully.")
    return gf

# Initialize the model once when the app starts
gf = instantiate_gramformer()

# --- ROUTES ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        original_text = request.form.get('text')
        if not original_text:
            return jsonify({'error': 'No text provided'}), 400

        # Perform the grammar check using Gramformer
        corrected_sentences = gf.correct(original_text, max_candidates=1)
        # Gramformer returns a set, so we get the first (and only) result
        corrected_text = list(corrected_sentences)[0]

        return render_template('index.html', corrected_text=corrected_text, original_text=original_text)
    
    return render_template('index.html')

@app.route('/save', methods=['POST'])
def save_essay():
    original_text = request.form.get('text')
    word_count = request.form.get('wordCount', 0, type=int)
    paragraph_count = request.form.get('paragraphCount', 0, type=int)
    backspace_count = request.form.get('backspaceCount', 0, type=int)

    if not original_text:
        return jsonify({'error': 'No text provided'}), 400

    # Perform correction before saving
    corrected_sentences = gf.correct(original_text, max_candidates=1)
    corrected_text = list(corrected_sentences)[0]

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

# --- ANALYSIS ROUTE (REMOVED) ---
# The /analyze route is removed as Gramformer doesn't provide a list of mistakes.
# You should also remove the link/button for this from your HTML templates.

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
    essay = Essay.query.get_or_4_04(essay_id)
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
