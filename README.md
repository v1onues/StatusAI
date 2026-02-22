<p align="center">
  <h1 align="center">⚡ StatusAI</h1>
  <p align="center">
    <strong>AI-Powered Discord Rich Presence</strong><br>
    Bilgisayarındaki aktif pencereleri takip edip, AI ile havalı durum mesajları yayınla.
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/Discord-RPC-5865F2?logo=discord&logoColor=white" alt="Discord">
    <img src="https://img.shields.io/badge/AI-Gemini%20%7C%20OpenAI%20%7C%20Groq-orange?logo=google&logoColor=white" alt="AI">
  </p>
</p>

---

## 🚀 Ne Yapıyor?

StatusAI, bilgisayarında hangi uygulamanın açık olduğunu algılayıp, AI (Gemini, OpenAI veya Groq) kullanarak Discord profilinde **esprili, teknik ve karizmatik** durum mesajları yayınlar.

**Örnek çıktılar:**
```
⚡ Auth sistemini hackliyor... şaka, yazıyorum
🎵 Spotify + Code = Tanrı modu aktif
🔥 Bug avında, silah: console.log
🎮 Ranked'da carry, hayatta da carry
```

## ✨ Özellikler

| Özellik | Açıklama |
|---------|----------|
| 🖥️ **Akıllı Takip** | VS Code, Spotify, Browser, Oyunlar ve daha fazlasını otomatik algılar |
| 🤖 **AI Entegrasyonu** | Gemini, OpenAI veya Groq ile anlık status üretimi |
| 🎮 **Oyun Tespiti** | VALORANT, LoL, CS2, GTA V, Minecraft... otomatik tanır |
| 📁 **VS Code Detayı** | Hangi dosyayı ve projeyi düzenlediğinizi yakalar |
| 🎵 **Spotify Desteği** | Dinlediğiniz şarkıyı status'a yansıtır |
| 🔄 **Dinamik Güncelleme** | Her 15-30 saniyede otomatik yenileme |
| 🛡️ **Hata Toleransı** | İnternet koparsa offline moda geçer, kapanmaz |
| ⚡ **Önbellek** | Aynı aktivite tekrarında API'yi boşuna çağırmaz |

---

## 📦 Kurulum

### 1. Gereksinimler

- **Python 3.10+** — [İndir](https://www.python.org/downloads/)
- **Discord Masaüstü Uygulaması** — Açık olmalı

### 2. Bağımlılıkları Yükle

```bash
pip install -r requirements.txt
```

### 3. Discord Uygulama Oluştur

1. [Discord Developer Portal](https://discord.com/developers/applications) adresine git
2. **"New Application"** butonuna tıkla
3. Uygulamaya bir isim ver (örn: `StatusAI`)
4. Sol menüden **"OAuth2"** > **"General"** sayfasına git
5. **"Application ID"** numarasını kopyala — bu senin `discord_client_id` değerin

> **İpucu:** Rich Presence'ta büyük resim göstermek istiyorsan, sol menüden **"Rich Presence"** > **"Art Assets"** kısmına `logo` adında bir görsel yükle.

### 4. Config Dosyasını Düzenle

`config.json` dosyasını aç ve bilgilerini gir:

```json
{
    "discord_client_id": "123456789012345678",
    "ai_provider": "gemini",
    "ai_api_key": "AIza...",
    "ai_model": "gemini-2.0-flash",
    "persona": "Karizmatik bir senior developer, esprili ve teknik",
    "language": "tr",
    "update_interval": 20,
    "fallback_status": "💤 AFK — Birazdan dönerim."
}
```

| Alan | Açıklama |
|------|----------|
| `discord_client_id` | Discord Developer Portal'dan aldığın Application ID |
| `ai_provider` | `"gemini"`, `"openai"` veya `"groq"` |
| `ai_api_key` | Gemini, OpenAI veya Groq API anahtarın |
| `ai_model` | Kullanılacak model (varsayılan: `gemini-2.0-flash`) |
| `persona` | AI'ın karakteri — durum mesajlarının tonu buna göre şekillenir |
| `language` | Mesaj dili: `tr`, `en`, `de`, `fr`, `es` |
| `update_interval` | Kaç saniyede bir güncelleme yapılacak (15-60) |
| `fallback_status` | API hata verdiğinde gösterilecek statik mesaj |
| `tracked_apps` | Takip edilecek uygulamalar (process adı → görünen ad) |

### 5. Çalıştır

```bash
python main.py
```

---

## 🎯 AI Provider Seçimi

### Google Gemini (Önerilen)
- **Ücretsiz katman** mevcut — düşük hacimli kullanım için ideal
- API Key al: [Google AI Studio](https://aistudio.google.com/apikey)
- `config.json`'da:
  ```json
  "ai_provider": "gemini",
  "ai_model": "gemini-2.0-flash"
  ```

### OpenAI
- API Key al: [OpenAI Platform](https://platform.openai.com/api-keys)
- `config.json`'da:
  ```json
  "ai_provider": "openai",
  "ai_model": "gpt-4o-mini"
  ```

### Groq (Ultra-Hızlı)
- **Ücretsiz katman** mevcut — en hızlı inference
- API Key al: [Groq Console](https://console.groq.com/keys)
- `config.json`'da:
  ```json
  "ai_provider": "groq",
  "ai_model": "llama-3.3-70b-versatile"
  ```

---

## 🛠️ Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| `Discord'a bağlanılamadı` | Discord uygulamasının açık olduğundan emin ol |
| `config.json parse hatası` | JSON formatını kontrol et (virgüller, tırnak işaretleri) |
| `API Key hatası` | API anahtarının doğru ve aktif olduğunu kontrol et |
| `Durum gözükmüyor` | Discord ayarlarından **Activity Status** açık olmalı |

---

## 📂 Proje Yapısı

```
StatusAI/
├── main.py          # Ana orkestratör — RPC döngüsü
├── trackers.py      # Pencere ve süreç takipçisi
├── ai_engine.py     # AI durum mesajı üreticisi
├── config.json      # Kullanıcı ayarları
├── requirements.txt # Python bağımlılıkları
└── README.md        # Bu dosya
```

---

<p align="center">
  <sub>Made with ⚡ by StatusAI</sub>
</p>
