/**
 * GUMMA PUBLIC SCHOOL - MAIN JAVASCRIPT BUNDLE (main.js)
 * Modular interactions: Mobile Drawer, Notice Marquee, Gallery Lightbox,
 * Fee Calculator, FAQ Accordion, Back-to-Top, and Form Validation.
 */

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initNoticeMarquee();
    initBackToTop();
    initGalleryLightbox();
    initFeeCalculator();
    initAccordions();
    initInquiryForms();
    highlightActiveNavLink();
});

/* ==========================================================================
   1. Mobile Navigation & Accessibility Drawer
   ========================================================================== */
function initNavigation() {
    const toggleBtn = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (!toggleBtn || !navMenu) return;

    // Create backdrop if not present
    let backdrop = document.querySelector('.nav-backdrop');
    if (!backdrop) {
        backdrop = document.createElement('div');
        backdrop.className = 'nav-backdrop';
        document.body.appendChild(backdrop);
    }

    const openMenu = () => {
        navMenu.classList.add('active');
        backdrop.classList.add('active');
        toggleBtn.setAttribute('aria-expanded', 'true');
        document.body.style.overflow = 'hidden';
    };

    const closeMenu = () => {
        navMenu.classList.remove('active');
        backdrop.classList.remove('active');
        toggleBtn.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
    };

    toggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = navMenu.classList.contains('active');
        isOpen ? closeMenu() : openMenu();
    });

    backdrop.addEventListener('click', closeMenu);

    // Close on link click
    const navLinks = navMenu.querySelectorAll('.nav-link, .btn');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                closeMenu();
            }
        });
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && navMenu.classList.contains('active')) {
            closeMenu();
        }
    });

    // Close if resized to desktop
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768 && navMenu.classList.contains('active')) {
            closeMenu();
        }
    });
}

/* ==========================================================================
   2. Active Navigation Link Detection
   ========================================================================== */
function highlightActiveNavLink() {
    const currentPath = window.location.pathname.split('/').pop() || 'index.html';
    const navLinks = document.querySelectorAll('.nav-menu .nav-link');
    
    navLinks.forEach(link => {
        const linkHref = link.getAttribute('href');
        if (linkHref === currentPath || (currentPath === '' && linkHref === 'index.html')) {
            link.classList.add('active');
        } else if (linkHref !== currentPath && linkHref !== 'index.html') {
            link.classList.remove('active');
        }
    });
}

/* ==========================================================================
   3. Back-to-Top Floating Button
   ========================================================================== */
function initBackToTop() {
    const backBtn = document.querySelector('.back-to-top');
    if (!backBtn) return;

    window.addEventListener('scroll', () => {
        if (window.scrollY > 350) {
            backBtn.classList.add('visible');
        } else {
            backBtn.classList.remove('visible');
        }
    });

    backBtn.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

/* ==========================================================================
   4. Announcement Ticker Hover Pause
   ========================================================================== */
function initNoticeMarquee() {
    const ticker = document.querySelector('.ticker-track');
    if (!ticker) return;

    ticker.addEventListener('mouseenter', () => {
        ticker.style.animationPlayState = 'paused';
    });

    ticker.addEventListener('mouseleave', () => {
        ticker.style.animationPlayState = 'running';
    });
}

/* ==========================================================================
   5. Interactive Photo Gallery & Lightbox Viewer
   ========================================================================== */
function initGalleryLightbox() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    const galleryItems = Array.from(document.querySelectorAll('.gallery-item'));
    const modal = document.querySelector('.lightbox-modal');

    // Filter Functionality
    if (filterButtons.length && galleryItems.length) {
        filterButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                filterButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const filterValue = btn.getAttribute('data-filter');

                galleryItems.forEach(item => {
                    const category = item.getAttribute('data-category');
                    if (filterValue === 'all' || category === filterValue) {
                        item.style.display = 'block';
                        setTimeout(() => { item.style.opacity = '1'; }, 10);
                    } else {
                        item.style.opacity = '0';
                        setTimeout(() => { item.style.display = 'none'; }, 200);
                    }
                });
            });
        });
    }

    // Lightbox Functionality
    if (!modal || !galleryItems.length) return;

    const modalImg = modal.querySelector('.lightbox-img');
    const modalCaption = modal.querySelector('.lightbox-caption');
    const closeBtn = modal.querySelector('.lightbox-close');
    const prevBtn = modal.querySelector('.lightbox-prev');
    const nextBtn = modal.querySelector('.lightbox-next');

    let currentIndex = 0;
    let visibleItems = () => galleryItems.filter(item => item.style.display !== 'none');

    function openLightbox(index) {
        const items = visibleItems();
        if (index < 0) index = items.length - 1;
        if (index >= items.length) index = 0;
        currentIndex = index;

        const currentItem = items[currentIndex];
        const img = currentItem.querySelector('img');
        const title = currentItem.querySelector('.gallery-item-title') ? currentItem.querySelector('.gallery-item-title').innerText : '';
        const category = currentItem.querySelector('.gallery-item-category') ? currentItem.querySelector('.gallery-item-category').innerText : '';

        modalImg.src = img.src;
        modalImg.alt = img.alt || title;
        modalCaption.innerHTML = `<strong>${title}</strong> <span style="opacity:0.8; font-size:0.85em; margin-left:8px;">[${category}]</span>`;

        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeLightbox() {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }

    galleryItems.forEach(item => {
        item.addEventListener('click', () => {
            const items = visibleItems();
            const index = items.indexOf(item);
            if (index !== -1) {
                openLightbox(index);
            }
        });
    });

    if (closeBtn) closeBtn.addEventListener('click', closeLightbox);
    if (prevBtn) prevBtn.addEventListener('click', () => openLightbox(currentIndex - 1));
    if (nextBtn) nextBtn.addEventListener('click', () => openLightbox(currentIndex + 1));

    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeLightbox();
    });

    document.addEventListener('keydown', (e) => {
        if (!modal.classList.contains('active')) return;
        if (e.key === 'Escape') closeLightbox();
        if (e.key === 'ArrowLeft') openLightbox(currentIndex - 1);
        if (e.key === 'ArrowRight') openLightbox(currentIndex + 1);
    });
}

/* ==========================================================================
   6. Transparent Fee Structure Calculator
   ========================================================================== */
function initFeeCalculator() {
    const gradeSelect = document.getElementById('calc-grade');
    const transportSelect = document.getElementById('calc-transport');
    const activityCheckboxes = document.querySelectorAll('.calc-addon');
    const totalDisplay = document.getElementById('calc-total-val');
    const quarterlyDisplay = document.getElementById('calc-quarterly-val');

    if (!gradeSelect || !totalDisplay) return;

    function calculateTotal() {
        const tuitionFee = parseInt(gradeSelect.value, 10) || 0;
        const transportFee = transportSelect ? (parseInt(transportSelect.value, 10) || 0) : 0;
        
        let addonTotal = 0;
        if (activityCheckboxes) {
            activityCheckboxes.forEach(cb => {
                if (cb.checked) {
                    addonTotal += parseInt(cb.value, 10) || 0;
                }
            });
        }

        const annualTotal = tuitionFee + transportFee + addonTotal;
        const quarterlyTotal = Math.round(annualTotal / 4);

        totalDisplay.innerText = `₹${annualTotal.toLocaleString('en-IN')}`;
        if (quarterlyDisplay) {
            quarterlyDisplay.innerText = `₹${quarterlyTotal.toLocaleString('en-IN')}`;
        }
    }

    gradeSelect.addEventListener('change', calculateTotal);
    if (transportSelect) transportSelect.addEventListener('change', calculateTotal);
    if (activityCheckboxes) {
        activityCheckboxes.forEach(cb => cb.addEventListener('change', calculateTotal));
    }

    // Initial calculation run
    calculateTotal();
}

/* ==========================================================================
   7. FAQ & Information Accordions
   ========================================================================== */
function initAccordions() {
    const headers = document.querySelectorAll('.accordion-header');
    
    headers.forEach(header => {
        header.addEventListener('click', () => {
            const item = header.parentElement;
            const isOpen = item.classList.contains('active');

            // Close other sibling items in same accordion
            const parent = item.parentElement;
            if (parent) {
                const siblings = parent.querySelectorAll('.accordion-item');
                siblings.forEach(s => s.classList.remove('active'));
            }

            if (!isOpen) {
                item.classList.add('active');
            }
        });
    });
}

/* ==========================================================================
   8. Inquiry & Contact Form Submissions
   ========================================================================== */
function initInquiryForms() {
    const forms = document.querySelectorAll('.ajax-inquiry-form');

    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            e.preventDefault();

            const alertBox = form.querySelector('.form-alert');
            const submitBtn = form.querySelector('button[type="submit"]');

            // Visual feedback
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerText = 'Submitting...';
            }

            setTimeout(() => {
                if (alertBox) {
                    alertBox.className = 'form-alert success';
                    alertBox.innerText = 'Thank you! Your query has been received. Our Admissions Office will reach out within 24 hours.';
                    alertBox.style.display = 'block';
                }
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerText = 'Message Sent Successfully ✓';
                }
                form.reset();

                // Recalculate fee if exists
                const gradeSelect = document.getElementById('calc-grade');
                if (gradeSelect) gradeSelect.dispatchEvent(new Event('change'));
            }, 800);
        });
    });
}
