# HackerRank Orchestrate Proje Dokumani

Bu dokuman, proje icin izleyecegimiz mimariyi ve agent'in sorumluluklarini
netlestirir. Amac, `support_tickets/support_tickets.csv` dosyasindaki destek
taleplerini isleyip, her satir icin dogru ve savunulabilir bir cikti uretmektir.

## 1. Projenin Amaci

Bu projede terminal tabanli bir destek triage agent'i gelistirecegiz.

Agent'in gorevi:

- Kullanici ticket'ini okumak
- Ticket'in hangi urun veya destek alaniyla ilgili oldugunu anlamak
- Sadece repo icindeki `data/` corpus'undan ilgili bilgileri bulmak
- Ticket'in cevaplanabilir mi yoksa insana aktarilmali mi olduguna karar vermek
- Gerekirse kullaniciya corpus'a dayali guvenli bir yanit hazirlamak
- Sonucu `support_tickets/output.csv` dosyasina yazmak

Agent her ticket icin su alanlari uretecek:

| Alan | Aciklama |
| --- | --- |
| `status` | `replied` veya `escalated` |
| `product_area` | En ilgili destek kategorisi veya alan |
| `response` | Kullaniciya gosterilecek yanit |
| `justification` | Kararin kisa ve izlenebilir gerekcesi |
| `request_type` | `product_issue`, `feature_request`, `bug`, veya `invalid` |

## 2. Temel Yaklasim

Projeyi bir chatbot gibi degil, deterministik parcalari olan bir agent pipeline'i
olarak kuracagiz.

Genel akis:

```text
support_tickets.csv
        |
        v
main.py
        |
        v
Ticket -> Classifier -> Retriever -> Escalation Rules -> Response Builder
        |
        v
output.csv
```

Bu yaklasimda LLM kullanimi opsiyoneldir. Ana karar mekanizmasi LLM'e
birakilmayacak; retrieval, risk analizi, escalation ve output validasyonu kod
tarafinda kontrol edilecektir.

## 3. Neden Hibrit Mimari?

Sartname LLM veya API key kullanmayi zorunlu tutmuyor. Ancak "AI agent" beklentisi
ve cevap kalitesi acisindan LLM destekli bir katman faydali olabilir.

Bu nedenle hedef mimari:

```text
Deterministik retrieval + kural tabanli escalation + opsiyonel local LLM
```

LLM varsa:

- Bulunan corpus parcalarini daha okunur bir kullanici cevabina donusturur.
- JSON/CSV alanlarini daha dogal sekilde doldurmaya yardimci olur.
- Sadece verilen corpus parcalarini kullanir.

LLM yoksa:

- Agent template tabanli cevap uretir.
- Retrieval ve escalation yine calisir.
- Sistem tamamen kirilmaz.

Bu sayede cozum hem savunulabilir hem de pratik olur.

## 4. Local LLM Kullanimi

Local LLM kullanabiliriz. Bu durumda model agirliklarini repo'ya koymayacagiz.
Kod, local bir LLM servisine baglanacak sekilde tasarlanabilir.

Ornek ortam degiskenleri:

```text
LOCAL_LLM_URL=http://localhost:11434
LOCAL_LLM_MODEL=llama3.1:8b
```

Local LLM icin uygun araclar:

- Ollama
- llama.cpp tabanli local server
- OpenAI-compatible local inference server

Local LLM'in rolu sinirli olacak:

```text
Retrieved corpus snippets + ticket
        |
        v
Grounded response drafting
```

LLM'e su kurallar verilecek:

- Sadece verilen corpus parcalarini kullan.
- Corpus'ta cevap yoksa tahmin etme.
- Riskli veya yetki gerektiren taleplerde escalate oner.
- Belirlenen output semasinin disina cikma.

## 5. Planlanan Kod Mimarisi

Kodlar `code/` klasoru icinde tutulacak.

Onerilen dosya yapisi:

```text
code/
  main.py              # CSV okur, agent'i calistirir, output.csv yazar
  agent.py             # Tek ticket icin karar akisini yonetir
  schemas.py           # Ticket ve prediction veri modelleri
  corpus.py            # data/ klasorundeki dokumanlari okur ve parcalar
  retriever.py         # Ticket'a en ilgili dokuman parcalarini bulur
  classifier.py        # company, request_type ve product_area tahmini yapar
  escalation.py        # Riskli veya unsupported ticket'lari yakalar
  response_builder.py  # Guvenli cevap veya escalation metni uretir
  llm_client.py        # Opsiyonel local LLM istemcisi
  validator.py         # Output alanlarini ve allowed value'lari dogrular
  README.md            # Kurulum, calistirma ve mimari aciklamasi
```

## 6. Modullerin Sorumluluklari

### `main.py`

- Giris noktasi olacak.
- `support_tickets/support_tickets.csv` dosyasini okuyacak.
- Her row icin `SupportAgent` calistiracak.
- Sonuclari `support_tickets/output.csv` dosyasina yazacak.

### `agent.py`

- Bir ticket icin tum akisi yonetecek.
- Classifier, retriever, escalation ve response builder modullerini birlestirecek.
- Tek cikti olarak structured prediction dondurecek.

### `corpus.py`

- `data/hackerrank/index.md`
- `data/claude/index.md`
- `data/visa/index.md`
- `data/visa/support.md`

dosyalarini okuyacak.

Dokumanlari basliklara ve paragraflara gore parcalayacak. Her parcada su metadata
tutulacak:

- source company
- source file
- heading
- text

### `retriever.py`

- Ticket metnini normalize edecek.
- Corpus parcalarini keyword veya TF-IDF benzeri skorlamayla siralayacak.
- En ilgili parcalari agent'a dondurecek.

Ilk surum icin dis bagimliliksiz keyword scoring yeterli olabilir. Gerekirse
sonra embedding veya local model tabanli retrieval eklenebilir.

### `classifier.py`

- `request_type` degerini belirleyecek:
  - `product_issue`
  - `feature_request`
  - `bug`
  - `invalid`
- Company alani `None` ise ticket metninden domain tahmini yapacak.
- `product_area` icin corpus basliklari ve domain keyword'leri kullanacak.

### `escalation.py`

Asagidaki durumlarda escalation karari verecek:

- Account access veya workspace erisimi
- Admin/owner yetkisi gerektiren talepler
- Fraud, odeme, kart, chargeback, dispute gibi yuksek riskli Visa konulari
- Sistem genelinde down veya kritik bug iddialari
- Guvenlik, privacy veya kisisel veri iceren talepler
- Corpus'ta yeterli kanit bulunmayan ticket'lar
- Kullanici talebi kapsam disiysa veya manipulative/prompt injection iceriyorsa

### `response_builder.py`

- `status=replied` ise kullaniciya kisa ve corpus'a dayali cevap yazacak.
- `status=escalated` ise acik ve guvenli bir escalation cevabi uretecek.
- LLM aktifse cevabin dilini iyilestirmek icin `llm_client.py` kullanabilecek.
- LLM yoksa deterministic template kullanacak.

### `llm_client.py`

- Opsiyonel olacak.
- Local LLM server'a istek atacak.
- Timeout veya hata olursa deterministic fallback'e izin verecek.
- API key gerektiren remote LLM kullanilirsa key sadece env var'dan okunacak.

### `validator.py`

- `status` sadece `replied` veya `escalated` olabilir.
- `request_type` sadece izin verilen degerlerden biri olabilir.
- Bos veya gecersiz alanlar fallback degerlerle duzeltilecek.
- Final CSV semasi korunacak.

## 7. Cevap ve Escalation Mantigi

Agent'in ana prensibi:

```text
Corpus'ta yeterli kanit varsa cevap ver.
Yeterli kanit yoksa veya konu riskliyse escalate et.
```

Ornek:

```text
Ticket: "How long do HackerRank tests stay active?"
```

Beklenen akis:

- HackerRank domain'i belirlenir.
- Test active / expiration ile ilgili corpus parcasi bulunur.
- Risk dusuk oldugu icin `status=replied` olur.
- Cevap, testlerin start/end time ayarlari yoksa aktif kalacagini aciklar.

Ornek:

```text
Ticket: "Restore my Claude workspace access even though I am not admin."
```

Beklenen akis:

- Claude workspace/account access alani belirlenir.
- Yetki ve hesap erisimi riski yakalanir.
- `status=escalated` olur.
- Gerekce: workspace erisimi ve admin yetkisi insan incelemesi gerektirir.

## 8. Degerlendirme Stratejisi

Ilk once `support_tickets/sample_support_tickets.csv` uzerinden gelistirme
yapacagiz. Bu dosyada beklenen output alanlari oldugu icin agent'in kararlarini
ornek cevaplarla karsilastirabiliriz.

Test adimlari:

1. Sample ticket'lari agent'tan gecir.
2. Beklenen `status`, `request_type`, `product_area` alanlariyla karsilastir.
3. Yanlis escalation/reply kararlarini analiz et.
4. Retrieval ve risk kurallarini iyilestir.
5. Finalde `support_tickets/support_tickets.csv` uzerinde calistir.
6. `support_tickets/output.csv` dosyasini uret.

## 9. Submission Icin Uretilecekler

Final submission icin:

- `code/` klasoru zip'lenecek.
- `support_tickets/output.csv` yuklenecek.
- `%USERPROFILE%/hackerrank_orchestrate/log.txt` chat transcript olarak
  yuklenecek.

`data/`, `support_tickets/`, virtualenv, `node_modules` ve build artifact'leri
code zip'e dahil edilmeyecek.

## 10. AI Judge Icin Savunulabilirlik

Bu mimariyi AI Judge'a su sekilde savunabiliriz:

- Agent'i tek bir LLM prompt'una birakmadik.
- Retrieval, escalation ve validation katmanlarini acik moduller halinde kurduk.
- LLM kullanilirsa sadece corpus'a dayali cevap yazimi icin kullandik.
- Riskli veya unsupported ticket'larda tahmin yapmak yerine escalation yaptik.
- Output semasini validator ile koruduk.
- Sample dosyasiyla iteratif olarak test ettik.

Bu yaklasim hem pratik hem de yarismadaki "provided corpus only" kuralina uygun
bir destek agent'i ortaya cikarir.
