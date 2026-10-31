"""English / Turkish strings for the charts and the dashboard.

Data stays in English internally (category keys, phase names); labels are
translated only at display time, so both languages always show the same numbers.
"""

from __future__ import annotations

from src.taxonomy import CATEGORIES

LANGS = {"en": "English", "tr": "Türkçe"}

CATEGORY_TR = {
    "customer_support": "Müşteri desteği",
    "account_restriction": "Hesap kısıtlama / KYC",
    "fees": "Ücretler ve fiyatlandırma",
    "transfers": "Transfer ve ödemeler",
    "fraud_security": "Dolandırıcılık, güvenlik ve gizlilik",
    "disputes_refunds": "İtiraz ve iadeler",
    "login_access": "Giriş ve kayıt",
    "app_bugs": "Uygulama hataları ve kullanılabilirlik",
    "card": "Kart sorunları",
    "features": "Ürün özellikleri ve limitler",
    "service_disruption": "Hizmet kapanması / yasal süreç",
    "other": "Diğer / sınıflandırılamayan",
}

PHASE_TR = {
    "Before the event": "Olay öncesi",
    "Shock 1": "1. şok",
    "Shock 2": "2. şok",
    "Between shocks 1 and 2": "Şoklar arası",
    "After the event": "Olay sonrası",
    "Relaunch": "Yeniden açılış",
}

# d3 locale definitions, applied to Vega-Lite charts in Turkish mode.
TR_LOCALE = {
    "number": {"decimal": ",", "thousands": ".", "grouping": [3], "currency": ["₺", ""]},
    "time": {
        "dateTime": "%a %e %b %X %Y", "date": "%d.%m.%Y", "time": "%H:%M:%S",
        "periods": ["ÖÖ", "ÖS"],
        "days": ["Pazar", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi"],
        "shortDays": ["Paz", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt"],
        "months": ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
                   "Eylül", "Ekim", "Kasım", "Aralık"],
        "shortMonths": ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki",
                        "Kas", "Ara"],
    },
}

STRINGS: dict[str, dict[str, str]] = {
    # ---- chart: shared --------------------------------------------------- #
    "app": {"en": "App", "tr": "Uygulama"},
    "category": {"en": "Category", "tr": "Kategori"},
    "share": {"en": "Share", "tr": "Pay"},
    "share_of_complaints": {"en": "Share of complaints", "tr": "Şikâyetler içindeki pay"},
    "complaints": {"en": "Complaints", "tr": "Şikâyet"},
    "all_complaints": {"en": "All complaints", "tr": "Toplam şikâyet"},
    "ci_low": {"en": "95% CI low", "tr": "%95 GA alt"},
    "ci_high": {"en": "95% CI high", "tr": "%95 GA üst"},
    "avg_rating": {"en": "Avg rating", "tr": "Ort. puan"},
    "avg_rating_axis": {"en": "Average rating (★)", "tr": "Ortalama puan (★)"},
    "month": {"en": "Month", "tr": "Ay"},
    "week_of": {"en": "Week of", "tr": "Hafta"},
    "reviews": {"en": "Reviews", "tr": "Yorum"},
    "phase": {"en": "Phase", "tr": "Dönem"},
    "start": {"en": "Start", "tr": "Başlangıç"},
    "end": {"en": "End", "tr": "Bitiş"},
    # ---- chart: complaint rate ------------------------------------------- #
    "rate_title": {"en": "How many reviews are complaints?",
                   "tr": "Yorumların ne kadarı şikâyet?"},
    "rate_subtitle": {"en": "Share of reviews with 3+ words classified as complaints",
                      "tr": "En az 3 kelimelik yorumlar içinde şikâyet olarak sınıflananların payı"},
    "rate_axis": {"en": "Share of reviews that are complaints",
                  "tr": "Şikâyet olan yorumların payı"},
    "complaint_rate": {"en": "Complaint rate", "tr": "Şikâyet oranı"},
    "reviews_with_text": {"en": "Reviews with text", "tr": "Metinli yorum"},
    # ---- chart: versions ------------------------------------------------- #
    "version": {"en": "Version", "tr": "Sürüm"},
    "significant_drop": {"en": "Significant drop", "tr": "Anlamlı düşüş"},
    "version_axis": {"en": "Version first seen in reviews",
                     "tr": "Sürümün yorumlarda ilk görüldüğü tarih"},
    "first_seen": {"en": "First seen", "tr": "İlk görülme"},
    "change_vs_prev": {"en": "Change vs previous", "tr": "Öncekine göre değişim"},
    "largest_rise": {"en": "Largest complaint rise", "tr": "En çok artan şikâyet"},
    "rise_pp": {"en": "Rise (pp)", "tr": "Artış (puan)"},
    "stars_unit": {"en": " stars", "tr": " yıldız"},
    "version_title": {"en": "{app}: average rating by app version",
                      "tr": "{app}: sürüme göre ortalama puan"},
    "group": {"en": "Group", "tr": "Grup"},
    # ---- chart: Papara --------------------------------------------------- #
    "reviews_per_week": {"en": "Reviews per week", "tr": "Haftalık yorum"},
    "rating_3wk": {"en": "Average rating (★, 3-wk mean)", "tr": "Ortalama puan (★, 3 hf. ort.)"},
    "complaint_share": {"en": "Complaint share", "tr": "Şikâyet payı"},
    "shutdown_share": {"en": "Shutdown/regulatory share", "tr": "Kapanma/yasal süreç payı"},
    "timeline_title": {"en": "Papara: review volume and rating around the 2025 legal process",
                       "tr": "Papara: 2025 hukuki süreci etrafında yorum hacmi ve puan"},
    "timeline_subtitle": {
        "en": "Shaded = event phases detected from the data (shocks and the restricted "
              "period between them); line = relaunch",
        "tr": "Gölgeli alan = veriden tespit edilen olay dönemleri (şoklar ve aradaki "
              "kısıtlı dönem); çizgi = yeniden açılış"},
    "phase_title": {"en": "Papara: what users complained about in each phase",
                    "tr": "Papara: her dönemde kullanıcılar neden şikâyet etti?"},
    # ---- chart titles passed by callers ---------------------------------- #
    "heatmap_title": {"en": "What do users complain about?",
                      "tr": "Kullanıcılar neden şikâyet ediyor?"},
    "heatmap_subtitle": {
        "en": "Share of complaints per main problem · hover for counts and 95% confidence "
              "intervals",
        "tr": "Ana soruna göre şikâyet payı · sayılar ve %95 güven aralıkları için üzerine gelin"},
    "stars_title": {"en": "Average star rating", "tr": "Ortalama yıldız puanı"},
    "sentiment_title": {"en": "Text sentiment", "tr": "Metin duygusu"},
    "sentiment_axis": {"en": "Sentiment (−1 negative … +1 positive)",
                       "tr": "Duygu (−1 olumsuz … +1 olumlu)"},
    "all_reviews": {"en": "All reviews", "tr": "Tüm yorumlar"},
    "reviews_3words": {"en": "Reviews with 3+ words", "tr": "En az 3 kelimelik yorumlar"},
    "rolling_note": {"en": " · 4-week rolling mean", "tr": " · 4 haftalık hareketli ortalama"},
    "paired_title": {"en": "What PayPal users complain about, v8 vs v10",
                     "tr": "PayPal kullanıcıları neden şikâyet ediyor: v8 ve v10"},
    "paired_subtitle": {"en": "Complaints since {date} (staged rollout)",
                        "tr": "{date} sonrasındaki şikâyetler (kademeli dağıtım)"},
    # ---- strengths and weaknesses ---------------------------------------- #
    "tab_strengths": {"en": "Strengths & weaknesses", "tr": "Güçlü ve zayıf yönler"},
    "sw_matrix_title": {"en": "Who leads where?", "tr": "Kim nerede önde?"},
    "sw_matrix_subtitle": {
        "en": "Complaints per 100 reviews relative to the other apps · blue = fewer, red = more "
              "· faded = no notable difference",
        "tr": "Diğer uygulamalara göre 100 yorum başına şikâyet · mavi = daha az, kırmızı = "
              "daha fazla · soluk = belirgin fark yok"},
    "sw_legend": {"en": "This app ÷ other apps", "tr": "Bu uygulama ÷ diğerleri"},
    "sw_na": {"en": "not measurable for this app", "tr": "bu uygulama için ölçülemiyor"},
    "sw_notable": {"en": "notable difference", "tr": "belirgin fark"},
    "sw_similar": {"en": "no notable difference", "tr": "belirgin fark yok"},
    "sw_this_app": {"en": "This app (per 100 reviews)", "tr": "Bu uygulama (100 yorumda)"},
    "sw_other_apps": {"en": "Other apps", "tr": "Diğer uygulamalar"},
    "sw_ratio": {"en": "Ratio", "tr": "Oran"},
    "sw_status": {"en": "Status", "tr": "Durum"},
    "sw_axis": {"en": "Complaints per 100 reviews", "tr": "100 yorum başına şikâyet"},
    "sw_fewer": {"en": "{pct}% fewer", "tr": "%{pct} daha az"},
    "sw_more": {"en": "{x}× more", "tr": "{x} kat daha fazla"},
    "sw_dumbbell_title": {"en": "{app} vs the other apps", "tr": "{app} ve diğer uygulamalar"},
    "sw_dumbbell_subtitle": {
        "en": "Complaints per 100 reviews with text, by category · labels mark notable "
              "differences",
        "tr": "Kategoriye göre, metinli 100 yorum başına şikâyet · etiketler belirgin "
              "farkları gösterir"},
    "sw_intro": {
        "en": "Each app is compared with the **other apps combined**. Complaint categories are "
              "measured as **complaints per 100 reviews** (how often users hit the problem), "
              "not as a share of complaints. A difference counts as *notable* only if it is "
              "statistically clear (p < 0.01) and large enough to matter: ≥1.5× and ≥1 "
              "complaint per 100 reviews for categories; ≥0.3★ for rating; ≥5 points for "
              "complaint rate; ≥15 points for reply rate; ≥2× for reply time.",
        "tr": "Her uygulama **diğer uygulamaların toplamıyla** karşılaştırılır. Şikâyet "
              "kategorileri şikâyetler içindeki pay olarak değil, **100 yorum başına şikâyet** "
              "olarak ölçülür (kullanıcıların bu sorunla ne sıklıkla karşılaştığı). Bir fark "
              "yalnızca istatistiksel olarak netse (p < 0,01) ve pratikte önemli olacak kadar "
              "büyükse *belirgin* sayılır: kategorilerde ≥1,5 kat ve 100 yorumda ≥1 şikâyet; "
              "puanda ≥0,3★; şikâyet oranında ≥5 puan; yanıt oranında ≥15 puan; yanıt "
              "süresinde ≥2 kat."},
    "sw_leads": {"en": "Leads", "tr": "Önde olduğu alanlar"},
    "sw_lags": {"en": "Lags", "tr": "Geride olduğu alanlar"},
    "sw_none_leads": {"en": "No notable lead over the other apps.",
                      "tr": "Diğer uygulamalara göre belirgin bir üstünlüğü yok."},
    "sw_none_lags": {"en": "No notable weakness against the other apps.",
                     "tr": "Diğer uygulamalara göre belirgin bir zayıflığı yok."},
    "sw_vs": {"en": "vs {others} for the other apps", "tr": "diğer uygulamalarda {others}"},
    "sw_m_avg_stars": {"en": "Average rating", "tr": "Ortalama puan"},
    "sw_m_complaint_rate": {"en": "Complaint rate", "tr": "Şikâyet oranı"},
    "sw_m_reply_rate": {"en": "Company replies to complaints",
                        "tr": "Şirketin şikâyetlere yanıtı"},
    "sw_m_reply_hours": {"en": "Median reply time", "tr": "Medyan yanıt süresi"},
    "sw_hours": {"en": "{h} h", "tr": "{h} sa"},
    "sw_minutes": {"en": "{m} min", "tr": "{m} dk"},
    "sw_per100": {"en": "{v} per 100 reviews", "tr": "100 yorumda {v}"},
    "sw_papara_note": {
        "en": "Papara is compared on 6 of 10 categories: the smaller Turkish topic model has no "
              "reliable topics for customer support, fees, disputes and fraud. Its sample "
              "outside event weeks is small (527 reviews with text), so only large gaps reach "
              "significance.",
        "tr": "Papara 10 kategorinin 6'sında karşılaştırılıyor: daha küçük Türkçe konu "
              "modelinde müşteri desteği, ücretler, itirazlar ve dolandırıcılık için güvenilir "
              "konu yok. Olay haftaları dışındaki örneklemi küçük (527 metinli yorum), bu "
              "yüzden yalnızca büyük farklar anlamlı çıkıyor."},
    "sw_reply_note": {
        "en": "Reply data come from the developer replies shown on Google Play; reply times "
              "are measured from the review's last edit, so edited reviews are left out.",
        "tr": "Yanıt verileri Google Play'de görünen geliştirici yanıtlarından geliyor; yanıt "
              "süresi yorumun son düzenlenme anından ölçüldüğü için düzenlenmiş yorumlar "
              "hesaba katılmadı."},
    # ---- dashboard: header and filters ----------------------------------- #
    "page_title": {"en": "Do digital wallet users complain about the same things?",
                   "tr": "Dijital cüzdan kullanıcıları aynı şeylerden mi şikâyet ediyor?"},
    "caption": {
        "en": "Google Play reviews of Cash App (USA), PayPal (global), Revolut (Europe) and "
              "Papara (Turkey) · last 12 months · sentiment: XLM-RoBERTa · topics: BERTopic "
              "mapped to shared categories",
        "tr": "Cash App (ABD), PayPal (global), Revolut (Avrupa) ve Papara (Türkiye) Google "
              "Play yorumları · son 12 ay · duygu: XLM-RoBERTa · konular: ortak kategorilere "
              "eşlenmiş BERTopic"},
    "no_data": {"en": "Processed data not found. Run the pipeline first (see README: "
                      "collect → clean → sentiment → topics).",
                "tr": "İşlenmiş veri bulunamadı. Önce veri hattını çalıştırın (README: "
                      "toplama → temizleme → duygu → konular)."},
    "apps": {"en": "Apps", "tr": "Uygulamalar"},
    "exclude_event": {"en": "Exclude Papara event weeks", "tr": "Papara olay haftalarını çıkar"},
    "exclude_event_help": {
        "en": "Removes Papara weeks inside the 2025 shock phases detected from the data, so "
              "the legal process does not distort the cross-market comparison.",
        "tr": "Veriden tespit edilen 2025 şok dönemlerindeki Papara haftalarını çıkarır; "
              "böylece hukuki süreç pazar karşılaştırmasını çarpıtmaz."},
    "hide_shutdown": {"en": "Hide shutdown/regulatory complaints",
                      "tr": "Kapanma/yasal süreç şikâyetlerini gizle"},
    "hide_shutdown_help": {"en": "This category only exists for Papara (legal process).",
                           "tr": "Bu kategori yalnızca Papara'da var (hukuki süreç)."},
    "table_view": {"en": "Table view", "tr": "Tablo görünümü"},
    # ---- dashboard: tabs ------------------------------------------------- #
    "tab_overview": {"en": "Overview", "tr": "Genel bakış"},
    "tab_complaints": {"en": "Complaint themes", "tr": "Şikâyet konuları"},
    "tab_trend": {"en": "Sentiment trend", "tr": "Duygu trendi"},
    "tab_versions": {"en": "Version impact", "tr": "Sürüm etkisi"},
    "tab_papara": {"en": "Papara event", "tr": "Papara olayı"},
    "tab_reviews": {"en": "Review explorer", "tr": "Yorum gezgini"},
    # ---- dashboard: overview --------------------------------------------- #
    "average_rating": {"en": "Average rating", "tr": "Ortalama puan"},
    "complaint_rate_help": {"en": "Share of reviews with 3+ words classified as complaints",
                            "tr": "En az 3 kelimelik yorumlar içinde şikâyetlerin payı"},
    "text_sentiment": {"en": "Text sentiment", "tr": "Metin duygusu"},
    "text_sentiment_help": {"en": "Average XLM-R polarity, −1 (negative) to +1 (positive)",
                            "tr": "Ortalama XLM-R polaritesi, −1 (olumsuz) ile +1 (olumlu) arası"},
    "n_reviews": {"en": "{n} reviews", "tr": "{n} yorum"},
    "key_findings": {"en": "Key findings", "tr": "Ana bulgular"},
    "findings": {
        "en": "- **Same core problems everywhere.** App bugs, account restriction / KYC and "
              "transfers are in the top four in every market (49–60% of complaints).\n"
              "- **Market-specific layer:** Cash App → fraud & scams (14%); PayPal & Revolut → "
              "login and sign-up (13–15%); Papara → card delivery and KYC.\n"
              "- **PayPal v10** is rated 1.1★ lower than v8 over the same dates; app-bug "
              "complaints nearly double.\n"
              "- **Papara**: two shocks in 2025, a long dormant period and a relaunch in "
              "Sep 2026 that has not yet restored pre-event ratings.",
        "tr": "- **Her yerde aynı temel sorunlar.** Uygulama hataları, hesap kısıtlama / KYC "
              "ve transferler her pazarda ilk dört içinde (şikâyetlerin %49–60'ı).\n"
              "- **Pazara özgü katman:** Cash App → dolandırıcılık (%14); PayPal ve Revolut → "
              "giriş ve kayıt (%13–15); Papara → kart teslimatı ve KYC.\n"
              "- **PayPal v10**, aynı tarihlerde v8'den 1,1★ daha düşük puan alıyor; uygulama "
              "hatası şikâyetleri neredeyse iki katına çıkıyor.\n"
              "- **Papara**: 2025'te iki şok, uzun bir durgunluk ve Eylül 2026'da puanları "
              "henüz olay öncesi seviyeye döndürmeyen bir yeniden açılış."},
    # ---- dashboard: complaints ------------------------------------------- #
    "complaints_note": {
        "en": "Each complaint is counted once, under its **main** problem. Cross-cutting "
              "issues such as customer support and fees are therefore under-counted.",
        "tr": "Her şikâyet bir kez, **ana** sorunu altında sayılır. Bu yüzden müşteri desteği "
              "ve ücretler gibi diğer sorunlarla birlikte geçen konular olduğundan az görünür."},
    # ---- dashboard: trend ------------------------------------------------ #
    "granularity": {"en": "Granularity", "tr": "Zaman aralığı"},
    "freq_month": {"en": "Month", "tr": "Ay"},
    "freq_week": {"en": "Week", "tr": "Hafta"},
    "papara_noise": {
        "en": "Papara has ~10–40 reviews a month after the event, so its line is noisy; "
              "Nov–Dec 2025 fall inside the second shock.",
        "tr": "Papara olaydan sonra ayda ~10–40 yorum alıyor, bu yüzden çizgisi dalgalı; "
              "Kasım–Aralık 2025 ikinci şokun içinde."},
    # ---- dashboard: versions --------------------------------------------- #
    "versions_note": {
        "en": "Versions with at least 200 reviews. Red = drop of ≥0.3★ versus the previous "
              "version with Welch p < 0.01. Papara is excluded (too few reviews per version).",
        "tr": "En az 200 yorumu olan sürümler. Kırmızı = önceki sürüme göre ≥0,3★ düşüş "
              "(Welch p < 0,01). Papara dahil değil (sürüm başına yorum çok az)."},
    "all_versions": {"en": "All versions", "tr": "Tüm sürümler"},
    "paypal_compare": {"en": "PayPal v8 vs v10 over the same dates",
                       "tr": "Aynı tarihlerde PayPal v8 ve v10"},
    "v8_rating": {"en": "v8 rating", "tr": "v8 puanı"},
    "v10_rating": {"en": "v10 rating", "tr": "v10 puanı"},
    "welch": {"en": "Welch t-test", "tr": "Welch t-testi"},
    # ---- dashboard: Papara ----------------------------------------------- #
    "papara_note": {
        "en": "Event phases are **detected from the data**: a shock week has ≥1.75× the "
              "previous 8-week median volume and a ≥20-point rise in the complaint or "
              "shutdown share; a relaunch week has ≥2.5× the previous volume and a rating "
              "≥0.75★ higher. These weeks are kept out of the cross-market comparison.",
        "tr": "Olay dönemleri **veriden tespit edilir**: şok haftasında hacim önceki 8 "
              "haftanın medyanının ≥1,75 katıdır ve şikâyet ya da kapanma payı ≥20 puan "
              "artar; yeniden açılış haftasında hacim önceki dönemin ≥2,5 katı, puan ise "
              "≥0,75★ yüksektir. Bu haftalar pazar karşılaştırmasının dışında tutulur."},
    "baseline_note": {
        "en": "The shutdown/regulatory category is already 16% before the event (generic "
              "distrust complaints); read the event effect as the rise above that baseline.",
        "tr": "Kapanma/yasal süreç kategorisi olaydan önce de %16 (genel güvensizlik "
              "şikâyetleri); olay etkisini bu tabanın üzerindeki artış olarak okuyun."},
    # ---- dashboard: review explorer -------------------------------------- #
    "explorer_note": {
        "en": "Example complaints behind the numbers. Texts are read from your local "
              "`data/processed/` and are not part of the repository.",
        "tr": "Sayıların arkasındaki örnek şikâyetler. Metinler yerel `data/processed/` "
              "klasöründen okunur, repoda yer almaz."},
    "all": {"en": "All", "tr": "Tümü"},
    "rating": {"en": "Rating", "tr": "Puan"},
    "contains": {"en": "Contains", "tr": "İçerir"},
    "contains_placeholder": {"en": "e.g. refund, card", "tr": "ör. iade, kart"},
    "shuffle": {"en": "Show different examples", "tr": "Başka örnekler göster"},
    "matching": {"en": "{n} matching complaints", "tr": "{n} eşleşen şikâyet"},
}


# Column headers of the tables shown in the dashboard.
COLUMN_TR = {
    "app_name": "uygulama", "reviews": "yorum", "avg_stars": "ort_puan",
    "clean_reviews": "metinli_yorum", "avg_polarity": "ort_duygu", "complaints": "şikâyet",
    "complaint_rate": "şikâyet_oranı", "category_label": "kategori", "total": "toplam",
    "share": "pay", "ci_low": "ga_alt", "ci_high": "ga_üst", "period": "dönem",
    "neg_share": "olumsuz_payı", "version": "sürüm", "first_seen": "ilk_görülme",
    "ci": "ga_yarıçap", "delta": "değişim", "p_value": "p_değeri",
    "biggest_rise": "en_çok_artan", "rise_pp": "artış_puan", "phase": "dönem",
    "start": "başlangıç", "end": "bitiş", "reviews_per_week": "haftalık_yorum",
    "shutdown_share": "kapanma_payı", "five_star_complaints": "5_yıldızlı_şikâyet",
    "date": "tarih", "rating": "puan", "category": "kategori", "text": "metin",
    "key": "ölçüt", "value": "değer", "others": "diğerleri", "ratio": "oran",
    "better": "daha_iyi", "notable": "belirgin", "unit": "birim",
}


def localize_columns(df, lang: str = "en"):
    return df.rename(columns=COLUMN_TR) if lang == "tr" else df


def t(key: str, lang: str = "en", **kwargs) -> str:
    text = STRINGS[key].get(lang) or STRINGS[key]["en"]
    return text.format(**kwargs) if kwargs else text


def category_label(key: str, lang: str = "en") -> str:
    return CATEGORY_TR[key] if lang == "tr" else CATEGORIES[key]["label"]


_KEY_BY_EN_LABEL = {v["label"]: k for k, v in CATEGORIES.items()}


def translate_label(en_label: str, lang: str = "en") -> str:
    """Translate an English category label (as produced by src.analysis)."""
    if lang == "en" or en_label not in _KEY_BY_EN_LABEL:
        return en_label
    return CATEGORY_TR[_KEY_BY_EN_LABEL[en_label]]


def phase_name(name: str, lang: str = "en") -> str:
    return PHASE_TR.get(name, name) if lang == "tr" else name


def fmt_num(x: float, decimals: int = 2, lang: str = "en", signed: bool = False) -> str:
    """Number with the decimal separator of the language (12.5 -> 12,5 in Turkish)."""
    s = f"{x:+.{decimals}f}" if signed else f"{x:.{decimals}f}"
    return s.replace(".", ",") if lang == "tr" else s


def fmt_int(n: int, lang: str = "en") -> str:
    s = f"{n:,}"
    return s.replace(",", ".") if lang == "tr" else s


def fmt_pct(x: float, lang: str = "en") -> str:
    return f"%{x * 100:.0f}" if lang == "tr" else f"{x:.0%}"
