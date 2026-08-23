# OZKOK Loudness & Codec Simulator

**OZKOK Loudness & Codec Simulator**, masterlanmış (mastering işlemi bitmiş) ses dosyalarınızın Spotify, Apple Music, YouTube gibi popüler müzik akış platformlarında nasıl duyulacağını önceden test etmenizi sağlayan profesyonel bir analiz ve simülasyon aracıdır.

## 🌟 Özellikler
- **Gerçek Zamanlı Simülasyon:** Master dosyanızın Spotify, Apple Music, YouTube Music, TIDAL, Amazon Music ve Deezer platformlarındaki ses seviyesini anında duyun.
- **Loudness Normalization (Ses Seviyesi Normalizasyonu):** Platformların kendi normalizasyon algoritmalarına uygun olarak (Örn: Spotify için -14 LUFS) şarkınızın sesinin ne kadar kısılacağını (Penalty) veya açılacağını hesaplar.
- **Kayıpsız A/B Karşılaştırması:** Orijinal Master dosyanız ile Stream (Platform) versiyonu arasında kesintisiz, anlık geçişler (A/B) yaparak farklılıkları duyun.
- **Delta (Δ) Modu:** Yalnızca codec'in sese verdiği zararı veya kayıpları duymak için Orijinal ve Stream arasındaki fark sesini (Delta) dinleyin.
- **True Peak (Gerçek Tepe) Ölçümü ve ISP Tespiti:** Lossy (kayıplı) sıkıştırma sırasında ortaya çıkabilecek "Intersample Peak" (ISP) kırpılmalarını (clipping) otomatik olarak tespit edip uyarır.
- **Anında Dışa Aktarım (Export):** Simüle edilmiş ses dosyasını daha sonra incelemek üzere .wav formatında kaydedebilirsiniz.

## 🛠️ Nasıl Kullanılır?
1. **Dosya Yükleme:** Uygulamayı açın ve analiz etmek istediğiniz bir `WAV` veya `FLAC` dosyasını pencerenin ortasındaki alana sürükleyip bırakın.
2. **Platform Seçimi:** Şarkınızın yüklendiği platformlar anında analiz edilir. Ekrandaki platform kartlarından dinlemek istediğinizi seçin (Örn: Spotify, Apple Music).
3. **Dinleme Modları:**
   - **Normalize (ON/OFF):** Seçili platformun normalizasyon işlemini uygulayıp uygulamayacağını belirler. 
   - **A (Original) / B (Stream):** Orijinal (müdahale edilmemiş) master dosyanız ile seçili platformun yayınlayacağı versiyon arasında geçiş yapar.
   - **Delta (Δ):** Kayıplı sıkıştırma (Ogg/AAC) yüzünden seste meydana gelen net farkı duymanızı sağlar.
4. **Export:** Seçtiğiniz platform ayarlarına göre işlenmiş sesi dışa aktarmak için sağ alttaki `Export WAV` butonunu kullanın.

   <img width="1916" height="1002" alt="image" src="https://github.com/user-attachments/assets/baae5ef5-765a-43b5-8627-fc76b21fac92" />

   <img width="1919" height="1002" alt="image" src="https://github.com/user-attachments/assets/ea4121ce-c755-46a6-bede-8f39ff4b4e6b" />



## ⚙️ Arka Planda Neler Oluyor?
OZKOK Loudness Simulator, sadece basit bir ses kısma aracı değildir. Yüklediğiniz dosya üzerinde iki aşamalı profesyonel bir DSP (Digital Signal Processing - Dijital Sinyal İşleme) zinciri çalıştırır:

1. **LUFS Analizi (ITU-R BS.1770-4):** Ses dosyanız uluslararası yayın standartlarına göre analiz edilir. Şarkının Integrated LUFS (Entegre Ses Şiddeti) değeri ve True Peak (Gerçek Tepe Noktası) hassas bir şekilde ölçülür.
2. **Codec Simülasyonu:** Gerçek dünyadaki platformların kullandığı sıkıştırma algoritmaları birebir taklit edilir. 
   - Spotify için **Ogg Vorbis**, Apple Music için **AAC** gibi codec'ler ile ses geçici olarak kodlanıp (encode) tekrar çözülür (decode).
   - Bu kayıplı (lossy) sıkıştırma sırasında meydana gelebilecek duyulabilir frekans kayıpları, stereo imaj daralmaları veya tepe noktası bozulmaları (Intersample Peaks) hesaplanarak ekrana yansıtılır.
3. **Faz Uyumlu Çıkarma (Phase Alignment):** Delta (Δ) modu çalışırken, orijinal sinyal ile kodlanmış sinyal arasındaki ufak zaman (faz) kaymaları matematiksel olarak sıfırlanır (Cross-correlation). Böylece tarak filtrelenmesi (comb filtering) olmadan **gerçek codec artifact'lerini** duyarsınız.

---
*(Bu uygulama taşınabilirdir (portable) ve herhangi bir kuruluma ihtiyaç duymaz. Klasörü USB ile başka bir Windows bilgisayara taşıyıp direkt olarak `OZKOK Loudness Simulator.exe` dosyasını çalıştırarak kullanabilirsiniz.)*

