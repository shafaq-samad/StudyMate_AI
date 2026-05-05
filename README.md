# StudyMate AI

StudyMate AI is a Flask-based study assistant that helps users summarize notes, ask questions about their documents, generate quizzes, and create flashcards. It uses Gemini first, with Groq as a fallback when Gemini quota is exhausted.

## Features

- Smart text summarization in short, medium, and long formats
- Document-based Q&A
- Quiz generation for MCQ and True/False practice
- Flashcard generation for revision
- `.txt`, `.pdf`, and `.docx` upload support
- User accounts, study history, and password reset flow
- Rate limiting on AI endpoints

## Tech Stack

- Flask
- Gunicorn
- PostgreSQL
- Google Gemini
- Groq
- Flask-Mail
- Flask-Limiter
- PyPDF2
- docx2txt

## Project Structure

- `app.py`: Main Flask app and API routes
- `templates/`: HTML templates
- `static/`: CSS, JavaScript, and images
- `requirements.txt`: Python dependencies
- `Procfile`: Gunicorn startup command for Render
- `runtime.txt`: Python version for deployment

## Local Setup

1. Clone the repository.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with the environment variables below.
4. Run the app locally:

   ```bash
   python app.py
   ```

## Environment Variables

| Variable | Description |
| --- | --- |
| `FLASK_SECRET_KEY` | Secret key for sessions |
| `DATABASE_URL` | PostgreSQL connection string |
| `GEMINI_API_KEY` | Gemini API key |
| `GROQ_API_KEY` | Groq API key |
| `MAIL_SERVER` | SMTP host |
| `MAIL_PORT` | SMTP port, usually `587` |
| `MAIL_USERNAME` | SMTP username / email address |
| `MAIL_PASSWORD` | SMTP password or app password |
| `MAIL_USE_TLS` | `True` or `False` |
| `MAIL_USE_SSL` | `True` or `False` |

## Deploy To Render

1. Push the project to GitHub.
2. In Render, create a new **Web Service** and connect the repository.
3. Use these settings:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --workers 1 --threads 4 --timeout 120`
4. Set the environment variables from the table above in the Render dashboard.
5. Add your PostgreSQL database URL in `DATABASE_URL`.
6. Deploy the service and wait for the first build to finish.

## Notes For Render

- The app uses `runtime.txt` to pin Python `3.11.0`.
- Keep the `Procfile` start command aligned with Render if you change worker settings.
- If Gemini returns quota or rate-limit errors, the app automatically falls back to Groq.