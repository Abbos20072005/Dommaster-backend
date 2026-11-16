"""The store terms the assistant may quote (the `get_policy` tool): delivery, payment, returns, contacts.

The only source is the approved text of the site pages (BLD-103, Linear documents of 15.10.2026, live on
buildex.uz since 19.10): `/courier-delivery`, `/payment-methods`, `/returns`, `/contacts`. The site keeps its own copy
(frontend `content/trust/`), so **a change of a page must be repeated here** — nothing syncs them. Write only what
the page says: an unconfirmed term (delivery zone outside Tashkent, a fixed delivery price, a free delivery
threshold, "2 hours", pay on delivery) is left out on purpose (D25), the model then says it is not specified.
"""
from apps.service.merchant_feed import SITE_URL

PHONE = "+998 77 240 09 09"
EMAIL = "buildexuz@gmail.com"

CONTACT = {
    "uz": f"Telefon {PHONE}, har kuni 07:00–22:00; elektron pochta {EMAIL}.",
    "ru": f"Телефон {PHONE}, ежедневно 07:00–22:00; электронная почта {EMAIL}.",
}

POLICIES = {
    "delivery": {
        "path": "/courier-delivery",
        "uz": {
            "title": "Yetkazib berish",
            "summary": "Buyurtmani Toshkent bo'ylab yetkazib beramiz. Yetkazish narxi va taxminiy muddati manzilingiz "
                       "va buyurtma tarkibiga qarab hisoblanadi va to'lovdan oldin buyurtmani rasmiylashtirish "
                       "sahifasida ko'rsatiladi.",
            "terms": [
                "Hudud: Toshkent shahri. Manzilingizga yetkazish mumkinligi buyurtmani rasmiylashtirishda "
                "ko'rsatiladi.",
                "Narx: manzil va buyurtma bo'yicha hisoblanadi, buyurtmani tasdiqlashdan oldin jami summada alohida "
                "qator bo'lib ko'rinadi.",
                "Muddat: taxminiy muddat buyurtmani rasmiylashtirishda ko'rsatiladi.",
                "Og'ir va yirik yuk: qavatga ko'tarish, tushirish va kirish sharoiti oldindan kelishiladi; qo'shimcha "
                "haq bo'lsa, oldindan aytiladi. Oddiy yetkazish narxi ularni avtomatik qamrab olmaydi.",
                "Kechikish: muddat buzilishi xavfi bo'lsa, xabar beramiz va boshqa muddatni yoki buyurtmani bekor "
                "qilishni taklif qilamiz.",
                "Qabul qilish: tovarni olayotganda miqdori, ko'rinishi va butligini tekshiring; farq bo'lsa, darhol "
                "xabar bering.",
            ],
            "faq": [
                {"q": "Yetkazish narxini qachon bilaman?",
                 "a": "Manzilni kiritganingizdan keyin, to'lovdan oldin. Narx buyurtmaning jami summasida alohida "
                      "ko'rsatiladi."},
                {"q": "Yetkazish narxiga qavatga ko'tarish kiradimi?",
                 "a": "Avtomatik kirmaydi. Og'ir yoki yirik yuk uchun ko'tarish va tushirish oldindan kelishiladi, "
                      "qo'shimcha haq bo'lsa oldindan aytiladi."},
                {"q": "Yetkazib berib bo'lmasa, pul nima bo'ladi?",
                 "a": "Bajarilmagan qism uchun to'langan pul qaytariladi (tartibi «Qaytarish» sahifasida)."},
            ],
        },
        "ru": {
            "title": "Доставка",
            "summary": "Доставляем заказы по Ташкенту. Стоимость и ориентировочный срок доставки рассчитываются по "
                       "вашему адресу и составу заказа и показываются на странице оформления до оплаты.",
            "terms": [
                "Зона: город Ташкент. Возможность доставки по вашему адресу показывается при оформлении заказа.",
                "Стоимость: рассчитывается по адресу и заказу, отдельной строкой в итоговой сумме до подтверждения "
                "заказа.",
                "Срок: ориентировочный срок показывается при оформлении заказа.",
                "Тяжёлые и крупные грузы: подъём на этаж, разгрузка и условия заезда согласуются заранее; если есть "
                "доплата, о ней сообщается заранее. Обычная стоимость доставки их автоматически не включает.",
                "Задержка: если срок под угрозой, мы сообщим и предложим другой срок или отмену заказа.",
                "Приёмка: при получении проверьте количество, внешний вид и комплектность; о расхождениях сообщите "
                "сразу.",
            ],
            "faq": [
                {"q": "Когда я узнаю стоимость доставки?",
                 "a": "После ввода адреса, до оплаты. Стоимость показывается отдельной строкой в итоговой сумме "
                      "заказа."},
                {"q": "Входит ли подъём на этаж в стоимость доставки?",
                 "a": "Автоматически нет. Подъём и разгрузка тяжёлого или крупного груза согласуются заранее; если "
                      "есть доплата, о ней сообщается заранее."},
                {"q": "Что с деньгами, если доставка невозможна?",
                 "a": "Деньги за невыполненную часть заказа возвращаются (порядок — на странице «Возврат»)."},
            ],
        },
    },
    "payment": {
        "path": "/payment-methods",
        "uz": {
            "title": "To'lov usullari",
            "summary": "Buyurtmani karta bilan onlayn to'lashingiz mumkin: Atmos, Click, Payme yoki Uzum. Yuridik "
                       "shaxslar bank o'tkazmasi orqali to'laydi. Jami summa so'mda va buyurtmani tasdiqlashdan "
                       "oldin ko'rsatiladi.",
            "terms": [
                "Karta bilan onlayn (hamma xaridorlar): buyurtmani rasmiylashtirishda to'lov tizimini tanlaysiz — "
                "Atmos, Click, Payme yoki Uzum; to'lov shu tizim oynasida o'tadi.",
                "Bank o'tkazmasi (yuridik shaxslar): tashkilot rekvizitlari buyurtmada ko'rsatiladi, to'lov "
                "«ENERGOSNAB» MChJ hisob raqamiga o'tkaziladi (rekvizitlar to'lov usullari sahifasida).",
                "Har bir buyurtma uchun qaysi usullar mavjudligi rasmiylashtirish sahifasida ko'rsatiladi.",
                "Tasdiqlangan buyurtma narxi sizning roziligingizsiz oshirilmaydi.",
                "To'lov to'lov tizimidan tasdiq kelganda o'tgan hisoblanadi. Pul ikki marta yechilgan bo'lsa, bizga "
                "murojaat qiling — tekshirib, ortiqchasini qaytaramiz.",
                "Buyurtma bekor qilinsa yoki yetkazib bo'lmasa, bajarilmagan qism uchun pul qaytariladi, odatda "
                "to'langan usul bilan.",
                "Karta ma'lumotlari va bank kodlari faqat to'lov tizimi oynasida kiritiladi. Buildex xodimlari SMS "
                "kod so'ramaydi — kodni hech kimga bermang.",
            ],
            "faq": [
                {"q": "To'lov o'tdimi, qanday bilaman?",
                 "a": "To'lov tizimidan tasdiq kelgach buyurtma holati yangilanadi va sizga xabar yuboriladi."},
                {"q": "Pul yechildi, lekin buyurtma ko'rinmayapti.",
                 "a": f"Buyurtma raqami yoki to'lov vaqti bilan bizga murojaat qiling: {PHONE}."},
            ],
        },
        "ru": {
            "title": "Способы оплаты",
            "summary": "Заказ можно оплатить картой онлайн: Atmos, Click, Payme или Uzum. Юридические лица "
                       "оплачивают банковским переводом. Итоговая сумма в сумах показывается до подтверждения "
                       "заказа.",
            "terms": [
                "Картой онлайн (все покупатели): при оформлении выберите платёжную систему — Atmos, Click, Payme или "
                "Uzum; оплата проходит в окне этой системы.",
                "Банковский перевод (юридические лица): реквизиты организации указываются в заказе, оплата "
                "переводится на расчётный счёт ООО «ENERGOSNAB» (реквизиты на странице способов оплаты).",
                "Доступные способы для конкретного заказа показываются на странице оформления.",
                "Цена подтверждённого заказа не повышается без вашего согласия.",
                "Оплата считается прошедшей после подтверждения от платёжной системы. Если деньги списаны дважды, "
                "напишите нам — проверим и вернём лишнее.",
                "Если заказ отменён или доставка невозможна, деньги за невыполненную часть возвращаются, как "
                "правило, тем же способом.",
                "Данные карты и банковские коды вводятся только в окне платёжной системы. Сотрудники Buildex не "
                "запрашивают SMS-код — никому его не сообщайте.",
            ],
            "faq": [
                {"q": "Как понять, что оплата прошла?",
                 "a": "После подтверждения от платёжной системы статус заказа обновится и вы получите уведомление."},
                {"q": "Деньги списаны, а заказа не видно.",
                 "a": f"Напишите нам с номером заказа или временем оплаты: {PHONE}."},
            ],
        },
    },
    "returns": {
        "path": "/returns",
        "uz": {
            "title": "Qaytarish va almashtirish",
            "summary": "Sifatli tovarni xarid kunidan 10 kun ichida almashtirish mumkin; bunday tovar sotuvda "
                       "bo'lmasa, pul qaytariladi. Nuqsonli, noto'g'ri yoki to'liq bo'lmagan tovar bo'yicha talablar "
                       "qonunga muvofiq ko'rib chiqiladi. Murojaatni 3 ish kunida ko'rib chiqamiz, qaror qabul "
                       "qilingach pulni 10 kalendar kun ichida qaytaramiz.",
            "terms": [
                "Sifatli tovar to'g'ri kelmadi: xarid kunidan 10 kun ichida ayni shunday tovarga almashtirish, u "
                "sotuvda bo'lmasa — pulni qaytarish. Qonundagi shartlar va hukumat belgilagan almashtirilmaydigan "
                "tovarlar ro'yxati amal qiladi.",
                "Tovar nuqsonli, noto'g'ri yoki to'liq emas: almashtirish, nuqsonni bartaraf etish, narxni "
                "kamaytirish yoki xaridni bekor qilish — qonun va kafolat muddati bo'yicha.",
                "Buyurtmani o'zgartirish yoki bekor qilish: buyurtma qaysi bosqichda ekaniga qarab ko'rib chiqiladi.",
                f"Qanday qaytariladi: 1) telefon {PHONE} yoki {EMAIL} orqali buyurtma raqami va sababini aytib "
                "murojaat qiling; 2) murojaat 3 ish kunida ko'rib chiqiladi; 3) tovarni Toshkent, Chilonzor tumani, "
                "Arnasoy ko'chasi, 10A ga yoki buyurtmadagi Buildex olib ketish nuqtasiga topshirasiz, yirik tovarni "
                "olib ketishni siz bilan kelishamiz; 4) pul qaror qabul qilingach 10 kalendar kun ichida qaytariladi "
                "(bank yoki to'lov tizimi orqali o'tish vaqti bunga kirmaydi).",
                "Pul odatda siz to'lagan usul bilan qaytariladi; pul o'tkazish xarajatini Buildex to'laydi.",
                "Kafolat: muddati va tartibi tovar hujjatida yoki tovar sahifasida ko'rsatiladi. Chek yo'qolgan "
                "bo'lsa ham, xaridni boshqa dalil bilan tasdiqlay olsangiz, talab faqat shu sababli rad etilmaydi.",
            ],
            "faq": [
                {"q": "Qaysi tovarlarni qaytarib bo'lmaydi?",
                 "a": "Hukumat belgilagan almashtirilmaydigan tovarlar ro'yxatidagilar. Nuqsonli tovarga bu cheklov "
                      "tegishli emas."},
                {"q": "Tovar katta va og'ir. O'zim olib kelishim kerakmi?",
                 "a": "Yo'q. Yirik tovarni olib ketishni siz bilan kelishamiz."},
                {"q": "Buyurtmani hali olmadim. Bekor qilsam bo'ladimi?",
                 "a": "Ha, buyurtma raqami bilan murojaat qiling. Bekor qilish buyurtma qaysi bosqichda ekaniga "
                      "qarab ko'rib chiqiladi."},
            ],
        },
        "ru": {
            "title": "Возврат и обмен",
            "summary": "Товар надлежащего качества можно обменять в течение 10 дней со дня покупки; если такого "
                       "товара нет в продаже, деньги возвращаются. Требования по товару с недостатками, "
                       "неправильному или некомплектному товару рассматриваются по закону. Обращение рассматриваем "
                       "за 3 рабочих дня, после решения возвращаем деньги в течение 10 календарных дней.",
            "terms": [
                "Товар надлежащего качества не подошёл: в течение 10 дней со дня покупки обмен на такой же товар, "
                "если его нет в продаже — возврат денег. Действуют условия закона и утверждённый правительством "
                "перечень товаров, не подлежащих обмену.",
                "Товар с недостатком, неправильный или некомплектный: замена, устранение недостатка, снижение цены "
                "или расторжение покупки — по закону и гарантийному сроку.",
                "Изменение или отмена заказа: рассматривается с учётом этапа выполнения заказа.",
                f"Как вернуть: 1) обратитесь по телефону {PHONE} или {EMAIL}, укажите номер заказа и причину; "
                "2) обращение рассматривается за 3 рабочих дня; 3) передайте товар по адресу Ташкент, Чиланзарский "
                "район, ул. Арнасой, 10А или в пункт выдачи Buildex, указанный в заказе, вывоз крупного товара "
                "согласуем с вами; 4) деньги возвращаются в течение 10 календарных дней после решения (время "
                "прохождения платежа через банк или платёжную систему в этот срок не входит).",
                "Деньги возвращаются, как правило, тем же способом, которым вы платили; расходы на перевод несёт "
                "Buildex.",
                "Гарантия: срок и порядок указаны в документах на товар или на странице товара. Если чек утерян, но "
                "покупку можно подтвердить иначе, требование не отклоняется только по этой причине.",
            ],
            "faq": [
                {"q": "Какие товары нельзя вернуть?",
                 "a": "Товары из утверждённого правительством перечня товаров, не подлежащих обмену. На товар с "
                      "недостатками это ограничение не распространяется."},
                {"q": "Товар большой и тяжёлый. Нужно привезти самому?",
                 "a": "Нет. Вывоз крупного товара согласуем с вами."},
                {"q": "Заказ ещё не получен. Можно отменить?",
                 "a": "Да, обратитесь с номером заказа. Отмена рассматривается с учётом этапа выполнения заказа."},
            ],
        },
    },
    "contacts": {
        "path": "/contacts",
        "uz": {
            "title": "Kontaktlar",
            "summary": f"Telefon {PHONE}, har kuni 07:00–22:00. Elektron pochta {EMAIL}. Manzil: Toshkent shahri, "
                       "Chilonzor tumani, Arnasoy ko'chasi, 10A. Buyurtma bo'yicha murojaat qilsangiz, buyurtma "
                       "raqamini ayting.",
            "terms": ["Sotuvchi: «ENERGOSNAB» MChJ (Buildex brendi), STIR 308542198."],
            "faq": [],
        },
        "ru": {
            "title": "Контакты",
            "summary": f"Телефон {PHONE}, ежедневно 07:00–22:00. Электронная почта {EMAIL}. Адрес: г. Ташкент, "
                       "Чиланзарский район, ул. Арнасой, 10А. Если обращаетесь по заказу, назовите номер заказа.",
            "terms": ["Продавец: ООО «ENERGOSNAB» (бренд Buildex), ИНН 308542198."],
            "faq": [],
        },
    },
}

TOPICS = tuple(POLICIES)


def _language(language):
    return language if language in ("uz", "ru") else "ru"


def source(topic, language):
    """{topic, title, url} of the page an answer took the terms from (the client shows it under the answer)."""
    policy = POLICIES[topic]
    return {"topic": topic, "title": policy[_language(language)]["title"], "url": SITE_URL + policy["path"]}


def policy(topic, language):
    """The terms of `topic` for the model: the page's summary, terms, FAQ, the contacts and the page url."""
    text = POLICIES[topic][_language(language)]
    return {**source(topic, language), "summary": text["summary"], "terms": text["terms"], "faq": text["faq"],
            "contact": CONTACT[_language(language)]}
