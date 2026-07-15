# Macro Radar Kazakhstan

Личный Streamlit-инструмент для сбора макроэкономических данных Казахстана,
просмотра истории и формирования Excel/PowerPoint.

## Что умеет

- получает USD/KZT из официального RSS НБРК;
- получает базовую ставку и TONIA из НБРК либо из явного ручного fallback;
- получает инфляцию и компоненты из публикации БНС;
- получает последнюю цену Brent;
- проверяет допустимые диапазоны;
- сохраняет историю без дублей в Supabase;
- при сбое показывает последние успешные значения и предупреждение об устаревании;
- сравнивает с предыдущим наблюдением, неделей и месяцем;
- формирует Excel и PowerPoint по запросу;
- обновляется вручную или по расписанию GitHub Actions.

## 1. Создание Supabase

1. Создайте проект в Supabase.
2. Откройте `SQL Editor`.
3. Выполните [supabase/schema.sql](supabase/schema.sql).
4. В `Project Settings → API` скопируйте Project URL и service role key.

Service role key используется только серверной частью. Не добавляйте его в Git.
RLS включён, а публичные политики намеренно не созданы.

## 2. Локальный запуск

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
streamlit run app.py
```

Заполните `.streamlit/secrets.toml` своими значениями Supabase.

## 3. Миграция переданной истории

После создания таблиц и настройки переменных:

```powershell
python scripts/migrate_legacy.py
```

Скрипт переносит поддерживаемые ряды из `storage/macro_database.xlsx` и
`storage/macro_history.csv`. Исторические записи маркируются `warning`, потому
что их происхождение и качество автоматически подтвердить нельзя.

## 4. Streamlit Community Cloud

1. Загрузите проект в приватный GitHub-репозиторий.
2. Создайте приложение на `share.streamlit.io`.
3. Выберите `app.py` как entrypoint.
4. Добавьте в Secrets:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
```

5. Ограничьте доступ к приложению нужными email.

## 5. Плановое обновление

В GitHub `Settings → Secrets and variables → Actions` создайте:

- `SUPABASE_URL`;
- `SUPABASE_SERVICE_ROLE_KEY`;
- опционально `MANUAL_BASE_RATE` и `MANUAL_TONIA_RATE` как аварийный fallback.

Workflow `.github/workflows/update-data.yml` запускается по рабочим дням в
08:30 Asia/Qyzylorda и также поддерживает ручной запуск.

### Примечание по ставкам НБРК

Публичный RSS курса работает без авторизации. Репозиторий открытых данных НБРК
публикует базовую ставку и TONIA, но его endpoint данных требует авторизацию, а
главная страница рендерится динамически. Поэтому валютный курс и ставки сделаны
разными коннекторами: ошибка ставки не блокирует сохранение USD/KZT.

До подключения авторизованного API можно задать `MANUAL_BASE_RATE` и
`MANUAL_TONIA_RATE` в Streamlit/GitHub Secrets. Если значения не заданы и
автоматический парсер недоступен, запуск будет `partial`, а dashboard покажет
последние успешно сохранённые ставки.

## Корпоративный PowerPoint

Если есть настоящий шаблон, положите его в:

```text
templates/macro_template.pptx
```

Если шаблона нет, приложение создаст стандартную презентацию.

## Проверка

```powershell
pytest
```

Сетевые источники специально изолированы в `macro_radar/sources`, поэтому их
можно менять без переделки базы, dashboard и генератора отчётов.
