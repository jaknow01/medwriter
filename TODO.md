## TODO

### 1. Streszczanie artykułów a interakcja użytkownika

Jeśli najnowszy wygenerowany artykuł jest streszczany i podawany do pamięci modelu jako streszczenie, użytkownik może mieć problem z wchodzeniem z nim w interakcję — zadawaniem pytań doprecyzowujących, zmianą konkretnych fragmentów itp. Model nie "widzi" wtedy pełnej treści artykułu, tylko jego skrót.

**Proponowane rozwiązanie:** nie streszczać ostatniego artykułu w rozmowie — tylko te starsze. Przy budowaniu `chat_history` w `_build_chat_history()` najnowsza wiadomość typu `article` powinna być przekazywana w pełnej treści, a streszczenia stosowane wyłącznie do wcześniejszych artykułów.

---

### 2. Format zwracanych artykułów — HTML

Obecnie artykuły są zwracane jako plaintext. Docelowo agent (lub osobne wywołanie LLM po wygenerowaniu artykułu) powinien zwracać artykuł w postaci HTML, gotowego do wklejenia na stronę internetową firmy.

**Zmiany backendowe:**
- System prompt lub post-processing generujący HTML z treści artykułu
- Kolumna `content` dla wiadomości typu `article` przechowuje HTML

**Zmiany frontendowe:**
- Wiadomości typu `simple` renderowane jak dotychczas (plaintext/markdown)
- Wiadomości typu `article` renderowane jako HTML (`innerHTML`) — podgląd artykułu tak jak wyglądałby na stronie
- Przyciski przy artykule:
  - "Kopiuj HTML" — kopiuje surowy kod HTML do schowka
  - "Kopiuj tekst" — kopiuje treść bez tagów
