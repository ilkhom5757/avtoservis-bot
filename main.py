#!/usr/bin/env python3
"""
AVTOSERVIS BOT — v1.2
Ikki tilli: O'zbek / Русский
Har bir xodim o'z tilini tanlaydi
"""

import os
import json
import logging
from datetime import datetime, date

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# ══════════════════════════════════════════════════════════
# НАСТРОЙКИ
# ══════════════════════════════════════════════════════════
TOKEN    = os.environ.get("BOT_TOKEN", "ТВОЙ_ТОКЕН")
OWNER_ID = int(os.environ.get("OWNER_ID", "368817660"))
DATA_FILE = "data.json"

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

STAFF: dict = {OWNER_ID: "Руководитель 👑"}
# Язык каждого пользователя: {uid: "uz" или "ru"}
USER_LANG: dict = {}

# ══════════════════════════════════════════════════════════
# ПЕРЕВОДЫ
# ══════════════════════════════════════════════════════════
T = {
    # --- Общие ---
    "cancel":        {"uz": "❌ Bekor",        "ru": "❌ Отмена"},
    "skip":          {"uz": "⏭ O'tkazib",      "ru": "⏭ Пропустить"},
    "yes":           {"uz": "✅ Ha",            "ru": "✅ Да"},
    "no":            {"uz": "➡️ Yo'q",          "ru": "➡️ Нет"},
    "cancelled":     {"uz": "❌ Bekor qilindi.","ru": "❌ Отменено."},
    "no_access":     {"uz": "⛔ Ruxsat yo'q.\n\nSening ID: `{uid}`\nRahbarga yuboring.",
                      "ru": "⛔ Нет доступа.\n\nТвой ID: `{uid}`\nСкинь руководителю."},
    "only_owner":    {"uz": "⛔ Faqat rahbar uchun.", "ru": "⛔ Только для руководителя."},
    "no_open":       {"uz": "Ochiq buyurtmalar yo'q.", "ru": "Нет открытых заявок."},
    "enter_num":     {"uz": "Faqat raqam kiriting:", "ru": "Только цифры:"},
    "not_found":     {"uz": "❌ Topilmadi:", "ru": "❌ Не найдено:"},
    "enter_order":   {"uz": "*Buyurtma raqamini* kiriting:", "ru": "Введи *номер заявки:*"},

    # --- Выбор языка ---
    "choose_lang":   {"uz": "🌐 Tilni tanlang / Выберите язык:",
                      "ru": "🌐 Tilni tanlang / Выберите язык:"},
    "lang_set":      {"uz": "✅ Til: O'zbek\n\nAmal tanlang:",
                      "ru": "✅ Язык: Русский\n\nВыбери действие:"},

    # --- Главное меню ---
    "btn_accept":    {"uz": "🚗 Mashina qabul",    "ru": "🚗 Принять машину"},
    "btn_open":      {"uz": "📋 Ochiq buyurtmalar", "ru": "📋 Открытые заявки"},
    "btn_part":      {"uz": "🔩 Ehtiyot qism",      "ru": "🔩 Запчасть"},
    "btn_pay":       {"uz": "💰 To'lov",            "ru": "💰 Оплата"},
    "btn_expense":   {"uz": "📤 Xarajat",           "ru": "📤 Расход по заявке"},
    "btn_close":     {"uz": "✅ Buyurtmani yopish", "ru": "✅ Закрыть заявку"},
    "btn_history":   {"uz": "📞 Mijoz tarixi",      "ru": "📞 История клиента"},
    "btn_report":    {"uz": "📊 Kunlik hisobot",    "ru": "📊 Отчёт за день"},
    "btn_debts":     {"uz": "💸 Qarzlar",           "ru": "💸 Долги"},
    "btn_staff":     {"uz": "👥 Xodimlar",          "ru": "👥 Сотрудники"},

    # --- Приёмка ---
    "accept_title":  {"uz": "🚗 *Qabul*\n\nMashina raqami yoki markasi:",
                      "ru": "🚗 *Приёмка*\n\nНомер или марка машины:"},
    "accept_client": {"uz": "👤 Mijoz ismi:", "ru": "👤 Имя клиента:"},
    "accept_phone":  {"uz": "📱 Mijoz telefoni:\n_(yoki O'tkazib)_",
                      "ru": "📱 Телефон клиента:\n_(или Пропустить)_"},
    "accept_problem":{"uz": "📝 Muammo / nima shikoyati:",
                      "ru": "📝 Что жалуется / проблема:"},
    "accept_master": {"uz": "👨‍🔧 Qaysi usta oladi?", "ru": "👨‍🔧 Какой мастер берёт?"},
    "accept_service":{"uz": "🔧 Xizmat turi:", "ru": "🔧 Тип услуги:"},
    "accept_done":   {"uz": "✅ *Buyurtma №{id} yaratildi!*\n\n🚗 {car} | {client}\n🔧 {service} → {master}\n📝 {problem}",
                      "ru": "✅ *Заявка №{id} создана!*\n\n🚗 {car} | {client}\n🔧 {service} → {master}\n📝 {problem}"},
    "repeat_client": {"uz": "\n\n⚡ *Mijoz bizda {n} marta bo'lgan*\nOxirgi: {date} | {service}",
                      "ru": "\n\n⚡ *Клиент был у нас {n} раз(а)*\nПоследний: {date} | {service}"},
    "choose_master": {"uz": "Ustani ro'yxatdan tanlang:", "ru": "Выбери мастера из списка:"},

    # --- Запчасть ---
    "part_title":    {"uz": "🔩 *Ochiq buyurtmalar:*\n", "ru": "🔩 *Открытые заявки:*\n"},
    "part_source_q": {"uz": "Ehtiyot qism qayerdan?", "ru": "Откуда запчасть?"},
    "part_name_q":   {"uz": "Ehtiyot qism nomi:", "ru": "Название запчасти:"},
    "part_cost_q":   {"uz": "💸 Tannarxi — qancha sotib olindi (so'm):\n_(faqat sening hisobingga)_",
                      "ru": "💸 Себестоимость — сколько купили (сум):\n_(для твоего учёта)_"},
    "part_sell_q":   {"uz": "💰 Mijozga narxi (so'm):", "ru": "💰 Цена клиенту (сум):"},
    "part_work_q":   {"uz": "💰 Ish narxi (so'm):", "ru": "💰 Стоимость работы (сум):"},
    "part_done":     {"uz": "✅ *Ehtiyot qism №{id}ga qo'shildi*\n🔩 {name} [{source}]\n💰 {sell} so'm{margin}",
                      "ru": "✅ *Запчасть к №{id}*\n🔩 {name} [{source}]\n💰 {sell} сум{margin}"},
    "margin_line":   {"uz": "\n📈 Foyda: {m} so'm", "ru": "\n📈 Маржа: {m} сум"},

    # --- Источник запчасти ---
    "src_client":    {"uz": "👤 Mijoz olib keldi", "ru": "👤 Клиент привёз"},
    "src_bought":    {"uz": "🛒 Biz sotib oldik",  "ru": "🛒 Мы купили"},
    "src_stock":     {"uz": "📦 Ombordan",          "ru": "📦 Со склада"},

    # --- Услуги ---
    "svc_lift":      {"uz": "🔧 Ko'taruvchi/ta'mir", "ru": "🔧 Подъёмник/ремонт"},
    "svc_oil":       {"uz": "🛢 Moy almashtirish",   "ru": "🛢 Замена масла"},
    "svc_elec":      {"uz": "⚡ Elektrik",            "ru": "⚡ Электрика"},
    "svc_wash":      {"uz": "🚿 Yuvish",              "ru": "🚿 Мойка"},
    "svc_polish":    {"uz": "✨ Sayqallash",           "ru": "✨ Полировка"},
    "svc_tint":      {"uz": "🪟 Tonirovka",           "ru": "🪟 Тонировка"},
    "svc_pdr":       {"uz": "🔨 PDR (botiq)",         "ru": "🔨 PDR (вмятина)"},
    "svc_film":      {"uz": "🛡 Himoya plyonka",      "ru": "🛡 Бронеплёнка"},
    "svc_other":     {"uz": "🔩 Boshqa",              "ru": "🔩 Другое"},

    # --- Оплата ---
    "pay_title":     {"uz": "💰 *To'lov*\n\nOchiq buyurtmalar:\n",
                      "ru": "💰 *Оплата*\n\nОткрытые заявки:\n"},
    "pay_uzs_q":     {"uz": "💵 Naqd UZS miqdori (so'm):\n_(yo'q bo'lsa 0)_",
                      "ru": "💵 Сумма наличными UZS:\n_(введи 0 если нет)_"},
    "pay_has_usd":   {"uz": "💵 Dollar (USD) to'lov bormi?", "ru": "💵 Есть оплата в долларах (USD)?"},
    "pay_rate_q":    {"uz": "💱 Dollar kursi (1$ uchun so'm):", "ru": "💱 Курс доллара (сум за $1):"},
    "pay_usd_q":     {"uz": "💵 Dollar miqdori ($):", "ru": "💵 Сколько долларов ($):"},
    "pay_has_card":  {"uz": "💳 Karta orqali to'lov bormi?", "ru": "💳 Есть оплата картой?"},
    "pay_card_q":    {"uz": "💳 Karta summasi (so'm):", "ru": "💳 Сумма по карте (сум):"},
    "pay_has_bank":  {"uz": "🏦 O'tkazma bormi?", "ru": "🏦 Есть перечисление?"},
    "pay_bank_q":    {"uz": "🏦 O'tkazma summasi (so'm):", "ru": "🏦 Сумма перечислением (сум):"},
    "pay_has_debt":  {"uz": "📝 Mijoz to'liq to'lamadimi (qarz)?", "ru": "📝 Клиент не доплатил (долг)?"},
    "pay_debt_q":    {"uz": "📝 Qarz summasi (so'm):", "ru": "📝 Сумма долга (сум):"},
    "pay_disc_q":    {"uz": "🎁 Chegirma (so'm)?\n_(yo'q bo'lsa O'tkazib)_",
                      "ru": "🎁 Скидка (сум)?\n_(или Пропустить)_"},
    "pay_done":      {"uz": "✅ *№{id} buyurtmaga to'lov*\n\n{summary}{debt}",
                      "ru": "✅ *Оплата по заявке №{id}*\n\n{summary}{debt}"},
    "pay_debt_warn": {"uz": "\n\n⚠️ *Qarz qayd etildi!*", "ru": "\n\n⚠️ *Долг зафиксирован!*"},
    "pay_uzs_line":  {"uz": "  💵 Naqd UZS: {v} so'm", "ru": "  💵 Наличные UZS: {v} сум"},
    "pay_usd_line":  {"uz": "  💵 USD: ${a} × {r} = {v} so'm", "ru": "  💵 USD: ${a} × {r} = {v} сум"},
    "pay_card_line": {"uz": "  💳 Karta: {v} so'm", "ru": "  💳 Карта: {v} сум"},
    "pay_bank_line": {"uz": "  🏦 O'tkazma: {v} so'm", "ru": "  🏦 Перечисление: {v} сум"},
    "pay_debt_line": {"uz": "  📝 Qarz {m}: {v} so'm", "ru": "  📝 Долг {m}: {v} сум"},
    "pay_disc_line": {"uz": "  🎁 Chegirma: {v} so'm", "ru": "  🎁 Скидка: {v} сум"},
    "pay_total":     {"uz": "  ─────────────\n  💰 Qabul qilindi: {v} so'm",
                      "ru": "  ─────────────\n  💰 Получено: {v} сум"},

    # --- Расходы ---
    "exp_title":     {"uz": "📤 *Buyurtma bo'yicha xarajat*\n", "ru": "📤 *Расход по заявке*\n"},
    "exp_type_q":    {"uz": "Xarajat turi:", "ru": "Тип расхода:"},
    "exp_desc_q":    {"uz": "📝 Tavsif:\n_(yoki O'tkazib)_", "ru": "📝 Описание:\n_(или Пропустить)_"},
    "exp_amt_q":     {"uz": "💸 Xarajat summasi (so'm):", "ru": "💸 Сумма расхода (сум):"},
    "exp_done":      {"uz": "📤 *№{id} xarajat*\n{type}: {desc}\n💸 {amt} so'm\nJami xarajat: {total} so'm",
                      "ru": "📤 *Расход по №{id}*\n{type}: {desc}\n💸 {amt} сум\nВсего расходов: {total} сум"},
    "exp_benzin":    {"uz": "🚗 Benzin/yetkazib berish", "ru": "🚗 Бензин/доставка"},
    "exp_parts":     {"uz": "🛒 Ehtiyot qism sotib olish", "ru": "🛒 Покупка запчастей"},
    "exp_master":    {"uz": "👨‍🔧 Chaqirilgan usta", "ru": "👨‍🔧 Вызывной мастер"},
    "exp_tool":      {"uz": "🧰 Asbob/sarflanadigan material", "ru": "🧰 Инструмент/расходники"},
    "exp_other":     {"uz": "💰 Boshqa", "ru": "💰 Другое"},

    # --- Закрытие ---
    "close_title":   {"uz": "✅ *Buyurtmani yopish*\n", "ru": "✅ *Закрыть заявку*\n"},
    "close_done":    {"uz": "✅ *Buyurtma №{id} yopildi!*\n\n🚗 {car} | {client}{phone}{debt}",
                      "ru": "✅ *Заявка №{id} закрыта!*\n\n🚗 {car} | {client}{phone}{debt}"},
    "close_call":    {"uz": "\n\n📞 Mijozga qo'ng'iroq qiling: *{phone}*",
                      "ru": "\n\n📞 Позвони клиенту: *{phone}*"},
    "close_call2":   {"uz": "\n\n📞 Mijozga qo'ng'iroq qiling!",
                      "ru": "\n\n📞 Позвони клиенту!"},
    "close_debt":    {"uz": "\n\n⚠️ *Yopilmagan qarz bor!*", "ru": "\n\n⚠️ *Есть незакрытый долг!*"},

    # --- История ---
    "hist_q":        {"uz": "📞 Mijoz telefonini kiriting:", "ru": "📞 Введи телефон клиента:"},
    "hist_none":     {"uz": "🔍 {phone} raqamli mijoz topilmadi.", "ru": "🔍 Клиент {phone} не найден."},
    "hist_header":   {"uz": "👤 *{name}* | {phone}\n📊 Tashriflar: {n} | Jami: {total} so'm\n─────────────",
                      "ru": "👤 *{name}* | {phone}\n📊 Визитов: {n} | Потратил: {total} сум\n─────────────"},

    # --- Отчёт ---
    "rep_title":     {"uz": "📊 *{date} kunlik hisobot*\n", "ru": "📊 *Отчёт за {date}*\n"},
    "rep_orders":    {"uz": "📋 Buyurtmalar: {t}  |  Yopilgan: {c}  |  Ishda: {w}",
                      "ru": "📋 Заявок: {t}  |  Закрыто: {c}  |  В работе: {w}"},
    "rep_received":  {"uz": "\n💰 *Qabul qilindi: {v} so'm*", "ru": "\n💰 *Получено: {v} сум*"},
    "rep_uzs":       {"uz": "  💵 Naqd UZS: {v} so'm", "ru": "  💵 Наличные UZS: {v} сум"},
    "rep_usd":       {"uz": "  💵 Naqd USD: {v} so'm", "ru": "  💵 Наличные USD: {v} сум"},
    "rep_card":      {"uz": "  💳 Karta: {v} so'm", "ru": "  💳 Карта: {v} сум"},
    "rep_bank":      {"uz": "  🏦 O'tkazma: {v} so'm", "ru": "  🏦 Перечисление: {v} сум"},
    "rep_debt":      {"uz": "  📝 Qarzlar (olinmagan): {v} so'm", "ru": "  📝 Долги (не получено): {v} сум"},
    "rep_exp":       {"uz": "\n📤 Xarajatlar: {v} so'm", "ru": "\n📤 Расходы: {v} сум"},
    "rep_margin":    {"uz": "📈 Ehtiyot qism foydasi: {v} so'm", "ru": "📈 Маржа запчастей: {v} сум"},
    "rep_profit":    {"uz": "\n✅ *Sof foyda: {v} so'm*", "ru": "\n✅ *Чистая прибыль: {v} сум*"},
    "rep_list":      {"uz": "\n─────────────────\n*Buyurtmalar:*", "ru": "\n─────────────────\n*Заявки:*"},
    "rep_none":      {"uz": "📊 Bugun buyurtma yo'q.", "ru": "📊 Сегодня заявок нет."},

    # --- Долги ---
    "debt_title":    {"uz": "💸 *Qarzlar ({n}) — jami: {total} so'm*\n",
                      "ru": "💸 *Долги ({n}) — итого: {total} сум*\n"},
    "debt_none":     {"uz": "✅ Qarz yo'q!", "ru": "✅ Долгов нет!"},
    "debt_close_cmd":{"uz": "\nYopish: /qarz BUYURTMA_RAQAMI", "ru": "\nЗакрыть: /долг НОМЕР"},
    "debt_closed":   {"uz": "✅ №{id} qarz yopildi!\n🚗 {car} | {client}",
                      "ru": "✅ Долг по №{id} закрыт!\n🚗 {car} | {client}"},
    "debt_none2":    {"uz": "Bu buyurtmada qarz yo'q.", "ru": "Долгов нет."},

    # --- Сотрудники ---
    "staff_title":   {"uz": "👥 *Xodimlar:*\n", "ru": "👥 *Сотрудники:*\n"},
    "staff_add_fmt": {"uz": "Qo'shish: /qoshish 123456789 Ism", "ru": "Добавить: /добавить 123456789 Имя"},
    "staff_added":   {"uz": "✅ {name} qo'shildi!", "ru": "✅ {name} добавлен!"},
    "staff_fmt_err": {"uz": "❌ Format: /qoshish 123456789 Ism", "ru": "❌ Ошибка. Формат: /добавить 123456789 Имя"},

    # --- Открытые заявки ---
    "open_title":    {"uz": "📋 *Ochiq buyurtmalar ({n}):*\n", "ru": "📋 *Открытые заявки ({n}):*\n"},
    "open_none":     {"uz": "✅ Ochiq buyurtmalar yo'q!", "ru": "✅ Открытых заявок нет!"},

    # --- Карточка заявки ---
    "card_status":   {"uz": "\n📊 Holat: *{s}*", "ru": "\n📊 Статус: *{s}*"},
    "card_parts":    {"uz": "\n🔩 *Ehtiyot qismlar:*", "ru": "\n🔩 *Запчасти:*"},
    "card_margin":   {"uz": "  📈 Foyda: {v} so'm", "ru": "  📈 Маржа: {v} сум"},
    "card_pay":      {"uz": "\n💰 *To'lov:*", "ru": "\n💰 *Оплата:*"},
    "card_exp":      {"uz": "\n📤 *Xarajatlar:*", "ru": "\n📤 *Расходы:*"},
    "card_exp_tot":  {"uz": "  Jami xarajat: {v} so'm", "ru": "  Итого расход: {v} сум"},
    "card_profit":   {"uz": "  ✅ Sof foyda: {v} so'm", "ru": "  ✅ Чистая прибыль: {v} сум"},
    "card_debt_mark":{"uz": " 💸QARZ {v} so'm", "ru": " 💸ДОЛГ {v} сум"},

    # --- Статусы ---
    "status_work":   {"uz": "ishda", "ru": "в работе"},
    "status_closed": {"uz": "yopildi", "ru": "закрыто"},
}

def t(key: str, uid: int, **kwargs) -> str:
    lang = USER_LANG.get(uid, "ru")
    text = T.get(key, {}).get(lang, T.get(key, {}).get("ru", key))
    if kwargs:
        try: text = text.format(**kwargs)
        except: pass
    return text

def lang(uid): return USER_LANG.get(uid, "ru")

# ══════════════════════════════════════════════════════════
# СПРАВОЧНИКИ (зависят от языка)
# ══════════════════════════════════════════════════════════
def get_masters(): return ["Abduraxmon", "Axror", "Abdulloh", "Tonirovkachi", "Kuzovchi", "Elektrik"]

def get_services(uid):
    return [t(k, uid) for k in ["svc_lift","svc_oil","svc_elec","svc_wash","svc_polish","svc_tint","svc_pdr","svc_film","svc_other"]]

def get_sources(uid):
    return [t(k, uid) for k in ["src_client","src_bought","src_stock"]]

def get_expenses(uid):
    return [t(k, uid) for k in ["exp_benzin","exp_parts","exp_master","exp_tool","exp_other"]]

# ══════════════════════════════════════════════════════════
# СОСТОЯНИЯ
# ══════════════════════════════════════════════════════════
(
    LANG_SELECT,
    A_CAR, A_CLIENT, A_PHONE, A_PROBLEM, A_MASTER, A_SERVICE,
    P_ORDER, P_SOURCE, P_NAME, P_COST, P_SELL,
    PAY_ORDER, PAY_UZS, PAY_HAS_USD, PAY_USD_RATE, PAY_USD_AMT,
    PAY_HAS_CARD, PAY_CARD, PAY_HAS_BANK, PAY_BANK,
    PAY_HAS_DEBT, PAY_DEBT, PAY_DISCOUNT,
    EXP_ORDER, EXP_TYPE, EXP_DESC, EXP_AMOUNT,
    CLOSE_ORDER, HIST_PHONE,
) = range(30)

# ══════════════════════════════════════════════════════════
# БАЗА ДАННЫХ
# ══════════════════════════════════════════════════════════
def load() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"orders": [], "next_id": 1, "clients": {}, "user_langs": {}}

def save(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_langs():
    d = load()
    for uid_str, lg in d.get("user_langs", {}).items():
        USER_LANG[int(uid_str)] = lg

def save_lang(uid: int, lg: str):
    USER_LANG[uid] = lg
    d = load()
    d.setdefault("user_langs", {})[str(uid)] = lg
    save(d)

def new_id() -> int:
    d = load(); n = d["next_id"]; d["next_id"] += 1; save(d); return n

def add_order(order: dict):
    d = load()
    d["orders"].append(order)
    phone = order.get("phone", "").strip()
    if phone:
        if phone not in d["clients"]:
            d["clients"][phone] = {"name": order["client"], "orders": []}
        d["clients"][phone]["orders"].append(order["id"])
    save(d)

def get_order(oid: int):
    return next((o for o in load()["orders"] if o["id"] == oid), None)

def update_order(oid: int, upd: dict):
    d = load()
    for o in d["orders"]:
        if o["id"] == oid: o.update(upd)
    save(d)

def open_orders(): return [o for o in load()["orders"] if o["status"] != "closed"]
def today_orders(): return [o for o in load()["orders"] if o["date"] == date.today().isoformat()]

def all_debts():
    result = []
    for o in load()["orders"]:
        amt = sum(dp.get("amount_uzs", 0) for dp in o.get("payment", {}).get("debt_parts", []) if not dp.get("paid"))
        if amt > 0: result.append((o, amt))
    return result

def client_history(phone: str):
    d = load()
    if phone in d["clients"]:
        ids = set(d["clients"][phone]["orders"])
        return [o for o in d["orders"] if o["id"] in ids]
    return []

# ══════════════════════════════════════════════════════════
# УТИЛИТЫ
# ══════════════════════════════════════════════════════════
def is_staff(uid): return uid in STAFF or uid == OWNER_ID
def is_owner(uid): return uid == OWNER_ID
def sname(uid): return STAFF.get(uid, f"ID:{uid}")
def fmt(n):
    try: return f"{int(n):,}".replace(",", " ")
    except: return str(n)
def now_t(): return datetime.now().strftime("%H:%M")
def today_d(): return date.today().isoformat()

def payment_summary(pay: dict, uid: int) -> str:
    lines = []
    total = 0
    if pay.get("uzs", 0):
        lines.append(t("pay_uzs_line", uid, v=fmt(pay["uzs"])))
        total += pay["uzs"]
    if pay.get("usd_amt", 0):
        uzs_eq = pay["usd_amt"] * pay.get("usd_rate", 1)
        lines.append(t("pay_usd_line", uid, a=pay["usd_amt"], r=fmt(pay["usd_rate"]), v=fmt(uzs_eq)))
        total += uzs_eq
    if pay.get("card", 0):
        lines.append(t("pay_card_line", uid, v=fmt(pay["card"])))
        total += pay["card"]
    if pay.get("bank", 0):
        lines.append(t("pay_bank_line", uid, v=fmt(pay["bank"])))
        total += pay["bank"]
    for dp in pay.get("debt_parts", []):
        mark = "✅" if dp.get("paid") else "⏳"
        lines.append(t("pay_debt_line", uid, m=mark, v=fmt(dp["amount_uzs"])))
    if pay.get("discount", 0):
        lines.append(t("pay_disc_line", uid, v=fmt(pay["discount"])))
    lines.append(t("pay_total", uid, v=fmt(total)))
    return "\n".join(lines)

def order_card(o: dict, uid: int, short=False) -> str:
    pay = o.get("payment", {})
    expenses = o.get("expenses", [])
    received = (pay.get("uzs", 0) + pay.get("usd_amt", 0) * pay.get("usd_rate", 1)
                + pay.get("card", 0) + pay.get("bank", 0))
    debt_total = sum(dp.get("amount_uzs", 0) for dp in pay.get("debt_parts", []) if not dp.get("paid"))
    exp_total = sum(e["amount"] for e in expenses)
    parts_margin = sum(p.get("sell_price", 0) - p.get("cost_price", 0) for p in o.get("parts", []))
    has_debt = debt_total > 0
    icon = "✅" if o["status"] == "closed" else ("⏳" if has_debt else "🔧")
    status_text = t("status_closed", uid) if o["status"] == "closed" else t("status_work", uid)

    if short:
        debt_mark = t("card_debt_mark", uid, v=fmt(debt_total)) if has_debt else ""
        return (f"{icon} №{o['id']} | {o['car']} | {o['client']}\n"
                f"   {o['service']} → {o['master']}{debt_mark}\n"
                f"   📅 {o['date']} {o['time']}")

    lines = [
        f"📋 *№{o['id']}*  {icon}",
        f"🚗 *{o['car']}*",
        f"👤 {o['client']} | 📱 {o['phone']}",
        f"🔧 {o['service']} → *{o['master']}*",
        f"📝 {o['problem']}",
        f"📅 {o['date']} {o['time']}",
    ]
    if o.get("parts"):
        lines.append(t("card_parts", uid))
        for p in o["parts"]:
            lines.append(f"  • {p['name']} [{p['source']}] — {fmt(p['sell_price'])} so'm/сум")
        if parts_margin > 0:
            lines.append(t("card_margin", uid, v=fmt(parts_margin)))
    if pay:
        lines.append(t("card_pay", uid))
        lines.append(payment_summary(pay, uid))
    if expenses:
        lines.append(t("card_exp", uid))
        for e in expenses:
            lines.append(f"  • {e['type']}: {e.get('desc','')} — {fmt(e['amount'])} so'm/сум")
        lines.append(t("card_exp_tot", uid, v=fmt(exp_total)))
        lines.append(t("card_profit", uid, v=fmt(received - exp_total)))
    lines.append(t("card_status", uid, s=status_text))
    return "\n".join(lines)

async def notify_owner(ctx, text: str, uid: int):
    if uid != OWNER_ID:
        try:
            await ctx.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Notify failed: {e}")

# ══════════════════════════════════════════════════════════
# КЛАВИАТУРЫ
# ══════════════════════════════════════════════════════════
def kb_main(uid):
    rows = [
        [t("btn_accept", uid), t("btn_open", uid)],
        [t("btn_part", uid), t("btn_pay", uid)],
        [t("btn_expense", uid), t("btn_close", uid)],
        [t("btn_history", uid)],
    ]
    if is_owner(uid):
        rows += [[t("btn_report", uid), t("btn_debts", uid)], [t("btn_staff", uid)]]
    return ReplyKeyboardMarkup([[KeyboardButton(b) for b in r] for r in rows], resize_keyboard=True)

def kb_lang():
    return ReplyKeyboardMarkup([[KeyboardButton("🇺🇿 O'zbek"), KeyboardButton("🇷🇺 Русский")]], resize_keyboard=True)

def kb(items, cols=2, uid=None):
    cancel_text = t("cancel", uid) if uid else "❌"
    rows = [items[i:i+cols] for i in range(0, len(items), cols)]
    rows.append([cancel_text])
    return ReplyKeyboardMarkup([[KeyboardButton(b) for b in r] for r in rows], resize_keyboard=True)

def kb_yn(uid):
    return ReplyKeyboardMarkup([
        [KeyboardButton(t("yes", uid)), KeyboardButton(t("no", uid))],
        [KeyboardButton(t("cancel", uid))]
    ], resize_keyboard=True)

def kb_cancel(uid):
    return ReplyKeyboardMarkup([[KeyboardButton(t("cancel", uid))]], resize_keyboard=True)

def kb_skip(uid):
    return ReplyKeyboardMarkup([[KeyboardButton(t("skip", uid)), KeyboardButton(t("cancel", uid))]], resize_keyboard=True)

def is_cancel(text, uid): return text == t("cancel", uid)
def is_skip(text, uid): return text == t("skip", uid)
def is_yes(text, uid): return text == t("yes", uid)

# ══════════════════════════════════════════════════════════
# СТАРТ + ВЫБОР ЯЗЫКА
# ══════════════════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        await update.message.reply_text(
            f"⛔ Ruxsat yo'q / Нет доступа.\n\nID: `{uid}`",
            parse_mode="Markdown"
        )
        return
    # Если язык уже выбран — сразу меню
    if uid in USER_LANG:
        await update.message.reply_text(t("lang_set", uid), parse_mode="Markdown", reply_markup=kb_main(uid))
        return
    await update.message.reply_text(t("choose_lang", uid), reply_markup=kb_lang())
    return

async def cmd_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Сменить язык в любой момент"""
    uid = update.effective_user.id
    if not is_staff(uid): return
    await update.message.reply_text(t("choose_lang", uid), reply_markup=kb_lang())

async def add_staff_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Format: /добавить 123456789 Abduraxmon"); return
    try:
        STAFF[int(args[0])] = " ".join(args[1:])
        await update.message.reply_text(f"✅ {' '.join(args[1:])} added!")
    except:
        await update.message.reply_text("❌ Error.")

# ══════════════════════════════════════════════════════════
# 1. ПРИЁМКА
# ══════════════════════════════════════════════════════════
async def accept_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    ctx.user_data.clear()
    await update.message.reply_text(t("accept_title", uid), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return A_CAR

async def accept_car(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    ctx.user_data["car"] = update.message.text
    await update.message.reply_text(t("accept_client", uid), reply_markup=kb_cancel(uid))
    return A_CLIENT

async def accept_client(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    ctx.user_data["client"] = update.message.text
    await update.message.reply_text(t("accept_phone", uid), parse_mode="Markdown", reply_markup=kb_skip(uid))
    return A_PHONE

async def accept_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    phone = "" if is_skip(update.message.text, uid) else update.message.text
    ctx.user_data["phone"] = phone
    extra = ""
    if phone:
        history = client_history(phone)
        if history:
            last = history[-1]
            extra = t("repeat_client", uid, n=len(history), date=last["date"], service=last["service"])
    await update.message.reply_text(t("accept_problem", uid) + extra, parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return A_PROBLEM

async def accept_problem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    ctx.user_data["problem"] = update.message.text
    await update.message.reply_text(t("accept_master", uid), reply_markup=kb(get_masters(), uid=uid))
    return A_MASTER

async def accept_master(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    if update.message.text not in get_masters():
        await update.message.reply_text(t("choose_master", uid), reply_markup=kb(get_masters(), uid=uid))
        return A_MASTER
    ctx.user_data["master"] = update.message.text
    await update.message.reply_text(t("accept_service", uid), reply_markup=kb(get_services(uid), uid=uid))
    return A_SERVICE

async def accept_service(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    oid = new_id()
    order = {
        "id": oid, "date": today_d(), "time": now_t(),
        "car": ctx.user_data["car"], "client": ctx.user_data["client"],
        "phone": ctx.user_data["phone"], "problem": ctx.user_data["problem"],
        "master": ctx.user_data["master"], "service": update.message.text,
        "parts": [], "payment": {}, "expenses": [],
        "status": "in_work", "created_by": sname(uid),
    }
    add_order(order)
    msg = t("accept_done", uid, id=oid, car=order["car"], client=order["client"], service=order["service"], master=order["master"], problem=order["problem"])
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
    await notify_owner(ctx, f"🔔 *New order #{oid}*\n🚗 {order['car']} | {order['client']}\n🔧 {order['service']} → {order['master']}\n📝 {order['problem']}\n👤 {sname(uid)}", uid)
    return ConversationHandler.END

# ══════════════════════════════════════════════════════════
# 2. ЗАПЧАСТЬ
# ══════════════════════════════════════════════════════════
async def part_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    orders = open_orders()
    if not orders:
        await update.message.reply_text(t("no_open", uid), reply_markup=kb_main(uid)); return ConversationHandler.END
    ctx.user_data.clear()
    lines = [t("part_title", uid)] + [order_card(o, uid, short=True) for o in orders] + ["\n" + t("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return P_ORDER

async def part_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o or o["status"] == "closed":
            await update.message.reply_text(t("not_found", uid)); return P_ORDER
        ctx.user_data["order_id"] = oid
        await update.message.reply_text(f"#{oid} | {o['car']}\n\n{t('part_source_q', uid)}", reply_markup=kb(get_sources(uid), uid=uid))
        return P_SOURCE
    except:
        await update.message.reply_text(t("enter_num", uid)); return P_ORDER

async def part_source(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    if update.message.text not in get_sources(uid):
        await update.message.reply_text(t("part_source_q", uid), reply_markup=kb(get_sources(uid), uid=uid)); return P_SOURCE
    ctx.user_data["source"] = update.message.text
    await update.message.reply_text(t("part_name_q", uid), reply_markup=kb_cancel(uid))
    return P_NAME

async def part_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    ctx.user_data["part_name"] = update.message.text
    if ctx.user_data["source"] == t("src_client", uid):
        ctx.user_data["cost_price"] = 0
        await update.message.reply_text(t("part_work_q", uid), reply_markup=kb_cancel(uid))
        return P_SELL
    await update.message.reply_text(t("part_cost_q", uid), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return P_COST

async def part_cost(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        ctx.user_data["cost_price"] = int(update.message.text.replace(" ", ""))
        await update.message.reply_text(t("part_sell_q", uid), reply_markup=kb_cancel(uid))
        return P_SELL
    except:
        await update.message.reply_text(t("enter_num", uid)); return P_COST

async def part_sell(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        sell = int(update.message.text.replace(" ", ""))
        cost = ctx.user_data.get("cost_price", 0)
        part = {"name": ctx.user_data["part_name"], "source": ctx.user_data["source"], "cost_price": cost, "sell_price": sell}
        oid = ctx.user_data["order_id"]
        o = get_order(oid)
        update_order(oid, {"parts": o.get("parts", []) + [part]})
        margin_line = t("margin_line", uid, m=fmt(sell - cost)) if sell > cost else ""
        msg = t("part_done", uid, id=oid, name=part["name"], source=part["source"], sell=fmt(sell), margin=margin_line)
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
        await notify_owner(ctx, msg, uid)
        return ConversationHandler.END
    except:
        await update.message.reply_text(t("enter_num", uid)); return P_SELL

# ══════════════════════════════════════════════════════════
# 3. ОПЛАТА
# ══════════════════════════════════════════════════════════
async def pay_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    orders = open_orders()
    if not orders:
        await update.message.reply_text(t("no_open", uid), reply_markup=kb_main(uid)); return ConversationHandler.END
    ctx.user_data.clear()
    ctx.user_data["pay"] = {"uzs": 0, "usd_amt": 0, "usd_rate": 0, "card": 0, "bank": 0, "debt_parts": [], "discount": 0}
    lines = [t("pay_title", uid)] + [order_card(o, uid, short=True) for o in orders] + ["\n" + t("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return PAY_ORDER

async def pay_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o or o["status"] == "closed":
            await update.message.reply_text(t("not_found", uid)); return PAY_ORDER
        ctx.user_data["order_id"] = oid
        await update.message.reply_text(
            order_card(o, uid) + "\n\n" + t("pay_uzs_q", uid),
            parse_mode="Markdown", reply_markup=kb_cancel(uid)
        )
        return PAY_UZS
    except:
        await update.message.reply_text(t("enter_num", uid)); return PAY_ORDER

async def pay_uzs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        ctx.user_data["pay"]["uzs"] = int(update.message.text.replace(" ", ""))
        await update.message.reply_text(t("pay_has_usd", uid), reply_markup=kb_yn(uid))
        return PAY_HAS_USD
    except:
        await update.message.reply_text(t("enter_num", uid)); return PAY_UZS

async def pay_has_usd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    if is_yes(update.message.text, uid):
        await update.message.reply_text(t("pay_rate_q", uid), reply_markup=kb_cancel(uid))
        return PAY_USD_RATE
    await update.message.reply_text(t("pay_has_card", uid), reply_markup=kb_yn(uid))
    return PAY_HAS_CARD

async def pay_usd_rate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        ctx.user_data["pay"]["usd_rate"] = int(update.message.text.replace(" ", ""))
        await update.message.reply_text(t("pay_usd_q", uid), reply_markup=kb_cancel(uid))
        return PAY_USD_AMT
    except:
        await update.message.reply_text(t("enter_num", uid)); return PAY_USD_RATE

async def pay_usd_amt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        ctx.user_data["pay"]["usd_amt"] = int(update.message.text.replace(" ", ""))
        await update.message.reply_text(t("pay_has_card", uid), reply_markup=kb_yn(uid))
        return PAY_HAS_CARD
    except:
        await update.message.reply_text(t("enter_num", uid)); return PAY_USD_AMT

async def pay_has_card(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    if is_yes(update.message.text, uid):
        await update.message.reply_text(t("pay_card_q", uid), reply_markup=kb_cancel(uid))
        return PAY_CARD
    await update.message.reply_text(t("pay_has_bank", uid), reply_markup=kb_yn(uid))
    return PAY_HAS_BANK

async def pay_card(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        ctx.user_data["pay"]["card"] = int(update.message.text.replace(" ", ""))
        await update.message.reply_text(t("pay_has_bank", uid), reply_markup=kb_yn(uid))
        return PAY_HAS_BANK
    except:
        await update.message.reply_text(t("enter_num", uid)); return PAY_CARD

async def pay_has_bank(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    if is_yes(update.message.text, uid):
        await update.message.reply_text(t("pay_bank_q", uid), reply_markup=kb_cancel(uid))
        return PAY_BANK
    await update.message.reply_text(t("pay_has_debt", uid), reply_markup=kb_yn(uid))
    return PAY_HAS_DEBT

async def pay_bank(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        ctx.user_data["pay"]["bank"] = int(update.message.text.replace(" ", ""))
        await update.message.reply_text(t("pay_has_debt", uid), reply_markup=kb_yn(uid))
        return PAY_HAS_DEBT
    except:
        await update.message.reply_text(t("enter_num", uid)); return PAY_BANK

async def pay_has_debt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    if is_yes(update.message.text, uid):
        await update.message.reply_text(t("pay_debt_q", uid), reply_markup=kb_cancel(uid))
        return PAY_DEBT
    await update.message.reply_text(t("pay_disc_q", uid), parse_mode="Markdown", reply_markup=kb_skip(uid))
    return PAY_DISCOUNT

async def pay_debt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        ctx.user_data["pay"]["debt_parts"].append({"amount_uzs": int(update.message.text.replace(" ", "")), "paid": False, "date": today_d()})
        await update.message.reply_text(t("pay_disc_q", uid), parse_mode="Markdown", reply_markup=kb_skip(uid))
        return PAY_DISCOUNT
    except:
        await update.message.reply_text(t("enter_num", uid)); return PAY_DEBT

async def pay_discount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    if not is_skip(update.message.text, uid):
        try:
            ctx.user_data["pay"]["discount"] = int(update.message.text.replace(" ", ""))
        except:
            await update.message.reply_text(t("enter_num", uid)); return PAY_DISCOUNT
    pay = ctx.user_data["pay"]
    oid = ctx.user_data["order_id"]
    update_order(oid, {"payment": pay})
    has_debt = bool(pay.get("debt_parts"))
    debt_warn = t("pay_debt_warn", uid) if has_debt else ""
    summary = payment_summary(pay, uid)
    msg = t("pay_done", uid, id=oid, summary=summary, debt=debt_warn)
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
    await notify_owner(ctx, msg, uid)
    return ConversationHandler.END

# ══════════════════════════════════════════════════════════
# 4. РАСХОДЫ
# ══════════════════════════════════════════════════════════
async def exp_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    orders = open_orders()
    if not orders:
        await update.message.reply_text(t("no_open", uid), reply_markup=kb_main(uid)); return ConversationHandler.END
    ctx.user_data.clear()
    lines = [t("exp_title", uid)] + [order_card(o, uid, short=True) for o in orders] + ["\n" + t("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return EXP_ORDER

async def exp_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o:
            await update.message.reply_text(t("not_found", uid)); return EXP_ORDER
        ctx.user_data["order_id"] = oid
        await update.message.reply_text(f"#{oid} | {o['car']}\n\n{t('exp_type_q', uid)}", reply_markup=kb(get_expenses(uid), uid=uid))
        return EXP_TYPE
    except:
        await update.message.reply_text(t("enter_num", uid)); return EXP_ORDER

async def exp_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    if update.message.text not in get_expenses(uid):
        await update.message.reply_text(t("exp_type_q", uid), reply_markup=kb(get_expenses(uid), uid=uid)); return EXP_TYPE
    ctx.user_data["exp_type"] = update.message.text
    await update.message.reply_text(t("exp_desc_q", uid), parse_mode="Markdown", reply_markup=kb_skip(uid))
    return EXP_DESC

async def exp_desc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    ctx.user_data["exp_desc"] = "" if is_skip(update.message.text, uid) else update.message.text
    await update.message.reply_text(t("exp_amt_q", uid), reply_markup=kb_cancel(uid))
    return EXP_AMOUNT

async def exp_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        amount = int(update.message.text.replace(" ", ""))
        oid = ctx.user_data["order_id"]
        expense = {"type": ctx.user_data["exp_type"], "desc": ctx.user_data["exp_desc"], "amount": amount, "time": now_t(), "by": sname(uid)}
        o = get_order(oid)
        update_order(oid, {"expenses": o.get("expenses", []) + [expense]})
        total_exp = sum(e["amount"] for e in o.get("expenses", [])) + amount
        msg = t("exp_done", uid, id=oid, type=expense["type"], desc=expense["desc"], amt=fmt(amount), total=fmt(total_exp))
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
        await notify_owner(ctx, msg, uid)
        return ConversationHandler.END
    except:
        await update.message.reply_text(t("enter_num", uid)); return EXP_AMOUNT

# ══════════════════════════════════════════════════════════
# 5. ЗАКРЫТИЕ
# ══════════════════════════════════════════════════════════
async def close_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    orders = open_orders()
    if not orders:
        await update.message.reply_text(t("no_open", uid), reply_markup=kb_main(uid)); return ConversationHandler.END
    ctx.user_data.clear()
    lines = [t("close_title", uid)] + [order_card(o, uid, short=True) for o in orders] + ["\n" + t("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return CLOSE_ORDER

async def close_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o:
            await update.message.reply_text(t("not_found", uid)); return CLOSE_ORDER
        has_debt = any(not dp.get("paid") for dp in o.get("payment", {}).get("debt_parts", []))
        debt_warn = t("close_debt", uid) if has_debt else ""
        update_order(oid, {"status": "closed", "closed_time": now_t(), "closed_by": sname(uid)})
        phone = o.get("phone", "")
        phone_line = t("close_call", uid, phone=phone) if phone else t("close_call2", uid)
        msg = t("close_done", uid, id=oid, car=o["car"], client=o["client"], phone=phone_line, debt=debt_warn)
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
        await notify_owner(ctx, f"🏁 #{oid} closed | {o['car']} | {o['client']} | {sname(uid)}", uid)
        return ConversationHandler.END
    except:
        await update.message.reply_text(t("enter_num", uid)); return CLOSE_ORDER

# ══════════════════════════════════════════════════════════
# 6. ИСТОРИЯ КЛИЕНТА
# ══════════════════════════════════════════════════════════
async def hist_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    ctx.user_data.clear()
    await update.message.reply_text(t("hist_q", uid), reply_markup=kb_cancel(uid))
    return HIST_PHONE

async def hist_show(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    phone = update.message.text.strip()
    history = client_history(phone)
    if not history:
        await update.message.reply_text(t("hist_none", uid, phone=phone), reply_markup=kb_main(uid))
        return ConversationHandler.END
    total = sum(
        o.get("payment", {}).get("uzs", 0) +
        o.get("payment", {}).get("usd_amt", 0) * o.get("payment", {}).get("usd_rate", 1) +
        o.get("payment", {}).get("card", 0) + o.get("payment", {}).get("bank", 0)
        for o in history
    )
    lines = [t("hist_header", uid, name=history[0]["client"], phone=phone, n=len(history), total=fmt(total))]
    for o in history[-5:]:
        lines.append(order_card(o, uid, short=True))
        lines.append("─────────────")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))
    return ConversationHandler.END

# ══════════════════════════════════════════════════════════
# 7. ОТЧЁТ
# ══════════════════════════════════════════════════════════
async def cmd_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        await update.message.reply_text(t("only_owner", uid)); return
    orders = today_orders()
    if not orders:
        await update.message.reply_text(t("rep_none", uid)); return
    t_uzs = t_usd = t_card = t_bank = t_debt = t_exp = t_margin = 0
    for o in orders:
        p = o.get("payment", {})
        t_uzs  += p.get("uzs", 0)
        t_usd  += p.get("usd_amt", 0) * p.get("usd_rate", 1)
        t_card += p.get("card", 0)
        t_bank += p.get("bank", 0)
        t_debt += sum(dp.get("amount_uzs", 0) for dp in p.get("debt_parts", []) if not dp.get("paid"))
        t_exp  += sum(e["amount"] for e in o.get("expenses", []))
        t_margin += sum(pt.get("sell_price", 0) - pt.get("cost_price", 0) for pt in o.get("parts", []))
    received = t_uzs + t_usd + t_card + t_bank
    closed = sum(1 for o in orders if o["status"] == "closed")
    lines = [
        t("rep_title", uid, date=today_d()),
        t("rep_orders", uid, t=len(orders), c=closed, w=len(orders)-closed),
        t("rep_received", uid, v=fmt(received)),
        t("rep_uzs", uid, v=fmt(t_uzs)),
        t("rep_usd", uid, v=fmt(t_usd)),
        t("rep_card", uid, v=fmt(t_card)),
        t("rep_bank", uid, v=fmt(t_bank)),
        t("rep_debt", uid, v=fmt(t_debt)),
        t("rep_exp", uid, v=fmt(t_exp)),
        t("rep_margin", uid, v=fmt(t_margin)),
        t("rep_profit", uid, v=fmt(received - t_exp)),
        t("rep_list", uid),
    ]
    for o in orders:
        lines.append(order_card(o, uid, short=True))
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))

# ══════════════════════════════════════════════════════════
# 8. ДОЛГИ
# ══════════════════════════════════════════════════════════
async def cmd_debts(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        await update.message.reply_text(t("only_owner", uid)); return
    debts = all_debts()
    if not debts:
        await update.message.reply_text(t("debt_none", uid), reply_markup=kb_main(uid)); return
    total = sum(amt for _, amt in debts)
    lines = [t("debt_title", uid, n=len(debts), total=fmt(total))]
    for o, amt in debts:
        lines.append(f"#{o['id']} | {o['car']} | {o['client']}\n  📱 {o['phone']} | 💸 {fmt(amt)} | 📅 {o['date']}")
        lines.append("─────────────")
    lines.append(t("debt_close_cmd", uid))
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))

async def cmd_close_debt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid): return
    args = ctx.args
    if not args:
        await update.message.reply_text("/qarz 5 yoki /долг 5"); return
    try:
        oid = int(args[0])
        o = get_order(oid)
        if not o:
            await update.message.reply_text(t("not_found", uid)); return
        pay = o.get("payment", {})
        changed = any(True for dp in pay.get("debt_parts", []) if not dp.get("paid"))
        for dp in pay.get("debt_parts", []):
            if not dp.get("paid"):
                dp["paid"] = True; dp["paid_time"] = now_t()
        if changed:
            update_order(oid, {"payment": pay})
            await update.message.reply_text(t("debt_closed", uid, id=oid, car=o["car"], client=o["client"]), reply_markup=kb_main(uid))
        else:
            await update.message.reply_text(t("debt_none2", uid))
    except:
        await update.message.reply_text("/qarz 5 yoki /долг 5")

async def cmd_staff(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid): return
    lines = [t("staff_title", uid)] + [f"• {n} — ID: `{sid}`" for sid, n in STAFF.items()]
    lines.append(t("staff_add_fmt", uid))
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))

async def cmd_open_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return
    orders = open_orders()
    if not orders:
        await update.message.reply_text(t("open_none", uid), reply_markup=kb_main(uid)); return
    lines = [t("open_title", uid, n=len(orders))]
    for o in orders:
        lines.append(order_card(o, uid, short=True))
        lines.append("─────────────")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))

# ══════════════════════════════════════════════════════════
# ОТМЕНА И РОУТЕР
# ══════════════════════════════════════════════════════════
async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ctx.user_data.clear()
    await update.message.reply_text(t("cancelled", uid), reply_markup=kb_main(uid))
    return ConversationHandler.END

async def router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    # Выбор языка
    if text == "🇺🇿 O'zbek":
        save_lang(uid, "uz")
        await update.message.reply_text(t("lang_set", uid), parse_mode="Markdown", reply_markup=kb_main(uid)); return
    if text == "🇷🇺 Русский":
        save_lang(uid, "ru")
        await update.message.reply_text(t("lang_set", uid), parse_mode="Markdown", reply_markup=kb_main(uid)); return

    if not is_staff(uid):
        await update.message.reply_text(f"⛔ ID: `{uid}`", parse_mode="Markdown"); return

    # Если язык не выбран — предложить
    if uid not in USER_LANG:
        await update.message.reply_text(t("choose_lang", uid), reply_markup=kb_lang()); return

    if text in [t("btn_open", uid)]:       await cmd_open_orders(update, ctx)
    elif text in [t("btn_report", uid)]:   await cmd_report(update, ctx)
    elif text in [t("btn_debts", uid)]:    await cmd_debts(update, ctx)
    elif text in [t("btn_staff", uid)]:    await cmd_staff(update, ctx)

# ══════════════════════════════════════════════════════════
# ЗАПУСК
# ══════════════════════════════════════════════════════════
def main():
    load_langs()  # Загружаем сохранённые языки
    app = Application.builder().token(TOKEN).build()

    def conv(triggers: list, states, entry_fn):
        pattern = "^(" + "|".join(triggers) + ")$"
        return ConversationHandler(
            entry_points=[MessageHandler(filters.Regex(pattern), entry_fn)],
            states=states,
            fallbacks=[MessageHandler(filters.ALL, cancel)],
        )

    # Приёмка — триггеры на обоих языках
    app.add_handler(conv(
        [T["btn_accept"]["uz"], T["btn_accept"]["ru"]],
        {A_CAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_car)],
         A_CLIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_client)],
         A_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_phone)],
         A_PROBLEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_problem)],
         A_MASTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_master)],
         A_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_service)]},
        accept_start
    ))

    # Запчасть
    app.add_handler(conv(
        [T["btn_part"]["uz"], T["btn_part"]["ru"]],
        {P_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, part_order)],
         P_SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, part_source)],
         P_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, part_name)],
         P_COST: [MessageHandler(filters.TEXT & ~filters.COMMAND, part_cost)],
         P_SELL: [MessageHandler(filters.TEXT & ~filters.COMMAND, part_sell)]},
        part_start
    ))

    # Оплата
    app.add_handler(conv(
        [T["btn_pay"]["uz"], T["btn_pay"]["ru"]],
        {PAY_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_order)],
         PAY_UZS: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_uzs)],
         PAY_HAS_USD: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_has_usd)],
         PAY_USD_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_usd_rate)],
         PAY_USD_AMT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_usd_amt)],
         PAY_HAS_CARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_has_card)],
         PAY_CARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_card)],
         PAY_HAS_BANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_has_bank)],
         PAY_BANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_bank)],
         PAY_HAS_DEBT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_has_debt)],
         PAY_DEBT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_debt)],
         PAY_DISCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_discount)]},
        pay_start
    ))

    # Расходы
    app.add_handler(conv(
        [T["btn_expense"]["uz"], T["btn_expense"]["ru"]],
        {EXP_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_order)],
         EXP_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_type)],
         EXP_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_desc)],
         EXP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_amount)]},
        exp_start
    ))

    # Закрытие
    app.add_handler(conv(
        [T["btn_close"]["uz"], T["btn_close"]["ru"]],
        {CLOSE_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, close_confirm)]},
        close_start
    ))

    # История
    app.add_handler(conv(
        [T["btn_history"]["uz"], T["btn_history"]["ru"]],
        {HIST_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, hist_show)]},
        hist_start
    ))

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("lang", cmd_lang))
    app.add_handler(CommandHandler("добавить", add_staff_cmd))
    app.add_handler(CommandHandler("qoshish", add_staff_cmd))
    app.add_handler(CommandHandler("долг", cmd_close_debt))
    app.add_handler(CommandHandler("qarz", cmd_close_debt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

    print("✅ Avtoservis boti v1.2 ishga tushdi / Запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
