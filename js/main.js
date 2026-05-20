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
let currentLang = 'en';

function setLanguage(lang) {
    currentLang = lang;
    
    // Translate text contents
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (translations[lang][key]) {
            element.innerText = translations[lang][key];
        }
    });

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
    
    // Save preference
    localStorage.setItem('preferredLang', lang);
    
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

// GSAP & Dropdown Listeners Init
document.addEventListener('DOMContentLoaded', () => {
    const savedLang = localStorage.getItem('preferredLang') || 'en';
    setLanguage(savedLang);

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
