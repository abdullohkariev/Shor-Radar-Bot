"""Bot interface strings (en / uz Latin / ru).
!! Uzbek and Russian are first drafts: have native speakers proofread before the demo."""

UI = {
 "welcome": {
  "en": "🌱 Sho'r Radar\nHelps farmers in Uzbekistan decide when to irrigate, when salt flushing may be suitable, and which crops fit salty soil.\n\nChoose your language:",
  "uz": "🌱 Sho'r Radar\nO'zbekistondagi fermerlarga qachon sug'orish, qachon tuzni yuvish mumkinligi va sho'r yerga qaysi ekinlar mosligini aniqlashda yordam beradi.\n\nTilni tanlang:",
  "ru": "🌱 Sho'r Radar\nПомогает фермерам Узбекистана решать, когда поливать, когда возможна промывка от солей и какие культуры подходят для засолённых почв.\n\nВыберите язык:"},
 "about": {
  "en": ("ℹ️ What Sho'r Radar does\n"
         "• 💧 Irrigation signal: IRRIGATE / MONITOR / WAIT, with the reason\n"
         "• 🧂 Salt-risk indicator and carefully qualified flushing timing\n"
         "• 🌾 Salt-aware crop and rotation ideas\n"
         "• 🗓 Season outlook based on past data\n"
         "• 👥 Community: share tips with other farmers\n\n"
         "How it works\n"
         "1) You register your field (location, crop, soil info).\n"
         "2) We take NASA POWER satellite-based weather and soil-wetness data for your location, plus a 7-day forecast from Open-Meteo.\n"
         "3) Simple, transparent rules turn it into advice and explain why.\n"
         "4) You get a morning notification when action may be needed.\n\n"
         "⚠️ Limits: NASA data is a ~50 km grid, and satellites do NOT measure salt in your soil. This is decision support, not a measurement. Rules are not yet agronomist-validated. Confirm locally (soil EC test, agronomist)."),
  "uz": ("ℹ️ Sho'r Radar nima qiladi\n"
         "• 💧 Sug'orish signali: SUG'ORING / KUZATING / KUTING, sababi bilan\n"
         "• 🧂 Sho'rlanish xavfi ko'rsatkichi va yuvish vaqti bo'yicha ehtiyotkor maslahat\n"
         "• 🌾 Sho'rga mos ekin va almashlab ekish g'oyalari\n"
         "• 🗓 O'tgan ma'lumotlarga asoslangan mavsum rejasi\n"
         "• 👥 Hamjamiyat: boshqa fermerlar bilan maslahat almashing\n\n"
         "Qanday ishlaydi\n"
         "1) Dalangizni kiritasiz (joylashuv, ekin, tuproq ma'lumoti).\n"
         "2) Biz joyingiz uchun NASA POWER sun'iy yo'ldosh asosidagi ob-havo va tuproq namligi ma'lumotini va Open-Meteo'dan 7 kunlik prognozni olamiz.\n"
         "3) Oddiy va shaffof qoidalar maslahat beradi va sababini tushuntiradi.\n"
         "4) Chora kerak bo'lsa, ertalab xabar olasiz.\n\n"
         "⚠️ Cheklovlar: NASA ma'lumoti ~50 km katak, yo'ldoshlar tuproqdagi tuzni O'LCHAMAYDI. Bu qaror qabul qilishga yordam, o'lchov emas. Qoidalar hali agronom tomonidan tasdiqlanmagan. Joyida tekshiring (tuproq EC tahlili, agronom)."),
  "ru": ("ℹ️ Что делает Sho'r Radar\n"
         "• 💧 Сигнал полива: ПОЛИВАТЬ / НАБЛЮДАТЬ / ЖДАТЬ с причиной\n"
         "• 🧂 Индикатор риска засоления и осторожные подсказки по срокам промывки\n"
         "• 🌾 Идеи по культурам и севообороту для засолённых почв\n"
         "• 🗓 План сезона по прошлым данным\n"
         "• 👥 Сообщество: делитесь советами с другими фермерами\n\n"
         "Как это работает\n"
         "1) Вы добавляете поле (место, культура, данные о почве).\n"
         "2) Мы берём спутниковые данные NASA POWER о погоде и влажности почвы для вашего места и 7-дневный прогноз Open-Meteo.\n"
         "3) Простые прозрачные правила превращают их в совет и объясняют причину.\n"
         "4) Утром вы получаете уведомление, если нужны действия.\n\n"
         "⚠️ Ограничения: данные NASA — сетка ~50 км, спутники НЕ измеряют соль в вашей почве. Это помощь в принятии решений, а не измерение. Правила пока не проверены агрономом. Уточняйте на месте (анализ EC почвы, агроном).")},
 "btn_register": {"en": "✅ Register", "uz": "✅ Ro'yxatdan o'tish", "ru": "✅ Регистрация"},
 "ask_name": {"en": "What is your name? (shown to other farmers in the community)",
              "uz": "Ismingiz nima? (hamjamiyatda boshqa fermerlarga ko'rinadi)",
              "ru": "Как вас зовут? (будет видно другим фермерам в сообществе)"},
 "name_bad": {"en": "Please send a name of 2-40 characters.", "uz": "Iltimos, 2-40 belgidan iborat ism yuboring.",
              "ru": "Отправьте имя длиной 2-40 символов."},
 "ask_region": {"en": "Choose your area (or share your location):", "uz": "Hududingizni tanlang (yoki joylashuvni yuboring):",
                "ru": "Выберите ваш район (или отправьте геопозицию):"},
 "loc_btn": {"en": "📍 Share location", "uz": "📍 Joylashuvni yuborish", "ru": "📍 Отправить геопозицию"},
 "reg_done": {"en": "Welcome, {name}! 🎉 Now add your first field.", "uz": "Xush kelibsiz, {name}! 🎉 Endi birinchi dalangizni qo'shing.",
              "ru": "Добро пожаловать, {name}! 🎉 Теперь добавьте первое поле."},
 "need_reg": {"en": "Please register first: /start", "uz": "Avval ro'yxatdan o'ting: /start", "ru": "Сначала зарегистрируйтесь: /start"},

 "m_status": {"en": "📊 Status", "uz": "📊 Holat", "ru": "📊 Статус"},
 "m_fields": {"en": "🌾 My fields", "uz": "🌾 Dalalarim", "ru": "🌾 Мои поля"},
 "m_add":    {"en": "➕ Add field", "uz": "➕ Dala qo'shish", "ru": "➕ Добавить поле"},
 "m_plan":   {"en": "🗓 Plan", "uz": "🗓 Reja", "ru": "🗓 План"},
 "m_comm":   {"en": "👥 Community", "uz": "👥 Hamjamiyat", "ru": "👥 Сообщество"},
 "m_set":    {"en": "⚙️ Settings", "uz": "⚙️ Sozlamalar", "ru": "⚙️ Настройки"},
 "m_about":  {"en": "ℹ️ About", "uz": "ℹ️ Haqida", "ru": "ℹ️ О боте"},
 "m_app": {"en": "👉 Open Sho'r Radar", "uz": "👉 Sho'r Radarni ochish", "ru": "👉 Открыть Sho'r Radar"},
 "open_app_msg": {"en": "Open the Sho'r Radar app 👇", "uz": "Sho'r Radar ilovasini oching 👇", "ru": "Откройте приложение Sho'r Radar 👇"},
 "app_welcome": {
  "en": "🌱 Sho'r Radar\nTells you every day if your field needs water.\n\n1️⃣ Tap the button below\n2️⃣ Add your field (1 minute)\n3️⃣ See what to do today\n\nWe will also message you here in the morning when something needs action.",
  "uz": "🌱 Sho'r Radar\nDalangizni sug'orish kerakmi, har kuni aytib turadi.\n\n1️⃣ Pastdagi tugmani bosing\n2️⃣ Dalangizni qo'shing (1 daqiqa)\n3️⃣ Bugun nima qilishni ko'ring\n\nChora kerak bo'lsa, ertalab shu yerga xabar yozamiz.",
  "ru": "🌱 Sho'r Radar\nКаждый день подсказывает, нужен ли вашему полю полив.\n\n1️⃣ Нажмите кнопку ниже\n2️⃣ Добавьте поле (1 минута)\n3️⃣ Узнайте, что делать сегодня\n\nКогда нужны действия, мы напишем вам здесь утром."},
 "menu_hint": {"en": "Choose an option 👇", "uz": "Bo'limni tanlang 👇", "ru": "Выберите раздел 👇"},

 "ask_fname": {"en": "Give this field a name (e.g. “North field”):", "uz": "Dalaga nom bering (masalan, “Shimoliy dala”):",
               "ru": "Дайте полю название (например, «Северное поле»):"},
 "ask_floc": {"en": "Where is the field? Pick the nearest covered location, or share the exact location.",
              "uz": "Dala qayerda? Eng yaqin hududni tanlang yoki aniq joylashuvni yuboring.",
              "ru": "Где поле? Выберите ближайший район или отправьте точную геопозицию."},
 "loc_out": {"en": "This location is outside the area we cover (Uzbekistan). Pick one of the listed locations.",
             "uz": "Bu joy bizning qamrov hududimizdan (O'zbekiston) tashqarida. Ro'yxatdagi joylardan birini tanlang.",
             "ru": "Это место вне зоны покрытия (Узбекистан). Выберите один из районов в списке."},
 "crop_q": {"en": "Which crop is on this field?", "uz": "Bu dalada qaysi ekin?", "ru": "Какая культура на этом поле?"},
 "stage_q": {"en": "Growth stage?", "uz": "Rivojlanish bosqichi?", "ru": "Фаза развития?"},
 "gw_q": {"en": "How deep is groundwater? (best guess)", "uz": "Yer osti suvi qancha chuqurlikda? (taxminan)", "ru": "Как глубоко грунтовые воды? (примерно)"},
 "dr_q": {"en": "Is drainage working?", "uz": "Zovur (drenaj) ishlayaptimi?", "ru": "Дренаж работает?"},
 "fl_q": {"en": "When was this field last flushed (leached)?", "uz": "Dala oxirgi marta qachon yuvilgan?", "ru": "Когда поле промывали в последний раз?"},
 "ec_q": {"en": "Salinity of this field, if you know it (soil test or experience):", "uz": "Dala sho'rligi, agar bilsangiz (tuproq tahlili yoki tajriba):",
          "ru": "Засоление поля, если знаете (анализ почвы или опыт):"},
 "saved": {"en": "Field saved ✅", "uz": "Dala saqlandi ✅", "ru": "Поле сохранено ✅"},
 "updated": {"en": "Updated ✅", "uz": "Yangilandi ✅", "ru": "Обновлено ✅"},
 "nofield": {"en": "You have no fields yet. Tap ➕ Add field.", "uz": "Hali dalangiz yo'q. ➕ Dala qo'shish tugmasini bosing.",
             "ru": "У вас пока нет полей. Нажмите ➕ Добавить поле."},
 "err": {"en": "NASA data source is unavailable right now. Try again later.", "uz": "NASA ma'lumot manbasi hozir mavjud emas. Keyinroq urinib ko'ring.",
         "ru": "Источник данных NASA сейчас недоступен. Попробуйте позже."},
 "loading": {"en": "⏳ Getting NASA data…", "uz": "⏳ NASA ma'lumotlari olinmoqda…", "ru": "⏳ Получаю данные NASA…"},
 "which_field": {"en": "Which field?", "uz": "Qaysi dala?", "ru": "Какое поле?"},
 "fields_title": {"en": "Your fields:", "uz": "Dalalaringiz:", "ru": "Ваши поля:"},
 "salt_unknown": {"en": "Field salinity not measured: the salt indicator is an estimate. Measure soil EC before planning flushing.",
                  "uz": "Dala sho'rligi o'lchanmagan: sho'rlanish ko'rsatkichi taxminiy. Yuvishni rejalashtirishdan oldin tuproq EC sini o'lchang.",
                  "ru": "Засоление поля не измерено: индикатор соли приблизительный. Перед промывкой измерьте EC почвы."},
 "recent": {"en": "Recent signals", "uz": "So'nggi signallar", "ru": "Последние сигналы"},

 "b_status": {"en": "📊 Status", "uz": "📊 Holat", "ru": "📊 Статус"},
 "b_plan": {"en": "🗓 Plan", "uz": "🗓 Reja", "ru": "🗓 План"},
 "b_stage": {"en": "🌱 Change stage", "uz": "🌱 Bosqichni o'zgartirish", "ru": "🌱 Сменить фазу"},
 "b_salt": {"en": "🧂 Update soil info", "uz": "🧂 Tuproq ma'lumoti", "ru": "🧂 Данные о почве"},
 "b_crop": {"en": "🌾 Change crop", "uz": "🌾 Ekinni o'zgartirish", "ru": "🌾 Сменить культуру"},
 "b_notif_on": {"en": "🔔 Alerts: on", "uz": "🔔 Bildirishnoma: yoqilgan", "ru": "🔔 Уведомления: вкл"},
 "b_notif_off": {"en": "🔕 Alerts: off", "uz": "🔕 Bildirishnoma: o'chiq", "ru": "🔕 Уведомления: выкл"},
 "b_delete": {"en": "🗑 Delete", "uz": "🗑 O'chirish", "ru": "🗑 Удалить"},
 "b_yes": {"en": "Yes, delete", "uz": "Ha, o'chirish", "ru": "Да, удалить"},
 "b_no": {"en": "Cancel", "uz": "Bekor qilish", "ru": "Отмена"},
 "confirm_del": {"en": "Delete this field?", "uz": "Bu dalani o'chiraymi?", "ru": "Удалить это поле?"},
 "deleted": {"en": "Deleted.", "uz": "O'chirildi.", "ru": "Удалено."},
 "field_gone": {"en": "Field not found.", "uz": "Dala topilmadi.", "ru": "Поле не найдено."},

 "comm_title": {"en": "👥 Farmer community\nShare practical tips. Advice here comes from other farmers and is NOT verified by an agronomist.",
                "uz": "👥 Fermerlar hamjamiyati\nAmaliy maslahatlar bilan o'rtoqlashing. Bu yerdagi maslahatlar boshqa fermerlardan va agronom tomonidan TASDIQLANMAGAN.",
                "ru": "👥 Сообщество фермеров\nДелитесь практическими советами. Советы здесь от других фермеров и НЕ проверены агрономом."},
 "c_region": {"en": "📰 My area", "uz": "📰 Hududim", "ru": "📰 Мой район"},
 "c_all": {"en": "🌍 All areas", "uz": "🌍 Barcha hududlar", "ru": "🌍 Все районы"},
 "c_write": {"en": "✍️ Write a post", "uz": "✍️ Post yozish", "ru": "✍️ Написать пост"},
 "c_mine": {"en": "🗂 My posts", "uz": "🗂 Postlarim", "ru": "🗂 Мои посты"},
 "c_none": {"en": "No posts yet. Be the first!", "uz": "Hozircha postlar yo'q. Birinchi bo'ling!", "ru": "Постов пока нет. Будьте первым!"},
 "ask_post": {"en": "Write your tip or question (10-500 characters). Do not share phone numbers or personal data.",
              "uz": "Maslahat yoki savolingizni yozing (10-500 belgi). Telefon raqami va shaxsiy ma'lumot yozmang.",
              "ru": "Напишите совет или вопрос (10-500 символов). Не публикуйте телефоны и личные данные."},
 "post_bad": {"en": "The post must be 10-500 characters.", "uz": "Post 10-500 belgidan iborat bo'lishi kerak.", "ru": "Пост должен быть 10-500 символов."},
 "post_limit": {"en": "Daily post limit reached (5). Try tomorrow.", "uz": "Kunlik post limiti tugadi (5). Ertaga urinib ko'ring.", "ru": "Достигнут дневной лимит постов (5). Попробуйте завтра."},
 "post_saved": {"en": "Posted ✅", "uz": "Joylandi ✅", "ru": "Опубликовано ✅"},
 "reported": {"en": "Thanks, reported.", "uz": "Rahmat, shikoyat qabul qilindi.", "ru": "Спасибо, жалоба принята."},
 "reported_already": {"en": "You already reported this post.", "uz": "Siz bu postga allaqachon shikoyat qilgansiz.", "ru": "Вы уже жаловались на этот пост."},
 "cancelled": {"en": "Cancelled.", "uz": "Bekor qilindi.", "ru": "Отменено."},

 "set_title": {"en": "⚙️ Settings", "uz": "⚙️ Sozlamalar", "ru": "⚙️ Настройки"},
 "s_lang": {"en": "🌐 Language", "uz": "🌐 Til", "ru": "🌐 Язык"},
 "s_region": {"en": "📍 My area", "uz": "📍 Hududim", "ru": "📍 Мой район"},
 "s_notif_on": {"en": "🔔 Morning alerts: on", "uz": "🔔 Ertalabki xabarlar: yoqilgan", "ru": "🔔 Утренние уведомления: вкл"},
 "s_notif_off": {"en": "🔕 Morning alerts: off", "uz": "🔕 Ertalabki xabarlar: o'chiq", "ru": "🔕 Утренние уведомления: выкл"},
 "s_delete": {"en": "🗑 Delete my account and data", "uz": "🗑 Akkaunt va ma'lumotlarni o'chirish", "ru": "🗑 Удалить аккаунт и данные"},
 "confirm_acc": {"en": "Delete your account, fields and posts? This cannot be undone.",
                 "uz": "Akkaunt, dalalar va postlar o'chirilsinmi? Buni qaytarib bo'lmaydi.",
                 "ru": "Удалить аккаунт, поля и посты? Это нельзя отменить."},
 "acc_deleted": {"en": "Your data was deleted. Send /start to register again.", "uz": "Ma'lumotlaringiz o'chirildi. Qayta ro'yxatdan o'tish uchun /start yuboring.",
                 "ru": "Ваши данные удалены. Для новой регистрации отправьте /start."},
 "alert_head": {"en": "🔔 Morning update", "uz": "🔔 Ertalabki xabar", "ru": "🔔 Утреннее сообщение"},
 "max_fields": {"en": "You can add up to {n} fields.", "uz": "Ko'pi bilan {n} ta dala qo'shish mumkin.", "ru": "Можно добавить не более {n} полей."},
 "app_not_set": {"en": "The app is not available right now. Please try again later.", "uz": "Ilova hozir mavjud emas. Keyinroq urinib ko'ring.", "ru": "Приложение сейчас недоступно. Попробуйте позже."},
 "farmer": {"en": "Farmer", "uz": "Fermer", "ru": "Фермер"},
 "like": {"en": "👍", "uz": "👍", "ru": "👍"},
 "report": {"en": "🚩 Report", "uz": "🚩 Shikoyat", "ru": "🚩 Пожаловаться"},
 "del_post": {"en": "🗑 Delete", "uz": "🗑 O'chirish", "ru": "🗑 Удалить"},
}

CROP_NAMES = {
 "cotton": {"en": "Cotton", "uz": "Paxta", "ru": "Хлопчатник"},
 "wheat": {"en": "Wheat", "uz": "Bug'doy", "ru": "Пшеница"},
 "barley": {"en": "Barley", "uz": "Arpa", "ru": "Ячмень"},
 "sugar_beet": {"en": "Sugar beet", "uz": "Qand lavlagi", "ru": "Сахарная свёкла"},
 "sorghum": {"en": "Sorghum", "uz": "Jo'xori", "ru": "Сорго"},
 "rice": {"en": "Rice", "uz": "Sholi", "ru": "Рис"},
 "tomato": {"en": "Tomato", "uz": "Pomidor", "ru": "Томат"},
 "alfalfa": {"en": "Alfalfa", "uz": "Beda", "ru": "Люцерна"},
 "maize": {"en": "Maize", "uz": "Makkajo'xori", "ru": "Кукуруза"},
 "potato": {"en": "Potato", "uz": "Kartoshka", "ru": "Картофель"},
 "onion": {"en": "Onion", "uz": "Piyoz", "ru": "Лук"},
}
STAGE_NAMES = {
 "fallow": {"en": "Fallow", "uz": "Shudgor", "ru": "Пар"},
 "initial": {"en": "Sowing / emergence", "uz": "Ekish / unib chiqish", "ru": "Посев / всходы"},
 "development": {"en": "Growth", "uz": "O'sish", "ru": "Рост"},
 "mid": {"en": "Mid-season (flowering)", "uz": "Gullash / o'rta davr", "ru": "Середина сезона (цветение)"},
 "late": {"en": "Ripening / harvest", "uz": "Pishish / hosil", "ru": "Созревание / уборка"},
}
GW_NAMES = {
 "shallow": {"en": "Shallow (<2 m)", "uz": "Sayoz (<2 m)", "ru": "Близко (<2 м)"},
 "medium": {"en": "Medium (2-3 m)", "uz": "O'rtacha (2-3 m)", "ru": "Средне (2-3 м)"},
 "deep": {"en": "Deep (>3 m)", "uz": "Chuqur (>3 m)", "ru": "Глубоко (>3 м)"},
 "unknown": {"en": "Don't know", "uz": "Bilmayman", "ru": "Не знаю"},
}
DR_NAMES = {
 "good": {"en": "✅ Working", "uz": "✅ Ishlayapti", "ru": "✅ Работает"},
 "poor": {"en": "❌ Not working", "uz": "❌ Ishlamayapti", "ru": "❌ Не работает"},
 "unknown": {"en": "Don't know", "uz": "Bilmayman", "ru": "Не знаю"},
}
FL_NAMES = {   # value -> (days stored in DB or None)
 "lt6": {"en": "< 6 months ago", "uz": "6 oydan kam oldin", "ru": "менее 6 мес. назад"},
 "6to12": {"en": "6-12 months ago", "uz": "6-12 oy oldin", "ru": "6-12 мес. назад"},
 "gt12": {"en": "> 1 year ago", "uz": "1 yildan oldin", "ru": "более года назад"},
 "unk": {"en": "Never / don't know", "uz": "Hech qachon / bilmayman", "ru": "Не было / не знаю"},
}
FL_DAYS = {"lt6": 90, "6to12": 270, "gt12": 500, "unk": None}
EC_NAMES = {
 "low": {"en": "Low", "uz": "Past", "ru": "Низкое"},
 "medium": {"en": "Medium", "uz": "O'rtacha", "ru": "Среднее"},
 "high": {"en": "High (white crust)", "uz": "Yuqori (oq qobiq)", "ru": "Высокое (белая корка)"},
 "unk": {"en": "Don't know", "uz": "Bilmayman", "ru": "Не знаю"},
}
LANG_BUTTONS = [("🇺🇿 O'zbekcha", "uz"), ("🇷🇺 Русский", "ru"), ("🇬🇧 English", "en")]


def tr(key: str, lang: str, **p) -> str:
    e = UI[key]
    return e.get(lang, e["en"]).format(**p) if p else e.get(lang, e["en"])


def nm(table: dict, key: str, lang: str) -> str:
    e = table.get(key)
    return e.get(lang, e["en"]) if e else key
