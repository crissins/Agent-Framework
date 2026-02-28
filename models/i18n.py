# models/i18n.py
"""
Internationalisation (i18n) string tables for the book template renderer.

Each language is a flat dictionary whose keys match the ``BOOK.i18n.*``
fields consumed by the master HTML template's JavaScript.  Adding a new
language is as simple as copying an existing dict and translating.
"""

from __future__ import annotations
from typing import Dict

# ── String tables ─────────────────────────────────────────────────────

_STRINGS: Dict[str, Dict[str, str]] = {
    # ── Spanish (default) ─────────────────────────────────────────────
    "es": {
        # TOC page
        "index":           "Índice",
        "book_contents":   "Contenido del Libro",
        # Cover meta labels
        "country":         "País",
        "method":          "Método",
        "chapters_label":  "Capítulos",
        "language_label":  "Idioma",
        "years_old":       "años",
        # Chapter headers
        "chapter":         "Capítulo",
        "ch_abbr":         "Cap.",
        # QR / video
        "scan_to_watch":   "Escanea para ver el video",
        # Grade labels
        "grade_primary":   "Primaria",
        "grade_secondary": "Secundaria",
        "grade_high":      "Preparatoria",
        # Block type labels (fallback when LLM doesn't provide them)
        "key_concept":     "Concepto Clave",
        "example":         "Ejemplo",
        "activity":        "Actividad",
        "challenge":       "Desafío Creativo",
        "did_you_know":    "¿Sabías que…?",
        "question":        "Pregunta para Pensar",
    },

    # ── English ───────────────────────────────────────────────────────
    "en": {
        "index":           "Index",
        "book_contents":   "Book Contents",
        "country":         "Country",
        "method":          "Method",
        "chapters_label":  "Chapters",
        "language_label":  "Language",
        "years_old":       "years old",
        "chapter":         "Chapter",
        "ch_abbr":         "Ch.",
        "scan_to_watch":   "Scan to watch the video",
        "grade_primary":   "Elementary",
        "grade_secondary": "Middle School",
        "grade_high":      "High School",
        "key_concept":     "Key Concept",
        "example":         "Example",
        "activity":        "Activity",
        "challenge":       "Creative Challenge",
        "did_you_know":    "Did you know…?",
        "question":        "Think About It",
    },

    # ── Portuguese ────────────────────────────────────────────────────
    "pt": {
        "index":           "Índice",
        "book_contents":   "Conteúdo do Livro",
        "country":         "País",
        "method":          "Método",
        "chapters_label":  "Capítulos",
        "language_label":  "Idioma",
        "years_old":       "anos",
        "chapter":         "Capítulo",
        "ch_abbr":         "Cap.",
        "scan_to_watch":   "Escaneie para ver o vídeo",
        "grade_primary":   "Ensino Fundamental I",
        "grade_secondary": "Ensino Fundamental II",
        "grade_high":      "Ensino Médio",
        "key_concept":     "Conceito-Chave",
        "example":         "Exemplo",
        "activity":        "Atividade",
        "challenge":       "Desafio Criativo",
        "did_you_know":    "Você sabia…?",
        "question":        "Pergunta para Pensar",
    },

    # ── French ────────────────────────────────────────────────────────
    "fr": {
        "index":           "Index",
        "book_contents":   "Table des Matières",
        "country":         "Pays",
        "method":          "Méthode",
        "chapters_label":  "Chapitres",
        "language_label":  "Langue",
        "years_old":       "ans",
        "chapter":         "Chapitre",
        "ch_abbr":         "Ch.",
        "scan_to_watch":   "Scannez pour voir la vidéo",
        "grade_primary":   "Primaire",
        "grade_secondary": "Collège",
        "grade_high":      "Lycée",
        "key_concept":     "Concept Clé",
        "example":         "Exemple",
        "activity":        "Activité",
        "challenge":       "Défi Créatif",
        "did_you_know":    "Le saviez-vous… ?",
        "question":        "Question de Réflexion",
    },

    # ── German ────────────────────────────────────────────────────────
    "de": {
        "index":           "Inhaltsverzeichnis",
        "book_contents":   "Buchinhalt",
        "country":         "Land",
        "method":          "Methode",
        "chapters_label":  "Kapitel",
        "language_label":  "Sprache",
        "years_old":       "Jahre alt",
        "chapter":         "Kapitel",
        "ch_abbr":         "Kap.",
        "scan_to_watch":   "Scannen Sie, um das Video anzusehen",
        "grade_primary":   "Grundschule",
        "grade_secondary": "Sekundarstufe I",
        "grade_high":      "Sekundarstufe II",
        "key_concept":     "Schlüsselkonzept",
        "example":         "Beispiel",
        "activity":        "Aktivität",
        "challenge":       "Kreative Herausforderung",
        "did_you_know":    "Wusstest du…?",
        "question":        "Denkfrage",
    },

    # ── Italian ───────────────────────────────────────────────────────
    "it": {
        "index":           "Indice",
        "book_contents":   "Contenuto del Libro",
        "country":         "Paese",
        "method":          "Metodo",
        "chapters_label":  "Capitoli",
        "language_label":  "Lingua",
        "years_old":       "anni",
        "chapter":         "Capitolo",
        "ch_abbr":         "Cap.",
        "scan_to_watch":   "Scansiona per vedere il video",
        "grade_primary":   "Scuola Primaria",
        "grade_secondary": "Scuola Secondaria",
        "grade_high":      "Liceo",
        "key_concept":     "Concetto Chiave",
        "example":         "Esempio",
        "activity":        "Attività",
        "challenge":       "Sfida Creativa",
        "did_you_know":    "Lo sapevi…?",
        "question":        "Domanda di Riflessione",
    },

    # ── Japanese ──────────────────────────────────────────────────────
    "ja": {
        "index":           "目次",
        "book_contents":   "本の内容",
        "country":         "国",
        "method":          "方法",
        "chapters_label":  "章",
        "language_label":  "言語",
        "years_old":       "歳",
        "chapter":         "第",
        "ch_abbr":         "章",
        "scan_to_watch":   "QRコードをスキャンして動画を見る",
        "grade_primary":   "小学校",
        "grade_secondary": "中学校",
        "grade_high":      "高等学校",
        "key_concept":     "キーコンセプト",
        "example":         "例",
        "activity":        "アクティビティ",
        "challenge":       "クリエイティブチャレンジ",
        "did_you_know":    "知っていましたか…？",
        "question":        "考えてみよう",
    },

    # ── Chinese (Simplified) ──────────────────────────────────────────
    "zh": {
        "index":           "目录",
        "book_contents":   "书籍内容",
        "country":         "国家",
        "method":          "方法",
        "chapters_label":  "章节",
        "language_label":  "语言",
        "years_old":       "岁",
        "chapter":         "第",
        "ch_abbr":         "章",
        "scan_to_watch":   "扫描二维码观看视频",
        "grade_primary":   "小学",
        "grade_secondary": "初中",
        "grade_high":      "高中",
        "key_concept":     "核心概念",
        "example":         "示例",
        "activity":        "活动",
        "challenge":       "创意挑战",
        "did_you_know":    "你知道吗……？",
        "question":        "思考题",
    },

    # ── Arabic (RTL) ─────────────────────────────────────────────────
    "ar": {
        "index":           "الفهرس",
        "book_contents":   "محتويات الكتاب",
        "country":         "البلد",
        "method":          "الطريقة",
        "chapters_label":  "الفصول",
        "language_label":  "اللغة",
        "years_old":       "سنوات",
        "chapter":         "الفصل",
        "ch_abbr":         "ف.",
        "scan_to_watch":   "امسح الرمز لمشاهدة الفيديو",
        "grade_primary":   "المرحلة الابتدائية",
        "grade_secondary": "المرحلة المتوسطة",
        "grade_high":      "المرحلة الثانوية",
        "key_concept":     "المفهوم الأساسي",
        "example":         "مثال",
        "activity":        "نشاط",
        "challenge":       "تحدٍّ إبداعي",
        "did_you_know":    "هل كنت تعلم…؟",
        "question":        "سؤال للتفكير",
    },

    # ── Korean ────────────────────────────────────────────────────────
    "ko": {
        "index":           "목차",
        "book_contents":   "책 내용",
        "country":         "국가",
        "method":          "방법",
        "chapters_label":  "장",
        "language_label":  "언어",
        "years_old":       "세",
        "chapter":         "제",
        "ch_abbr":         "장",
        "scan_to_watch":   "QR 코드를 스캔하여 동영상 보기",
        "grade_primary":   "초등학교",
        "grade_secondary": "중학교",
        "grade_high":      "고등학교",
        "key_concept":     "핵심 개념",
        "example":         "예시",
        "activity":        "활동",
        "challenge":       "창의적 도전",
        "did_you_know":    "알고 있었나요…?",
        "question":        "생각해 보기",
    },

    # ── Hindi ─────────────────────────────────────────────────────────
    "hi": {
        "index":           "विषयसूची",
        "book_contents":   "पुस्तक सामग्री",
        "country":         "देश",
        "method":          "विधि",
        "chapters_label":  "अध्याय",
        "language_label":  "भाषा",
        "years_old":       "वर्ष",
        "chapter":         "अध्याय",
        "ch_abbr":         "अ.",
        "scan_to_watch":   "वीडियो देखने के लिए स्कैन करें",
        "grade_primary":   "प्राथमिक",
        "grade_secondary": "माध्यमिक",
        "grade_high":      "उच्च माध्यमिक",
        "key_concept":     "मुख्य अवधारणा",
        "example":         "उदाहरण",
        "activity":        "गतिविधि",
        "challenge":       "रचनात्मक चुनौती",
        "did_you_know":    "क्या आप जानते हैं…?",
        "question":        "सोचने का प्रश्न",
    },
}

# RTL languages for proper text direction
RTL_LANGUAGES = {"ar", "he", "fa", "ur"}

# ── Public API ────────────────────────────────────────────────────────

def get_i18n_strings(lang_code: str) -> Dict[str, str]:
    """
    Return the i18n string table for the given ISO-639-1 language code.

    Falls back to Spanish (``es``) when the language is not available.
    """
    code = lang_code.lower().strip()[:2]
    return dict(_STRINGS.get(code, _STRINGS["es"]))


def detect_lang_code(language_name: str) -> str:
    """
    Fuzzy-map a free-text language name (e.g. ``"Español"``, ``"English"``,
    ``"Português"``) to its ISO-639-1 two-letter code.
    """
    name = language_name.lower().strip()
    _MAP = {
        "es": ["español", "espanol", "spanish", "castellano"],
        "en": ["english", "inglés", "ingles"],
        "pt": ["português", "portugues", "portuguese"],
        "fr": ["français", "francais", "french"],
        "de": ["deutsch", "german", "alemán", "aleman"],
        "it": ["italiano", "italian"],
        "ja": ["日本語", "japanese", "japonés", "japones"],
        "zh": ["中文", "chinese", "chino"],
        "ar": ["العربية", "arabic", "árabe", "arabe"],
        "ko": ["한국어", "korean", "coreano"],
        "hi": ["हिन्दी", "hindi"],
    }
    for code, aliases in _MAP.items():
        for alias in aliases:
            if alias in name or name in alias:
                return code
    return "es"  # default


def is_rtl(lang_code: str) -> bool:
    """Return True if the language is written right-to-left."""
    return lang_code.lower().strip()[:2] in RTL_LANGUAGES


def available_languages() -> list[str]:
    """Return all supported language codes."""
    return sorted(_STRINGS.keys())
