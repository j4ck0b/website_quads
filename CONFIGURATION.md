# Instrukcja Konfiguracji Systemu Rezerwacji (Stripe, Supabase, Google Calendar, SMTP)

Ten dokument opisuje, jak skonfigurować wszystkie integracje w backendzie, aby system rezerwacji działał w pełni automatycznie i bezpiecznie.

---

## 1. Baza Danych Supabase
System obsługuje lokalną bazę SQLite (domyślnie do testów) oraz bazę produkcyjną Supabase (PostgreSQL).

W pliku `backend/.env` ustaw następujące zmienne:
```env
DB_TYPE=supabase
SUPABASE_DB_URL=postgresql://postgres.yourprojectid:yourpassword@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```
*Uwaga: Tabela `bookings` zostanie automatycznie stworzona w bazie Supabase przy pierwszym uruchomieniu serwera (funkcja `init_db()` w `app.py`).*

---

## 2. Bramka Płatności Stripe
Aby obsługiwać płatności za rezerwacje online:

1. Zaloguj się do **Stripe Dashboard**.
2. Pobierz **Secret Key** z zakładki *Developers -> API keys* (zaczyna się od `sk_test_` lub `sk_live_`).
3. Wklej go do pliku `backend/.env`:
   ```env
   STRIPE_SECRET_KEY=sk_test_...
   ```
4. **Webhook Stripe (Potwierdzanie rezerwacji)**:
   * **Produkcyjnie**: W panelu Stripe przejdź do *Developers -> Webhooks*, dodaj nowy endpoint wskazujący na adres Twojego wdrożonego backendu: `https://twoja-domena.com/api/webhook` i wybierz zdarzenie `checkout.session.completed`. Skopiuj wygenerowany klucz podpisu webhooka i dodaj do `.env`:
     ```env
     STRIPE_WEBHOOK_SECRET=whsec_...
     ```
   * **Lokalnie do testów**: Pobierz program **Stripe CLI**, zaloguj się (`stripe login`) i uruchom przekierowanie:
     ```bash
     stripe listen --forward-to localhost:5005/api/webhook
     ```
     Stripe CLI wygeneruje w konsoli tymczasowy klucz `whsec_...`, który wklejasz do `.env`.

---

## 3. Synchronizacja i Zarządzanie z Google Calendar
System pobiera zajętość quadów bezpośrednio z Twojego kalendarza Google, dzięki czemu możesz zarządzać rezerwacjami z poziomu aplikacji kalendarza na telefonie/komputerze.

1. Wejdź na **Google Cloud Console** (https://console.cloud.google.com).
2. Stwórz projekt, włącz **Google Calendar API**.
3. Przejdź do *IAM & Admin -> Service Accounts* i stwórz nowe konto usługowe (Service Account).
4. Wygeneruj dla tego konta klucz w formacie **JSON**, pobierz go i zapisz w folderze `backend` pod nazwą `service-account.json` (plik ten jest automatycznie ignorowany przez `.gitignore` dla bezpieczeństwa).
5. W pliku `backend/.env` dodaj:
   ```env
   GOOGLE_SERVICE_ACCOUNT_FILE=service-account.json
   GOOGLE_CALENDAR_ID=twoj-kalendarz@gmail.com
   ```
6. **Kluczowy krok**: Otwórz swój Google Calendar w przeglądarce, wejdź w ustawienia kalendarza, który chcesz synchronizować, i w sekcji *Share with specific people* dodaj adres e-mail swojego konta usługowego (np. `service-account@project.iam.gserviceaccount.com`) z uprawnieniami **Make changes to events** (Wprowadzanie zmian w wydarzeniach).

### Jak kalendarz steruje wolnymi miejscami:
* Gdy klient opłaci rezerwację, system sam doda wydarzenie: `Teide Quad: Jan Kowalski (1S, 1D)` na odpowiednią godzinę (13:00 lub 18:30).
* Możesz ręcznie przesuwać to wydarzenie (drag & drop) lub je usunąć – strona automatycznie zwolni ten termin.
* Możesz ręcznie utworzyć wydarzenie blokujące (np. wpisując słowo `block`, `blokada`, `close` lub `private`) – system rozpozna to i odejmie odpowiednią liczbę miejsc. Jeśli nie wpiszesz liczby miejsc w tytule blokady (np. sam wpis "Prywatna grupa"), system zablokuje całą wycieczkę (4 quady).

---

## 4. Powiadomienia E-mail (SMTP)
Aby klient oraz właściciel otrzymywali e-maile z potwierdzeniem oraz plikiem kalendarza `.ics`:

Wypełnij poniższe zmienne w `backend/.env`:
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=twoj-email@gmail.com
SMTP_PASSWORD=twoje-haslo-aplikacji
BUSINESS_OWNER_EMAIL=twoj-email-do-odbioru-powiadomien@gmail.com
```
*Uwaga: W przypadku Gmaila, hasło musi być wygenerowane jako "Hasło aplikacji" w ustawieniach konta Google (dwuetapowa weryfikacja).*

---

## 5. Uruchomienie Serwera Backend
Aby uruchomić backend lokalnie, przejdź do folderu `backend` i wpisz:
```bash
python3 app.py
```
Backend będzie nasłuchiwał na porcie `5005` (zgodnie z konfiguracją w `js/main.js`).
