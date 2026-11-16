"""All user-facing text in en / uz (Latin) / ru. Engine returns keys; this renders them.
!! Uzbek and Russian strings are first drafts - need review by a native speaker / agronomist."""

T = {
 "st_IRRIGATE": {"en": "IRRIGATE", "uz": "SUG'ORING", "ru": "ПОЛИВАТЬ"},
 "st_MONITOR":  {"en": "MONITOR", "uz": "KUZATING", "ru": "НАБЛЮДАТЬ"},
 "st_WAIT":     {"en": "WAIT", "uz": "KUTING", "ru": "ЖДАТЬ"},
 "lv_LOW":    {"en": "Low", "uz": "Past", "ru": "Низкий"},
 "lv_MEDIUM": {"en": "Medium", "uz": "O'rtacha", "ru": "Средний"},
 "lv_HIGH":   {"en": "High", "uz": "Yuqori", "ru": "Высокий"},
 "fl_CONSIDER":    {"en": "Consider flushing", "uz": "Yuvishni ko'rib chiqing", "ru": "Можно рассмотреть промывку"},
 "fl_NOT_NOW":     {"en": "Not now", "uz": "Hozir emas", "ru": "Не сейчас"},
 "fl_NOT_ADVISED": {"en": "Not advised", "uz": "Tavsiya etilmaydi", "ru": "Не рекомендуется"},
 "fl_NOT_NEEDED":  {"en": "Not needed now", "uz": "Hozir kerak emas", "ru": "Сейчас не нужна"},

 "irr_fallow":  {"en": "The field is fallow, so no irrigation is needed.",
                 "uz": "Dala bo'sh (shudgor), sug'orish shart emas.",
                 "ru": "Поле под паром, полив не нужен."},
 "irr_rain":    {"en": "Significant rain ({rain} mm) is forecast within 3 days.",
                 "uz": "3 kun ichida sezilarli yog'ingarchilik ({rain} mm) kutilmoqda.",
                 "ru": "В ближайшие 3 дня ожидаются осадки ({rain} мм)."},
 "irr_dry":     {"en": "Root-zone moisture is low and no useful rain is forecast.",
                 "uz": "Ildiz qatlamida namlik past va foydali yog'in kutilmayapti.",
                 "ru": "Влажность корневой зоны низкая, полезных осадков не ожидается."},
 "irr_deficit": {"en": "The 7-day water deficit ({deficit} mm) is above the limit for this crop.",
                 "uz": "So'nggi 7 kundagi suv tanqisligi ({deficit} mm) me'yordan yuqori.",
                 "ru": "Дефицит воды за 7 дней ({deficit} мм) выше нормы для культуры."},
 "irr_watch":   {"en": "Moisture is declining or a deficit is building ({deficit} mm). Re-check in 1-2 days.",
                 "uz": "Namlik kamaymoqda ({deficit} mm tanqislik). 1-2 kundan keyin qayta tekshiring.",
                 "ru": "Влажность снижается, нарастает дефицит ({deficit} мм). Проверьте через 1-2 дня."},
 "irr_recent":  {"en": "You logged an irrigation {n} day(s) ago. Satellite wetness cannot see irrigation water, so the advice waits and counts water use only since then.",
                 "uz": "Siz {n} kun oldin sug'orishni yozgansiz. Yo'ldosh namligi sug'orish suvini ko'rmaydi, shuning uchun maslahat kutadi va suv sarfini faqat o'shandan beri hisoblaydi.",
                 "ru": "Вы отметили полив {n} дн. назад. Спутниковая влажность не видит поливную воду, поэтому совет ждёт и считает расход воды только с того момента."},
 "irr_ok":      {"en": "Soil moisture and the recent water balance look adequate.",
                 "uz": "Tuproq namligi va so'nggi suv balansi yetarli ko'rinadi.",
                 "ru": "Влажность почвы и водный баланс в норме."},

 "flush_not_needed": {"en": "Salt-risk indicator is low, so flushing is not a priority.",
                      "uz": "Sho'rlanish xavfi past, yuvish ustuvor emas.",
                      "ru": "Риск засоления низкий, промывка не приоритетна."},
 "flush_drainage":   {"en": "Flushing without working drainage can make salinity worse. Check drainage first.",
                      "uz": "Zovur (drenaj) ishlamasa, yuvish sho'rlanishni kuchaytirishi mumkin. Avval zovurni tekshiring.",
                      "ru": "Промывка без работающего дренажа может усилить засоление. Сначала проверьте дренаж."},
 "flush_frost":      {"en": "Frost expected or recent: soil may be frozen, so water will not drain properly.",
                      "uz": "Sovuq kutilmoqda yoki bo'lgan: tuproq muzlagan bo'lishi mumkin, suv singmaydi.",
                      "ru": "Ожидаются или были заморозки: почва может быть мёрзлой, вода не впитается."},
 "flush_rain":       {"en": "Heavy rain ({rain} mm) is forecast; wait to avoid waterlogging.",
                      "uz": "Kuchli yog'in ({rain} mm) kutilmoqda; suv bosishining oldini olish uchun kuting.",
                      "ru": "Ожидается сильный дождь ({rain} мм); подождите, чтобы избежать переувлажнения."},
 "flush_high_et":    {"en": "Evaporation is still high ({et0} mm/day); salts can rise back to the surface.",
                      "uz": "Bug'lanish hali yuqori ({et0} mm/kun); tuzlar yana yuzaga ko'tarilishi mumkin.",
                      "ru": "Испарение пока высокое ({et0} мм/день); соли могут подняться обратно."},
 "flush_consider":   {"en": "Conditions look suitable to consider flushing (cool, no frost or heavy rain ahead). Confirm with a local agronomist.",
                      "uz": "Sharoit yuvishni ko'rib chiqish uchun mos (salqin, sovuq va kuchli yog'in yo'q). Mahalliy agronom bilan maslahatlashing.",
                      "ru": "Условия подходят, чтобы рассмотреть промывку (прохладно, нет заморозков и ливней). Уточните у агронома."},
 "flush_consider_unknown_drainage": {
                      "en": "Weather looks suitable to consider flushing, but drainage and groundwater depth are unknown. Confirm with a local agronomist first.",
                      "uz": "Ob-havo yuvishni ko'rib chiqish uchun mos, lekin zovur va yer osti suvi chuqurligi noma'lum. Avval agronom bilan maslahatlashing.",
                      "ru": "Погода подходит для промывки, но дренаж и глубина грунтовых вод неизвестны. Сначала уточните у агронома."},

 "flush_saline_water": {"en": "Your irrigation water is saline (EC {ec} dS/m). Flushing with it may add salt instead of removing it. Check water quality and find a better source first.",
                       "uz": "Sug'orish suvingiz sho'r (EC {ec} dS/m). U bilan yuvish tuzni ketkazish o'rniga qo'shishi mumkin. Avval suv sifatini tekshiring va yaxshiroq manba toping.",
                       "ru": "Поливная вода засолена (EC {ec} дСм/м). Промывка ею может добавить соль, а не вывести. Сначала проверьте качество воды и найдите лучший источник."},
 "alert_frost": {"en": "❄️ Frost expected in the next 3 days (down to {t}°C): protect seedlings and do not irrigate or flush.",
                 "uz": "❄️ Keyingi 3 kunda sovuq kutilmoqda ({t}°C gacha): ko'chatlarni asrang, sug'orish va yuvish kerak emas.",
                 "ru": "❄️ В ближайшие 3 дня ожидаются заморозки (до {t}°C): берегите всходы, не поливайте и не промывайте."},
 "alert_rain": {"en": "🌧 Heavy rain expected ({mm} mm in 3 days): hold off irrigation and check drainage.",
                "uz": "🌧 Kuchli yog'in kutilmoqda (3 kunda {mm} mm): sug'orishni to'xtating va zovurni tekshiring.",
                "ru": "🌧 Ожидается сильный дождь ({mm} мм за 3 дня): отложите полив и проверьте дренаж."},
 "factor_arid":  {"en": "dry climate (little rain vs evaporation)", "uz": "quruq iqlim (yog'in bug'lanishdan kam)", "ru": "сухой климат (осадков мало по сравнению с испарением)"},
 "factor_gw":    {"en": "groundwater shallow/unknown", "uz": "yer osti suvi sayoz/noma'lum", "ru": "грунтовые воды близко/неизвестны"},
 "factor_flush": {"en": "no recent flushing", "uz": "yaqinda yuvilmagan", "ru": "давно не было промывки"},
 "factor_ec":    {"en": "reported high salinity", "uz": "yuqori sho'rlanish xabar qilingan", "ru": "заявлено высокое засоление"},

 "rot_high":   {"en": "Rotation idea: salt-tolerant crop (barley, cotton, sugar beet) -> winter leaching with drainage -> moderately tolerant crop.",
                "uz": "Almashlab ekish: sho'rga chidamli ekin (arpa, paxta, qand lavlagi) -> zovur bilan qishki yuvish -> o'rtacha chidamli ekin.",
                "ru": "Севооборот: солеустойчивая культура (ячмень, хлопчатник, сахарная свёкла) -> зимняя промывка с дренажом -> умеренно устойчивая культура."},
 "rot_medium": {"en": "Rotation idea: tolerant crops (wheat, cotton) with periodic leaching; avoid very sensitive crops (onion, potato, maize) on the worst patches.",
                "uz": "Almashlab ekish: chidamli ekinlar (bug'doy, paxta) va davriy yuvish; eng sho'r joylarda sezgir ekinlardan (piyoz, kartoshka, makkajo'xori) qoching.",
                "ru": "Севооборот: устойчивые культуры (пшеница, хлопчатник) и периодическая промывка; на самых засолённых участках избегайте чувствительных культур."},
 "rot_low":    {"en": "Most crops are suitable; keep irrigation efficient and monitor salt.",
                "uz": "Ko'pchilik ekinlar mos; sug'orishni tejamli olib boring va sho'rlanishni kuzating.",
                "ru": "Подходит большинство культур; поливайте экономно и следите за засолением."},

 "h_irr":   {"en": "Irrigation", "uz": "Sug'orish", "ru": "Полив"},
 "h_salt":  {"en": "Salt risk", "uz": "Sho'rlanish xavfi", "ru": "Риск засоления"},
 "h_flush": {"en": "Flushing", "uz": "Yuvish", "ru": "Промывка"},
 "h_crops": {"en": "Crop ideas", "uz": "Ekin tavsiyalari", "ru": "Подбор культур"},
 "because": {"en": "Because of", "uz": "Sabab", "ru": "Причины"},
 "disclaimer": {"en": "Decision support, not a measurement. NASA data is ~50 km grid, so confirm locally.",
                "uz": "Qaror qabul qilishga yordam, o'lchov emas. NASA ma'lumoti ~50 km katak, shuning uchun joyida tekshiring.",
                "ru": "Помощь в принятии решений, не измерение. Данные NASA ~50 км, уточняйте на месте."},
 "demo_note": {"en": "(demo data)", "uz": "(demo ma'lumot)", "ru": "(демо-данные)"},
 "plan_head":  {"en": "Season outlook (from past NASA data)", "uz": "Mavsum rejasi (NASAning o'tgan ma'lumotlari asosida)", "ru": "План сезона (по прошлым данным NASA)"},
 "plan_frost": {"en": "frost is usual: no irrigation or flushing, protect seedlings", "uz": "odatda sovuq bo'ladi: sug'orish va yuvish yo'q, ko'chatlarni asrang", "ru": "обычно заморозки: ни полива, ни промывки, берегите всходы"},
 "plan_peak_et": {"en": "hot and dry ({et0} mm/day evaporation): peak irrigation demand", "uz": "issiq va quruq (bug'lanish {et0} mm/kun): sug'orishga eng ko'p ehtiyoj", "ru": "жарко и сухо (испарение {et0} мм/день): пик потребности в поливе"},
 "plan_peak_et_salt": {"en": "hot and dry ({et0} mm/day): peak irrigation demand and salts rise to the surface; avoid flushing", "uz": "issiq va quruq ({et0} mm/kun): sug'orish talabi yuqori, tuzlar yuzaga ko'tariladi; yuvmang", "ru": "жарко и сухо ({et0} мм/день): пик полива, соли поднимаются к поверхности; не промывайте"},
 "plan_drainage_first": {"en": "fix drainage before any flushing", "uz": "yuvishdan oldin zovurni tuzating", "ru": "перед промывкой наладьте дренаж"},
 "plan_leach": {"en": "cool, low evaporation: possible flushing window (confirm with an agronomist)", "uz": "salqin, bug'lanish past: yuvish uchun mumkin bo'lgan davr (agronom bilan tasdiqlang)", "ru": "прохладно, испарение низкое: возможное окно для промывки (уточните у агронома)"},
 "plan_leach_check": {"en": "cool, low evaporation: possible flushing window if drainage works (check drainage and groundwater first)", "uz": "salqin, bug'lanish past: zovur ishlasa yuvish mumkin (avval zovur va yer osti suvini tekshiring)", "ru": "прохладно, испарение низкое: промывка возможна при работающем дренаже (сначала проверьте дренаж и грунтовые воды)"},
 "plan_mild":  {"en": "moderate conditions: follow the regular irrigation signal", "uz": "o'rtacha sharoit: oddiy sug'orish signaliga amal qiling", "ru": "умеренные условия: ориентируйтесь на обычный сигнал полива"},
 "plan_trend_dry":  {"en": "The last 90 days were drier than a year ago ({cur} vs {prev} mm): watch moisture and salt closely.", "uz": "So'nggi 90 kun o'tgan yilga nisbatan quruqroq ({cur} va {prev} mm): namlik va sho'rlanishni diqqat bilan kuzating.", "ru": "Последние 90 дней суше, чем год назад ({cur} и {prev} мм): внимательно следите за влажностью и солями."},
 "plan_trend_wet":  {"en": "The last 90 days were wetter than a year ago ({cur} vs {prev} mm): check drainage and waterlogging.", "uz": "So'nggi 90 kun o'tgan yilga nisbatan namroq ({cur} va {prev} mm): zovur va suv bosishini tekshiring.", "ru": "Последние 90 дней влажнее, чем год назад ({cur} и {prev} мм): проверьте дренаж и переувлажнение."},
 "plan_trend_same": {"en": "Rainfall over the last 90 days is similar to a year ago.", "uz": "So'nggi 90 kundagi yog'in o'tgan yilga o'xshash.", "ru": "Осадки за последние 90 дней близки к прошлогодним."},
 "plan_rot_head": {"en": "Rotation idea (next seasons)", "uz": "Almashlab ekish g'oyasi (keyingi mavsumlar)", "ru": "Идея севооборота (следующие сезоны)"},
 "plan_leach_step": {"en": "winter leaching with drainage", "uz": "zovur bilan qishki yuvish", "ru": "зимняя промывка с дренажом"},
 "plan_disc": {"en": "Based on past NASA POWER data (about {days} days). It shows typical conditions, NOT a forecast. Check with a local agronomist.", "uz": "NASA POWERning o'tgan ma'lumotlari (taxminan {days} kun) asosida. Bu odatiy sharoit, bashorat EMAS. Mahalliy agronom bilan maslahatlashing.", "ru": "По прошлым данным NASA POWER (около {days} дней). Это типичные условия, а НЕ прогноз. Уточните у агронома."},
 "months": {"en": "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec", "uz": "Yan Fev Mar Apr May Iyn Iyl Avg Sen Okt Noy Dek", "ru": "Янв Фев Мар Апр Май Июн Июл Авг Сен Окт Ноя Дек"},
}
LANGS = ("en", "uz", "ru")
EMOJI = {"IRRIGATE": "💧", "MONITOR": "👀", "WAIT": "⏳"}
RISK_EMOJI = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}


def t(key: str, lang: str = "en", **p) -> str:
    entry = T.get(key)
    if not entry:
        return key
    return entry.get(lang, entry["en"]).format(**p)


def render(advice: dict, lang: str = "en", crop_names: dict | None = None) -> dict:
    lang = lang if lang in LANGS else "en"
    irr, sal, fl, cr = advice["irrigation"], advice["salinity"], advice["flush"], advice["crops"]
    nmap = crop_names or {}
    good = [nmap.get(c["crop"], c["crop"].replace("_", " ")) for c in cr["crops"] if c["fit"] == "good"][:4]
    avoid = [nmap.get(c["crop"], c["crop"].replace("_", " ")) for c in cr["crops"] if c["fit"] == "avoid"][:3]
    factors = ", ".join(t(f["key"], lang) for f in sal["factors"][:2])
    out = {
        "irrigation_status": t("st_" + irr["status"], lang),
        "irrigation_reason": t(irr["reason_key"], lang, **irr["params"]),
        "salt_level": t("lv_" + sal["level"], lang),
        "salt_factors": factors,
        "flush_status": t("fl_" + fl["status"], lang),
        "flush_reason": t(fl["reason_key"], lang, **fl["params"]),
        "rotation": t(cr["rotation_key"], lang),
        "good_crops": good, "avoid_crops": avoid,
        "disclaimer": t("disclaimer", lang),
    }
    demo = " " + t("demo_note", lang) if advice["data"]["source"] == "demo" else ""
    out["message"] = (
        f"{EMOJI[irr['status']]} {t('h_irr', lang)}: {out['irrigation_status']}{demo}\n{out['irrigation_reason']}\n\n"
        f"{RISK_EMOJI[sal['level']]} {t('h_salt', lang)}: {out['salt_level']} ({sal['score']}/100)\n"
        f"{t('because', lang)}: {factors or '-'}\n\n"
        f"🚿 {t('h_flush', lang)}: {out['flush_status']}\n{out['flush_reason']}\n\n"
        f"🌾 {t('h_crops', lang)}: {', '.join(good)}\n{out['rotation']}\n\n"
        f"ℹ️ {out['disclaimer']}")
    return out


def render_plan(plan: dict, lang: str = "en", crop_names: dict | None = None) -> str:
    lang = lang if lang in LANGS else "en"
    names = crop_names or {}
    months = t("months", lang).split()
    lines = [f"🗓 {t('plan_head', lang)}", f"{RISK_EMOJI[plan['level']]} {t('h_salt', lang)}: {t('lv_' + plan['level'], lang)}", ""]
    for o in plan["outlook"]:
        lines.append(f"• {months[o['month'] - 1]}: {t(o['key'], lang, **o['params'])}")
    if plan.get("trend"):
        lines += ["", t(plan["trend"]["key"], lang, **plan["trend"]["params"])]
    steps = []
    for st in plan["rotation"]:
        steps.append(names.get(st["crop"], st["crop"].replace("_", " ")) if st["kind"] == "crop" else t("plan_leach_step", lang))
    lines += ["", f"🔁 {t('plan_rot_head', lang)}:", " → ".join(steps), "", f"ℹ️ {t('plan_disc', lang, days=plan['history_days'])}"]
    return "\n".join(lines)
