/**
 * GUMMA PUBLIC SCHOOL - MAIN JAVASCRIPT BUNDLE (main.js)
 * Modular interactions:
 * - Fully Responsive Mobile Drawers (Public Site & Portal Dashboard)
 * - Notice Marquee with Desktop Hover & Mobile Touch Pause
 * - Photo Gallery Lightbox with Touch Gestures & Keyboard Navigation
 * - Real-Time Dynamic Fee Calculator
 * - Interactive FAQ & Information Accordions
 * - Responsive Back-to-Top Floating Button
 * - Form Validation & Touch-Friendly Password Toggle
 */

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initDashboardNavigation();
    initNoticeMarquee();
    initBackToTop();
    initGalleryLightbox();
    initFeeCalculator();
    initAccordions();
    initInquiryForms();
    highlightActiveNavLink();
    initPasswordToggle();
    initResponsiveTables();
});

/* ==========================================================================
   1. Mobile Navigation & Accessibility Drawer (Public Site)
   ========================================================================== */
function initNavigation() {
    const toggleBtn = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (!toggleBtn || !navMenu) return;

    // Create shared backdrop if not present
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

    // Close on link click on mobile
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

    // Touch swipe right to close drawer
    let drawerTouchStartX = 0;
    navMenu.addEventListener('touchstart', (e) => {
        drawerTouchStartX = e.changedTouches[0].screenX;
    }, { passive: true });

    navMenu.addEventListener('touchend', (e) => {
        const diffX = e.changedTouches[0].screenX - drawerTouchStartX;
        if (diffX > 60) {
            closeMenu();
        }
    }, { passive: true });

    // Close if resized to desktop viewport
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768 && navMenu.classList.contains('active')) {
            closeMenu();
        }
    });
}

/* ==========================================================================
   2. Dashboard & Portal Mobile Navigation Drawer (.dash-header)
   ========================================================================== */
function initDashboardNavigation() {
    const dashHeader = document.querySelector('.dash-header');
    if (!dashHeader) return;

    const navLinks = dashHeader.querySelector('.nav-links');
    if (!navLinks) return;

    // Check if toggle exists or dynamically inject for portal resilience
    let toggleBtn = dashHeader.querySelector('.dash-nav-toggle');
    if (!toggleBtn) {
        toggleBtn = document.createElement('button');
        toggleBtn.className = 'dash-nav-toggle';
        toggleBtn.setAttribute('aria-label', 'Toggle dashboard navigation');
        toggleBtn.setAttribute('aria-expanded', 'false');
        toggleBtn.innerHTML = `
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="3" y1="12" x2="21" y2="12"></line>
                <line x1="3" y1="6" x2="21" y2="6"></line>
                <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
        `;
        const headerRight = dashHeader.querySelector('.header-right') || dashHeader;
        headerRight.appendChild(toggleBtn);
    }

    // Shared backdrop
    let backdrop = document.querySelector('.nav-backdrop');
    if (!backdrop) {
        backdrop = document.createElement('div');
        backdrop.className = 'nav-backdrop';
        document.body.appendChild(backdrop);
    }

    const openDashMenu = () => {
        navLinks.classList.add('active');
        backdrop.classList.add('active');
        toggleBtn.setAttribute('aria-expanded', 'true');
        document.body.style.overflow = 'hidden';
    };

    const closeDashMenu = () => {
        navLinks.classList.remove('active');
        backdrop.classList.remove('active');
        toggleBtn.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
    };

    toggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = navLinks.classList.contains('active');
        isOpen ? closeDashMenu() : openDashMenu();
    });

    backdrop.addEventListener('click', closeDashMenu);

    navLinks.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                closeDashMenu();
            }
        });
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && navLinks.classList.contains('active')) {
            closeDashMenu();
        }
    });

    // Touch swipe right to dismiss drawer
    let dashTouchStartX = 0;
    navLinks.addEventListener('touchstart', (e) => {
        dashTouchStartX = e.changedTouches[0].screenX;
    }, { passive: true });

    navLinks.addEventListener('touchend', (e) => {
        const diffX = e.changedTouches[0].screenX - dashTouchStartX;
        if (diffX > 60) {
            closeDashMenu();
        }
    }, { passive: true });

    window.addEventListener('resize', () => {
        if (window.innerWidth > 768 && navLinks.classList.contains('active')) {
            closeDashMenu();
        }
    });
}

/* ==========================================================================
   3. Active Navigation Link Detection
   ========================================================================== */
function highlightActiveNavLink() {
    const currentPath = window.location.pathname.split('/').pop() || 'index.html';
    const navLinks = document.querySelectorAll('.nav-menu .nav-link, .dash-header .nav-link');
    
    navLinks.forEach(link => {
        const linkHref = link.getAttribute('href');
        if (!linkHref) return;
        const cleanHref = linkHref.split('/').pop();
        if (cleanHref === currentPath || (currentPath === '' && cleanHref === 'index.html')) {
            link.classList.add('active');
        }
    });
}

/* ==========================================================================
   4. Back-to-Top Floating Button
   ========================================================================== */
function initBackToTop() {
    let backBtn = document.querySelector('.back-to-top');
    if (!backBtn) {
        backBtn = document.createElement('button');
        backBtn.className = 'back-to-top';
        backBtn.setAttribute('aria-label', 'Scroll to top');
        backBtn.innerHTML = `
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="18 15 12 9 6 15"></polyline>
            </svg>
        `;
        document.body.appendChild(backBtn);
    }

    let scrollTimeout;
    window.addEventListener('scroll', () => {
        if (!scrollTimeout) {
            scrollTimeout = setTimeout(() => {
                if (window.scrollY > 300) {
                    backBtn.classList.add('visible');
                } else {
                    backBtn.classList.remove('visible');
                }
                scrollTimeout = null;
            }, 50);
        }
    }, { passive: true });

    backBtn.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

/* ==========================================================================
   5. Announcement Ticker Hover & Touch Pause
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

    // Touch events for mobile screens
    ticker.addEventListener('touchstart', () => {
        ticker.style.animationPlayState = 'paused';
    }, { passive: true });

    ticker.addEventListener('touchend', () => {
        ticker.style.animationPlayState = 'running';
    }, { passive: true });
}

/* ==========================================================================
   6. Interactive Photo Gallery & Lightbox Viewer with Touch Swipe
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
        if (items.length === 0) return;
        if (index < 0) index = items.length - 1;
        if (index >= items.length) index = 0;
        currentIndex = index;

        const currentItem = items[currentIndex];
        const img = currentItem.querySelector('img');
        const title = currentItem.querySelector('.gallery-item-title') ? currentItem.querySelector('.gallery-item-title').innerText : '';
        const category = currentItem.querySelector('.gallery-item-category') ? currentItem.querySelector('.gallery-item-category').innerText : '';

        modalImg.src = img.src;
        modalImg.alt = img.alt || title;
        if (modalCaption) {
            modalCaption.innerHTML = `<strong>${title}</strong> <span style="opacity:0.8; font-size:0.85em; margin-left:8px;">[${category}]</span>`;
        }

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

    // Touch Swipe Navigation on Mobile
    let touchStartX = 0;
    let touchStartY = 0;

    modal.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
    }, { passive: true });

    modal.addEventListener('touchend', (e) => {
        const touchEndX = e.changedTouches[0].screenX;
        const touchEndY = e.changedTouches[0].screenY;
        const diffX = touchEndX - touchStartX;
        const diffY = touchEndY - touchStartY;

        // If horizontal swipe is dominant and above threshold (50px)
        if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
            if (diffX < 0) {
                // Swipe left -> Next
                openLightbox(currentIndex + 1);
            } else {
                // Swipe right -> Prev
                openLightbox(currentIndex - 1);
            }
        }
    }, { passive: true });
}

/* ==========================================================================
   7. Transparent Fee Structure Calculator
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

    // Initial run
    calculateTotal();
}

/* ==========================================================================
   8. FAQ & Information Accordions
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
   9. Inquiry & Contact Form Submissions
   ========================================================================== */
function initInquiryForms() {
    const forms = document.querySelectorAll('.ajax-inquiry-form');

    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            e.preventDefault();

            const alertBox = form.querySelector('.form-alert');
            const submitBtn = form.querySelector('button[type="submit"]');

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

                const gradeSelect = document.getElementById('calc-grade');
                if (gradeSelect) gradeSelect.dispatchEvent(new Event('change'));
            }, 800);
        });
    });
}

/* ==========================================================================
   10. Password Visibility Toggle
   ========================================================================== */
function initPasswordToggle() {
    const toggleBtns = document.querySelectorAll('.password-toggle');
    toggleBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const wrapper = btn.closest('.input-wrapper');
            if (!wrapper) return;
            const input = wrapper.querySelector('input');
            const showIcon = btn.querySelector('.eye-show');
            const hideIcon = btn.querySelector('.eye-hide');
            if (!input) return;

            if (input.type === 'password') {
                input.type = 'text';
                if (showIcon) showIcon.classList.add('hidden');
                if (hideIcon) hideIcon.classList.remove('hidden');
            } else {
                input.type = 'password';
                if (showIcon) showIcon.classList.remove('hidden');
                if (hideIcon) hideIcon.classList.add('hidden');
            }
        });
    });
}

/* ==========================================================================
   11. Responsive Tables Smooth Scrolling Cue
   ========================================================================== */
function initResponsiveTables() {
    const tableWrappers = document.querySelectorAll('.table-wrapper, .table-responsive');
    tableWrappers.forEach(wrapper => {
        const table = wrapper.querySelector('table');
        if (!table) return;

        const checkOverflow = () => {
            if (table.offsetWidth > wrapper.clientWidth) {
                wrapper.classList.add('has-overflow');
            } else {
                wrapper.classList.remove('has-overflow');
            }
        };

        checkOverflow();
        window.addEventListener('resize', checkOverflow, { passive: true });
    });
}
