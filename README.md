# Gumma Public School — Official Webpage

> **Knowledge • Integrity • Excellence**  
> A modern, responsive, and deployable institutional website for **Gumma Public School**, Gajapati District, Odisha (CBSE Affiliated).

---

## 🏛️ Project Overview

This repository houses the complete, production-ready static website for Gumma Public School. Engineered with clean semantic HTML5, modern vanilla CSS3 design systems, and modular vanilla JavaScript, it is completely self-contained and ready for immediate one-click deployment on **GitHub Pages**, **Vercel**, or **Netlify**.

---

## 📁 Repository Structure

```
-Gumma-Public-School_Webpage/
├── index.html              # Main homepage (Hero, Notice ticker, Stats, Facilities preview)
├── about.html              # Vision, mission, history, principal's desk, safety accreditations
├── academics.html          # CBSE curriculum pathways, labs, faculty directory, rules
├── admissions.html         # Age eligibility matrix, interactive fee calculator, document checklist
├── gallery.html            # Category-filterable campus photo gallery & Lightbox modal
├── contact.html            # Interactive inquiry form, direct directory, and embedded Google Map
├── css/
│   ├── style.css           # Global institutional design system & components
│   └── responsive.css      # Fluid breakpoints & mobile navigation drawer
├── js/
│   └── main.js             # Navigation toggle, notice marquee, lightbox, calculator, form handlers
├── assets/
│   ├── images/             # Optimized campus, laboratory, library, sports, and crest imagery
│   │   ├── campus_hero.jpg
│   │   ├── school_emblem.jpg
│   │   ├── science_lab.jpg
│   │   ├── library_reading.jpg
│   │   ├── sports_ground.jpg
│   │   ├── computer_lab.jpg
│   │   ├── principal_portrait.jpg
│   │   └── annual_day_event.jpg
│   └── docs/               # Downloadable sample PDFs
│       ├── GPS_Admission_Brochure_2026_27.pdf
│       ├── GPS_Admission_Application_Form.pdf
│       └── GPS_Syllabus_Curriculum_Guide.pdf
├── README.md               # Repository documentation & deployment guide
└── .gitignore              # Repository hygiene rules
```

---

## 🎨 UI/UX Design System & Aesthetics

- **Primary Colors**: Deep Academic Blue (`#0d2f62`, `#071c3c`, `#1a4484`) reflecting trust, scholarship, and tradition.
- **Accent Color**: Warm Amber / Gold (`#d97706`, `#f59e0b`) for buttons, badges, highlights, and notice banners.
- **Surfaces & Backgrounds**: Crisp clean whites (`#ffffff`) and cool slate off-white (`#f8fafc`, `#f1f5f9`).
- **Typography**:
  - **Headings**: *Playfair Display* — grounded, authoritative institutional serif.
  - **Body & Controls**: *Outfit* — modern, ultra-clean, high legibility on mobile screens.

---

## ⚡ Key Features

1. **📢 Announcement Ticker**:
   - Scrolling notice bar for live announcements, admissions deadlines, and exam notifications with hover-pause functionality.
2. **🧮 Interactive Fee Calculator**:
   - Dynamic real-time calculation of annual tuition, school bus route options, and extracurricular kits with quarterly installment breakdown.
3. **🖼️ Interactive Photo Gallery & Lightbox**:
   - Filterable categories (*Campus*, *Academics & Labs*, *Sports*, *Annual Day*).
   - Fullscreen Lightbox modal viewer supporting mouse navigation and keyboard arrow keys (`←`, `→`, `Esc`).
4. **📱 Responsive Mobile Drawer**:
   - Touch-friendly hamburger navigation with background blur backdrop, focus management, and automatic close on link selection or outside click.
5. **📋 Admissions & Age Matrix**:
   - Transparent age criteria table compliant with National Education Policy (NEP) guidelines and document checklists.
6. **🗺️ Interactive Map & Direct Calling**:
   - Integrated Google Maps embed for Gumma, Odisha with click-to-call (`tel:+91...`) and click-to-email (`mailto:...`) actions.

---

## 🚀 Deployment Guide

### Option 1: GitHub Pages (Recommended)
1. Push this repository to GitHub:
   ```bash
   git add .
   git commit -m "Deploy Gumma Public School website"
   git push origin main
   ```
2. Navigate to your repository **Settings** > **Pages**.
3. Under **Build and deployment** > **Branch**, select `main` / `root` and click **Save**.
4. Your website will be live at `https://<username>.github.io/<repo-name>/`.

### Option 2: Vercel
1. Import the repository in [Vercel Dashboard](https://vercel.com).
2. Framework Preset: **Other** (Root directory: `./`).
3. Click **Deploy**.

### Option 3: Local Preview
Open any `.html` file directly in any modern browser, or run a local lightweight web server:
```bash
# Using Python
python -m http.server 8000

# Using Node.js npx serve
npx serve .
```
Then visit `http://localhost:8000` in your web browser.

---

## 🛡️ Technical Standards & Accessibility
- **Meta Viewport**: Configured on all HTML documents (`<meta name="viewport" content="width=device-width, initial-scale=1.0">`).
- **Image Optimization**: All campus photography compressed and optimized under 160 KB for rapid 3G/4G loading.
- **Semantic Structure**: Proper `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<aside>`, and `<footer>` landmarks.
- **ARIA & Accessibility**: Form controls labeled, navigation landmarks tagged, and descriptive `alt` texts on all imagery.

---

&copy; 2026 Gumma Public School. All Rights Reserved.