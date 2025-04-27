# Tax AI

An intelligent tax form parser and advisor that uses OCR and AI to process tax documents and provide guidance.

## Features

- PDF and image-based tax form parsing (W-2, 1099-NEC)
- Box-based OCR extraction for accurate data capture
- AI-powered tax guidance and advice
- Integration with IRS tax guides
- Web-based interface for easy interaction

## Prerequisites

- Python 3.8+
- Tesseract OCR
- Poppler (for PDF processing)
- Anthropic API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tax-ai.git
cd tax-ai
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install system dependencies:
- Windows:
  - Install Tesseract OCR: Download and install from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
  - Install Poppler: Download and add to PATH from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases/)
- Linux:
  ```bash
  sudo apt-get install tesseract-ocr poppler-utils
  ```
- macOS:
  ```bash
  brew install tesseract poppler
  ```

5. Set up environment variables:
Create a `.env` file with:
```
ANTHROPIC_API_KEY=your_api_key_here
```

## Usage

1. Start the server:
```bash
uvicorn main:app --reload
```

2. Access the web interface at `http://localhost:8000`

3. API Endpoints:
- `POST /parse-tax-form`: Upload and parse tax forms
  - Parameters:
    - `file`: PDF or image file
    - `form_type`: "W-2" or "1099-NEC"
- `POST /tax-guidance`: Get AI-powered tax advice
  - Parameters:
    - `message`: Your tax question
    - `conversation_id`: Optional conversation ID for context

## Project Structure

```
tax-ai/
├── main.py              # FastAPI application and endpoints
├── rag_handler.py       # RAG system for tax guide processing
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables
└── tax_guides_db/       # Vector store for tax guides
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License

## Acknowledgments

- FastAPI for the web framework
- Tesseract OCR for text extraction
- Anthropic for AI capabilities
- IRS for tax documentation 