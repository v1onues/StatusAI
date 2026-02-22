<p align="center">
  <h1 align="center">⚡ StatusAI v3.0.0</h1>
  <p align="center">
    <strong>AI-Powered Discord Rich Presence & Masaüstü Uygulaması</strong><br>
    Bilgisayarındaki aktif pencereleri takip edip, AI ile havalı durum mesajları yayınla. Artık yepyeni 8-bit retro arayüzü ve yerleşik otomatik güncelleme sistemiyle!
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/Discord-RPC-5865F2?logo=discord&logoColor=white" alt="Discord">
    <img src="https://img.shields.io/badge/AI-Gemini%20%7C%20OpenAI%20%7C%20Groq-orange?logo=google&logoColor=white" alt="AI">
  </p>
</p>

---

## 🚀 StatusAI Nedir?

StatusAI, bilgisayarında hangi uygulamanın veya oyunun açık olduğunu algılayıp, AI (Gemini, OpenAI veya Groq) kullanarak Discord profilinde **esprili, teknik ve karizmatik** durum mesajları yayınlayan akıllı bir masaüstü aracıdır.

Sürüm **3.0.0** ile birlikte artık terminal siyah ekranlarından kurtulup; performans sensörleri, Discord Live Preview (Canlı Önizleme), Kara Liste filtreleme ve Dinamik Persona seçimi gibi devasa yenilikleri barındıran **tamamen bağımsız bir Webview Masaüstü (.exe)** uygulaması haline geldi!

**Örnek AI durum çıktıları:**
```
⚡ Auth sistemini hackliyor... şaka, yazıyorum
🎵 Spotify + Code = Tanrı modu aktif
🔥 Bug avında, silah: console.log
🎮 Ranked'da carry, hayatta da carry
```

---

## ✨ v3.0.0 Yeni Özellikler

### 🕹️ 8-Bit Retro Dashboard
Uygulama artık tamamen görsel, karanlık mod ve 8-bit / piksel sanat tasarım diline sahip havalı bir arayüze (Dashboard) sahip! Menüler arası geçiş, log ekranı, konfigürasyon ve daha fazlası.

### 👾 Discord Live Preview Widget
Discord arayüzünü birebir taklit eden, arka plandaki AI motorunun ne tür bir durum (status) ürettiğini, ne kadar süredir çalıştığını (Uptime) gerçek zamanlı ve canlı olarak gösteren bir eklenti penceresi eklendi.

### 🛡️ Gizlilik ve Kara Liste (Blacklist) Sistemi
Ayarlar menüsüne eklenen **Kara Liste** alanına virgülle ayırarak girdiğiniz kelimeler (örn: *Banka, Özel, Şifre*) takip edilen pencere ismiyle eşleşirse, StatusAI otomatik olarak kendini gizler ve Discord'da uygulamanızı "Gizli (Hidden)" olarak gösterir. Böylece istemediğiniz pencereler başkaları tarafından asla görülmez.

### 🎭 Dinamik Karakterler (Personalar)
Artık AI'ın senin adına atacağı mesajların üslubunu tek tuşla seçebilirsin!
* **Geliştirici:** Teknik, kod üzerine ve esprili.
* **Agresif:** Sert, rekabetçi (Oyunlar için harika).
* **Şairane:** Edebi ve sanatsal bir ton.
* **Özel:** %100 kendi belirleyeceğin komutlarla!

### 📊 Canlı Performans Monitörü
Arayüzün içerisindeki sekmelerde anlık olarak CPU (işlemci) ve RAM kullanım yüzdeleri 8-bit bir ilerleme çubuğuyla saniyede bir güncellenir. Ayrı bir görev yöneticisi açmana gerek kalmaz.

### 🔄 Otomatik Güncelleyici (Auto-Updater)
Senin hiçbir şey indirmene gerek kalmadan; StatusAI açıldığında **GitHub üzerinden** yeni sürüm kontrolü yapar. Eğer yayınlanmış yeni bir versiyon bulursa, yukarıdan aşağıya şık bir "Yeni Sürüm Mevcut!" bildirim banner'ı indirir ve tek tıkla yeni .exe'yi almanı sağlar.

### 📦 Kurulumsuz "Tek Tıkla" Kullanım (.exe)
Eski sürümlerdeki Python kurulum eziyeti tamamen kaldırıldı. Artık tek bir **StatusAI.exe** dosyası olarak sunuluyor. Çalıştırıldığında masaüstü penceresi açılır, kapatılırsa **sistem tepsisine (sağ alt köşe)** yerleşerek arka planda güç tüketmeden sessizce çalışmaya devam eder.

---

## 💻 Kurulum ve Kullanım

### Yöntem 1: Doğrudan Executable (Önerilen)

Eğer sadece programı kullanmak istiyorsan, kodlarla uğraşmana gerek yok:
1. GitHub deposundaki **Releases (Sürümler)** sekmesine git.
2. En güncel **StatusAI_v3.0.0.exe** dosyasını indir.
3. Çift tıkla ve çalıştır! (Windows Defender ilk açılışta uyarı verebilir, "Yine de Çalıştır" demen yeterli).
4. Arayüz açılınca `Ayarlar` menüsünden **Discord Client ID** ve **AI API Key** (örn: Gemini/Groq) girip kaydet.
5. Ana ekrandan botu Başlat!

### Yöntem 2: Kaynak Kodundan Çalıştırma / Geliştirme

Koda müdahale etmek, kendi `build` (derleme) işlemini yapmak istersen:

1. **Gereksinimler:** Python 3.10+ yüklü olmalı.
2. Depoyu klonla:
   ```bash
   git clone https://github.com/v1onues/StatusAI.git
   cd StatusAI
   ```
3. Bağımlılıkları yükle:
   ```bash
   pip install -r requirements.txt
   ```
4. Kendi `StatusAI.exe` dosyanı derlemek ve üretmek için hazır betiği çalıştır:
   ```bash
   python build.py
   ```
   *Not: İşlem bittiğinde `dist` klasörü içerisinde tamamen entegre `.exe` dosyası bulunacaktır.*

---

## 🔑 Discord Application Nasıl Kurulur?

1. [Discord Developer Portal](https://discord.com/developers/applications) adresine git.
2. **"New Application"** butonuna tıkla.
3. Uygulamaya havalı bir isim ver.
4. Sol taraftan **"OAuth2" -> "General"** sekmesindeki **"Application ID"** kopyala.
5. Bu numarayı StatusAI penceresindeki **Ayarlar -> Discord Client ID** alanına yapıştır!

---

## 🛠️ Mimari ve Teknolojiler

* **Frontend:** Vanilla JS, CSS3, DOM API (Siyah Beyaz minimalist 8-bit / Pixel-art konsepti).
* **Backend:** Python, Flask (Lokal mikro-sunucu), PyWebview, Threading (`.exe` içinde lokal porttan çalışır).
* **AI Engine:** Google Gemini, Groq, OpenAI API'ları.
* **Sistem Takibi:** ctypes (Windows API), psutil, win32gui.
* **Paketleme:** PyInstaller (Standalone binary compiler).
* **Sistem Tepsisi:** PyStray, Pillow.

---

## 📡 GitHub Profiline Canlı Durum Ekleme (Koleth Presence) 💎

StatusAI'nın en can alıcı yan özelliklerinden biri, Discord durumunuzu anlık olarak GitHub profilinizde (README) jilet gibi bir kart olarak göstermenize olanak tanımasıdır!

### 1. Kurulum ve Hazırlık
Discord API kısıtlamaları gereği, Discord botunun sizi "Online" görebilmesi ve anlık statuslarınızı çekebilmesi için botla en az bir ortak sunucuda bulunmanız gerekir.
👉 **[Koleth Discord Sunucusuna Katıl](https://discord.gg/koleth)**

### 2. README Dosyasına Kartı Ekleyin
Kendi GitHub profilinize gidip (kullanıcı adınızla aynı olan depo), `README.md` dosyasını açın ve şu kodu istediğiniz yere yapıştırın:

```html
<p align="center">
  <img src="https://koleth-presence.vercel.app/api/presence/SENIN_DISCORD_ID_BURAYA" alt="My Live Status" />
</p>
```
*(Not: URL'deki `SENIN_DISCORD_ID_BURAYA` kısmını kendi gerçek 18 haneli Discord numaranla değiştirmeyi unutma!)*

> **🔥 Pro Tip:** Linkin sonuna `?v=1` gibi rastgele değerler ekleyerek (örn: `.../ID?v=2`) GitHub'ın sinir bozucu görsel önbelleğini (cache) istediğiniz zaman kırabilir ve durumunuzu saniyesinde GitHub profilinizde güncelleyebilirsiniz.

---

## 🤝 Katkıda Bulunun

Projeye katkı sağlamaktan çekinmeyin! Yeni özellikler eklemek, farklı diller / temalar tasarlamak (Örn: Anime teması, Cyberpunk vs.) veya hataları bildirmek isterseniz "Pull Request" veya "Issues" sekmesini kullanabilirsiniz.

Güle güle, afiyetle status atın! 🎉
