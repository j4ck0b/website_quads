import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
import pytz
from icalendar import Calendar, Event

# Load email environment configurations
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT", "587")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
BUSINESS_OWNER_EMAIL = os.getenv("BUSINESS_OWNER_EMAIL")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)
REPLY_TO = os.getenv("REPLY_TO", "info@primequads.com")

def generate_ics_content(booking, lang="en"):
    """
    Generates an iCalendar (.ics) file content as bytes for a booking.
    The Teide Quad Expedition lasts for 3.5 hours.
    """
    cal = Calendar()
    cal.add('prodid', '-//Prime Quads Tenerife Booking System//EN')
    cal.add('version', '2.0')

    event = Event()
    
    # Localized Summary
    summary_dict = {
        "en": "Teide National Park Quad Expedition",
        "pl": "Wycieczka Quadami - Park Narodowy Teide",
        "es": "Expedición en Quad al Teide - Parque Nacional"
    }
    summary = summary_dict.get(lang, summary_dict["en"])
    event.add('summary', summary)
    
    # Parse date and time
    dt_str = f"{booking['date']} {booking['time']}"
    naive_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    
    # Tenerife is in Europe/London or Atlantic/Canary timezone
    tz = pytz.timezone('Atlantic/Canary')
    start_dt = tz.localize(naive_dt)
    end_dt = start_dt + timedelta(hours=3, minutes=30)  # 3.5 hours duration
    
    event.add('dtstart', start_dt)
    event.add('dtend', end_dt)
    event.add('dtstamp', datetime.now(pytz.utc))
    
    # Localized Descriptions
    if lang == "pl":
        description = (
            f"Dziękujemy za rezerwację z Prime Quads Tenerife!\n\n"
            f"ID Rezerwacji: {booking['id']}\n"
            f"Klient: {booking['name']}\n"
            f"Telefon: {booking['phone']}\n"
            f"Quady jednoosobowe: {booking['single_quads']}\n"
            f"Quady dwuosobowe: {booking['double_quads']}\n"
            f"Suma opłacona: €{booking['total_price']}\n\n"
            f"Prosimy o przybycie 30 minut przed rozpoczęciem wycieczki. Nie zapomnij fizycznego prawa jazdy kategorii B (wymagany oryginalny dokument)!"
        )
    elif lang == "es":
        description = (
            f"¡Gracias por reservar con Prime Quads Tenerife!\n\n"
            f"ID de Reserva: {booking['id']}\n"
            f"Cliente: {booking['name']}\n"
            f"Teléfono: {booking['phone']}\n"
            f"Quads individuales: {booking['single_quads']}\n"
            f"Quads dobles: {booking['double_quads']}\n"
            f"Total pagado: €{booking['total_price']}\n\n"
            f"Por favor, llegue 30 minutos antes del inicio del tour. ¡No olvide su licencia de conducir B (es obligatorio presentarla físicamente)!"
        )
    else:
        description = (
            f"Thank you for booking with Prime Quads Tenerife!\n\n"
            f"Booking ID: {booking['id']}\n"
            f"Customer: {booking['name']}\n"
            f"Phone: {booking['phone']}\n"
            f"Single Quads: {booking['single_quads']}\n"
            f"Double Quads: {booking['double_quads']}\n"
            f"Total Paid: €{booking['total_price']}\n\n"
            f"Please arrive 30 minutes before the tour starts. Don't forget your B driver's license (physical copy mandatory)!"
        )
        
    event.add('description', description)
    event.add('location', 'Extreme Prime Tours SL, Las Américas, Tenerife')
    event.add('uid', f"booking-{booking['id']}@primequads.com")
    
    cal.add_component(event)
    return cal.to_ical()
 
def send_booking_emails(booking):
    """
    Sends email confirmation with an attached .ics file to:
    1. The client (thanking them and providing event details in their chosen language)
    2. The business owner (notifying them of the new booking)
    """
    # Verify SMTP configuration
    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD]):
        print("[WARNING] SMTP settings are incomplete in .env. Skipping email sending.")
        print(f"[SANDBOX EMAIL LOG] Booking confirmed for {booking['name']} ({booking['email']}) on {booking['date']} at {booking['time']}")
        return False
        
    lang = booking.get("lang", "en")
    ics_bytes = generate_ics_content(booking, lang=lang)
    
    # 1. Send email to Client
    try:
        msg_client = MIMEMultipart('mixed')
        msg_client['From'] = EMAIL_FROM
        msg_client['To'] = booking['email']
        msg_client['Reply-To'] = REPLY_TO
        
        # Maps link
        maps_link = "https://maps.app.goo.gl/RZqSN9bJkTNnVFLm7?g_st=ic"
        
        # HTML Common Head Style
        html_style = """
        <style>
          body {
            background-color: #0c0c0c;
            color: #e0e0e0;
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 0;
          }
          .wrapper {
            background-color: #0c0c0c;
            padding: 20px;
          }
          .container {
            max-width: 600px;
            margin: 0 auto;
            background-color: #161616;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #282828;
          }
          .header {
            background: linear-gradient(135deg, #1f1f1f 0%, #0d0d0d 100%);
            padding: 30px;
            text-align: center;
            border-bottom: 2px solid #ff6600;
          }
          .logo-text {
            font-size: 28px;
            font-weight: 800;
            color: #ffffff;
            text-decoration: none;
            letter-spacing: 1px;
          }
          .logo-text span {
            color: #ff6600;
          }
          .content {
            padding: 30px;
          }
          h1 {
            font-size: 22px;
            color: #ffffff;
            margin-top: 0;
            margin-bottom: 15px;
          }
          .lead {
            font-size: 16px;
            line-height: 1.6;
            color: #cccccc;
            margin-bottom: 25px;
          }
          .details-box {
            background-color: #1f1f1f;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 25px;
            border-left: 4px solid #ff6600;
          }
          .details-title {
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #ff6600;
            font-weight: bold;
            margin-bottom: 15px;
          }
          .detail-row {
            margin-bottom: 10px;
            font-size: 15px;
            color: #e0e0e0;
          }
          .detail-row strong {
            color: #ffffff;
          }
          .checklist-box {
            background-color: #1f1f1f;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 25px;
            border: 1px solid #282828;
          }
          .checklist-title {
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 15px;
          }
          .checklist-item {
            font-size: 14px;
            line-height: 1.5;
            margin-bottom: 12px;
            color: #cccccc;
          }
          .checklist-item strong {
            color: #ffffff;
          }
          .warning-box {
            background-color: #2a1508;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 25px;
            border: 1px solid #ff6600;
          }
          .warning-title {
            font-size: 16px;
            font-weight: bold;
            color: #ff8833;
            margin-bottom: 10px;
          }
          .warning-text {
            font-size: 14px;
            line-height: 1.6;
            color: #ffd4b8;
          }
          .btn-container {
            text-align: center;
            margin: 30px 0 10px 0;
          }
          .btn {
            background-color: #ff6600;
            color: #ffffff !important;
            padding: 14px 28px;
            text-decoration: none;
            font-weight: bold;
            border-radius: 6px;
            display: inline-block;
            font-size: 15px;
            box-shadow: 0 4px 12px rgba(255, 102, 0, 0.3);
          }
          .footer {
            background-color: #0d0d0d;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #666666;
            border-top: 1px solid #1f1f1f;
          }
          .footer a {
            color: #ff6600;
            text-decoration: none;
          }
        </style>
        """

        # Select translation content
        if lang == "pl":
            msg_client['Subject'] = 'Potwierdzenie Rezerwacji - Wycieczka Quadami na Teide ✨'
            body_client = (
                f"Cześć {booking['name']},\n\n"
                f"Twoja rezerwacja na wycieczkę quadem do Parku Narodowego Teide została pomyślnie potwierdzona! 🏔️🏍️\n\n"
                f"--- Szczegóły Rezerwacji ---\n"
                f"📅 Data: {booking['date']}\n"
                f"🕒 Godzina: {booking['time']} (BĄDŹ DOKŁADNIE 30 MINUT WCZEŚNIEJ!)\n"
                f"🏍️ Quady jednoosobowe (1 osoba): {booking['single_quads']}\n"
                f"🏍️ Quady dwuosobowe (2 osoby): {booking['double_quads']}\n"
                f"💰 Suma opłacona: €{booking['total_price']}\n\n"
                f"⚠️ WAŻNE INFORMACJE - CO ZABRAĆ ZE SOBĄ:\n"
                f"- Fizyczne, oryginalne prawo jazdy kategorii B (wymagane dla kierowców). Kopie, zdjęcia ani aplikacje mobilne NIE SĄ AKCEPTOWANE przez hiszpańską policję.\n"
                f"- Dowód osobisty lub paszport.\n"
                f"- Pełne, zakryte obuwie sportowe (np. adidasy, buty trekkingowe). Sandały i klapki są surowo zabronione ze względów bezpieczeństwa.\n"
                f"- Okulary przeciwsłoneczne i krem z filtrem.\n"
                f"- Wygodne ubranie sportowe na cebulkę (temperatura na Teide powyżej 2000m n.p.m. potrafi spaść nawet o 15°C! Zapewniamy wiatroodporne kurtki na miejscu).\n\n"
                f"📍 DOJAZD (Przybądź 30 min przed startem):\n"
                f"Nasze biuro: Extreme Prime Tours SL, Las Américas, Teneryfa, Hiszpania\n"
                f"Link do Map Google: {maps_link}\n\n"
                f"Do tej wiadomości dołączyliśmy plik kalendarza (.ics), aby automatycznie dodać to wydarzenie do kalendarza Apple, Google lub Outlook.\n\n"
                f"Do zobaczenia wkrótce,\n"
                f"Zespół Prime Quads"
            )
            
            html_client = f"""<!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              {html_style}
            </head>
            <body>
              <div class="wrapper">
                <div class="container">
                  <div class="header">
                    <a href="https://primequads.com" class="logo-text">PRIME<span>QUADS</span></a>
                  </div>
                  <div class="content">
                    <h1>Rezerwacja Potwierdzona! 🏔️🏍️</h1>
                    <p class="lead">Cześć {booking['name']}, Twoja wyprawa quadem do Parku Narodowego Teide została pomyślnie opłacona i zarejestrowana w naszym systemie. Przygotuj się na niezapomniane wrażenia!</p>
                    
                    <div class="warning-box">
                      <div class="warning-title">⚠️ Bądź 30 minut wcześniej!</div>
                      <div class="warning-text">Wymagane jest przybycie na miejsce zbiórki dokładnie <strong>30 minut przed planowanym startem wycieczki</strong>. Wyjeżdżamy w grupach punktualnie i nie ma możliwości spóźnienia się!</div>
                    </div>

                    <div class="details-box">
                      <div class="details-title">Szczegóły Wycieczki</div>
                      <div class="detail-row">📅 <strong>Data:</strong> {booking['date']}</div>
                      <div class="detail-row">🕒 <strong>Godzina startu:</strong> {booking['time']} (zbiórka o { (datetime.strptime(booking['time'], "%H:%M") - timedelta(minutes=30)).strftime("%H:%M") })</div>
                      <div class="detail-row">🏍️ <strong>Quady pojedyncze:</strong> {booking['single_quads']}</div>
                      <div class="detail-row">🏍️ <strong>Quady podwójne:</strong> {booking['double_quads']}</div>
                      <div class="detail-row">💰 <strong>Opłacona kwota:</strong> €{booking['total_price']}</div>
                    </div>

                    <div class="checklist-box">
                      <div class="checklist-title">📋 Co musisz ze sobą zabrać:</div>
                      <div class="checklist-item">🪪 <strong>Oryginalne fizyczne prawo jazdy kat. B</strong> – Wszyscy kierowcy muszą mieć ze sobą oryginalny plastikowy dokument. Kopie, zdjęcia w telefonie oraz aplikacje (np. mObywatel) nie są akceptowane przez policję drogową w Hiszpanii. Brak dokumentu = brak możliwości jazdy!</div>
                      <div class="checklist-item">👟 <strong>Zakryte buty sportowe</strong> – Adidasy lub buty trekkingowe są obowiązkowe. Sandały, klapki czy japonki są niedozwolone ze względów bezpieczeństwa.</div>
                      <div class="checklist-item">📄 <strong>Dowód osobisty lub Paszport</strong> – Wymagany do odprawy.</div>
                      <div class="checklist-item">🕶️ <strong>Okulary przeciwsłoneczne i krem z filtrem</strong> – Słońce na Teneryfie pali bardzo mocno, zwłaszcza w górach.</div>
                      <div class="checklist-item">🧥 <strong>Ubranie na cebulkę</strong> – Wjeżdżamy na ponad 2000 metrów n.p.m., gdzie temperatura może być znacznie niższa niż na wybrzeżu. Na trasie bezpłatnie udostępniamy wiatroodporne kurtki.</div>
                    </div>

                    <div class="checklist-box">
                      <div class="checklist-title">📍 Jak do nas dojechać:</div>
                      <p style="font-size: 14px; color: #cccccc; margin-bottom: 15px; line-height: 1.5;">Nasze biuro mieści się pod adresem: <strong>Extreme Prime Tours SL, Las Américas, Teneryfa</strong>. W okolicy bywają trudności z parkowaniem, dlatego prosimy o zaplanowanie dojazdu wcześniej.</p>
                      <div class="btn-container">
                        <a href="{maps_link}" class="btn" target="_blank">🗺️ Otwórz Nawigację w Mapach Google</a>
                      </div>
                    </div>

                    <p style="font-size: 13px; color: #888888; line-height: 1.5; text-align: center; margin-top: 30px;">Do maila dołączyliśmy plik kalendarza (.ics). Kliknij go dwukrotnie, aby dodać wycieczkę bezpośrednio do swojego kalendarza.</p>
                  </div>
                  <div class="footer">
                    © 2026 Extreme Prime Tours SL. Wszelkie prawa zastrzeżone.<br>
                    Telefon / WhatsApp: +34 600 000 000 | <a href="mailto:{REPLY_TO}">{REPLY_TO}</a>
                  </div>
                </div>
              </div>
            </body>
            </html>
            """
        elif lang == "es":
            msg_client['Subject'] = 'Reserva Confirmada - Expedición en Quad al Teide ✨'
            body_client = (
                f"Hola {booking['name']},\n\n"
                f"¡Tu reserva para la expedición en quad al Parque Nacional del Teide está oficialmente confirmada! 🏔️🏍️\n\n"
                f"--- Detalles de la Reserva ---\n"
                f"📅 Fecha: {booking['date']}\n"
                f"🕒 Hora: {booking['time']} (¡POR FAVOR, LLEGUE 30 MINUTOS ANTES!)\n"
                f"🏍️ Quads individuales (1 persona): {booking['single_quads']}\n"
                f"🏍️ Quads dobles (2 personas): {booking['double_quads']}\n"
                f"💰 Total pagado: €{booking['total_price']}\n\n"
                f"⚠️ INFORMACIÓN IMPORTANTE - QUÉ TRAER:\n"
                f"- Licencia de conducir física B original (obligatoria para conductores). Las copias, fotos o licencias digitales NO son aceptadas por las autoridades.\n"
                f"- DNI o Pasaporte.\n"
                f"- Calzado deportivo cerrado (obligatorio). No se permiten sandalias o chanclas por seguridad.\n"
                f"- Gafas de sol y protector solar.\n"
                f"- Ropa cómoda de abrigo (en el Teide a más de 2000m la temperatura baja drásticamente. Ofrecemos chaquetas cortavientos gratuitas).\n\n"
                f"📍 CÓMO LLEGAR (Llegada 30 min antes del inicio):\n"
                f"Nuestra oficina: Extreme Prime Tours SL, Las Américas, Tenerife, España\n"
                f"Enlace de Google Maps: {maps_link}\n\n"
                f"Adjuntamos el evento (.ics) para que lo agregues automáticamente a tu calendario de Apple, Google u Outlook.\n\n"
                f"Nos vemos pronto,\n"
                f"El equipo de Prime Quads"
            )
            
            html_client = f"""<!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              {html_style}
            </head>
            <body>
              <div class="wrapper">
                <div class="container">
                  <div class="header">
                    <a href="https://primequads.com" class="logo-text">PRIME<span>QUADS</span></a>
                  </div>
                  <div class="content">
                    <h1>¡Reserva Confirmada! 🏔️🏍️</h1>
                    <p class="lead">Hola {booking['name']}, tu pago para la excursión al Teide ha sido procesado con éxito. ¡Prepárate para una aventura inolvidable!</p>
                    
                    <div class="warning-box">
                      <div class="warning-title">⚠️ ¡Llegue 30 minutos antes!</div>
                      <div class="warning-text">Es obligatorio llegar al punto de encuentro exactamente <strong>30 minutos antes de la hora programada</strong> para las instrucciones de seguridad. ¡Salimos puntuales en grupo!</div>
                    </div>

                    <div class="details-box">
                      <div class="details-title">Detalles de la Reserva</div>
                      <div class="detail-row">📅 <strong>Fecha:</strong> {booking['date']}</div>
                      <div class="detail-row">🕒 <strong>Hora de inicio:</strong> {booking['time']} (Punto de encuentro a las { (datetime.strptime(booking['time'], "%H:%M") - timedelta(minutes=30)).strftime("%H:%M") })</div>
                      <div class="detail-row">🏍️ <strong>Quads individuales:</strong> {booking['single_quads']}</div>
                      <div class="detail-row">🏍️ <strong>Quads dobles:</strong> {booking['double_quads']}</div>
                      <div class="detail-row">💰 <strong>Total pagado:</strong> €{booking['total_price']}</div>
                    </div>

                    <div class="checklist-box">
                      <div class="checklist-title">📋 Qué debes traer contigo:</div>
                      <div class="checklist-item">🪪 <strong>Permiso de conducir físico B (Original)</strong> – Todos los conductores deben presentar su carné de conducir físico original. Las fotos, copias o licencias digitales no son aceptadas por las autoridades locales de tráfico. ¡Sin carné no podrás conducir!</div>
                      <div class="checklist-item">👟 <strong>Zapatos deportivos cerrados</strong> – Calzado deportivo o de montaña obligatorio. No se permiten sandalias o chanclas.</div>
                      <div class="checklist-item">📄 <strong>DNI o Pasaporte</strong> – Requerido para el registro.</div>
                      <div class="checklist-item">🕶️ <strong>Gafas de sol y protector solar</strong> – La radiación solar es alta en altitudes elevadas.</div>
                      <div class="checklist-item">🧥 <strong>Ropa de abrigo por capas</strong> – Subiremos a más de 2000m de altitud, donde la temperatura puede ser fresca. Proveemos chaquetas cortavientos gratis.</div>
                    </div>

                    <div class="checklist-box">
                      <div class="checklist-title">📍 Cómo llegar al punto de encuentro:</div>
                      <p style="font-size: 14px; color: #cccccc; margin-bottom: 15px; line-height: 1.5;">Nuestra oficina está en: <strong>Extreme Prime Tours SL, Las Américas, Tenerife</strong>. Recomendamos planificar el parking con tiempo suficiente.</p>
                      <div class="btn-container">
                        <a href="{maps_link}" class="btn" target="_blank">🗺️ Abrir en Google Maps</a>
                      </div>
                    </div>

                    <p style="font-size: 13px; color: #888888; line-height: 1.5; text-align: center; margin-top: 30px;">Hemos adjuntado un archivo (.ics). Ábrelo para guardar automáticamente esta fecha en tu calendario.</p>
                  </div>
                  <div class="footer">
                    © 2026 Extreme Prime Tours SL. Todos los derechos reservados.<br>
                    Teléfono / WhatsApp: +34 600 000 000 | <a href="mailto:{REPLY_TO}">{REPLY_TO}</a>
                  </div>
                </div>
              </div>
            </body>
            </html>
            """
        else:
            msg_client['Subject'] = 'Booking Confirmed - Teide Quad Expedition ✨'
            body_client = (
                f"Hi {booking['name']},\n\n"
                f"Your booking for the Teide National Park Quad Expedition is officially confirmed! 🏔️🏍️\n\n"
                f"--- Reservation Details ---\n"
                f"📅 Date: {booking['date']}\n"
                f"🕒 Time: {booking['time']} (PLEASE ARRIVE 30 MINUTES EARLY!)\n"
                f"🏍️ Single Quads (1-person): {booking['single_quads']}\n"
                f"🏍️ Double Quads (2-person): {booking['double_quads']}\n"
                f"💰 Total Paid: €{booking['total_price']}\n\n"
                f"⚠️ IMPORTANT INFORMATION - WHAT TO BRING:\n"
                f"- Physical, original category B driver's license (mandatory for all drivers). Copies, photos, or digital app versions are NOT accepted by Spanish traffic police.\n"
                f"- ID Card or Passport.\n"
                f"- Fully closed-toe athletic/sport shoes (mandatory). Sandals, flip-flops, or high heels are strictly forbidden for safety reasons.\n"
                f"- Sunglasses and sunscreen.\n"
                f"- Warm sportswear layer (temperatures above 2000m altitude drops significantly. Windproof jackets are provided on site).\n\n"
                f"📍 DIRECTIONS & LOCATION (Arrive 30 min early):\n"
                f"Meeting point: Extreme Prime Tours SL, Las Américas, Tenerife, Spain\n"
                f"Google Maps Link: {maps_link}\n\n"
                f"We have attached a calendar event file (.ics) to automatically add this tour to your Apple, Google, or Outlook calendar.\n\n"
                f"See you soon,\n"
                f"Prime Quads Team"
            )
            
            html_client = f"""<!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              {html_style}
            </head>
            <body>
              <div class="wrapper">
                <div class="container">
                  <div class="header">
                    <a href="https://primequads.com" class="logo-text">PRIME<span>QUADS</span></a>
                  </div>
                  <div class="content">
                    <h1>Booking Confirmed! 🏔️🏍️</h1>
                    <p class="lead">Hi {booking['name']}, your payment for the Teide Volcano Expedition has been processed successfully. Get ready for an unforgettable off-road journey!</p>
                    
                    <div class="warning-box">
                      <div class="warning-title">⚠️ Arrive 30 minutes early!</div>
                      <div class="warning-text">You are required to arrive at the meeting point exactly <strong>30 minutes before your scheduled departure time</strong> for instructions. The tour group departs punctually!</div>
                    </div>

                    <div class="details-box">
                      <div class="details-title">Reservation Details</div>
                      <div class="detail-row">📅 <strong>Date:</strong> {booking['date']}</div>
                      <div class="detail-row">🕒 <strong>Start Time:</strong> {booking['time']} (Arrive at { (datetime.strptime(booking['time'], "%H:%M") - timedelta(minutes=30)).strftime("%H:%M") })</div>
                      <div class="detail-row">🏍️ <strong>Single Quads:</strong> {booking['single_quads']}</div>
                      <div class="detail-row">🏍️ <strong>Double Quads:</strong> {booking['double_quads']}</div>
                      <div class="detail-row">💰 <strong>Total Paid:</strong> €{booking['total_price']}</div>
                    </div>

                    <div class="checklist-box">
                      <div class="checklist-title">📋 What you must bring:</div>
                      <div class="checklist-item">🪪 <strong>Original Physical B Driver's License</strong> – All drivers must present their physical original card license. Photocopies, smartphone photos, or digital driver apps are not recognized by Spanish traffic police. No license = no driving!</div>
                      <div class="checklist-item">👟 <strong>Closed-toe shoes</strong> – Running shoes or sneakers are mandatory. Strictly no sandals, slides, or flip-flops.</div>
                      <div class="checklist-item">📄 <strong>ID Card or Passport</strong> – Required for group registration.</div>
                      <div class="checklist-item">🕶️ <strong>Sunglasses & Sunscreen</strong> – Mountain sun is intense.</div>
                      <div class="checklist-item">🧥 <strong>Warm clothing layers</strong> – We ascend above 2000m where the weather gets cold. Windproof jackets are provided on site free of charge.</div>
                    </div>

                    <div class="checklist-box">
                      <div class="checklist-title">📍 How to find us:</div>
                      <p style="font-size: 14px; color: #cccccc; margin-bottom: 15px; line-height: 1.5;">Our office is located at: <strong>Extreme Prime Tours SL, Las Américas, Tenerife</strong>. Parking space can be scarce, so plan your arrival accordingly.</p>
                      <div class="btn-container">
                        <a href="{maps_link}" class="btn" target="_blank">🗺️ Open in Google Maps</a>
                      </div>
                    </div>

                    <p style="font-size: 13px; color: #888888; line-height: 1.5; text-align: center; margin-top: 30px;">We have attached a calendar event file (.ics). Open it to automatically save the date to your calendar.</p>
                  </div>
                  <div class="footer">
                    © 2026 Extreme Prime Tours SL. All rights reserved.<br>
                    Phone / WhatsApp: +34 600 000 000 | <a href="mailto:{REPLY_TO}">{REPLY_TO}</a>
                  </div>
                </div>
              </div>
            </body>
            </html>
            """
            
        msg_body = MIMEMultipart('alternative')
        msg_body.attach(MIMEText(body_client, 'plain'))
        msg_body.attach(MIMEText(html_client, 'html'))
        msg_client.attach(msg_body)
        
        # Attach ICS
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(ics_bytes)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="teide_quad_tour.ics"')
        msg_client.attach(part)
        
        # Connect & Send
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg_client)
            print(f"Confirmation email successfully sent to client: {booking['email']}")
            
    except Exception as e:
        print(f"Error sending email to client: {e}")

    # 2. Send email to Business Owner
    owner_email = BUSINESS_OWNER_EMAIL or SMTP_USER
    try:
        msg_owner = MIMEMultipart()
        msg_owner['From'] = EMAIL_FROM
        msg_owner['To'] = owner_email
        msg_owner['Reply-To'] = booking['email']
        msg_owner['Subject'] = f"New Booking Confirmed: {booking['name']} - {booking['date']}"
        
        body_owner = (
            f"Hello Prime Quads Team,\n\n"
            f"A new booking has been confirmed via Stripe payment:\n\n"
            f"👤 Customer: {booking['name']}\n"
            f"✉️ Email: {booking['email']}\n"
            f"📞 Phone: {booking['phone']}\n"
            f"📅 Date: {booking['date']}\n"
            f"🕒 Time: {booking['time']}\n"
            f"🏍️ Single Quads: {booking['single_quads']}\n"
            f"🏍️ Double Quads: {booking['double_quads']}\n"
            f"💰 Total Amount: €{booking['total_price']}\n"
            f"🆔 Booking ID: {booking['id']}\n"
            f"🌐 Site Language: {lang.upper()}\n\n"
            f"Attached is the calendar file to add this to your system."
        )
        msg_owner.attach(MIMEText(body_owner, 'plain'))
        
        # Attach ICS
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(ics_bytes)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="new_booking.ics"')
        msg_owner.attach(part)
        
        # Connect & Send
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg_owner)
            print(f"Notification email successfully sent to owner: {owner_email}")
            
    except Exception as e:
        print(f"Error sending email to business owner: {e}")
        
    return True

def send_contact_email(name, email, message, lang="en"):
    """
    Sends contact form details to the business owner.
    """
    # Verify SMTP configuration
    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD]):
        print("[WARNING] SMTP settings are incomplete in .env. Skipping contact email sending.")
        return False
        
    owner_email = BUSINESS_OWNER_EMAIL or SMTP_USER
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = owner_email
        msg['Reply-To'] = email
        msg['Subject'] = f"New Contact Message from {name} ✉️"
        
        body = (
            f"You received a new message from the contact form on Prime Quads:\n\n"
            f"👤 Name: {name}\n"
            f"✉️ Email: {email}\n"
            f"🌐 Preferred Language: {lang.upper()}\n\n"
            f"💬 Message:\n{message}\n"
        )
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect & Send
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
            print(f"Contact email successfully sent to owner: {owner_email}")
            
    except Exception as e:
        print(f"Error sending contact email: {e}")
        return False
        
    return True
