# KitabiAI - Intelligent Book Processing System

![CI/CD](https://github.com/YOUR_USERNAME/KitabiAI/workflows/CI-CD/badge.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Docker](https://img.shields.io/badge/docker-enabled-blue.svg)

An intelligent document processing system that extracts tables of contents from PDF books in multiple languages, with specialized support for Arabic text.

## 🚀 Features

- **Multi-language Support**: Processes English and Arabic documents
- **Intelligent TOC Extraction**: 
  - Bookmark-based extraction for PDFs with embedded bookmarks
  - Pattern-based extraction for Arabic documents
  - Fallback mechanisms for documents without structured TOCs
- **Azure Document Intelligence Integration**: Advanced text extraction using Azure AI
- **RESTful API**: Easy-to-use endpoints for document processing
- **Docker Support**: Containerized deployment for consistency

## 🛠️ Tech Stack

- **Backend**: Python 3.9+, Flask
- **AI/ML**: Azure Document Intelligence
- **PDF Processing**: PyPDF2
- **Containerization**: Docker, Docker Compose
- **CI/CD**: GitHub Actions

## 📋 Prerequisites

- Python 3.9 or higher
- Docker and Docker Compose (optional)
- Azure Document Intelligence API key

## 🔧 Installation

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/KitabiAI.git
cd KitabiAI
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your Azure credentials
```

5. Run the application:
```bash
python main.py
```

### Docker Deployment

1. Build and run with Docker Compose:
```bash
docker-compose up --build
```

The application will be available at `http://localhost:5000`

## 📚 API Usage

### Upload and Process Document

```bash
POST /upload
Content-Type: multipart/form-data

# Example with curl:
curl -X POST -F "file=@book.pdf" http://localhost:5000/upload
```

### Response Format

```json
{
  "bookmarks_found": true,
  "sections": [
    {
      "section_id": "1",
      "title": "Chapter 1: Introduction",
      "level": 1,
      "page_start": 1,
      "page_end": 15
    }
  ]
}
```

## 🏗️ Project Structure

```
KitabiAI/
├── app/
│   ├── core/           # Core configuration and logging
│   ├── models/         # Data models and schemas
│   ├── routers/        # API endpoints
│   ├── services/       # Business logic
│   │   ├── arabic_toc_extractor.py
│   │   ├── language_detector.py
│   │   └── toc_extractor.py
│   └── ui/            # User interface components
├── .github/
│   └── workflows/     # CI/CD pipelines
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── main.py
```

## 🧪 Testing

```bash
# Run tests (when implemented)
pytest tests/
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👤 Author

**Your Name**
- GitHub: https://github.com/suhaJamal
- LinkedIn: https://www.linkedin.com/in/suha-islaih/

## 🙏 Acknowledgments

- Azure Document Intelligence for OCR capabilities
- OpenAI for architectural guidance
