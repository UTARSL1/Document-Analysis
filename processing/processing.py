import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple

import cv2
import numpy as np
from PIL import Image
from pdf2image import convert_from_path
import img2pdf


SUPPORTED_IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def safe_filename(filename: str) -> str:
    keep = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    return "".join(ch for ch in filename if ch in keep) or "upload"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def preprocess_image(image: Image.Image) -> Image.Image:
    # TODO: add deskew, denoise, and contrast normalization
    np_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    blurred = cv2.medianBlur(np_img, 3)
    return Image.fromarray(blurred)


def convert_input_to_images(input_path: Path, output_dir: Path) -> List[Path]:
    ensure_dir(output_dir)
    ext = input_path.suffix.lower()
    images = []
    if ext == ".pdf":
        pages = convert_from_path(str(input_path), dpi=300)
        for idx, page in enumerate(pages, start=1):
            output_path = output_dir / f"page_{idx}.png"
            page.save(output_path, "PNG")
            images.append(output_path)
    elif ext in SUPPORTED_IMAGE_TYPES:
        output_path = output_dir / f"page_1{ext}"
        shutil.copy(input_path, output_path)
        images.append(output_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    return images


def run_layout_ocr(image_path: Path) -> Tuple[List[Dict[str, Any]], str]:
    # TODO: integrate PaddleOCR PP-Structure layout detection
    # Placeholder output for layout regions
    dummy_text = "Sample OCR text"
    elements = [
        {
            "type": "text",
            "bbox": [50, 50, 500, 120],
            "text": dummy_text,
            "confidence": 0.9,
        }
    ]
    return elements, dummy_text


def create_image_pdf(image_paths: List[Path], output_pdf: Path) -> None:
    with open(output_pdf, "wb") as f:
        f.write(img2pdf.convert([str(p) for p in image_paths]))


def create_searchable_pdf(input_pdf: Path, output_pdf: Path) -> None:
    # TODO: tune OCRmyPDF parameters and language pack
    result = subprocess.run(
        [
            "ocrmypdf",
            "--deskew",
            "--force-ocr",
            "--output-type",
            "pdf",
            str(input_pdf),
            str(output_pdf),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"OCRmyPDF failed: {result.stderr}")


def build_json_output(
    document_id: str,
    doc_type: str,
    page_entries: List[Dict[str, Any]],
    warnings: List[str],
) -> Dict[str, Any]:
    return {
        "document_id": document_id,
        "doc_type": doc_type,
        "pages": page_entries,
        "metadata": {
            "layout_model": "TODO-paddleocr-pp-structure",
            "ocr_model": "TODO-paddleocr",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "warnings": warnings,
        },
    }


def process_document(
    document_id: str,
    doc_type: str,
    input_path: Path,
    output_root: Path,
) -> Dict[str, Any]:
    warnings: List[str] = []
    work_dir = output_root / document_id
    images_dir = work_dir / "images"
    ensure_dir(images_dir)

    image_paths = convert_input_to_images(input_path, images_dir)

    page_entries: List[Dict[str, Any]] = []
    processed_images: List[Path] = []

    for page_no, image_path in enumerate(image_paths, start=1):
        with Image.open(image_path) as img:
            preprocessed = preprocess_image(img)
            preprocessed_path = images_dir / f"preprocessed_{page_no}.png"
            preprocessed.save(preprocessed_path)
            processed_images.append(preprocessed_path)
            width, height = preprocessed.size

        elements, page_text = run_layout_ocr(preprocessed_path)
        for idx, element in enumerate(elements):
            element["reading_order_index"] = idx

        page_entries.append(
            {
                "page_no": page_no,
                "width": width,
                "height": height,
                "full_text": page_text,
                "elements": elements,
            }
        )

    image_pdf_path = work_dir / "image_only.pdf"
    create_image_pdf(processed_images, image_pdf_path)

    searchable_pdf_path = work_dir / "searchable.pdf"
    create_searchable_pdf(image_pdf_path, searchable_pdf_path)

    json_output = build_json_output(document_id, doc_type, page_entries, warnings)
    json_path = work_dir / "output.json"
    ensure_dir(json_path.parent)
    json_path.write_text(json.dumps(json_output, indent=2))

    return {
        "searchable_pdf_path": str(searchable_pdf_path),
        "json_path": str(json_path),
        "json_output": json_output,
    }
