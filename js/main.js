// Navbar Scroll Effect
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
});

// Mobile Menu Toggle
const navLinks = document.querySelector('.nav-links');
const navToggle = document.createElement('div');
navToggle.className = 'nav-toggle';
navToggle.innerHTML = '<span></span><span></span><span></span>';
document.querySelector('.nav-content').appendChild(navToggle);

navToggle.addEventListener('click', () => {
    navLinks.classList.toggle('active');
    navToggle.classList.toggle('open');
});

// Smooth Scrolling
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const targetId = this.getAttribute('href');
        if (targetId === '#') return;
        
        const targetEl = document.querySelector(targetId);
        if (targetEl) {
            e.preventDefault();
            navLinks.classList.remove('active');
            navToggle.classList.remove('open');
            targetEl.scrollIntoView({
                behavior: 'smooth'
            });
        }
    });
});

// Premium Glassmorphic Toast Notification System
function showPremiumToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = 'custom-toast';
    toast.innerHTML = `
        <div class="toast-content" style="
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 1rem 1.75rem;
            background: rgba(20, 20, 20, 0.85);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border: 1px solid ${type === 'success' ? 'rgba(255, 102, 0, 0.4)' : 'rgba(255, 0, 0, 0.4)'};
            border-radius: 12px;
            color: #fff;
            font-family: inherit;
            font-size: 0.95rem;
            font-weight: 600;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5), 0 0 20px ${type === 'success' ? 'rgba(255, 102, 0, 0.15)' : 'rgba(255, 0, 0, 0.15)'};
            pointer-events: auto;
        ">
            <span style="font-size: 1.25rem;">${type === 'success' ? '✨' : '⚠️'}</span>
            <span>${message}</span>
        </div>
    `;
    
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position: fixed; bottom: 30px; right: 30px; z-index: 9999; pointer-events: none; display: flex; flex-direction: column; gap: 10px;';
        document.body.appendChild(container);
    }
    
    container.appendChild(toast);
    
    // Dynamic GSAP entrance animation
    gsap.fromTo(toast, 
        { opacity: 0, y: 30, scale: 0.9 }, 
        { opacity: 1, y: 0, scale: 1, duration: 0.5, ease: 'back.out(1.7)' }
    );
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
        gsap.to(toast, { 
            opacity: 0, 
            y: -20, 
            scale: 0.9, 
            duration: 0.4, 
            ease: 'power2.in',
            onComplete: () => {
                toast.remove();
            }
        });
    }, 4000);
}

// Form Handling
const bookingForm = document.getElementById('booking-form');
if (bookingForm) {
    bookingForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const btn = bookingForm.querySelector('button');
        const originalText = btn.innerText;
        btn.innerText = translations[currentLang]["contact.form.sending"] || 'Sending...';
        btn.disabled = true;
        
        setTimeout(() => {
            showPremiumToast(translations[currentLang]["contact.form.success"] || 'Thank you!', 'success');
            bookingForm.reset();
            btn.innerText = translations[currentLang]["contact.form.submit"] || 'Send Message';
            btn.disabled = false;
        }, 1500);
    });
}

// Translation Engine
let activeRotatorIndex = 0;
let currentLang = 'en';

function updateFAQSchema(lang) {
    const faqSchemaEl = document.getElementById('faq-schema');
    if (!faqSchemaEl || !translations[lang]) return;
    
    const schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": translations[lang]["faq.q1"] || "",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": translations[lang]["faq.a1"] || ""
                }
            },
            {
                "@type": "Question",
                "name": translations[lang]["faq.q2"] || "",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": translations[lang]["faq.a2"] || ""
                }
            },
            {
                "@type": "Question",
                "name": translations[lang]["faq.q3"] || "",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": translations[lang]["faq.a3"] || ""
                }
            },
            {
                "@type": "Question",
                "name": translations[lang]["faq.q4"] || "",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": translations[lang]["faq.a4"] || ""
                }
            }
        ]
    };
    
    faqSchemaEl.textContent = JSON.stringify(schema, null, 2);
}

function setLanguage(lang) {
    currentLang = lang;
    
    // Translate text contents
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (translations[lang][key]) {
            element.innerText = translations[lang][key];
        }
    });

    // Update currently active rotating text instantly
    const rotatingTextEl = document.getElementById('hero-rotating-text');
    if (rotatingTextEl) {
        const rotatingKeys = [
            "hero.rotate.1",
            "hero.rotate.2",
            "hero.rotate.3",
            "hero.rotate.4",
            "hero.rotate.5"
        ];
        rotatingTextEl.innerText = translations[lang][rotatingKeys[activeRotatorIndex]] || "Feel the Adrenaline";
    }

    // Translate placeholder attributes
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        const key = element.getAttribute('data-i18n-placeholder');
        if (translations[lang][key]) {
            element.setAttribute('placeholder', translations[lang][key]);
        }
    });

    // Dynamically update document title & meta tags for premium SEO
    if (translations[lang]["seo.title"]) {
        document.title = translations[lang]["seo.title"];
    }
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc && translations[lang]["seo.description"]) {
        metaDesc.setAttribute('content', translations[lang]["seo.description"]);
    }
    document.documentElement.lang = lang;
    
    // Update dynamic JSON-LD FAQ Schema for SEO snippets
    updateFAQSchema(lang);

    // Reset open FAQ panels on language switch to prevent layout clipping
    document.querySelectorAll('.faq-item').forEach(item => {
        item.classList.remove('active');
        const panel = item.querySelector('.faq-panel');
        if (panel) panel.style.maxHeight = '0px';
        const icon = item.querySelector('.faq-icon');
        if (icon) {
            icon.textContent = '+';
            icon.style.transform = 'rotate(0deg)';
        }
    });
    
    // Save preference
    localStorage.setItem('preferredLang', lang);

    // Update URL parameter without page reload
    const url = new URL(window.location.href);
    if (lang === 'en') {
        url.searchParams.delete('lang');
    } else {
        url.searchParams.set('lang', lang);
    }
    window.history.replaceState({}, '', url.toString() + window.location.hash);
    
    // Update active dropdown items state
    document.querySelectorAll('.lang-dropdown-item').forEach(btn => {
        const btnLang = btn.getAttribute('data-lang');
        btn.classList.toggle('active', btnLang === lang);
    });
    
    // Update trigger active text
    const activeText = document.getElementById('activeLangText');
    if (activeText) {
        activeText.innerText = lang.toUpperCase();
    }
}

// Language Dropdown Click Handlers
function selectLanguage(lang) {
    setLanguage(lang);
    const menu = document.getElementById('langMenu');
    if (menu) menu.classList.remove('active');
    const arrow = document.querySelector('.lang-dropdown-trigger .arrow');
    if (arrow) arrow.style.transform = 'rotate(0deg)';
}

document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const urlLang = urlParams.get('lang');
    const validLangs = ['en', 'pl', 'es'];
    const savedLang = (urlLang && validLangs.includes(urlLang)) ? urlLang : (localStorage.getItem('preferredLang') || 'en');
    setLanguage(savedLang);

    // Robust Initialization of FAQ Accordion Trigger
    try {
        const triggers = document.querySelectorAll('.faq-trigger');
        triggers.forEach(trigger => {
            trigger.addEventListener('click', () => {
                const item = trigger.parentElement;
                const panel = trigger.nextElementSibling;
                const icon = trigger.querySelector('.faq-icon');
                const isOpen = item.classList.contains('active');
                
                // Close all other panels
                document.querySelectorAll('.faq-item').forEach(otherItem => {
                    if (otherItem !== item) {
                        otherItem.classList.remove('active');
                        const otherPanel = otherItem.querySelector('.faq-panel');
                        if (otherPanel) otherPanel.style.maxHeight = '0px';
                        const otherIcon = otherItem.querySelector('.faq-icon');
                        if (otherIcon) {
                            otherIcon.textContent = '+';
                            otherIcon.style.transform = 'rotate(0deg)';
                        }
                    }
                });
                
                // Toggle current panel
                if (isOpen) {
                    item.classList.remove('active');
                    panel.style.maxHeight = '0px';
                    icon.textContent = '+';
                    icon.style.transform = 'rotate(0deg)';
                } else {
                    item.classList.add('active');
                    panel.style.maxHeight = panel.scrollHeight + "px";
                    icon.textContent = '−';
                    icon.style.transform = 'rotate(180deg)';
                }
            });
        });
    } catch (e) {
        console.error("Failed to initialize FAQ accordion triggers", e);
    }

    // Dropdown Trigger Listener
    const trigger = document.getElementById('langTrigger');
    const menu = document.getElementById('langMenu');
    const arrow = document.querySelector('.lang-dropdown-trigger .arrow');
    
    if (trigger && menu) {
        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            menu.classList.toggle('active');
            if (arrow) {
                arrow.style.transform = menu.classList.contains('active') ? 'rotate(180deg)' : 'rotate(0deg)';
            }
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', () => {
            menu.classList.remove('active');
            if (arrow) arrow.style.transform = 'rotate(0deg)';
        });
    }

    // Register ScrollTrigger
    gsap.registerPlugin(ScrollTrigger);

    // Dynamic Hero Text Rotator using GSAP
    function initHeroTextRotator() {
        const textEl = document.getElementById('hero-rotating-text');
        if (!textEl) return;

        const rotatingKeys = [
            "hero.rotate.1",
            "hero.rotate.2",
            "hero.rotate.3",
            "hero.rotate.4",
            "hero.rotate.5"
        ];

        setInterval(() => {
            gsap.to(textEl, {
                opacity: 0,
                y: -15,
                scale: 0.97,
                duration: 0.35,
                ease: "power2.in",
                onComplete: () => {
                    activeRotatorIndex = (activeRotatorIndex + 1) % rotatingKeys.length;
                    const nextKey = rotatingKeys[activeRotatorIndex];
                    textEl.innerText = translations[currentLang][nextKey] || "Feel the Adrenaline";

                    gsap.fromTo(textEl, 
                        { opacity: 0, y: 15, scale: 0.97 },
                        { opacity: 1, y: 0, scale: 1, duration: 0.5, ease: "back.out(1.2)" }
                    );
                }
            });
        }, 4000);
    }

    initHeroTextRotator();

    // Hero Animation
    gsap.from('.hero-content h1', { opacity: 0, y: 50, duration: 1, delay: 0.2 });
    gsap.from('.hero-content p', { opacity: 0, y: 50, duration: 1, delay: 0.4 });
    gsap.from('.hero-btns', { opacity: 0, y: 50, duration: 1, delay: 0.6 });

    // Parallax Hero
    gsap.to('.hero-bg img', {
        yPercent: 20,
        ease: 'none',
        scrollTrigger: {
            trigger: '.hero',
            start: 'top top',
            end: 'bottom top',
            scrub: true
        }
    });

    // Section Headers
    gsap.utils.toArray('.section h2').forEach(heading => {
        gsap.from(heading, {
            scrollTrigger: {
                trigger: heading,
                start: 'top 80%',
            },
            opacity: 0,
            y: 30,
            duration: 0.8
        });
    });

    // Single Tour Showcase
    const singleTour = document.querySelector('.single-tour-container');
    if (singleTour) {
        gsap.from(singleTour, {
            scrollTrigger: {
                trigger: singleTour,
                start: 'top 85%',
            },
            opacity: 0,
            y: 50,
            duration: 1
        });
    }

    // Booking Widget Section
    const bookingWidget = document.querySelector('.booking-widget-wrapper');
    if (bookingWidget) {
        gsap.from(bookingWidget, {
            scrollTrigger: {
                trigger: bookingWidget,
                start: 'top 85%',
            },
            opacity: 0,
            y: 50,
            duration: 1
        });
    }

    // Gallery Items
    gsap.utils.toArray('.gallery-item').forEach((item, i) => {
        gsap.from(item, {
            scrollTrigger: {
                trigger: item,
                start: 'top 90%',
            },
            opacity: 0,
            scale: 0.8,
            duration: 0.6,
            delay: i % 4 * 0.1
        });
    });

    });
});

// Switch Main Image in Gallery Showcase
function switchMainImage(imgSrc, thumbEl) {
    const mainImg = document.getElementById('tour-main-img');
    if (!mainImg) return;
    
    // Add dynamic transition fade out
    mainImg.style.opacity = '0.3';
    
    setTimeout(() => {
        mainImg.src = imgSrc;
        mainImg.style.opacity = '1';
    }, 200);
    
    // Update active class state on thumbnails
    document.querySelectorAll('.thumb-item').forEach(item => {
        item.classList.remove('active');
    });
    thumbEl.classList.add('active');
}

// Lightbox & 3D Mobile Card Stack Gallery
document.addEventListener('DOMContentLoaded', () => {
    const desktopImages = document.querySelectorAll('.gallery-grid .gallery-item img');
    const lightbox = document.getElementById('lightboxModal');
    const lightboxImg = document.getElementById('lightbox-img');
    const lightboxClose = document.querySelector('.lightbox-close');
    const lightboxPrev = document.querySelector('.lightbox-prev');
    const lightboxNext = document.querySelector('.lightbox-next');
    const lightboxCounter = document.querySelector('.lightbox-counter');
    
    if (!lightbox) return;

    let currentIndex = 0;
    const imagesArray = Array.from(desktopImages).map(img => img.src);

    function showImage(index) {
        if (index < 0) index = imagesArray.length - 1;
        if (index >= imagesArray.length) index = 0;
        currentIndex = index;
        
        lightboxImg.style.opacity = '0';
        lightboxImg.style.transform = 'scale(0.95)';
        
        setTimeout(() => {
            lightboxImg.src = imagesArray[currentIndex];
            lightboxImg.style.opacity = '1';
            lightboxImg.style.transform = 'scale(1)';
            lightboxCounter.innerText = `${currentIndex + 1} / ${imagesArray.length}`;
        }, 150);
    }

    // Expose showImage globally to call it from Card Stack clicks
    window.showLightboxImage = showImage;

    // Desktop gallery clicks
    desktopImages.forEach((img, index) => {
        img.addEventListener('click', () => {
            lightbox.classList.add('active');
            showImage(index);
            document.body.style.overflow = 'hidden';
        });
    });

    if (lightboxClose) {
        lightboxClose.addEventListener('click', () => {
            lightbox.classList.remove('active');
            document.body.style.overflow = '';
        });
    }

    if (lightboxPrev) {
        lightboxPrev.addEventListener('click', (e) => {
            e.stopPropagation();
            showImage(currentIndex - 1);
        });
    }

    if (lightboxNext) {
        lightboxNext.addEventListener('click', (e) => {
            e.stopPropagation();
            showImage(currentIndex + 1);
        });
    }

    // Close on overlay click
    lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox || e.target.classList.contains('lightbox-content')) {
            lightbox.classList.remove('active');
            document.body.style.overflow = '';
        }
    });

    // Keyboard support
    document.addEventListener('keydown', (e) => {
        if (!lightbox.classList.contains('active')) return;
        if (e.key === 'Escape') {
            lightbox.classList.remove('active');
            document.body.style.overflow = '';
        } else if (e.key === 'ArrowLeft') {
            showImage(currentIndex - 1);
        } else if (e.key === 'ArrowRight') {
            showImage(currentIndex + 1);
        }
    });

    // Innovative 3D Card Stack Gallery logic (Mobile-Only)
    const deck = document.querySelector('.gallery-card-deck');
    const cards = document.querySelectorAll('.gallery-card');
    const prevBtn = document.getElementById('stackPrev');
    const nextBtn = document.getElementById('stackNext');
    const stackInfo = document.getElementById('stackInfo');
    
    if (deck && cards.length > 0) {
        let activeIndex = 0;
        const totalCards = cards.length;
        
        function arrangeCards() {
            cards.forEach((card, index) => {
                let order = (index - activeIndex + totalCards) % totalCards;
                
                if (order < 3) {
                    card.style.display = 'block';
                    card.style.zIndex = totalCards - order;
                    
                    gsap.to(card, {
                        y: order * 18,
                        scale: 1 - order * 0.05,
                        z: -order * 30,
                        rotateX: -order * 2,
                        opacity: 1 - order * 0.25,
                        duration: 0.45,
                        ease: 'power2.out',
                        overwrite: 'auto'
                    });
                } else {
                    card.style.display = 'none';
                    card.style.opacity = '0';
                }
            });
            
            if (stackInfo) {
                stackInfo.innerText = `${activeIndex + 1} / ${totalCards}`;
            }
        }
        
        arrangeCards();
        
        cards.forEach((card, index) => {
            let isDragging = false;
            let startX = 0;
            let startY = 0;
            let currentX = 0;
            let currentY = 0;
            
            card.addEventListener('pointerdown', (e) => {
                let order = (index - activeIndex + totalCards) % totalCards;
                if (order !== 0) return;
                
                isDragging = true;
                startX = e.clientX;
                startY = e.clientY;
                card.setPointerCapture(e.pointerId);
                
                gsap.killTweensOf(card);
            });
            
            card.addEventListener('pointermove', (e) => {
                if (!isDragging) return;
                
                currentX = e.clientX - startX;
                currentY = e.clientY - startY;
                
                gsap.set(card, {
                    x: currentX,
                    y: currentY,
                    rotate: currentX * 0.05,
                    rotateY: currentX * 0.02
                });
            });
            
            card.addEventListener('pointerup', (e) => {
                if (!isDragging) return;
                isDragging = false;
                card.releasePointerCapture(e.pointerId);
                
                const dragThreshold = 100;
                
                if (Math.abs(currentX) > dragThreshold) {
                    const swipeDirection = currentX > 0 ? 1 : -1;
                    
                    gsap.to(card, {
                        x: swipeDirection * 500,
                        y: currentY + (currentY > 0 ? 100 : -100),
                        rotate: swipeDirection * 45,
                        opacity: 0,
                        duration: 0.5,
                        ease: 'power2.in',
                        onComplete: () => {
                            activeIndex = (activeIndex + 1) % totalCards;
                            arrangeCards();
                        }
                    });
                } else {
                    // Tap detection (minimal drag)
                    if (Math.abs(currentX) < 5 && Math.abs(currentY) < 5) {
                        if (lightbox) {
                            lightbox.classList.add('active');
                            showImage(index);
                            document.body.style.overflow = 'hidden';
                        }
                    } else {
                        // Snap back
                        gsap.to(card, {
                            x: 0,
                            y: 0,
                            rotate: 0,
                            rotateY: 0,
                            duration: 0.4,
                            ease: 'back.out(1.5)'
                        });
                    }
                }
                
                currentX = 0;
                currentY = 0;
            });
            
            card.addEventListener('pointercancel', () => {
                if (!isDragging) return;
                isDragging = false;
                gsap.to(card, {
                    x: 0,
                    y: 0,
                    rotate: 0,
                    rotateY: 0,
                    duration: 0.4,
                    ease: 'back.out(1.5)'
                });
            });
        });
        
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                let frontCard = cards[activeIndex];
                gsap.to(frontCard, {
                    x: 500,
                    rotate: 45,
                    opacity: 0,
                    duration: 0.5,
                    ease: 'power2.in',
                    onComplete: () => {
                        activeIndex = (activeIndex + 1) % totalCards;
                        arrangeCards();
                    }
                });
            });
        }
        
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                activeIndex = (activeIndex - 1 + totalCards) % totalCards;
                let newFrontCard = cards[activeIndex];
                arrangeCards();
                
                gsap.fromTo(newFrontCard, 
                    { x: -500, rotate: -45, opacity: 0 },
                    { x: 0, rotate: 0, opacity: 1, duration: 0.5, ease: 'power2.out' }
                );
            });
        }
    }

    // --- WhatsApp Booking Form Logic ---
    let singleQuadsCount = 0;
    let doubleQuadsCount = 0;

    function adjustQuad(type, amount) {
        if (type === 'single') {
            singleQuadsCount = Math.max(0, singleQuadsCount + amount);
            const countEl = document.getElementById('single-quad-count');
            if (countEl) countEl.innerText = singleQuadsCount;
        } else if (type === 'double') {
            doubleQuadsCount = Math.max(0, doubleQuadsCount + amount);
            const countEl = document.getElementById('double-quad-count');
            if (countEl) countEl.innerText = doubleQuadsCount;
        }
        updateBookingPrice();
    }

    function updateBookingPrice() {
        const totalPrice = (singleQuadsCount * 120) + (doubleQuadsCount * 140);
        const priceEl = document.getElementById('booking-total-price');
        if (priceEl) {
            priceEl.innerText = `€${totalPrice}`;
        }
    }

    // Expose functions globally for HTML onclick attributes
    window.adjustQuad = adjustQuad;
    window.updateBookingPrice = updateBookingPrice;

    // Set minimum date to today
    const bookingDateInput = document.getElementById('booking-date');
    if (bookingDateInput) {
        const today = new Date().toISOString().split('T')[0];
        bookingDateInput.setAttribute('min', today);
    }

    // Handle Form Submit
    const whatsappBookingForm = document.getElementById('whatsapp-booking-form');
    if (whatsappBookingForm) {
        whatsappBookingForm.addEventListener('submit', (e) => {
            e.preventDefault();

            if (singleQuadsCount === 0 && doubleQuadsCount === 0) {
                const errorMsg = translations[currentLang]["booking.form.validation.quads"] || "Please select at least 1 quad bike.";
                showPremiumToast(errorMsg, "error");
                return;
            }

            const date = document.getElementById('booking-date').value;
            const time = document.getElementById('booking-time').value;
            const name = document.getElementById('booking-name').value;
            const phone = document.getElementById('booking-phone').value;
            const email = document.getElementById('booking-email').value;
            const total = (singleQuadsCount * 120) + (doubleQuadsCount * 140);

            let message = "";
            if (currentLang === 'pl') {
                message = `Cześć Prime Quads! Chcę zarezerwować wycieczkę:\n\n` +
                          `🏔️ Wycieczka: Teide National Park Quad Expedition\n` +
                          `📅 Data: ${date}\n` +
                          `🕒 Godzina: ${time}\n` +
                          `🏍️ Quady pojedyncze: ${singleQuadsCount} (1-osobowe)\n` +
                          `🏍️ Quady podwójne: ${doubleQuadsCount} (2-osobowe)\n` +
                          `💰 Łączna kwota: €${total}\n\n` +
                          `Dane kontaktowe:\n` +
                          `👤 Imię i nazwisko: ${name}\n` +
                          `📞 Telefon: ${phone}\n` +
                          `✉️ E-mail: ${email}`;
            } else if (currentLang === 'es') {
                message = `¡Hola Prime Quads! Quiero reservar una excursión:\n\n` +
                          `🏔️ Excursión: Teide National Park Quad Expedition\n` +
                          `📅 Fecha: ${date}\n` +
                          `🕒 Horario: ${time}\n` +
                          `🏍️ Quads individuales: ${singleQuadsCount} (1 persona)\n` +
                          `🏍️ Quads dobles: ${doubleQuadsCount} (2 personas)\n` +
                          `💰 Precio total: €${total}\n\n` +
                          `Datos de contacto:\n` +
                          `👤 Nombre completo: ${name}\n` +
                          `📞 Teléfono: ${phone}\n` +
                          `✉️ Email: ${email}`;
            } else {
                message = `Hello Prime Quads! I would like to book a tour:\n\n` +
                          `🏔️ Tour: Teide National Park Quad Expedition\n` +
                          `📅 Date: ${date}\n` +
                          `🕒 Time: ${time}\n` +
                          `🏍️ Single Quads: ${singleQuadsCount} (1 person)\n` +
                          `🏍️ Double Quads: ${doubleQuadsCount} (2 people)\n` +
                          `💰 Total Price: €${total}\n\n` +
                          `Contact info:\n` +
                          `👤 Full Name: ${name}\n` +
                          `📞 Phone: ${phone}\n` +
                          `✉️ Email: ${email}`;
            }

            const encodedText = encodeURIComponent(message);
            const whatsappNumber = "34711075369"; // Business WhatsApp Number
            const whatsappUrl = `https://wa.me/${whatsappNumber}?text=${encodedText}`;

            window.open(whatsappUrl, '_blank');

            const redirectingMsg = currentLang === 'pl' ? 'Przekierowanie do WhatsApp...' : (currentLang === 'es' ? 'Redirigiendo a WhatsApp...' : 'Redirecting to WhatsApp...');
            showPremiumToast(redirectingMsg, 'success');
        });
    }
});
