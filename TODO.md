# Upload PDF — pozostałe etapy

Etapy 1-3 (zależności, moduł PDF, konfiguracja) ukończone.

## Etap 4: Endpoint API — wysyłanie wiadomości z plikami

Plik: `src/api/routes/messages.py`

Zmiana `send_message` z JSON body na `multipart/form-data`:
- `content: str = Form(...)`, `files: list[UploadFile] = File(default=[])`
- Walidacja: każdy plik musi być PDF, limit rozmiaru 10MB
- Przetwarzanie w API: dla każdego pliku `PDFProcessor.process_pdf(bytes)` → chunki
- Chunki przekazane do `job_queue.create_job()` jako JSON w Redis

## Etap 5: Job queue — obsługa chunków PDF

Plik: `src/redis/job_queue.py`

Dodanie opcjonalnego `pdf_chunks: list[dict] | None` do `create_job()`.
Każdy chunk to `{"text": str, "filename": str}`.

## Etap 6: Worker — indeksowanie chunków i wstrzykiwanie kontekstu

Pliki: `src/worker/worker.py`, `src/worker/poll.py`

- Worker inicjalizuje `DocumentStore` w `initialize()`
- Nowa metoda `_index_pdf_chunks()` — zapisuje chunki do ChromaDB
- Nowa metoda `_get_pdf_context()` — hybrid query (BM25+vector), formatowanie
- W `process_query_with_context()`: jeśli `pdf_chunks` → indeksuj, pobierz kontekst, dołącz do full_query
- W `poll.py`: wyciągnij `pdf_chunks` z job_data, przekaż dalej

## Etap 7: Cleanup przy usuwaniu rozmowy

Pliki: `src/api/routes/conversations.py`, `src/api/dependencies.py`, `src/api/main.py`

- `DocumentStore` jako globalna dependency (jak db_manager, redis_manager)
- Init w lifespan `main.py`
- W `delete_conversation()`: `document_store.delete_by_conv_id(conv_id)`

## Etap 8: Frontend — input pliku

Pliki: `src/ui/chat.html`, `src/ui/static/js/api.js`

- Ukryty `<input type="file" accept=".pdf" multiple>` z przyciskiem 📎
- Wyświetlanie nazw wybranych plików
- `sendMessage()` zmieniony na `FormData` z obsługą wielu plików
- Czyszczenie file input po wysłaniu

## Etap 9: Docker Compose

Plik: `docker-compose.yml`

- Nowy volume `chromadb_data`
- Montowanie w serwisach `api` i `worker` pod `/app/data/chromadb`
- Env `CHROMADB_DIR=/app/data/chromadb` w obu serwisach
