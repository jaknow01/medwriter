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
