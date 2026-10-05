import os
import json
import logging
from typing import List, Optional
from models import (
    Claim,
    ClaimType,
    ClaimElementAnalysis,
    ClaimAnalysisResult,
    ElementMatchStatus,
    InfringementRiskLevel,
    InfringementReport,
    PatentAnalysisRequest,
)
from claim_extractor import ClaimExtractor

logger = logging.getLogger("patentguard.analyzer")

# Model rekomendasi Google Gemini API
AI_MODEL_NAME = "gemini-3.8-flash"


class InfringementAnalyzer:
    """
    Mesin analisis potensi pelanggaran paten berbasis AI.
    Menerapkan hukum paten 'All-Elements Rule' dan 'Doctrine of Equivalents'.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = None
        self._init_client()

    def _init_client(self):
        """Inisialisasi Google GenAI Client jika API key tersedia."""
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Gagal menginisialisasi google-genai Client: {e}")
                self.client = None

    def analyze(self, request: PatentAnalysisRequest) -> InfringementReport:
        """
        Alur kerja utama:
        1. Ekstrak klaim dari teks paten.
        2. Analisis klaim terhadap fitur produk menggunakan Gemini 3.8 Flash (atau heuristic fallback jika offline).
        3. Hitung skor risiko kumulatif dan buat rekomendasi design-around.
        """
        # 1. Ekstraksi klaim paten
        claims = ClaimExtractor.extract_claims(request.patent_text)
        if not claims:
            # Fallback jika teks paten tidak memiliki format klaim yang terbaca
            claims = [
                Claim(
                    claim_number=1,
                    claim_type=ClaimType.INDEPENDENT,
                    depends_on=None,
                    preamble="Patent Invention",
                    body=request.patent_text[:300],
                    elements=[request.patent_text[:300]],
                    full_text=request.patent_text,
                )
            ]

        # Inisialisasi API key jika dikirimkan dalam request
        if request.api_key and (not self.client or self.api_key != request.api_key):
            self.api_key = request.api_key
            self._init_client()

        # 2. Analisis menggunakan AI Gemini jika client tersedia
        if self.client:
            try:
                return self._analyze_with_gemini(claims, request)
            except Exception as e:
                logger.error(f"Error saat memanggil Gemini API: {e}. Mengalihkan ke Heuristic Analyzer.")

        # 3. Fallback ke Heuristic Rule-Based Analyzer jika Gemini API belum terkonfigurasi
        return self._analyze_heuristic(claims, request)

    def _analyze_with_gemini(self, claims: List[Claim], request: PatentAnalysisRequest) -> InfringementReport:
        """
        Memanggil Google Gemini API dengan model gemini-3.8-flash dan skema keluaran terstruktur.
        """
        from google.genai import types

        # Siapkan payload teks klaim terstruktur untuk prompt AI
        claims_summary = []
        for c in claims:
            claims_summary.append({
                "claim_number": c.claim_number,
                "claim_type": c.claim_type.value,
                "depends_on": c.depends_on,
                "preamble": c.preamble,
                "elements": c.elements,
                "full_text": c.full_text,
            })

        system_instruction = (
            "Anda adalah Senior Patent Attorney dan Ahli Litigasi Hak Kekayaan Intelektual (HAKI) berstandar internasional. "
            "Tugas Anda adalah melakukan perbandingan teknis-hukum secara cermat antara klaim paten dan fitur produk "
            "menggunakan doktrin paten resmi:\n"
            "1. 'All-Elements Rule' (Pelanggaran Literal): Terjadi jika dan hanya jika SETIAP elemen klaim ditemukan secara identik pada produk.\n"
            "2. 'Doctrine of Equivalents': Jika suatu elemen hilang secara literal, evaluasi apakah fitur produk melakukan fungsi yang sama, "
            "dengan cara yang substansial sama, untuk menghasilkan hasil yang sama (Function-Way-Result Test).\n"
            "3. Jika satu elemen penting hilang sama sekali (MISSING) dan tidak ada ekuivalennya, maka tidak ada pelanggaran literal pada klaim tersebut.\n"
            "4. Berikan rekomendasi teknis 'Design-Around' yang spesifik untuk membantu tim produk merekayasa ulang fiturnya agar bebas paten."
        )

        user_prompt = f"""
Berikut adalah data klaim paten dan fitur produk yang akan diuji:

=== NAMA PRODUK ===
{request.product_name}

=== SPESIFIKASI & FITUR PRODUK ===
{request.product_features}

=== KLAIM PATEN ===
{json.dumps(claims_summary, indent=2, ensure_ascii=False)}

Tolong lakukan analisis elemen-demi-elemen (Claim Chart) untuk setiap klaim di atas, tentukan tingkat risiko (HIGH, MEDIUM, LOW), dan berikan rekomendasi Design-Around.
Kembalikan respon sesuai format JSON schema yang diminta.
"""

        response = self.client.models.generate_content(
            model=AI_MODEL_NAME,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_json_schema=InfringementReport.model_json_schema(),
                temperature=0.2,
            ),
        )

        raw_json = json.loads(response.text)
        return InfringementReport.model_validate(raw_json)

    def _analyze_heuristic(self, claims: List[Claim], request: PatentAnalysisRequest) -> InfringementReport:
        """
        Mesin pencocokan heuristik cerdas (Local Semantic Fallback)
        Mendukung perbandingan dwibahasa (EN-ID) dan akar kata leksikal.
        """
        product_text_lower = request.product_features.lower()
        product_tokens = set(re_tokenize(product_text_lower))
        product_name = request.product_name
        claim_results: List[ClaimAnalysisResult] = []

        total_indep = sum(1 for c in claims if c.claim_type == ClaimType.INDEPENDENT)
        total_dep = sum(1 for c in claims if c.claim_type == ClaimType.DEPENDENT)

        overall_high_risk = False
        overall_med_risk = False
        design_around_suggestions: List[str] = []

        for claim in claims:
            element_analyses: List[ClaimElementAnalysis] = []
            matched_count = 0
            missing_count = 0
            equivalent_count = 0

            for idx, element in enumerate(claim.elements, start=1):
                elem_lower = element.lower()
                keywords = [
                    w for w in re_tokenize(elem_lower)
                    if len(w) > 3 and w not in STOPWORDS
                ]

                # Pencocokan dwibahasa & leksikal dengan normalisasi akar kata
                matched_keywords = []
                for kw in keywords:
                    if is_keyword_matched(kw, product_text_lower, product_tokens):
                        matched_keywords.append(kw)

                match_ratio = len(matched_keywords) / max(len(keywords), 1)

                if match_ratio >= 0.50:
                    status = ElementMatchStatus.MATCHED
                    reasoning = f"Elemen terpenuhi secara literal. Komponen teknis ({', '.join(matched_keywords[:4])}) terkonfirmasi pada spesifikasi produk."
                    matched_count += 1
                elif match_ratio >= 0.25:
                    status = ElementMatchStatus.EQUIVALENT
                    reasoning = f"Ditemukan padanan fungsional sebagian ({', '.join(matched_keywords[:3])}). Berpotensi memenuhi Doctrine of Equivalents jika fungsinya serupa."
                    equivalent_count += 1
                else:
                    status = ElementMatchStatus.MISSING
                    reasoning = "Elemen tidak ditemukan dalam spesifikasi produk. Menjadi dasar kuat untuk lolos dari klaim ini (All-Elements Rule)."
                    missing_count += 1
                    if claim.claim_type == ClaimType.INDEPENDENT:
                        design_around_suggestions.append(
                            f"Pertahankan absennya elemen '{element[:80]}...' pada produk {product_name} untuk menggugurkan klaim independen {claim.claim_number}."
                        )

                element_analyses.append(
                    ClaimElementAnalysis(
                        element_index=idx,
                        claim_element=element,
                        matched_product_feature=f"Fitur: {', '.join(matched_keywords[:3])}" if matched_keywords else None,
                        status=status,
                        reasoning=reasoning,
                        doctrine_applied="Literal Infringement / All-Elements Rule",
                    )
                )

            # Evaluasi tingkat risiko klaim
            if missing_count == 0 and matched_count > 0:
                claim_risk = InfringementRiskLevel.HIGH
                overall_high_risk = True
                claim_summary = f"Semua elemen klaim {claim.claim_number} terpenuhi oleh produk. Potensi pelanggaran literal tinggi."
            elif missing_count > 0 and (matched_count > 0 or equivalent_count > 0):
                if equivalent_count > 0:
                    claim_risk = InfringementRiskLevel.MEDIUM
                    overall_med_risk = True
                    claim_summary = f"Klaim {claim.claim_number} memiliki elemen ekuivalen meski tidak semua elemen literal terpenuhi."
                else:
                    claim_risk = InfringementRiskLevel.LOW
                    claim_summary = f"Klaim {claim.claim_number} aman karena terdapat elemen kunci yang hilang (All-Elements Rule)."
            else:
                claim_risk = InfringementRiskLevel.LOW
                claim_summary = f"Tidak ada kecocokan substansial antara produk dan klaim {claim.claim_number}."

            claim_results.append(
                ClaimAnalysisResult(
                    claim_number=claim.claim_number,
                    claim_type=claim.claim_type,
                    depends_on=claim.depends_on,
                    claim_preamble=claim.preamble,
                    risk_level=claim_risk,
                    element_analyses=element_analyses,
                    summary=claim_summary,
                )
            )

        # Penentuan overall risk
        if overall_high_risk:
            overall_risk = InfringementRiskLevel.HIGH
            exec_summary = (
                f"PERINGATAN RISIKO TINGGI: Produk '{product_name}' terindikasi memenuhi seluruh elemen pada satu atau lebih klaim independen. "
                "Disarankan segera melakukan konsultasi hukum HAKI atau menerapkan strategi Design-Around sebelum rilis komersial."
            )
        elif overall_med_risk:
            overall_risk = InfringementRiskLevel.MEDIUM
            exec_summary = (
                f"RISIKO SEDANG: Ditemukan kemiripan fungsional atau elemen ekuivalen pada produk '{product_name}'. "
                "Perlu verifikasi lebih detail terkait cakupan Doctrine of Equivalents."
            )
        else:
            overall_risk = InfringementRiskLevel.LOW
            exec_summary = (
                f"RISIKO RENDAH (AMAN): Produk '{product_name}' tidak memenuhi setidaknya satu elemen wajib dalam klaim independen paten. "
                "Berdasarkan All-Elements Rule, risiko pelanggaran paten literal sangat kecil."
            )

        # Filter rekomendasi unik
        unique_design_around = list(dict.fromkeys(design_around_suggestions))[:5]
        if not unique_design_around and overall_high_risk:
            unique_design_around.append("Ubah salah satu komponen inti klaim dengan mekanisme yang berbeda secara fundamental.")

        return InfringementReport(
            patent_title=request.patent_title or "Patent Analysis Document",
            product_name=product_name,
            overall_risk=overall_risk,
            total_claims_analyzed=len(claims),
            independent_claims_count=total_indep,
            dependent_claims_count=total_dep,
            claim_results=claim_results,
            design_around_recommendations=unique_design_around,
            executive_summary=exec_summary,
        )


def is_keyword_matched(kw: str, text: str, token_set: set) -> bool:
    """Mengecek apakah kata kunci cocok secara literal, substring, stem, atau sinonim dwibahasa."""
    if kw in text or kw in token_set:
        return True

    # Peta sinonim istilah paten umum ID <-> EN
    SYNONYM_MAP = {
        "processor": ["prosesor", "cpu", "komputer", "processor"],
        "processing": ["pemrosesan", "prosesor", "memproses", "processing"],
        "computing": ["komputer", "komputasi", "computing"],
        "algorithms": ["algoritma", "algoritme", "model", "algorithm"],
        "algorithm": ["algoritma", "algoritme", "model"],
        "controller": ["kontroler", "pengontrol", "pengendali", "controller"],
        "actuator": ["aktuator", "penggerak", "actuator"],
        "steering": ["kemudi", "setir", "steering"],
        "sensor": ["sensor", "pendeteksi", "pengindera"],
        "wireless": ["nirkabel", "wireless", "radio"],
        "transmitter": ["pemancar", "transmiter", "transmitter"],
        "receiver": ["penerima", "receiver"],
        "display": ["layar", "tampilan", "monitor", "display"],
        "storage": ["penyimpanan", "memori", "storage"],
        "battery": ["baterai", "daya", "battery"],
        "frame": ["rangka", "chassis", "frame"],
        "camera": ["kamera", "camera", "pencitraan"],
        "imaging": ["pencitraan", "imaging", "citra"],
    }

    synonyms = SYNONYM_MAP.get(kw.lower(), [])
    for syn in synonyms:
        if syn in text or syn in token_set:
            return True

    # Prefix matching jika panjang kata >= 5 (misal: "algorit" cocok dengan "algorithm" dan "algoritma")
    if len(kw) >= 5:
        stem = kw[:5]
        for token in token_set:
            if token.startswith(stem) or stem in token:
                return True

    return False



def re_tokenize(text: str) -> List[str]:
    import re
    return re.findall(r"\b[a-zA-Z0-9_\u00C0-\u017F\-]+\b", text)


STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "to", "for", "with", "by", "from",
    "at", "on", "as", "is", "are", "was", "were", "be", "been", "that", "this",
    "yang", "dan", "atau", "dari", "dalam", "untuk", "dengan", "pada", "oleh",
    "sebuah", "suatu", "tersebut", "merupakan", "adalah", "serta", "ke", "di",
    "comprising", "consisting", "having", "wherein", "said", "plurality"
}
