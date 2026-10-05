"""
PatentGuard AI - Multi-Document Ingestion & Intelligent Parser
Mengekstrak dokumen spesifikasi formula produk dan dokumen paten pembanding (PDF, TXT, DOCX).
Mendukung ekstraksi nama IUPAC, struktur formula, persentase bahan, dan tahapan proses.
"""

import io
import re
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("patentguard.doc_parser")


class DocumentParser:
    """Parser dokumen farmasi dan paten cerdas."""

    @staticmethod
    def extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
        """Mengekstrak teks dari file bytes (PDF atau TXT)."""
        filename_lower = filename.lower()

        if filename_lower.endswith(".pdf"):
            return DocumentParser._extract_from_pdf(file_bytes)
        elif filename_lower.endswith((".txt", ".md", ".csv", ".json")):
            try:
                return file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return file_bytes.decode("latin-1", errors="replace")
        elif filename_lower.endswith(".docx"):
            return DocumentParser._extract_from_docx(file_bytes)
        else:
            # Fallback to UTF-8 decoding
            try:
                return file_bytes.decode("utf-8", errors="replace")
            except Exception as e:
                logger.error(f"Gagal membaca format file {filename}: {e}")
                return ""

    @staticmethod
    def _extract_from_pdf(file_bytes: bytes) -> str:
        """Ekstraksi teks dari file PDF menggunakan pypdf."""
        try:
            from pypdf import PdfReader
            stream = io.BytesIO(file_bytes)
            reader = PdfReader(stream)
            extracted_pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    extracted_pages.append(f"--- Halaman {i + 1} ---\n{text}")
            return "\n\n".join(extracted_pages).strip()
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            return ""

    @staticmethod
    def extract_text_from_pdf(pdf_file_or_bytes) -> str:
        """Mengekstrak teks dari file PDF (file-like object atau bytes)."""
        if hasattr(pdf_file_or_bytes, "getvalue"):
            file_bytes = pdf_file_or_bytes.getvalue()
        elif hasattr(pdf_file_or_bytes, "read"):
            file_bytes = pdf_file_or_bytes.read()
        else:
            file_bytes = pdf_file_or_bytes
        return DocumentParser._extract_from_pdf(file_bytes)



    @staticmethod
    def _extract_from_docx(file_bytes: bytes) -> str:
        """Ekstraksi teks dari file docx menggunakan python-docx."""
        try:
            import docx
            stream = io.BytesIO(file_bytes)
            doc = docx.Document(stream)
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        full_text.append(row_text)
            return "\n".join(full_text).strip()
        except Exception as e:
            logger.error(f"Error parsing DOCX: {e}")
            return ""

    @staticmethod
    def parse_formula_specification(text: str) -> Dict[str, Any]:
        """
        Menganalisis spesifikasi formula internal:
        - Mengekstrak bahan dan konsentrasi (% w/w atau mg/tablet)
        - Mengekstrak bentuk sediaan
        - Mengekstrak tahapan proses manufaktur
        """
        ingredients = []
        lines = text.split("\n")

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Cari baris yang memuat nama bahan + angka persentase atau mg
            # Contoh: "HPMC K100M: 25% w/w" atau "- Avicel PH 102: 120 mg"
            match = re.search(r"[-*•]?\s*([a-zA-Z0-9\s\(\)\-\/\,]+?)\s*[:=]\s*(\d+(?:\.\d+)?)\s*(%|persen|w/w|mg|g)", line_str, re.IGNORECASE)
            if match:
                ing_name = match.group(1).strip()
                amount_val = float(match.group(2))
                unit = match.group(3).strip()
                ingredients.append({
                    "name": ing_name,
                    "amount": amount_val,
                    "unit": unit,
                    "raw_line": line_str
                })

        # Deteksi proses
        process_type = "Tidak terdefinisi"
        lower = text.lower()
        if "wet granulation" in lower or "granulasi basah" in lower:
            process_type = "Granulasi Basah (High-Shear Wet Granulation)"
        elif "direct compression" in lower or "kempa langsung" in lower:
            process_type = "Kempa Langsung (Direct Compression)"
        elif "roller compaction" in lower or "granulasi kering" in lower:
            process_type = "Granulasi Kering (Roller Compaction)"
        elif "hot melt" in lower or "hot-melt extrusion" in lower:
            process_type = "Ekstrusi Leleh Panas (Hot Melt Extrusion / HME)"

        return {
            "ingredients_detected": ingredients,
            "detected_process": process_type,
            "total_raw_lines": len(lines),
            "clean_text": text
        }


# Module level alias for convenience
extract_text_from_pdf = DocumentParser.extract_text_from_pdf

