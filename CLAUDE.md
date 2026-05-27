# KG Silkroad Inc. — Claude Code Instructions

## ⚡ ПЕРВЫМ ДЕЛОМ
Прочитай PROJECT_IDEA.md — там весь контекст бизнеса.
Следуй Spec-First методологии и Security Review правилам.

## 🏢 О проекте
Wholesale дистрибьютор витаминов, пептидов и спортпита из США/Европы в СНГ.
Сайт: статичный HTML/CSS/JS + Cloudflare Worker (AI ассистент).
GitHub: contact01-ship-it/kgsilkroad-website
Дизайн: тёмно-зелёный (#14281E) + золотой (#C4973A). Всегда двуязычный RU/EN.

## 📋 SPEC-FIRST ПРАВИЛА (обязательно)
1. Никогда не пиши код без плана — сначала опиши что будешь делать
2. Перед каждой фичей: user story → данные → логика → UI → edge cases
3. CLAUDE.md ≤ 120 строк — детали в PROJECT_IDEA.md
4. Конкретика вместо абстракций: числа, поля, эндпоинты

## 🔒 SECURITY ПРАВИЛА (перед каждым деплоем)
1. API ключи ТОЛЬКО в переменных окружения, никогда в коде
2. Cloudflare Worker API key — только на сервере, не в JS клиента
3. Валидация всех форм (WhatsApp форма, контакт форма)
4. XSS защита — экранировать весь пользовательский контент
5. Security headers: X-Frame-Options, CSP, X-Content-Type-Options
6. Rate limiting на формах заказа (макс 5 запросов/мин)
7. Перед деплоем запускать: /security-review

## 🚚 Логистика (цены за кг, всё включено с таможней)
- 🇰🇬 Кыргызстан: $12/кг, 2 недели
- 🇰🇿 Казахстан: $12/кг, 2 недели
- 🇺🇿 Узбекистан: $13/кг, 2 недели
- 🇷🇺 Россия: $20/кг, 3 недели
- Срок отсчитывается с момента получения от производителя
- Возможны небольшие доп. таможенные сборы

## 💊 Поставщик пептидов
Simple Peptide Wholesale (Charlie Rutherford, Dallas TX)
MOQ: 20 штук всего, минимум 5 на SKU
Варианты: naked bottles / generic label / private label
Отгрузка из США: 1-2 дня после заказа

## 🛠 gstack скиллы
Use /browse from gstack for all web browsing.
Available: /office-hours, /plan-ceo-review, /plan-eng-review,
/review, /ship, /qa, /retro, /investigate, /careful, /freeze, /guard,
/gstack-upgrade, /learn, /security-review

## ✅ Чеклист перед деплоем
- [ ] Запустить /security-review
- [ ] Нет API ключей в клиентском коде
- [ ] Все формы валидируются
- [ ] Двуязычность RU/EN проверена
- [ ] Мобильная версия проверена
