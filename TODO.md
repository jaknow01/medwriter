# TODO — Zarządzanie kontekstem konwersacji

## Aktualny stan: jak historia trafia do modelu

Są trzy mechanizmy które wyglądają jak zarządzanie historią, ale tylko jeden faktycznie działa:

1. **`_build_context()` + `full_query`** (worker.py:224-249) — **JEDYNY aktywny kanał.** Pobiera wszystkie wiadomości z Postgres, skleja w string, dopisuje aktualne query i wysyła jako `user_msg` do `agent.run()`. Model dostaje jeden duży blok tekstu z rolą `user`.

2. **Wewnętrzny memory `ReActAgent`** — **NIE kumuluje się.** Każde wywołanie `agent.run(user_msg=...)` tworzy nowy kontekst workflow. Pamięć nie jest przekazywana między wywołaniami (brak parametru `memory` lub `chat_history` w `.run()`). Nie ma ryzyka mieszania konwersacji ani narastania stanu.

3. **`self.chat_history`** w `MedicalArticleAgent` (agent.py:119) — **Martwy kod.** Lista jest modyfikowana w `chat()` (linia 137-149), ale nigdy nie jest przekazywana do `agent.run()` ani odczytywana przez żaden inny komponent.

### Sekwencja zdarzeń przy obsłudze wiadomości (flow z API)

1. API zapisuje wiadomość usera do Postgres (messages.py:137)
2. API tworzy job w Redis
3. Worker pobiera job, wywołuje `process_query_with_context(save_user_message=False)`
4. Worker robi `get_messages(conv_id)` — pobiera **wszystkie** wiadomości, **łącznie z aktualną** (bo API już ją zapisało)
5. `_build_context()` skleja je w string: `"Previous conversation:\nUser: ...\nAI: ...\nUser: aktualne query"`
6. Linia 242: `full_query = f"{context}\n\nUser: {query}"` — dopisuje aktualne query na końcu
7. `agent.chat(full_query)` → `agent.run(user_msg=full_query)` — model dostaje jeden string

**Efekt:** Ostatnia wiadomość usera pojawia się w stringu dwa razy — raz na końcu kontekstu z bazy, raz dopisana w linii 242. Reszta historii nie jest zdublowana.

---

## Problem 1: Brak limitu na kontekst z bazy

### Opis
`_build_context()` pobiera **wszystkie** wiadomości z Postgres bez żadnego limitu. Przy długich konwersacjach (20+ wiadomości) sam kontekst może zająć więcej tokenów niż okno kontekstowe modelu.

### Dotknięte pliki
- `src/worker/worker.py` — `_build_context()` (linia 263), `process_query_with_context()` (linia 224: `get_messages(conv_id)` — bierze wszystko)
- `src/database/repository.py` — `get_messages()` nie ma limitu

---

## Problem 2: Historia jako text blob zamiast structured messages

### Opis
Cała historia konwersacji trafia do modelu jako jeden string wewnątrz jednej wiadomości z rolą `user`. Model nie widzi właściwej struktury konwersacji (ról user/assistant jako osobnych wiadomości).

LLM-y są trenowane na rozróżnianiu ról w konwersacji. Wiadomość z `role=assistant` jest traktowana jako "to powiedziałem ja" — model lepiej utrzymuje spójność i styl. Tekst "AI: odpowiedź" w bloku usera to dla modelu cytat, nie jego własna pamięć.

`ReActAgent.run()` akceptuje parametr `chat_history` — listę `ChatMessage` z właściwymi rolami. Ten mechanizm nie jest wykorzystywany.

### Dotknięte pliki
- `src/worker/worker.py` — `_build_context()` buduje string zamiast listy `ChatMessage`
- `src/worker/agent.py` — `chat()` przekazuje string do `agent.run(user_msg=...)` zamiast używać `chat_history`

---

## Problem 3: Dublowanie ostatniej wiadomości usera

### Opis
API zapisuje wiadomość usera do Postgres **przed** utworzeniem joba. Worker pobiera wszystkie wiadomości (łącznie z aktualną) i buduje kontekst. Potem w linii 242 dopisuje aktualne query na końcu: `full_query = f"{context}\n\nUser: {query}"`. Ostatnia wiadomość usera pojawia się dwa razy.

### Dotknięte pliki
- `src/worker/worker.py` — linia 224 (pobiera wszystko) + linia 242 (dopisuje query)

---

## Problem 4: Martwy kod `self.chat_history`

### Opis
`MedicalArticleAgent.chat_history` (agent.py:119) jest listą `ChatMessage` modyfikowaną przy każdym `chat()` (linia 137-149), ale nigdy nie jest:
- przekazywana do `agent.run()`
- odczytywana przez żaden inny komponent (poza `get_chat_history()` które też nie jest wywoływane)

### Dotknięte pliki
- `src/worker/agent.py` — `self.chat_history`, `chat()`, `stream_chat()`, `reset_chat_history()`, `get_chat_history()`

---

## Problem 5: Artykuły eksplodują rozmiar kontekstu

### Opis
Agent generuje artykuły o długości 800-1500 słów (wymóg w system prompcie, agent.py linia 46). Przy sliding window np. 5 par wiadomości, jeśli 3 z nich to artykuły, kontekst ma 3000-4500 słów (~4000-6000 tokenów) samej historii — zanim jeszcze dojdzie aktualne query, kontekst PDF i system prompt.

Zwykłe wiadomości (dopytywanie, odpowiadanie na pytania) to 1-3 zdania. Artykuły to 50-100x więcej. Traktowanie ich jednakowo w historii jest nieefektywne.

---

## Rozwiązanie

### Kolejność implementacji
1. Najpierw Problemy 1-4 (limit, structured messages, deduplikacja, cleanup martwego kodu)
2. Potem Problem 5 (typowanie wiadomości + streszczenia artykułów)

### Krok 1: Structured messages + limit + cleanup

**Zasada:** Zamiast budować string z historii, budować listę `ChatMessage` z Postgres i przekazywać ją przez parametr `chat_history` do `agent.run()`. Usunąć martwy kod.

#### Zmiany:
- **`src/worker/worker.py`**:
  - `_build_context()` → zastąpić metodą budującą `list[ChatMessage]` z ostatnich N wiadomości z Postgres (bez aktualnej wiadomości usera — ta idzie jako `user_msg`)
  - `process_query_with_context()` → przekazywać `chat_history` do `agent.chat()`, a `agent.chat()` przekazuje do `agent.run(user_msg=query, chat_history=chat_history)`
  - Usunąć ręczne sklejanie `full_query`
- **`src/worker/agent.py`**:
  - `chat()` → przyjmować `chat_history` jako parametr, przekazywać do `self.agent.run(user_msg=message, chat_history=chat_history)`
  - Usunąć `self.chat_history`, `reset_chat_history()`, `get_chat_history()` — martwy kod
  - `stream_chat()` → analogicznie
- **`src/config/settings.py`** — nowy parametr `context_max_messages` (domyślnie 20)
- **`src/database/repository.py`** — opcjonalnie: limit w `get_messages()` lub przycinanie w workerze

#### Obsługa kontekstu PDF
Kontekst PDF nadal dorzucać jako osobną wiadomość `user` lub `system` przed historią konwersacji.

### Krok 2: Typowanie wiadomości + streszczenia artykułów

#### Koncept
Odpowiedzi agenta dzielą się na dwa typy:
- **SimpleAnswer** — zwykła wymiana: dopytywanie, odpowiadanie na pytania. Krótkie, trafiają do historii w pełni.
- **Article** — wygenerowany artykuł. Długi, w historii zastępowany streszczeniem.

#### Zmiany w bazie danych

**Tabela `Message`** (`src/database/models.py`) — dodać dwa pola:
- `message_type: str` — `"simple"` lub `"article"` (domyślnie `"simple"`). Dotyczy tylko wiadomości z role=AI.
- `summary: str | None` — streszczenie artykułu (null dla SimpleAnswer i wiadomości usera)

Pełna treść artykułu zostaje w `content` (user widzi go w UI). Pole `summary` to wersja do użytku w historii kontekstu. Wymaga migracji bazy (Alembic lub ręczny ALTER TABLE).

#### Klasyfikacja i streszczanie odpowiedzi

Po wygenerowaniu odpowiedzi przez agenta, worker:
1. **Klasyfikuje** typ odpowiedzi — heurystycznie (np. długość > 500 słów, zawiera nagłówki/sekcje, zawiera referencje `[1]`, `[2]`...)
2. Jeśli typ = **Article**: generuje streszczenie (1-3 zdania) przez tańszy model (gpt-4o-mini, analogicznie do `TitleGenerator`)
3. Zapisuje w Postgres: `content=pełny artykuł`, `message_type="article"`, `summary="Streszczenie..."`

#### Budowanie historii z uwzględnieniem typów

Przy budowaniu `list[ChatMessage]`:
- Dla `message_type="simple"` → używa `content`
- Dla `message_type="article"` → używa `summary` zamiast `content`

#### Pliki do modyfikacji

| Plik | Zmiana |
|------|--------|
| `src/database/models.py` | Dodać pola `message_type` i `summary` do modelu `Message` |
| `src/api/schemas.py` | Zaktualizować `MessageResponse` o nowe pola |
| `src/worker/worker.py` | Po `agent.chat()`: klasyfikacja typu, generowanie streszczenia, zapis z nowym typem |
| `src/worker/worker.py` | Budowanie `ChatMessage` list: logika wyboru `content` vs `summary` |
| `src/worker/title_generator.py` | Rozszerzyć lub stworzyć analogiczny `ArticleSummarizer` |
| `src/config/settings.py` | Parametry: `article_length_threshold`, `summary_model_name` |
| Migracja DB | ALTER TABLE messages ADD COLUMN message_type, ADD COLUMN summary |

### Krok 3 (opcjonalny, przyszłość): Summarization starszych wiadomości
- Przy konwersacjach dłuższych niż N wiadomości: streszczać starsze wiadomości jednym wywołaniem LLM
- Zapisywać streszczenie w Postgres (np. pole `summary` w tabeli `Conversation`)
- Nowy kontekst = streszczenie + ostatnie N wiadomości

---

## Weryfikacja
1. Sprawdzić że model dostaje właściwe `ChatMessage` z rolami (logować zawartość `chat_history` przed `agent.run()`)
2. Przetestować długą konwersację (>20 wiadomości) — agent powinien widzieć tylko ostatnie N wiadomości
3. Sprawdzić że ostatnia wiadomość usera nie jest zdublowana
4. Upewnić się że martwy kod (`self.chat_history` w agent.py) został usunięty
