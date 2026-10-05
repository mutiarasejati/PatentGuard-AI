# PatentGuard AI 🛡️
### AI-Powered Patent Infringement Detection, Chemical Nomenclature (IUPAC) & Pharmaceutical FTO Engine

**PatentGuard AI** adalah platform analitik hukum paten farmasi dan sains formulasi terdepan. Dirancang untuk **Principal Patent Analysts**, **Patent Attorneys**, dan **Pharmaceutical Formulators**, sistem ini mengevaluasi risiko kebebasan beroperasi (*Freedom-to-Operate / FTO*), mengidentifikasi zat aktif melalui nama IUPAC & sinonim kimia, memetakan peran fungsional eksipien melalui uji *Function-Way-Result (Doctrine of Equivalents)*, serta merumuskan strategi formulasi ulang bebas paten (*Design-Around*).

---

## 🚀 Fitur Utama & Modul Farmasi (v2.0)

### 1. Multi-Document Upload & Intelligent Parsing (`doc_parser.py`)
- Mendukung berkas formulasi internal (Master Formula Card / Spesifikasi Batch) dan dokumen paten pembanding dalam format **PDF**, **Word (.docx)**, dan **Teks Bebas**.
- Ekstraksi otomatis yang mengenali kadar zat aktif (% w/w, mg/unit dose), rasio polimer, serta tahapan proses manufaktur farmasi.

### 2. Chemical Nomenclature & Active Ingredient Matching (`ChemicalResolver`)
- **Cross-Reference Nama Kimia:** Menghubungkan secara otomatis antara Nama Dagang (*Trade Names*), Nama Generik Internasional (*INN*), Nama Kimia Standar **IUPAC**, Rumus Molekul, Berat Molekul, dan Nomor Registri **CAS**.
- **Deteksi Garam, Hidrat & Polimorf:** Mengenali apakah dokumen paten dan formula merujuk pada entitas kimia yang sama secara literal atau ekuivalen secara terapeutik (misal: Metformin HCl vs Metformin Base; Atorvastatin Crystalline Trihydrate Form I vs Amorphous Co-crystal).

### 3. Excipient Function Mapping & FWR Test (`ExcipientEvaluator`)
- **Taksonomi Eksipien Farmasetika Lengkap:**
  - *Release-controlling polymers* (HPMC K100M/K4M, Etilselulosa, Eudragit, Carbopol, Polyox, Xanthan Gum, Precirol ATO 5)
  - *Diluents / Fillers* (Avicel PH 102/200, Laktosa, Manitol, DCP)
  - *Binders* (PVP K30, HPC, Pregelatinized Starch)
  - *Disintegrants & Superdisintegrants* (Croscarmellose Sodium, Primojel, Crospovidone)
  - *Lubricants & Glidants* (Magnesium Stearate, Aerosil 200, Sodium Stearyl Fumarate, Talc)
  - *Surfactants / Solubilizers* (Polysorbate 80, Sodium Lauryl Sulfate, Poloxamer 188)
- **Uji Doktrin Ekuivalensi (Function-Way-Result Test / Graver Tank):** Menilai apakah substitusi bahan eksipien (misal: HPMC diganti Polyox) bekerja dengan cara dan hasil yang substansial sama (*Doctrine of Equivalents*) atau berbeda secara fundamental sehingga bebas paten (*Design-Around*).

### 4. Automated 4-Pillar Claim Charting & Infringement Risk Scoring
- Matriks perbandingan elemen klaim paten vs spesifikasi formula yang terbagi ke dalam 4 pilar farmasetik:
  1. **Active Ingredient** (Zat Aktif & Bentuk Garam/Polimorf)
  2. **Concentration Range** (Rentang % w/w, mg per dosis, atau rasio polimer)
  3. **Physicochemical Properties** (Viskositas larutan, profil disolusi pH 1.2 vs 6.8, ukuran partikel d90)
  4. **Manufacturing Process** (Granulasi basah high-shear, kempa langsung/direct compression, hot-melt extrusion)
- Skor risiko kuantitatif (0–100%) dan klasifikasi visual: `HIGH RISK` (Literal Infringement / All-Elements Rule), `MEDIUM RISK` (Doctrine of Equivalents), dan `LOW RISK` (Bebas Paten / Missing Elements).

### 5. Advanced Design-Around Recommendation Engine & Live Simulator
- Memberikan taktik reformulasi konkret:
  - *Eksploitasi Batas Numerik Klaim:* Penurunan konsentrasi polimer di bawah batas klaim dengan polimer sinergis.
  - *Substitusi Kelas Eksipien:* Beralih dari matriks hidrogel difusi (HPMC) ke matriks lipid erosi kanal pori (Precirol ATO 5).
  - *Peralihan Rute Proses:* Beralih dari klaim proses granulasi basah ke kempa langsung (direct compression).
  - *Rekayasa Bentuk Padat:* Sintesis kokristal farmasi (co-crystal) atau dispersi padat amorf.
- **Interactive Reformulation Sandbox:** Pengguna dapat mengedit formula secara langsung dan menguji ulang penurunan skor risiko secara real-time.

### 6. Exportable FTO Report (`report_generator.py`)
- **Unduh PDF Resmi:** Dibuat secara native melalui ReportLab dengan cover dossier, tabel IUPAC, matriks klaim, dan legal disclaimer.
- **Unduh Dokumen Word (.docx):** Dibuat via python-docx untuk kebutuhan dokumentasi internal RnD dan komite paten.
- **Export JSON:** Format terstruktur untuk integrasi sistem LIMS dan IP docketing.

---

## 🧪 Kasus Uji Farmasi Nyata (Built-in Benchmark Cases)

1. **Kasus 1: Metformin XR Extended-Release (High Risk / Literal Infringement)**
   - Paten: US654321 mengklaim 500-1000 mg Metformin HCl (IUPAC: *1,1-dimethylbiguanide hydrochloride*), 20-40% HPMC, pelincir, proses granulasi basah.
   - Formula: Glucosafe XR (Metformin HCl 500 mg, HPMC 28%, Mg Stearate, wet granulation) -> **HIGH RISK**.

2. **Kasus 2: Atorvastatin Lipid Erosion Matrix (Low Risk / Safe Design-Around)**
   - Paten: EP2198765 mengklaim Atorvastatin Calcium trihydrate Form I, HPMC phthalate enteric polymer, hot-melt extrusion.
   - Formula: Atorvastatin free base amorphous co-crystal, Precirol ATO 5 (matriks lipid), direct compression -> **LOW RISK (Lolos Paten via All-Elements Rule)**.

3. **Kasus 3: Paracetamol Sustained-Release Hydrogel (Medium Risk / Doctrine of Equivalents)**
   - Paten: WO202109876 mengklaim N-(4-hydroxyphenyl)acetamide 650 mg, 15-30% Xanthan Gum sebagai hydrogel retardant.
   - Formula: Paracetamol 650 mg dengan substitusi 22% Polyox WSR-303 (PEO) -> **MEDIUM RISK (Memenuhi Function-Way-Result Test)**.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.12, FastAPI, Uvicorn, Pydantic v2
- **Pharmaceutical AI Engine:** Google GenAI SDK (`google-genai`), Gemini 3.8 Flash (`gemini-3.8-flash`) + High-Precision Heuristic Fallback
- **Document & PDF Processing:** `reportlab`, `python-docx`, `pypdf`, `python-multipart`
- **Testing:** Pytest (20 Unit & Integration Tests)
- **Web Frontend:** Dual Mode:
  - **FastAPI Modern Web Dashboard:** Tailwind CSS + Alpine.js (`http://localhost:8000`)
  - **Streamlit Interactive App:** Streamlit Enterprise UI (`http://localhost:8501`)

---

## 📦 Struktur Direktori

```
patentguard/
├── app.py                 # FastAPI REST API Server & Endpoint Analisis Farmasi
├── pharma_engine.py       # Engine Kimia, IUPAC, Eksipien, & FTO Claim Chart
├── report_generator.py    # Generator Dokumen PDF (ReportLab) & Word (.docx)
├── doc_parser.py          # Parser Multi-Dokumen (PDF, DOCX, TXT) & Formula Card
├── analyzer.py            # Engine Analisis Paten Umum & Gemini AI
├── claim_extractor.py     # Parser Klaim Paten Independen & Dependen
├── models.py              # Pydantic v2 Data Models & Enums Farmasi
├── requirements.txt       # Daftar Dependensi Python
├── run.py                 # Runner Launcher untuk FastAPI / Streamlit
├── static/
│   └── index.html         # Web Dashboard Farmasi (Tailwind CSS + Alpine.js)
├── streamlit_app.py       # Antarmuka Web Streamlit Terintegrasi
└── tests/
    ├── test_pharma.py     # Unit test IUPAC, eksipien, FWR, & ekspor dokumen FTO
    ├── test_analyzer.py   # Unit test All-Elements Rule & Doctrine of Equivalents
    ├── test_api.py        # Integration test FastAPI REST API
    ├── test_extractor.py  # Unit test ekstraksi klaim
    └── test_pdf.py        # Unit test parser PDF & isolasi klaim
```

---

## ⚡ Cara Menjalankan

### 1. Set API Key Gemini (Opsional tapi Direkomendasikan)
```powershell
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```
*(Catatan: Jika API Key tidak diset, sistem otomatis menjalankan Heuristic Rule-Based Pharma Engine berkecepatan tinggi).*

### 2. Jalankan Server Web

**Opsi A: Dashboard FastAPI + Tailwind + Alpine.js (Disarankan)**
```powershell
python run.py fastapi
```
Buka peramban di: **`http://localhost:8000`**

**Opsi B: Antarmuka Web Streamlit**
```powershell
python run.py
```
Buka peramban di: **`http://localhost:8501`**

### 3. Menjalankan Unit Tests
```powershell
pytest -v
```
Semua 20 pengujian unit dan integrasi lolos verifikasi 100%.
