# TODO — Zarządzanie kontekstem konwersacji

## Problem 1: Mieszanie konwersacji w agent memory

### Opis
Każdy Worker ma własną instancję `MedicalArticleAgent` (w `src/worker/agent.py`). Agent używa LlamaIndex `ReActAgent`, który utrzymuje wewnętrzny memory (stan między wywołaniami `run()`). Worker obsługuje joby z **różnych konwersacji** po kolei — np. konwersację A, potem B, potem znowu A. Agent memory **nie jest czyszczony między jobami**, więc przy przetwarzaniu konwersacji B agent "pamięta" wymianę z konwersacji A.

### Dotknięte pliki
- `src/worker/worker.py` — `process_query_with_context()` wywołuje `self.agent.chat(full_query)` bez czyszczenia memory
- `src/worker/agent.py` — `MedicalArticleAgent.chat()` dodaje każdą wiadomość do `self.chat_history` (linia 137-149), a `ReActAgent` kumuluje stan wewnętrznie

### Skutek
Agent przy przetwarzaniu konwersacji B ma w memory wiadomości z konwersacji A. Może to powodować halucynacje, kontaminację odpowiedzi między konwersacjami, i nieoczekiwane zachowanie.

---

## Problem 2: Podwójna historia konwersacji

### Opis
Historia tej samej konwersacji trafia do agenta **dwoma kanałami jednocześnie**:

1. **Jako tekst w `full_query`** — `Worker._build_context()` (linia 263 w worker.py) pobiera **wszystkie** wiadomości z Postgres i skleja je w string:
   ```
   Previous conversation:
   User: pierwsza wiadomość
   AI: pierwsza odpowiedź
   ...
   User: {aktualne query}
   ```
   Ten string idzie jako argument do `agent.chat(full_query)`.

2. **W agent memory** — `ReActAgent` automatycznie dodaje każde wywołanie `run()` do swojego wewnętrznego stanu. Więc po 5 wiadomościach w konwersacji A, agent ma w memory 5 poprzednich "rozmów" (z których każda zawierała rosnący `_build_context`).

### Skutek
Przy N-tej wiadomości w konwersacji:
- `full_query` zawiera N-1 poprzednich wiadomości jako tekst
- Agent memory zawiera N-1 poprzednich wywołań (każde z rosnącym kontekstem)
- Efektywnie historia jest zduplikowana i rośnie kwadratowo
- Łatwo o przekroczenie limitu tokenów modelu

---

## Problem 3: Brak limitu na kontekst z bazy

### Opis
`Worker._build_context()` pobiera **wszystkie** wiadomości z Postgres bez żadnego limitu. Przy długich konwersacjach (20+ wiadomości) sam kontekst może zająć więcej tokenów niż okno kontekstowe modelu.

### Dotknięte pliki
- `src/worker/worker.py` — `_build_context()` (linia 263), `process_query_with_context()` (linia 224: `messages = await repo.get_messages(conv_id)` — bierze wszystko)
- `src/database/repository.py` — `get_messages()` prawdopodobnie nie ma limitu

---

## Rozwiązanie: Opcja A — Postgres jako jedyne źródło historii

### Zasada
Agent memory powinien być **resetowany przed każdym jobem**. Jedynym źródłem historii konwersacji jest baza Postgres, podawana przez `_build_context()`. To daje pełną kontrolę nad tym co i ile kontekstu trafia do agenta.

### Kroki implementacji

#### Krok 1: Reset agent memory przed każdym jobem
- W `src/worker/worker.py`, w `process_query_with_context()`, **przed** wywołaniem `agent.chat()`:
  - Wywołać `self.agent.reset_chat_history()` (metoda już istnieje w agent.py linia 198)
  - Sprawdzić czy ReActAgent z LlamaIndex ma osobny wewnętrzny memory do zresetowania (może wymagać `self.agent.agent.memory.reset()` lub podobnego)
- Efekt: agent zawsze zaczyna z czystym stanem, historia bierze się wyłącznie z `_build_context()`

#### Krok 2: Limit wiadomości w `_build_context()`
- Dodać parametr `max_messages` do `_build_context()` (np. domyślnie 20 — ostatnich 10 par user+AI)
- Ewentualnie dodać `context_max_messages` do `src/config/settings.py`
- Pobierać tylko ostatnie N wiadomości z Postgres (zmodyfikować query w `get_messages()` lub ciąć w `_build_context()`)

#### Krok 3 (opcjonalny, przyszłość): Summarization starszych wiadomości
- Przy konwersacjach dłuższych niż N wiadomości: streszczać starsze wiadomości jednym wywołaniem LLM
- Zapisywać streszczenie w Postgres (np. pole `summary` w tabeli `Conversation`)
- Nowy kontekst = streszczenie + ostatnie N wiadomości
- Wymaga dodatkowego wywołania LLM, ale zachowuje kluczowe informacje z początku konwersacji

### Pliki do modyfikacji
| Plik | Zmiana |
|------|--------|
| `src/worker/worker.py` | Reset agent memory w `process_query_with_context()`, limit w `_build_context()` |
| `src/worker/agent.py` | Upewnić się że `reset_chat_history()` czyści też ReActAgent memory |
| `src/config/settings.py` | Nowy parametr `context_max_messages` |
| `src/database/repository.py` | Opcjonalnie: limit w `get_messages()` |

### Weryfikacja
1. Uruchomić dwa joby z różnych konwersacji na tym samym workerze — odpowiedź z drugiej konwersacji nie powinna zawierać informacji z pierwszej
2. Przetestować długą konwersację (>20 wiadomości) — agent powinien widzieć tylko ostatnie N wiadomości + zachowywać się poprawnie
3. Sprawdzić rozmiar `full_query` w logach — nie powinien rosnąć bez limitu

---

## Problem 4: Artykuły eksplodują rozmiar kontekstu

### Opis
Agent generuje artykuły o długości 800-1500 słów (wymóg w system prompcie, `src/worker/agent.py` linia 46). Nawet ze sliding window np. 5 par wiadomości, jeśli 3 z nich to artykuły, kontekst ma 3000-4500 słów (~4000-6000 tokenów) samej historii — zanim jeszcze dojdzie aktualne query, kontekst PDF, i system prompt.

Zwykłe wiadomości (dopytywanie, odpowiadanie na pytania) to 1-3 zdania. Artykuły to 50-100x więcej. Traktowanie ich jednakowo w historii jest nieefektywne — agent nie potrzebuje pełnego tekstu poprzedniego artykułu żeby kontynuować rozmowę.

### Rozwiązanie: Typowanie wiadomości + streszczenia artykułów

#### Koncept
Odpowiedzi agenta dzielą się na dwa typy:
- **SimpleAnswer** — zwykła wymiana: dopytywanie o szczegóły, odpowiadanie na pytania, wyjaśnienia. Krótkie, trafiają do historii w pełni.
- **Article** — wygenerowany artykuł. Długi, w historii zastępowany streszczeniem.

#### Zmiany w bazie danych

**Tabela `Message`** (`src/database/models.py`) — dodać dwa pola:
- `message_type: str` — `"simple"` lub `"article"` (domyślnie `"simple"`). Dotyczy tylko wiadomości z role=AI, wiadomości usera są zawsze "simple".
- `summary: str | None` — streszczenie artykułu (null dla SimpleAnswer i wiadomości usera)

Pełna treść artykułu zawsze zostaje w `content` (user widzi go w UI). Pole `summary` to wersja do użytku w historii kontekstu.

Wymaga migracji bazy (Alembic lub ręczny ALTER TABLE).

#### Klasyfikacja i streszczanie odpowiedzi

Po wygenerowaniu odpowiedzi przez agenta, worker:
1. **Klasyfikuje** typ odpowiedzi — heurystycznie (np. długość > 500 słów, zawiera nagłówki/sekcje, zawiera referencje `[1]`, `[2]`...) lub przez szybkie wywołanie tańszego modelu
2. Jeśli typ = **Article**: generuje streszczenie (1-3 zdania) przez tańszy model (gpt-4o-mini, ten sam co `TitleGenerator` w `src/worker/title_generator.py`)
3. Zapisuje w Postgres: `content=pełny artykuł`, `message_type="article"`, `summary="Streszczenie..."`

#### Budowanie kontekstu z uwzględnieniem typów

`_build_context()` zmienia logikę:
- Dla wiadomości z `message_type="simple"` → używa `content` (pełna treść)
- Dla wiadomości z `message_type="article"` → używa `summary` zamiast `content`
- Wyjątek: **ostatni artykuł** w oknie może być w pełni (jeśli user do niego nawiązuje), albo też streszczony — do ustalenia

Przykładowy kontekst po 6 wiadomościach (3 pary):
```
Previous conversation:
User: Napisz artykuł o leczeniu cukrzycy typu 2
AI: [Artykuł] Wygenerowano artykuł o leczeniu cukrzycy typu 2 (1200 słów). Główne wątki: metformina jako pierwsza linia, modyfikacja diety, aktywność fizyczna. Źródła: 5 publikacji PubMed.
User: Dodaj sekcję o insulinoterapii
AI: [Artykuł] Zaktualizowano artykuł — dodano sekcję o insulinoterapii (1400 słów). Nowe wątki: wskazania do insuliny, typy insulin, schematy dawkowania.
User: Jakie są najnowsze badania o GLP-1?
```
Zamiast 2800 słów artykułów w historii — ~100 słów streszczeń.

#### Pliki do modyfikacji

| Plik | Zmiana |
|------|--------|
| `src/database/models.py` | Dodać pola `message_type` i `summary` do modelu `Message` |
| `src/api/schemas.py` | Zaktualizować `MessageResponse` o nowe pola |
| `src/worker/worker.py` | Po `agent.chat()`: klasyfikacja typu, generowanie streszczenia, zapis z nowym typem |
| `src/worker/worker.py` | `_build_context()`: logika wyboru `content` vs `summary` |
| `src/worker/title_generator.py` | Rozszerzyć lub stworzyć analogiczny `ArticleSummarizer` (może reużyć ten sam tańszy model) |
| `src/config/settings.py` | Parametry: `article_length_threshold`, `summary_model_name` |
| Migracja DB | ALTER TABLE messages ADD COLUMN message_type, ADD COLUMN summary |

#### Kolejność implementacji
1. Najpierw Krok 1-2 z sekcji "Rozwiązanie: Opcja A" (reset memory + sliding window) — eliminuje podwójną historię i mieszanie konwersacji
2. Potem typowanie wiadomości + streszczenia — optymalizuje rozmiar kontekstu przy dłuższych konwersacjach
3. Na końcu ewentualny summarization całej konwersacji (Krok 3 z Opcji A) — tylko jeśli potrzebny po wdrożeniu punktu 2
