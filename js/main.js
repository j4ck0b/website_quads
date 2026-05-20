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

// Form Handling
const bookingForm = document.getElementById('booking-form');
if (bookingForm) {
    bookingForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const btn = bookingForm.querySelector('button');
        btn.innerText = 'Sending...';
        btn.disabled = true;
        
        setTimeout(() => {
            alert('Thank you for your request! We will contact you soon.');
            bookingForm.reset();
            btn.innerText = 'Send Booking Request';
            btn.disabled = false;
        }, 1500);
    });
}

// Translation Engine
let currentLang = 'en';

function setLanguage(lang) {
    currentLang = lang;
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (translations[lang][key]) {
            element.innerText = translations[lang][key];
        }
    });
    
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
