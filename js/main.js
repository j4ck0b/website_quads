/* =============================================================
   main.js – Prime Quads Tenerife
   All DOM queries are null-guarded to work on every page.
   ============================================================= */

// ─── Configuration ────────────────────────────────────────────
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname.startsWith('192.168.')
    ? 'http://localhost:5005'
    : ''; // Puste dla produkcji na Vercelu (ścieżki relatywne)

// ─── State ────────────────────────────────────────────────────
let currentLang = 'en';
let activeRotatorIndex = 0;

// ─── Navbar Scroll Effect ─────────────────────────────────────
(function () {
    const navbar = document.getElementById('navbar');
    if (!navbar) return;
    window.addEventListener('scroll', () => {
        navbar.classList.toggle('scrolled', window.scrollY > 50);
    });
})();

// ─── Mobile Menu Toggle ───────────────────────────────────────
(function () {
    const navContent = document.querySelector('.nav-content');
    const navLinks   = document.querySelector('.nav-links');
    if (!navContent) return;

    const toggle = document.createElement('div');
    toggle.className = 'nav-toggle';
    toggle.innerHTML = '<span></span><span></span><span></span>';
    navContent.appendChild(toggle);

    toggle.addEventListener('click', () => {
        if (navLinks) navLinks.classList.toggle('active');
        toggle.classList.toggle('open');
    });

    // Smooth scroll anchor links & close menu
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const id = this.getAttribute('href');
            if (id === '#') return;
            const target = document.querySelector(id);
            if (!target) return;
            e.preventDefault();
            if (navLinks) navLinks.classList.remove('active');
            toggle.classList.remove('open');
            target.scrollIntoView({ behavior: 'smooth' });
        });
    });
})();

// ─── Toast Notification ───────────────────────────────────────
function showPremiumToast(message, type) {
    type = type || 'success';
    const toast = document.createElement('div');
    toast.className = 'custom-toast';
    toast.innerHTML = `
        <div class="toast-content" style="
            display:flex;align-items:center;gap:.75rem;padding:1rem 1.75rem;
            background:rgba(20,20,20,.85);backdrop-filter:blur(15px);
            -webkit-backdrop-filter:blur(15px);
            border:1px solid ${type === 'success' ? 'rgba(255,102,0,.4)' : 'rgba(255,0,0,.4)'};
            border-radius:12px;color:#fff;font-family:inherit;font-size:.95rem;
            font-weight:600;
            box-shadow:0 10px 30px rgba(0,0,0,.5),0 0 20px ${type === 'success' ? 'rgba(255,102,0,.15)' : 'rgba(255,0,0,.15)'};
            pointer-events:auto;">
            <span style="font-size:1.25rem">${type === 'success' ? '✨' : '⚠️'}</span>
            <span>${message}</span>
        </div>`;

    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed;bottom:30px;right:30px;z-index:9999;pointer-events:none;display:flex;flex-direction:column;gap:10px;';
        document.body.appendChild(container);
    }
    container.appendChild(toast);

    if (window.gsap) {
        gsap.fromTo(toast, { opacity: 0, y: 30, scale: .9 }, { opacity: 1, y: 0, scale: 1, duration: .5, ease: 'back.out(1.7)' });
        setTimeout(() => {
            gsap.to(toast, { opacity: 0, y: -20, scale: .9, duration: .4, ease: 'power2.in', onComplete: () => toast.remove() });
        }, 4000);
    } else {
        setTimeout(() => toast.remove(), 4000);
    }
}

// ─── FAQ Accordion ────────────────────────────────────────────
function initFAQ() {
    document.querySelectorAll('.faq-trigger').forEach(trigger => {
        trigger.addEventListener('click', () => {
            const item  = trigger.parentElement;
            const panel = trigger.nextElementSibling;
            const icon  = trigger.querySelector('.faq-icon');
            const isOpen = item.classList.contains('active');

            document.querySelectorAll('.faq-item').forEach(other => {
                if (other !== item) {
                    other.classList.remove('active');
                    const p = other.querySelector('.faq-panel');
                    const ic = other.querySelector('.faq-icon');
                    if (p)  p.style.maxHeight = '0px';
                    if (ic) { ic.textContent = '+'; ic.style.transform = 'rotate(0deg)'; }
                }
            });

            if (isOpen) {
                item.classList.remove('active');
                if (panel) panel.style.maxHeight = '0px';
                if (icon)  { icon.textContent = '+'; icon.style.transform = 'rotate(0deg)'; }
            } else {
                item.classList.add('active');
                if (panel) panel.style.maxHeight = panel.scrollHeight + 'px';
                if (icon)  { icon.textContent = '−'; icon.style.transform = 'rotate(180deg)'; }
            }
        });
    });
}

// ─── FAQ JSON-LD Schema ───────────────────────────────────────
function updateFAQSchema(lang) {
    const el = document.getElementById('faq-schema');
    if (!el || !translations || !translations[lang]) return;
    const t = translations[lang];
    el.textContent = JSON.stringify({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [1,2,3,4].map(n => ({
            "@type": "Question",
            "name": t[`faq.q${n}`] || "",
            "acceptedAnswer": { "@type": "Answer", "text": t[`faq.a${n}`] || "" }
        }))
    }, null, 2);
}

// ─── Translation Engine ───────────────────────────────────────
function setLanguage(lang) {
    if (!translations || !translations[lang]) return;
    currentLang = lang;
    const t = translations[lang];

    // Text content
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (el.id === 'gallery-toggle-btn') return; // Handled separately below
        if (t[key] !== undefined) el.innerText = t[key];
    });

    // Placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (t[key] !== undefined) el.setAttribute('placeholder', t[key]);
    });

    // Alt attributes
    document.querySelectorAll('[data-i18n-alt]').forEach(el => {
        const key = el.getAttribute('data-i18n-alt');
        if (t[key] !== undefined) el.setAttribute('alt', t[key]);
    });

    // Rotating hero text
    const rotating = document.getElementById('hero-rotating-text');
    if (rotating) {
        const keys = ['hero.rotate.1','hero.rotate.2','hero.rotate.3','hero.rotate.4','hero.rotate.5'];
        rotating.innerText = t[keys[activeRotatorIndex]] || 'Feel the Adrenaline';
    }

    // Title & meta description
    const pageName = window.location.pathname.split('/').pop() || 'index.html';
    const titleKey = `seo.title.${pageName}`;
    const descKey  = `seo.description.${pageName}`;
    document.title = t[titleKey] || t['seo.title'] || document.title;
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) metaDesc.setAttribute('content', t[descKey] || t['seo.description'] || '');
    document.documentElement.lang = lang;
    // Reset FAQ panels (unless they are supposed to be open by default on PL page)
    const isPlPage = window.location.pathname.indexOf('/pl/') !== -1;
    document.querySelectorAll('.faq-item').forEach(item => {
        if (isPlPage) {
            item.classList.add('active');
            const p  = item.querySelector('.faq-panel');
            const ic = item.querySelector('.faq-icon');
            if (p)  p.style.maxHeight = 'none';
            if (ic) { ic.textContent = '−'; ic.style.transform = 'rotate(180deg)'; }
        } else {
            item.classList.remove('active');
            const p  = item.querySelector('.faq-panel');
            const ic = item.querySelector('.faq-icon');
            if (p)  p.style.maxHeight = '0px';
            if (ic) { ic.textContent = '+'; ic.style.transform = 'rotate(0deg)'; }
        }
    });

    // Gallery toggle button translation respecting open state
    const toggleBtn = document.getElementById('gallery-toggle-btn');
    if (toggleBtn) {
        const isOpen = document.querySelector('.gallery-item.hidden-item.show-item') !== null;
        const key = isOpen ? 'gallery.show_less' : 'gallery.load_more';
        if (t[key] !== undefined) toggleBtn.innerText = t[key];
    }

    updateFAQSchema(lang);

    // Dropdown active state
    document.querySelectorAll('.lang-dropdown-item').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-lang') === lang);
    });
    const activeLangText = document.getElementById('activeLangText');
    if (activeLangText) activeLangText.innerText = lang.toUpperCase();

    localStorage.setItem('preferredLang', lang);

    // Re-render calendar header if on index page
    if (typeof renderCalendar === 'function') renderCalendar();
    if (typeof renderTimeSlots === 'function' && selectedDateStr) renderTimeSlots(currentAvailableSlots);
}

// Expose globally for any inline onclick that might exist
window.setLanguage = setLanguage;

// ─── Language Dropdown ────────────────────────────────────────
function initLangDropdown() {
    const trigger = document.getElementById('langTrigger');
    const menu    = document.getElementById('langMenu');
    if (!trigger || !menu) return;

    const arrow = trigger.querySelector('.arrow');

    trigger.addEventListener('click', e => {
        e.stopPropagation();
        const isOpen = menu.classList.toggle('active');
        if (arrow) arrow.style.transform = isOpen ? 'rotate(180deg)' : 'rotate(0deg)';
    });

    menu.addEventListener('click', e => e.stopPropagation());

    document.addEventListener('click', () => {
        menu.classList.remove('active');
        if (arrow) arrow.style.transform = 'rotate(0deg)';
    });
}

// ─── Contact Form ─────────────────────────────────────────────
function initContactForm() {
    const form = document.getElementById('booking-form');
    if (!form) return;
    form.addEventListener('submit', e => {
        e.preventDefault();
        
        const honeyInput = form.querySelector('input[name="website_url"]');
        const nameInput = form.querySelector('input[type="text"]:not([name="website_url"])');
        const emailInput = form.querySelector('input[type="email"]');
        const messageInput = form.querySelector('textarea');
        const btn = form.querySelector('button');
        if (!btn) return;
        
        const honey = honeyInput ? honeyInput.value : '';
        const name = nameInput ? nameInput.value : '';
        const email = emailInput ? emailInput.value : '';
        const message = messageInput ? messageInput.value : '';
        
        const t = (translations && translations[currentLang]) || {};
        btn.innerText = t['contact.form.sending'] || 'Sending…';
        btn.disabled = true;
        
        fetch(API_BASE_URL + '/api/contact', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, email: email, message: message, website_url: honey, lang: currentLang })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errData => {
                    throw new Error(errData.error || 'Failed to send message');
                });
            }
            return response.json();
        })
        .then(data => {
            showPremiumToast(t['contact.form.success'] || 'Thank you!', 'success');
            form.reset();
        })
        .catch(err => {
            console.error('Contact form error:', err);
            showPremiumToast(err.message || 'Error occurred. Please try again.', 'error');
        })
        .finally(() => {
            btn.innerText = t['contact.form.submit'] || 'Send Message';
            btn.disabled = false;
        });
    });
}

// ─── Gallery Thumbnail Switcher ───────────────────────────────
function switchMainImage(imgSrc, thumbEl) {
    const mainImg = document.getElementById('tour-main-img');
    if (!mainImg) return;
    mainImg.style.opacity = '0.3';
    setTimeout(() => { mainImg.src = imgSrc; mainImg.style.opacity = '1'; }, 200);
    document.querySelectorAll('.thumb-item').forEach(i => i.classList.remove('active'));
    if (thumbEl) thumbEl.classList.add('active');
}
window.switchMainImage = switchMainImage;

// ─── Lightbox ─────────────────────────────────────────────────
function initLightbox() {
    const lightbox = document.getElementById('lightboxModal');
    if (!lightbox) return;

    const lightboxImg     = document.getElementById('lightbox-img');
    const lightboxClose   = document.querySelector('.lightbox-close');
    const lightboxPrev    = document.querySelector('.lightbox-prev');
    const lightboxNext    = document.querySelector('.lightbox-next');
    const lightboxCounter = document.querySelector('.lightbox-counter');

    const desktopImages = document.querySelectorAll('.gallery-grid .gallery-item img');
    let currentIndex = 0;
    const imagesArray = Array.from(desktopImages).map(img => img.getAttribute('data-full-src') || img.src);

    function showImage(index) {
        if (!lightboxImg || !imagesArray.length) return;
        if (index < 0) index = imagesArray.length - 1;
        if (index >= imagesArray.length) index = 0;
        currentIndex = index;
        lightboxImg.style.opacity = '0';
        lightboxImg.style.transform = 'scale(.95)';
        setTimeout(() => {
            lightboxImg.src = imagesArray[currentIndex];
            lightboxImg.style.opacity = '1';
            lightboxImg.style.transform = 'scale(1)';
            if (lightboxCounter) lightboxCounter.innerText = `${currentIndex + 1} / ${imagesArray.length}`;
        }, 150);
    }
    window.showLightboxImage = showImage;

    desktopImages.forEach((img, i) => {
        img.addEventListener('click', () => {
            lightbox.classList.add('active');
            showImage(i);
            document.body.style.overflow = 'hidden';
        });
    });

    function closeLightbox() {
        lightbox.classList.remove('active');
        document.body.style.overflow = '';
    }

    if (lightboxClose) lightboxClose.addEventListener('click', closeLightbox);
    if (lightboxPrev)  lightboxPrev.addEventListener('click',  e => { e.stopPropagation(); showImage(currentIndex - 1); });
    if (lightboxNext)  lightboxNext.addEventListener('click',  e => { e.stopPropagation(); showImage(currentIndex + 1); });
    lightbox.addEventListener('click', e => {
        if (e.target === lightbox || e.target.classList.contains('lightbox-content')) closeLightbox();
    });
    document.addEventListener('keydown', e => {
        if (!lightbox.classList.contains('active')) return;
        if (e.key === 'Escape')      closeLightbox();
        if (e.key === 'ArrowLeft')   showImage(currentIndex - 1);
        if (e.key === 'ArrowRight')  showImage(currentIndex + 1);
    });
}

// ─── Mobile Card Stack Gallery ────────────────────────────────
function initCardStack() {
    const deck  = document.querySelector('.gallery-card-deck');
    const cards = document.querySelectorAll('.gallery-card');
    if (!deck || !cards.length) return;

    const prevBtn   = document.getElementById('stackPrev');
    const nextBtn   = document.getElementById('stackNext');
    const stackInfo = document.getElementById('stackInfo');
    const lightbox  = document.getElementById('lightboxModal');

    let activeIndex = 0;
    const total = cards.length;

    function arrangeCards() {
        cards.forEach((card, idx) => {
            const order = (idx - activeIndex + total) % total;
            if (order < 3) {
                card.style.display = 'block';
                card.style.zIndex = total - order;
                if (window.gsap) gsap.to(card, {
                    y: order * 18, scale: 1 - order * .05, z: -order * 30,
                    rotateX: -order * 2, opacity: 1 - order * .25,
                    duration: .45, ease: 'power2.out', overwrite: 'auto'
                });
            } else {
                card.style.display = 'none';
                card.style.opacity = '0';
            }
        });
        if (stackInfo) stackInfo.innerText = `${activeIndex + 1} / ${total}`;
    }
    arrangeCards();

    cards.forEach((card, idx) => {
        let dragging = false, startX = 0, startY = 0, curX = 0, curY = 0;

        card.addEventListener('pointerdown', e => {
            if ((idx - activeIndex + total) % total !== 0) return;
            dragging = true; startX = e.clientX; startY = e.clientY;
            card.setPointerCapture(e.pointerId);
            if (window.gsap) gsap.killTweensOf(card);
        });
        card.addEventListener('pointermove', e => {
            if (!dragging) return;
            curX = e.clientX - startX; curY = e.clientY - startY;
            if (window.gsap) gsap.set(card, { x: curX, y: curY, rotate: curX * .05, rotateY: curX * .02 });
        });
        card.addEventListener('pointerup', e => {
            if (!dragging) return;
            dragging = false;
            card.releasePointerCapture(e.pointerId);
            if (Math.abs(curX) > 100) {
                const dir = curX > 0 ? 1 : -1;
                if (window.gsap) gsap.to(card, {
                    x: dir * 500, y: curY + (curY > 0 ? 100 : -100), rotate: dir * 45, opacity: 0,
                    duration: .5, ease: 'power2.in',
                    onComplete: () => { activeIndex = (activeIndex + 1) % total; arrangeCards(); }
                });
            } else if (Math.abs(curX) < 5 && Math.abs(curY) < 5) {
                if (lightbox) {
                    lightbox.classList.add('active');
                    const imgEl = card.querySelector('img');
                    let foundIdx = -1;
                    if (imgEl && window.showLightboxImage) {
                        const srcVal = imgEl.getAttribute('data-full-src') || imgEl.getAttribute('src');
                        const imagesArray = Array.from(document.querySelectorAll('.gallery-grid .gallery-item img')).map(i => i.getAttribute('data-full-src') || i.src);
                        for (let i = 0; i < imagesArray.length; i++) {
                            if (imagesArray[i] === imgEl.src || imagesArray[i].endsWith(srcVal)) {
                                foundIdx = i;
                                break;
                            }
                        }
                    }
                    if (window.showLightboxImage) window.showLightboxImage(foundIdx !== -1 ? foundIdx : idx);
                    document.body.style.overflow = 'hidden';
                }
            } else {
                if (window.gsap) gsap.to(card, { x: 0, y: 0, rotate: 0, rotateY: 0, duration: .4, ease: 'back.out(1.5)' });
            }
            curX = 0; curY = 0;
        });
        card.addEventListener('pointercancel', () => {
            if (!dragging) return; dragging = false;
            if (window.gsap) gsap.to(card, { x: 0, y: 0, rotate: 0, rotateY: 0, duration: .4, ease: 'back.out(1.5)' });
        });
    });

    if (nextBtn) nextBtn.addEventListener('click', () => {
        if (window.gsap) gsap.to(cards[activeIndex], {
            x: 500, rotate: 45, opacity: 0, duration: .5, ease: 'power2.in',
            onComplete: () => { activeIndex = (activeIndex + 1) % total; arrangeCards(); }
        });
    });
    if (prevBtn) prevBtn.addEventListener('click', () => {
        activeIndex = (activeIndex - 1 + total) % total;
        arrangeCards();
        if (window.gsap) gsap.fromTo(cards[activeIndex], { x: -500, rotate: -45, opacity: 0 }, { x: 0, rotate: 0, opacity: 1, duration: .5, ease: 'power2.out' });
    });
}

// ─── Booking Calendar ─────────────────────────────────────────
var currentCalDate = new Date();
var selectedDateStr = '';
var selectedTimeStr = '';
var currentAvailableSlots = {};
var singleQuadsCount = 0;
var doubleQuadsCount = 0;

var MONTH_NAMES = {
    en: ['January','February','March','April','May','June','July','August','September','October','November','December'],
    pl: ['Styczeń','Luty','Marzec','Kwiecień','Maj','Czerwiec','Lipiec','Sierpień','Wrzesień','Październik','Listopad','Grudzień'],
    es: ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
};

function renderCalendar() {
    var calDays = document.getElementById('cal-days');
    var calHeader = document.getElementById('cal-month-year');
    if (!calDays || !calHeader) return;

    var year  = currentCalDate.getFullYear();
    var month = currentCalDate.getMonth();
    var names = MONTH_NAMES[currentLang] || MONTH_NAMES['en'];
    calHeader.innerText = names[month] + ' ' + year;

    var today = new Date();
    var prevBtn = document.getElementById('cal-prev');
    if (prevBtn) {
        var isCurrentMonth = (year === today.getFullYear() && month === today.getMonth());
        prevBtn.disabled = isCurrentMonth;
        prevBtn.style.opacity  = isCurrentMonth ? '0.25' : '1';
        prevBtn.style.cursor   = isCurrentMonth ? 'not-allowed' : 'pointer';
    }

    calDays.innerHTML = '';

    // First weekday offset (Mon=0)
    var firstDay = new Date(year, month, 1).getDay();
    var offset   = (firstDay + 6) % 7;
    var totalDays = new Date(year, month + 1, 0).getDate();
    var todayReset = new Date(today.getFullYear(), today.getMonth(), today.getDate());

    for (var i = 0; i < offset; i++) {
        var empty = document.createElement('div');
        empty.className = 'calendar-day empty';
        calDays.appendChild(empty);
    }

    for (var day = 1; day <= totalDays; day++) {
        (function(d) {
            var cell = document.createElement('div');
            cell.className = 'calendar-day';
            cell.innerText = d;

            var mStr = String(month + 1).padStart(2, '0');
            var dStr = String(d).padStart(2, '0');
            var dateVal = year + '-' + mStr + '-' + dStr;

            var checkDate = new Date(year, month, d);

            if (checkDate < todayReset) {
                cell.classList.add('disabled');
            } else {
                if (d === today.getDate() && month === today.getMonth() && year === today.getFullYear()) {
                    cell.classList.add('today');
                }
                if (selectedDateStr === dateVal) {
                    cell.classList.add('selected');
                }
                cell.addEventListener('click', function() {
                    document.querySelectorAll('.calendar-day').forEach(function(el) {
                        el.classList.remove('selected');
                    });
                    cell.classList.add('selected');
                    selectDate(dateVal);
                });
            }
            calDays.appendChild(cell);
        })(day);
    }
}

function selectDate(dateVal) {
    selectedDateStr = dateVal;
    var dateInput = document.getElementById('booking-date');
    if (dateInput) dateInput.value = dateVal;

    selectedTimeStr = '';
    var timeInput = document.getElementById('booking-time');
    if (timeInput) timeInput.value = '';

    var slotsContainer = document.getElementById('time-slots-container');
    if (slotsContainer) {
        var loadingText = currentLang === 'pl' ? 'Pobieranie dostępnych godzin…'
                        : currentLang === 'es' ? 'Cargando horarios…'
                        : 'Loading available times…';
        slotsContainer.innerHTML = '<div style="color:var(--text-muted);font-size:.95rem;font-style:italic;text-align:center;padding:2rem 0;">' + loadingText + '</div>';
    }

    fetch(API_BASE_URL + '/api/availability?date=' + dateVal)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data && data.slots) {
                currentAvailableSlots = data.slots;
                renderTimeSlots(data.slots);
            }
        })
        .catch(function(err) {
            console.error('Error fetching availability:', err);
            if (slotsContainer) slotsContainer.innerHTML = '<div style="color:var(--text-muted);font-size:.9rem;text-align:center;padding:1rem;">Could not load availability. Is the server running?</div>';
        });
}

function renderTimeSlots(slots) {
    var container = document.getElementById('time-slots-container');
    if (!container) return;
    container.innerHTML = '';

    var t = (translations && translations[currentLang]) || {};

    Object.keys(slots).forEach(function(time) {
        var remaining = slots[time];
        var pill = document.createElement('div');
        pill.className = 'time-slot-pill';

        var isFull = remaining <= 0;
        var remainingText = isFull
            ? (t['booking.form.time.slot_full'] || 'FULL')
            : (remaining + ' ' + (t['booking.form.time.slot_remaining'] || 'quads left'));

        var title = time === '13:00'
            ? (t['booking.form.time.afternoon'] || 'Afternoon Tour (13:00)')
            : (t['booking.form.time.sunset']    || 'Sunset Tour (18:30)');

        pill.innerHTML = '<span class="time-slot-name">' + title + '</span>'
                       + '<span class="time-slot-status">' + remainingText + '</span>';

        if (isFull) {
            pill.classList.add('disabled');
        } else {
            if (selectedTimeStr === time) pill.classList.add('selected');
            pill.addEventListener('click', function() {
                document.querySelectorAll('.time-slot-pill').forEach(function(el) { el.classList.remove('selected'); });
                pill.classList.add('selected');
                selectedTimeStr = time;
                var ti = document.getElementById('booking-time');
                if (ti) ti.value = time;
                validateQuadCapacity();
            });
        }
        container.appendChild(pill);
    });
}

function adjustQuad(type, amount) {
    var tempS = singleQuadsCount;
    var tempD = doubleQuadsCount;
    if (type === 'single') tempS = Math.max(0, tempS + amount);
    if (type === 'double') tempD = Math.max(0, tempD + amount);

    var timeVal = document.getElementById('booking-time');
    timeVal = timeVal ? timeVal.value : '';
    if (timeVal && currentAvailableSlots[timeVal] !== undefined) {
        var max = currentAvailableSlots[timeVal];
        if (tempS + tempD > max) {
            var msg = currentLang === 'pl'
                ? 'Brak wystarczającej liczby wolnych quadów (max: ' + max + ').'
                : currentLang === 'es'
                ? 'No hay suficientes quads disponibles (máx: ' + max + ').'
                : 'Not enough quads available for this slot (max: ' + max + ').';
            showPremiumToast(msg, 'error');
            return;
        }
    }
    singleQuadsCount = tempS;
    doubleQuadsCount = tempD;

    var sEl = document.getElementById('single-quad-count');
    var dEl = document.getElementById('double-quad-count');
    if (sEl) sEl.innerText = singleQuadsCount;
    if (dEl) dEl.innerText = doubleQuadsCount;
    updateBookingPrice();
}
window.adjustQuad = adjustQuad;

function updateBookingPrice() {
    var priceEl = document.getElementById('booking-total-price');
    if (priceEl) priceEl.innerText = '€' + (singleQuadsCount * 120 + doubleQuadsCount * 140);
}
window.updateBookingPrice = updateBookingPrice;

function validateQuadCapacity() {
    var ti = document.getElementById('booking-time');
    var timeVal = ti ? ti.value : '';
    if (!timeVal || currentAvailableSlots[timeVal] === undefined) return true;
    var max = currentAvailableSlots[timeVal];
    if (singleQuadsCount + doubleQuadsCount <= max) return true;

    while (singleQuadsCount + doubleQuadsCount > max) {
        if (doubleQuadsCount > 0) {
            doubleQuadsCount--;
            var dEl = document.getElementById('double-quad-count');
            if (dEl) dEl.innerText = doubleQuadsCount;
        } else if (singleQuadsCount > 0) {
            singleQuadsCount--;
            var sEl = document.getElementById('single-quad-count');
            if (sEl) sEl.innerText = singleQuadsCount;
        } else break;
    }
    updateBookingPrice();
    return false;
}

function initCalendar() {
    var prevBtn = document.getElementById('cal-prev');
    var nextBtn = document.getElementById('cal-next');
    if (!prevBtn && !nextBtn) return; // no calendar on this page

    if (prevBtn) prevBtn.addEventListener('click', function() {
        currentCalDate.setMonth(currentCalDate.getMonth() - 1);
        renderCalendar();
    });
    if (nextBtn) nextBtn.addEventListener('click', function() {
        currentCalDate.setMonth(currentCalDate.getMonth() + 1);
        renderCalendar();
    });

    renderCalendar();
}

// ─── Booking Form Submit ──────────────────────────────────────
function initBookingForm() {
    var form = document.getElementById('whatsapp-booking-form');
    if (!form) return;

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        var t = (translations && translations[currentLang]) || {};

        if (singleQuadsCount === 0 && doubleQuadsCount === 0) {
            showPremiumToast(t['booking.form.validation.quads'] || 'Please select at least 1 quad.', 'error');
            return;
        }

        var date  = document.getElementById('booking-date');
        var time  = document.getElementById('booking-time');
        var name  = document.getElementById('booking-name');
        var phone = document.getElementById('booking-phone');
        var email = document.getElementById('booking-email');
        var prefixEl = document.getElementById('booking-phone-prefix');

        if (!date || !date.value) {
            showPremiumToast(currentLang === 'pl' ? 'Proszę wybrać datę z kalendarza.' : 'Please select a date from the calendar.', 'error');
            return;
        }
        if (!time || !time.value) {
            showPremiumToast(currentLang === 'pl' ? 'Proszę wybrać godzinę wycieczki.' : 'Please select a tour time.', 'error');
            return;
        }

        var honeyEl = form.querySelector('input[name="website_url"]');
        var honey = honeyEl ? honeyEl.value : '';

        var submitBtn = form.querySelector('button[type="submit"]');
        var origHtml  = submitBtn ? submitBtn.innerHTML : '';
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerText = currentLang === 'pl' ? 'Przekierowywanie…' : currentLang === 'es' ? 'Redirigiendo…' : 'Redirecting to payment…';
        }

        fetch(API_BASE_URL + '/api/bookings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name:         name  ? name.value  : '',
                email:        email ? email.value : '',
                phone:        (function() {
                    var rawPhone = phone ? phone.value.trim() : '';
                    var prefix = prefixEl ? prefixEl.value : '';
                    var fullPhone = rawPhone;
                    if (prefix && !rawPhone.startsWith('+') && !rawPhone.startsWith('00')) {
                        if (rawPhone.startsWith('0')) {
                            rawPhone = rawPhone.substring(1);
                        }
                        fullPhone = prefix + ' ' + rawPhone;
                    }
                    return fullPhone;
                })(),
                date:         date.value,
                time:         time.value,
                single_quads: singleQuadsCount,
                double_quads: doubleQuadsCount,
                lang:         currentLang,
                website_url:  honey
            })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data && data.checkout_url) {
                window.location.href = data.checkout_url;
            } else {
                throw new Error(data.error || 'Checkout session failed');
            }
        })
        .catch(function(err) {
            console.error('Booking error:', err);
            showPremiumToast(err.message || 'Error occurred during checkout.', 'error');
            if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = origHtml; }
        });
    });
}

// ─── GSAP Animations ─────────────────────────────────────────
function initAnimations() {
    if (!window.gsap) return;

    gsap.registerPlugin(ScrollTrigger);

    // Hero text rotator
    var textEl = document.getElementById('hero-rotating-text');
    if (textEl) {
        var rotKeys = ['hero.rotate.1','hero.rotate.2','hero.rotate.3','hero.rotate.4','hero.rotate.5'];
        setInterval(function() {
            gsap.to(textEl, { opacity: 0, y: -15, scale: .97, duration: .35, ease: 'power2.in',
                onComplete: function() {
                    activeRotatorIndex = (activeRotatorIndex + 1) % rotKeys.length;
                    var t = (translations && translations[currentLang]) || {};
                    textEl.innerText = t[rotKeys[activeRotatorIndex]] || 'Feel the Adrenaline';
                    gsap.fromTo(textEl, { opacity: 0, y: 15, scale: .97 }, { opacity: 1, y: 0, scale: 1, duration: .5, ease: 'back.out(1.2)' });
                }
            });
        }, 4000);
    }

    // Hero entrance
    gsap.from('.hero-content h1', { opacity: 0, y: 50, duration: 1, delay: .2 });
    gsap.from('.hero-content p',  { opacity: 0, y: 50, duration: 1, delay: .4 });
    gsap.from('.hero-btns',       { opacity: 0, y: 50, duration: 1, delay: .6 });

    // Parallax hero
    var heroBg = document.querySelector('.hero-bg img');
    if (heroBg) gsap.to(heroBg, { yPercent: 20, ease: 'none', scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: true } });

    // Section headings
    gsap.utils.toArray('.section h2').forEach(function(h) {
        gsap.from(h, { scrollTrigger: { trigger: h, start: 'top 80%' }, opacity: 0, y: 30, duration: .8 });
    });

    // Single tour container
    var singleTour = document.querySelector('.single-tour-container');
    if (singleTour) gsap.from(singleTour, { scrollTrigger: { trigger: singleTour, start: 'top 85%' }, opacity: 0, y: 50, duration: 1 });

    // Booking widget
    var bw = document.querySelector('.booking-widget-wrapper');
    if (bw) gsap.from(bw, { scrollTrigger: { trigger: bw, start: 'top 85%' }, opacity: 0, y: 50, duration: 1 });

    // Gallery (only visible ones on start)
    gsap.utils.toArray('.gallery-item:not(.hidden-item)').forEach(function(item, i) {
        gsap.from(item, { scrollTrigger: { trigger: item, start: 'top 90%' }, opacity: 0, scale: .8, duration: .6, delay: (i % 4) * .1 });
    });
}

// ─── Boot ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
    // Detect language from URL path
    var path = window.location.pathname;
    var lang = 'en';
    if (path.indexOf('/pl/') !== -1) lang = 'pl';
    else if (path.indexOf('/es/') !== -1) lang = 'es';

    setLanguage(lang);
    initLangDropdown();
    initFAQ();
    initContactForm();
    initLightbox();
    initCardStack();
    initCalendar();
    initBookingForm();
    initNewsletterForm();
    initAnimations();
    initGalleryToggle();
});

// ─── Gallery Toggle (Load More) ───────────────────────────────
function initGalleryToggle() {
    const toggleBtn = document.getElementById('gallery-toggle-btn');
    if (!toggleBtn) return;

    let isOpen = false;

    toggleBtn.addEventListener('click', () => {
        isOpen = !isOpen;
        const hiddenItems = document.querySelectorAll('.gallery-grid .gallery-item.hidden-item');
        const t = (translations && translations[currentLang]) || {};

        if (isOpen) {
            // Show hidden items
            hiddenItems.forEach(item => {
                item.classList.add('show-item');
            });
            // Animate using GSAP
            if (window.gsap) {
                gsap.fromTo(hiddenItems, 
                    { opacity: 0, scale: 0.9, y: 30 }, 
                    { opacity: 1, scale: 1, y: 0, duration: 0.6, stagger: 0.04, ease: 'power2.out', overwrite: 'auto' }
                );
            }
            toggleBtn.innerText = t['gallery.show_less'] || 'Show Less';
        } else {
            // Hide items
            if (window.gsap) {
                gsap.to(hiddenItems, {
                    opacity: 0, scale: 0.9, y: 20, duration: 0.4, ease: 'power2.in',
                    onComplete: () => {
                        hiddenItems.forEach(item => item.classList.remove('show-item'));
                        // Smooth scroll back to gallery top so user is not lost
                        const gallerySec = document.getElementById('gallery');
                        if (gallerySec) gallerySec.scrollIntoView({ behavior: 'smooth' });
                    }
                });
            } else {
                hiddenItems.forEach(item => item.classList.remove('show-item'));
                const gallerySec = document.getElementById('gallery');
                if (gallerySec) gallerySec.scrollIntoView({ behavior: 'smooth' });
            }
            toggleBtn.innerText = t['gallery.load_more'] || 'Load More Photos';
        }
    });
}

// ─── Newsletter Form ──────────────────────────────────────────
function initNewsletterForm() {
    const form = document.getElementById('newsletter-form');
    if (!form) return;
    form.addEventListener('submit', e => {
        e.preventDefault();
        
        const emailInput = form.querySelector('input[type="email"]');
        const honeyInput = form.querySelector('input[name="website_url"]');
        const btn = form.querySelector('button');
        if (!btn) return;
        
        const email = emailInput ? emailInput.value : '';
        const honey = honeyInput ? honeyInput.value : '';
        
        const t = (translations && translations[currentLang]) || {};
        btn.innerText = t['footer.newsletter.sending'] || 'Subscribing…';
        btn.disabled = true;
        
        fetch(API_BASE_URL + '/api/newsletter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, website_url: honey, lang: currentLang })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errData => {
                    throw new Error(errData.error || 'Failed to subscribe');
                });
            }
            return response.json();
        })
        .then(data => {
            showPremiumToast(t['footer.newsletter.success'] || 'Subscribed successfully!', 'success');
            form.reset();
        })
        .catch(err => {
            console.error('Newsletter form error:', err);
            showPremiumToast(err.message || 'Error occurred. Please try again.', 'error');
        })
        .finally(() => {
            btn.innerText = t['footer.newsletter.submit'] || 'Subscribe';
            btn.disabled = false;
        });
    });
}
