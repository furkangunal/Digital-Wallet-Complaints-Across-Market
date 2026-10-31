"""Language-independent complaint categories.

BERTopic clusters are found separately per language; each cluster is then
mapped to one of these shared categories so that markets can be compared
side by side. The descriptions are embedded with the same multilingual model
as the reviews and used to *propose* a category for every topic; the final
mapping is reviewed by hand (``config/topic_mapping_<lang>.csv``).
"""

CATEGORIES: dict[str, dict[str, str]] = {
    "customer_support": {
        "label": "Customer support",
        "description": "Customer service is unreachable or unhelpful: no human agent, "
                       "only bots, slow or no reply, generic answers, issue never resolved. "
                       "Müşteri hizmetlerine ulaşılamıyor, canlı destek yok, cevap vermiyorlar.",
    },
    "account_restriction": {
        "label": "Account restriction / KYC",
        "description": "Account closed, frozen, suspended, limited or locked without explanation; "
                       "identity verification (KYC), ID or document checks failing, funds held "
                       "because the account is restricted. Hesabım kapatıldı, kısıtlandı, "
                       "dondu, kimlik doğrulama, onaylanmıyor.",
    },
    "fees": {
        "label": "Fees & pricing",
        "description": "Fees and charges are too high or unexpected: instant transfer fee, "
                       "withdrawal fee, exchange rate, subscription or plan price, interest. "
                       "Ücretler, komisyon, işlem ücreti, kesinti çok yüksek.",
    },
    "transfers": {
        "label": "Transfers & payments",
        "description": "Money transfers or payments fail, are delayed, pending or never arrive; "
                       "deposits, direct deposit, withdrawals to bank, payment declined at checkout. "
                       "Para transferi, havale, para yatırma veya çekme gerçekleşmiyor, gecikiyor.",
    },
    "fraud_security": {
        "label": "Fraud, security & privacy",
        "description": "Scams, fraud, hacked account, unauthorized transactions, stolen money, "
                       "phishing, and poor protection of victims. Dolandırıldım, hesabım "
                       "çalındı, izinsiz işlem.",
    },
    "disputes_refunds": {
        "label": "Disputes & refunds",
        "description": "Refunds, chargebacks, buyer or seller protection, disputes and claims "
                       "decided unfairly or never processed. İade, itiraz, para iadesi yapılmadı.",
    },
    "login_access": {
        "label": "Login & sign-up",
        "description": "Cannot log in or sign in, password reset, two-factor or SMS verification "
                       "code not received, locked out after changing phone or device. "
                       "Giriş yapamıyorum, SMS kodu gelmiyor, şifre.",
    },
    "app_bugs": {
        "label": "App bugs & usability",
        "description": "The app crashes, freezes, is slow, buggy, has glitches after an update, "
                       "screens do not load, bad design or user interface. Uygulama çöküyor, "
                       "donuyor, açılmıyor, güncelleme sonrası hata.",
    },
    "card": {
        "label": "Card issues",
        "description": "Debit or prepaid card problems: card declined, card not delivered, "
                       "card ordering, replacement card, ATM withdrawals. Kart gelmedi, "
                       "kart çalışmıyor, kart siparişi.",
    },
    "features": {
        "label": "Product features & limits",
        "description": "Requests for missing features, transaction or balance limits too low, "
                       "age restrictions, unsupported countries or banks, wanting new options. "
                       "Limitler düşük, yaş sınırı, özellik eklensin.",
    },
    "service_disruption": {
        "label": "Service shutdown / regulatory",
        "description": "The whole service is shut down, suspended or taken over by authorities, "
                       "legal or regulatory action, users asking the company to come back, "
                       "fear about their money due to the company's legal situation. "
                       "Kayyum, el konuldu, Papara kapandı, geri dön, yasal süreç.",
    },
    "other": {
        "label": "Other / unclassified",
        "description": "Generic negative statements without a specific issue.",
    },
}
