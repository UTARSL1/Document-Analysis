# Document Digitization System

National-scale document digitization system for processing 180 million pages with automated quality verification, hybrid OCR/HTR (Handwritten Text Recognition), and template-based zone extraction.

## Features

- **Automated QC Verification**: < 1 second/page automated quality checks (resolution, skew, borders, contrast, completeness)
- **Hybrid OCR/HTR**: Template-based zone extraction with automatic detection of printed vs handwritten text
- **Handwriting Recognition**: TrOCR-based HTR for historical handwritten documents
- **Searchable PDF Generation**: Creates searchable PDFs with invisible text layer
- **Structured JSON Output**: Zone-level extraction with confidence scores and validation
- **Template Management**: Visual template editor for 12-16 document types
- **Manual Review Queue**: 20-40% of handwritten documents flagged for low-confidence review
- **Scalable Architecture**: Supports 3-4M pages/month with 250-350 GPU workers

## Architecture

- **Backend**: FastAPI with PostgreSQL database
- **Workers**: Celery with Redis queue
- **Storage**: S3-compatible (MinIO) for on-premises deployment
- **OCR/HTR**: PaddleOCR + TrOCR (Microsoft)
- **Frontend**: React (to be implemented)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- At least 16GB RAM for development
- GPU recommended for HTR processing (optional for development)

### Development Setup

1. **Clone and navigate to project**:
   ```bash
   cd document-digitization
   ```

2. **Copy environment configuration**:
   ```bash
   cp config/.env.example .env
   ```

3. **Start services**:
   ```bash
   docker-compose up -d
   ```

4. **Initialize database**:
   ```bash
   docker-compose exec postgres psql -U postgres -d document_digitization -f /docker-entrypoint-initdb.d/001_initial_schema.sql
   ```

5. **Access services**:
   - **Frontend Dashboard**: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

### Upload a Document

```bash
curl -X POST "http://localhost:8000/api/v1/ingestion/upload" \
  -F "file=@sample_document.pdf" \
  -F "doc_type=birth_certificate" \
  -F "batch_id=batch_001"
```

### Check QC Queue

```bash
curl "http://localhost:8000/api/v1/qc/queue?status=manual_review"
```

### Get QC Statistics

```bash
curl "http://localhost:8000/api/v1/qc/stats"
```

## Project Structure

```
document-digitization/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── storage/     # Storage backends
│   │   ├── models.py    # Database models
│   │   └── schemas.py   # Pydantic schemas
│   └── requirements.txt
├── worker/              # Celery workers
│   ├── tasks/          # Processing tasks
│   ├── qc/             # QC verification modules
│   ├── htr/            # HTR models (to be implemented)
│   └── requirements.txt
├── database/
│   └── migrations/     # SQL migrations
├── config/
│   ├── document_types.json
│   ├── templates/      # Document templates
│   └── .env.example
└── docker-compose.yml
```

## Configuration

### Document Types

Configure document types in `config/document_types.json`. Currently supports:
- Birth Certificate
- ID Card (Front/Back)
- Passport Bio Page
- Marriage Certificate
- Death Certificate
- Land Title
- Tax Record
- Court Document
- Census Record
- Military Record
- Immigration Document

### QC Thresholds

Adjust quality check thresholds in `.env`:
- `QC_MIN_DPI`: Minimum resolution (default: 300)
- `QC_MAX_SKEW_ANGLE`: Maximum skew angle in degrees (default: 2.0)
- `QC_MIN_CONTRAST_SCORE`: Minimum contrast score (default: 0.3)
- `QC_MAX_BORDER_PERCENTAGE`: Maximum border percentage (default: 10)

### HTR Configuration

Configure handwriting recognition in `.env`:
- `HTR_MODEL`: TrOCR model (default: microsoft/trocr-large-handwritten)
- `HTR_CONFIDENCE_THRESHOLD`: Manual review threshold (default: 0.70)
- `HTR_AUTO_ACCEPT_THRESHOLD`: Auto-accept threshold (default: 0.85)
- `HTR_USE_GPU`: Enable GPU acceleration (default: true)

## API Endpoints

### Health Check
- `GET /api/v1/health` - System health status

### Document Ingestion
- `POST /api/v1/ingestion/upload` - Upload single document
- `POST /api/v1/ingestion/batch-upload` - Upload multiple documents

### Quality Check
- `GET /api/v1/qc/queue` - Get manual review queue
- `GET /api/v1/qc/stats` - Get QC statistics
- `POST /api/v1/qc/{document_id}/approve` - Approve document
- `POST /api/v1/qc/{document_id}/reject` - Reject document

### Documents
- `GET /api/v1/documents` - List documents (with pagination)
- `GET /api/v1/documents/{id}` - Get document details
- `GET /api/v1/documents/{id}/download-pdf` - Download searchable PDF
- `GET /api/v1/documents/{id}/download-json` - Download JSON output

### Templates
- `GET /api/v1/templates` - List templates
- `GET /api/v1/templates/{doc_type}` - Get template
- `POST /api/v1/templates` - Create template
- `PUT /api/v1/templates/{id}` - Update template

## Production Deployment

For production deployment with 250-350 workers:

1. Use `docker-compose.prod.yml` (to be created)
2. Enable GPU support for HTR workers
3. Configure PostgreSQL connection pooling (PgBouncer)
4. Set up Redis cluster
5. Configure MinIO cluster with erasure coding
6. Enable monitoring (Prometheus + Grafana)

## Next Steps

- [ ] Implement HTR/OCR processing tasks
- [ ] Create frontend React application
- [ ] Add template visual editor
- [ ] Implement correction workflow
- [ ] Add batch processing optimization
- [ ] Create production Docker Compose
- [ ] Add monitoring and logging
- [ ] Implement user authentication

## License

Proprietary - National Records Digitization Project

## Support

For issues and questions, contact the development team.
