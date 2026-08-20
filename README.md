# 🗺️ TXRACT – Survey Number Extractor

**TXRACT** is a desktop application designed to extract survey numbers (parcel numbers) from regional cadastral and land map scans (PDF, TIFF, PNG, JPEG) and export them directly to **DXF CAD files** with precise spatial coordinates.

It uses a **Hybrid OCR Engine** combining **RapidOCR** (for English numerals and fast detection) and **Tesseract OCR** (with Gujarati & Devanagari language models) to accurately parse faded, hand-drawn, or scanned village maps.

---

## ✨ Features

- **Hybrid OCR Pipeline**: Combines `RapidOCR` and `Tesseract` for multi-script recognition.
- **Multilingual Support**: Detects English (`0-9`), Gujarati (`૦-૯`), and Devanagari/Hindi (`०-૯`) numerals.
- **Auto-Normalization**: Normalizes Indic script digits to standard ASCII digits for universal CAD software compatibility (LibreCAD, AutoCAD, QCAD).
- **Advanced Image Preprocessing**: Uses Adaptive Thresholding & CLAHE contrast enhancement to read faint pencil marks, faded ink, and low-contrast scans.
- **Smart Filtering & Deduplication**:
  - Spatial deduplication prevents duplicate numbers across overlapping tiles.
  - Regex filtering eliminates dashed lines, border artifacts, and misread letters (e.g., `3e4`, `G2`).
- **Tiled Processing**: Splits high-resolution maps into overlapping tiles for high-accuracy recognition of small text.
- **PDF & Image Support**: Supports multi-page PDF rendering at configurable DPI, as well as TIFF, PNG, and JPEG.
- **Native Cross-Platform GUI**: Dark-themed Desktop UI built with Tkinter, optimized for macOS and Windows.

---

## 🛠️ Tech Stack

- **GUI**: Python `tkinter`
- **OCR Engines**: `rapidocr-onnxruntime`, `pytesseract`
- **CAD Export**: `ezdxf`
- **Image Processing**: `opencv-python`, `Pillow`, `numpy`
- **PDF Rendering**: `PyMuPDF` (`fitz`)

---

## 📋 System Requirements

### 1. Python
- Python **3.10** or higher (tested on Python 3.12).

### 2. Tesseract OCR Engine
TXRACT requires the system-level Tesseract OCR engine with the **Gujarati (`guj`)** and **English (`eng`)** language data files.

#### 🍏 macOS Setup:
Install Tesseract and language packages via Homebrew:
```bash
brew install tesseract
brew install tesseract-lang
