"""
ai_engine.py — StatusAI Storyteller Engine v3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Transforms multi-source computer activity into one charismatic,
grounded, 128-char status sentence. No hallucination. No fluff.
"""

import random
import re
import time
from typing import Optional


# ──────────────────────────────────────────────
#  Constants
# ──────────────────────────────────────────────

MAX_STATUS_LENGTH = 128

STORYTELLER_PROMPT = """Sen bir Discord durum mesajı yazarısın. Görüşün: kullanıcının gerçek bilgisayar aktivitelerini TEK karizmatik cümleye dönüştürmek.

## TEMEL KESİN KURALLAR

1. EN FAZLA {max_len} karakter.
2. SADECE aşağıdaki etiketli verileri kullan. VERİDE OLMAYAN HİÇBİR ŞEYİ SÖYLEMEYECEKSİN.
3. Veri etiketleri: AKTİF, KOD, MÜZİK, TARAYICI, OYUN. Bu etiketlerdeki bilgiyi birleştir.
4. UYDURMAK KESİNLİKLE YASAK. "Veritabanı tasarımı", "yerçekimi", "matrix", "hack" gibi veride olmayan ifadeler KULLANMA.
5. YouTube'da müzik videosu varsa → "dinliyor" veya "izliyor" olarak yaz.
6. Tırnak, tire, madde işareti, terminal formatı (root@, $) KULLANMA.
7. 1-2 emoji kullanabilirsin.
8. Düz metin, tek cümle, başka hiçbir şey yazma.
9. Dil: {language_name}
10. Persona tonu: {persona}

## BİRLEŞTİRME MANTIĞI

Birden fazla etiketli veri varsa, hepsini TEK doğal cümlede birleştir:
- MÜZİK + KOD → "X dinleyerek Y dosyasını düzenliyor"
- TARAYICI(YouTube) + KOD → "YouTube'da Z izlerken bir yandan kod yazıyor"
- AKTİF(Discord) → "Discord'da sohbet ediyor"
- AKTİF(mesajlaşma) → "Mesajlaşıyor" (detay verme)

### İyi Örnekler:
{examples}

### YASAK Örnekler:
- "Yerçekimini reddediyorum" → VERİDE YOK, UYDURMA
- "Veritabanı tasarımı yapıyor" → VERİDE YOK, UYDURMA
- "root@dev:~$ coding" → TERMİNAL FORMATI YASAK
- "Matrix'te kayboldum" → ABARTMA YASAK
- "Maalesef bu response..." → AÇIKLAMA YAZMA, SADECE CÜMLE YAZ
"""

# ──────────────────────────────────────────────
#  Persona Examples (grounded, realistic)
# ──────────────────────────────────────────────

PERSONA_EXAMPLES = {
    "hacker": [
        "YouTube'da Seda Tripkolic izlerken config dosyalarını düzenliyor 🎧",
        "StackOverflow'da çözüm ararken bir yandan API yazıyor ⚡",
        "GitHub'da PR review yaparken Spotify'dan müzik dinliyor 🔍",
        "Discord'da sohbet ederken arka planda bot geliştiriyor 🛠️",
    ],
    "sigma": [
        "YouTube'da müzik açık, VS Code'da kod yazıyor, durmuyor 💪",
        "StackOverflow'da araştırma yapıp backend optimize ediyor ⚡",
        "Spotify dinlerken deploy hazırlıyor, gece bitmez 🔥",
        "GitHub'da commit atarken yeni feature planlıyor 🎯",
    ],
    "chill": [
        "YouTube'da şarkı dinleyerek sakin sakin kod yazıyor ☕",
        "Spotify açık, kahve hazır, bug hunt zamanı 🌿",
        "Discord'da takılırken arka planda proje geliştiriyor 🎧",
        "Sakin bir gece, VS Code açık, müzik eşliğinde çalışıyor ✨",
    ],
    "gamer": [
        "VALORANT oynuyor, ara verildi mi bilinmez 🎮",
        "League arasında Discord'da sohbet ediyor ⚔️",
        "YouTube'da oyun videosu izliyor, sırada ranked var 🏆",
        "Twitch açık, bir yandan da side-project geliştiriyor 🎯",
    ],
    "poet": [
        "YouTube'da müzik akarken kodun ritmine kapılmış 🎵",
        "GitHub'da yeni bir sayfa açılıyor, hikaye sürüyor ✨",
        "Spotify eşliğinde sessizce mimari çiziyor 📝",
        "Gece sessiz, klavye tıkırtısı ve müzik var sadece 🌙",
    ],
    "custom": [
        "YouTube'da Seda Tripkolic dinlerken VS Code'da proje geliştiriyor ⚡",
        "StackOverflow'da araştırma yapıp kendi API'sini yazıyor 🔍",
        "Discord'da sohbet ederken arka planda Spotify çalıyor 🎧",
        "GitHub'da inceleme yaparken müzik dinliyor 🛠️",
    ],
}


# ──────────────────────────────────────────────
#  Language & Style
# ──────────────────────────────────────────────

LANGUAGE_MAP = {
    "tr": "Türkçe",
    "en": "English",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
}


# ──────────────────────────────────────────────
#  Cache & Stats
# ──────────────────────────────────────────────

class StatusCache:
    """Cache with history to enforce variety."""

    def __init__(self, max_history: int = 10):
        self._last_key: str = ""
        self._last_status: str = ""
        self._last_time: float = 0
        self._cache_ttl: float = 60
        self._history: list[str] = []
        self._max_history = max_history

    def get(self, key: str) -> Optional[str]:
        if (key == self._last_key
                and self._last_status
                and (time.time() - self._last_time) < self._cache_ttl):
            return self._last_status
        return None

    def set(self, key: str, status: str):
        self._last_key = key
        self._last_status = status
        self._last_time = time.time()
        self._history.append(status)
        if len(self._history) > self._max_history:
            self._history.pop(0)

    @property
    def recent(self) -> list[str]:
        return self._history[-3:]


class Stats:
    """AI engine statistics."""
    def __init__(self):
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.cache_hits = 0
        self.start_time = time.time()

    @property
    def uptime(self) -> str:
        elapsed = int(time.time() - self.start_time)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}s {minutes}d {seconds}s"
        return f"{minutes}d {seconds}s"

    @property
    def success_rate(self) -> str:
        if self.total_calls == 0:
            return "N/A"
        rate = (self.successful_calls / self.total_calls) * 100
        return f"{rate:.0f}%"


_cache = StatusCache()
stats = Stats()


# ──────────────────────────────────────────────
#  Providers
# ──────────────────────────────────────────────

def _generate_with_gemini(prompt: str, config: dict) -> str:
    import google.generativeai as genai
    genai.configure(api_key=config["ai_api_key"])
    model = genai.GenerativeModel(
        model_name=config.get("ai_model", "gemini-2.0-flash"),
        system_instruction=_build_system_prompt(config),
    )
    response = model.generate_content(prompt)
    return _clean(response.text)


def _generate_with_openai(prompt: str, config: dict) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=config["ai_api_key"])
    response = client.chat.completions.create(
        model=config.get("ai_model", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": _build_system_prompt(config)},
            {"role": "user", "content": prompt},
        ],
        max_tokens=80,
        temperature=0.9,
    )
    return _clean(response.choices[0].message.content)


def _generate_with_groq(prompt: str, config: dict) -> str:
    from groq import Groq
    client = Groq(api_key=config["ai_api_key"])
    response = client.chat.completions.create(
        model=config.get("ai_model", "llama-3.3-70b-versatile"),
        messages=[
            {"role": "system", "content": _build_system_prompt(config)},
            {"role": "user", "content": prompt},
        ],
        max_tokens=80,
        temperature=0.9,
    )
    return _clean(response.choices[0].message.content)


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────

def _resolve_persona(config: dict) -> str:
    persona_key = config.get("persona", "custom")
    
    # If custom and text is provided, use that literal text
    if persona_key == "custom":
        custom_text = config.get("custom_persona_text", "").strip()
        if custom_text:
            return custom_text

    presets = config.get("persona_presets", {})
    if persona_key in presets:
        return presets[persona_key]
    return persona_key


def _build_system_prompt(config: dict) -> str:
    lang_code = config.get("language", "tr")
    language_name = LANGUAGE_MAP.get(lang_code, lang_code)
    persona_key = config.get("persona", "custom")
    persona_desc = _resolve_persona(config)

    examples_list = PERSONA_EXAMPLES.get(persona_key, PERSONA_EXAMPLES["custom"])
    examples = "\n".join(
        f"- {ex}" for ex in random.sample(examples_list, min(3, len(examples_list)))
    )

    return STORYTELLER_PROMPT.format(
        max_len=MAX_STATUS_LENGTH,
        persona=persona_desc,
        language_name=language_name,
        examples=examples,
    )


def _build_user_prompt(activity_context: str) -> str:
    """Build the user prompt with activity data and variety enforcement."""
    prompt = activity_context

    recent = _cache.recent
    if recent:
        avoid = " | ".join(f'"{s}"' for s in recent)
        prompt += f"\n\nÖNCEKİ MESAJLAR (bunlardan farklı yaz): {avoid}"

    return prompt


def _clean(text: str) -> str:
    """Aggressively clean AI output."""
    if not text:
        return ""
    for _ in range(3):
        text = text.strip()
        text = text.strip('"').strip("'").strip('`')
        while text.startswith("- ") or text.startswith("• "):
            text = text[2:]
        while text.startswith("* ") or text.startswith("# "):
            text = text[2:]
        if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            text = text[1:-1]
        if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
            text = text[1:-1]
    text = text.strip()
    while text and text[0] in ('-', '•', '"', "'", '`', '#', '*', '>'):
        text = text[1:].lstrip()

    # Enforce length
    if len(text) > MAX_STATUS_LENGTH:
        text = text[:MAX_STATUS_LENGTH - 1]
        last_space = text.rfind(" ")
        if last_space > MAX_STATUS_LENGTH // 2:
            text = text[:last_space]
        text += "…"

    return text.strip()


# ──────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────

def generate_status(activity_context: str, config: dict) -> str:
    """
    Generate a storytelling Discord status from multi-source activity context.
    """
    if not activity_context or activity_context.strip() in ("", "Bilgisayar başında"):
        return config.get("fallback_status", "💤 AFK")

    # Cache check
    cached = _cache.get(activity_context)
    if cached:
        stats.cache_hits += 1
        return cached

    provider = config.get("ai_provider", "gemini").lower()
    stats.total_calls += 1
    prompt = _build_user_prompt(activity_context)

    try:
        if provider == "openai":
            status = _generate_with_openai(prompt, config)
        elif provider == "groq":
            status = _generate_with_groq(prompt, config)
        else:
            status = _generate_with_gemini(prompt, config)

        if not status:
            raise ValueError("Boş yanıt")

        stats.successful_calls += 1
        _cache.set(activity_context, status)
        return status

    except Exception as e:
        stats.failed_calls += 1
        print(f"  ⚠️  Storyteller hatası: {e}")
        return config.get("fallback_status", "💤 AFK — Birazdan dönerim.")


def get_stats() -> Stats:
    return stats
