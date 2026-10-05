import re
from typing import List, Optional, Tuple
from models import Claim, ClaimType


class ClaimExtractor:
    """
    Modul untuk mengekstrak, memilah, dan mengurai struktur klaim dari dokumen paten.
    Mendukung format paten internasional (USPTO, WIPO/PCT, EPO) dan nasional (DJKI Indonesia).
    """

    TRANSITIONAL_PHRASES = [
        r"comprising\b(?:\s+the\s+following)?(?:\s*:)?",
        r"comprises\b(?:\s*:)?",
        r"consisting\s+of\b(?:\s*:)?",
        r"consisting\s+essentially\s+of\b(?:\s*:)?",
        r"characterized\s+in\s+that\b(?:\s*:)?",
        r"terdiri\s+dari\b(?:\s*:)?",
        r"mencakup\b(?:\s*:)?",
        r"meliputi\b(?:\s*:)?",
        r"ditandai\s+dengan\b(?:\s*:)?",
        r"berkarakteristik\s+bahwa\b(?:\s*:)?",
    ]

    CLAIM_SECTION_HEADERS = [
        r"(?:what\s+is\s+claimed\s+is|we\s+claim|i\s+claim|claims\s*:|the\s+claims|klaim\s*:|tuntutan\s*:)",
    ]

    @classmethod
    def isolate_claims_section(cls, text: str) -> str:
        """
        Menemukan dan mengisolasi bagian klaim jika input berupa dokumen paten lengkap.
        """
        cleaned = text.strip()
        pattern = re.compile(
            r"(?:" + "|".join(cls.CLAIM_SECTION_HEADERS) + r")\s*\n+",
            re.IGNORECASE,
        )
        match = pattern.search(cleaned)
        if match:
            # Mengambil teks mulai dari header klaim hingga akhir dokumen
            return cleaned[match.end():].strip()
        return cleaned

    @classmethod
    def extract_claims(cls, raw_text: str) -> List[Claim]:
        """
        Mengekstrak seluruh klaim bernomor dari teks paten.
        """
        claims_text = cls.isolate_claims_section(raw_text)
        if not claims_text:
            return []

        # Mencari pola penomoran klaim, contoh: "1.", "1)", "Claim 1.", "Klaim 1."
        claim_start_regex = re.compile(
            r"(?:^|\n)\s*(?:(?:claim|klaim|tuntutan)\s+)?(\d+)[\.\)]\s+",
            re.IGNORECASE,
        )

        matches = list(claim_start_regex.finditer(claims_text))
        if not matches:
            # Jika tidak ada pola nomor klaim, anggap seluruh teks sebagai satu klaim independen
            preamble, body, elements = cls.parse_claim_elements(claims_text)
            return [
                Claim(
                    claim_number=1,
                    claim_type=ClaimType.INDEPENDENT,
                    depends_on=None,
                    preamble=preamble,
                    body=body,
                    elements=elements,
                    full_text=claims_text,
                )
            ]

        extracted_claims: List[Claim] = []
        for i, match in enumerate(matches):
            claim_num = int(match.group(1))
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(claims_text)

            claim_body_raw = claims_text[start_pos:end_pos].strip()
            # Pembersihan whitespace berlebih
            claim_body_raw = re.sub(r"\s+", " ", claim_body_raw)

            # Deteksi klaim dependen vs independen
            claim_type, depends_on = cls.detect_claim_dependency(claim_body_raw, claim_num)

            # Ekstraksi preamble, body, dan elemen-elemen klaim
            preamble, body, elements = cls.parse_claim_elements(claim_body_raw)

            extracted_claims.append(
                Claim(
                    claim_number=claim_num,
                    claim_type=claim_type,
                    depends_on=depends_on,
                    preamble=preamble,
                    body=body,
                    elements=elements,
                    full_text=f"{claim_num}. {claim_body_raw}",
                )
            )

        return extracted_claims

    @classmethod
    def detect_claim_dependency(cls, claim_text: str, current_claim_num: int) -> Tuple[ClaimType, Optional[int]]:
        """
        Mendeteksi apakah klaim merujuk ke klaim induk (klaim dependen).
        Contoh: "The device according to claim 1...", "Sistem sesuai klaim 1..."
        """
        dep_patterns = [
            r"(?:according\s+to|of|as\s+claimed\s+in)\s+claim\s+(\d+)",
            r"sesuai\s+(?:dengan\s+)?(?:klaim|tuntutan)\s+(\d+)",
            r"pada\s+(?:klaim|tuntutan)\s+(\d+)",
            r"berdasarkan\s+(?:klaim|tuntutan)\s+(\d+)",
            r"\bclaim\s+(\d+)\b",
            r"\bklaim\s+(\d+)\b",
        ]

        # Periksa bagian awal klaim (150 karakter pertama)
        initial_chunk = claim_text[:150]
        for pattern in dep_patterns:
            match = re.search(pattern, initial_chunk, re.IGNORECASE)
            if match:
                ref_num = int(match.group(1))
                if ref_num < current_claim_num:
                    return ClaimType.DEPENDENT, ref_num

        return ClaimType.INDEPENDENT, None

    @classmethod
    def parse_claim_elements(cls, claim_text: str) -> Tuple[str, str, List[str]]:
        """
        Memisahkan preamble dari body klaim berdasarkan transitional phrase,
        lalu memecah body menjadi elemen/limitasi individual.
        """
        preamble = ""
        body = claim_text
        combined_pattern = re.compile(
            r"^(.*?)\s*\b(" + "|".join(cls.TRANSITIONAL_PHRASES) + r")\s*(.*)$",
            re.IGNORECASE | re.DOTALL,
        )

        match = combined_pattern.match(claim_text)
        if match:
            preamble = match.group(1).strip()
            # transitional_phrase = match.group(2)
            body = match.group(3).strip()
        else:
            # Jika tidak ditemukan transitional phrase eksplisit, gunakan kalimat pertama sebagai preamble
            parts = claim_text.split(".", 1)
            if len(parts) > 1 and len(parts[0]) < 120:
                preamble = parts[0].strip()
                body = parts[1].strip()

        # Ekstraksi elemen/limitasi klaim
        elements = cls.split_into_elements(body)
        if not elements:
            elements = [body] if body else [claim_text]

        return preamble, body, elements

    @classmethod
    def split_into_elements(cls, body_text: str) -> List[str]:
        """
        Memecah klausul klaim menjadi elemen-elemen individual berdasarkan tanda titik-koma (;),
        klausul terstruktur, atau penanda elemen klaim paten.
        """
        if not body_text:
            return []

        # Pisahkan berdasarkan semicolon (;) jika ada
        if ";" in body_text:
            raw_elements = [e.strip() for e in body_text.split(";") if e.strip()]
        else:
            # Pisahkan berdasarkan baris baru atau kata sambung struktural klaim
            # seperti "a ", "an ", "wherein ", "di mana ", "terdiri dari ", atau "and [number/amount]"
            delimiters = r"\n+|(?<=[,.\n])\s+(?=(?:a|an|the|wherein|further|providing|generating|receiving|transmitting|suatu|sebuah|di\s+mana)\b)|\s+and\s+(?=\d+\s*(?:%|persen|mg|g|wt)\b)"
            raw_elements = [e.strip() for e in re.split(delimiters, body_text, flags=re.IGNORECASE) if e.strip()]

        cleaned_elements: List[str] = []
        for elem in raw_elements:
            # Hapus konjungsi di awal/akhir seperti "and ", "or ", "dan "
            e = re.sub(r"^(?:and|or|dan|serta)\s+", "", elem, flags=re.IGNORECASE).strip()
            e = re.sub(r"[\.;,]+$", "", e).strip()
            if len(e) > 5:
                cleaned_elements.append(e)

        return cleaned_elements
