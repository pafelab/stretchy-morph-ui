#!/usr/bin/env python3
"""
Scan a user's front-end code or live website for UI that could become stretchy morph UI.

Usage:
  python audit_ui.py PATH_OR_URL [PATH_OR_URL ...] [--json] [--max-hits 6]
                     [--dom] [--stdin] [--ext .html]
                     [--wait-ms 1500] [--viewport 1280x900] [--channel chromium|msedge|chrome]

PATH_OR_URL can be local files, local directories, or live http(s):// URLs.
- Local files/directories are scanned statically (zero external dependencies) across HTML,
  CSS/SCSS/Less/Stylus, JS/TS/JSX/TSX/MDX, Vue, Svelte, Astro, Angular, Web Components,
  and server/CMS templates (PHP/Blade, ERB, Twig, Handlebars, Nunjucks, Liquid, EJS, Pug,
  Jinja2/Django, Razor/Blazor, JSP, Phoenix HEEx, Go Templ).
- Live URLs (http:// or https://) — or local HTML files with --dom — are inspected in a
  headless browser (Playwright, falling back to Selenium+Chromium, or static HTTP HTML
  fetch when no browser automation library is installed). Live DOM inspection traverses
  Shadow DOM and uses computed-style / structural heuristics so it still finds UI on
  Tailwind-only, CSS-in-JS, Webflow, WordPress, Shopify, and obfuscated-class websites.
- --stdin scans code piped on standard input (pair with --ext .tsx / .vue / .html).

This is a heuristic first pass. Read the code (or inspect the live DOM selector) around
every hit before proposing anything.
"""
import argparse
import collections
import json
import os
import re
import signal
import sys
import urllib.error
import urllib.request
from pathlib import Path

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".nuxt", ".svelte-kit", "out",
    "coverage", "vendor", ".cache", ".turbo", ".vercel", "__pycache__", ".output",
    ".astro", ".angular", "venv", ".venv", "target", "bin", "obj",
}
# Skipped, and their candidate files are counted as skipped.
COUNTED_SKIP_DIRS = {"__tests__", "__mocks__", "storybook-static", "test-results", "playwright-report"}
SKIP_NAME_PARTS = (".min.", ".test.", ".spec.", ".stories.", ".story.", ".bundle.", ".chunk.")
SKILL_DIR = Path(__file__).resolve().parent.parent
CSS_EXTS = {".css", ".scss", ".sass", ".less", ".styl", ".pcss", ".postcss"}
JSX_EXTS = {".jsx", ".tsx", ".vue", ".svelte", ".astro", ".mdx"}
CUSTOM_TAG_EXTS = {".vue", ".html", ".htm", ".svelte", ".astro", ".php", ".erb", ".twig", ".hbs", ".njk", ".liquid", ".ejs"}
SFC_EXTS = {".vue", ".svelte", ".astro"}
COMMENT_STARTS = ("//", "/*", "*/", "* ", "<!--", "{/*", "{#", "<%#")
DEF_RX = re.compile(r'^\s*(export\s+)?(default\s+)?(async\s+)?(function|class|const)\s+[A-Z]\w*')
CORE_SIGN = "stretchy-core (already present)"

DEP_LABELS = (
    ("react", "react"),
    ("next", "next.js"),
    ("vue", "vue"),
    ("nuxt", "nuxt"),
    ("svelte", "svelte"),
    ("@sveltejs/kit", "sveltekit"),
    ("@angular/core", "angular"),
    ("astro", "astro"),
    ("solid-js", "solidjs"),
    ("@builder.io/qwik", "qwik"),
    ("preact", "preact"),
    ("lit", "lit / web components"),
    ("alpinejs", "alpine.js"),
    ("htmx.org", "htmx"),
    ("jquery", "jquery"),
    ("tailwindcss", "tailwind"),
    ("bootstrap", "bootstrap"),
    ("daisyui", "daisyui"),
    ("flowbite", "flowbite"),
    ("bulma", "bulma"),
    ("uikit", "uikit"),
    ("framer-motion", "framer-motion / motion"),
    ("motion", "framer-motion / motion"),
    ("@react-spring/web", "react-spring"),
    ("gsap", "gsap"),
    ("@formkit/auto-animate", "auto-animate"),
    ("lottie-web", "lottie"),
    ("lottie-react", "lottie"),
    ("@mantine/core", "mantine"),
    ("@nextui-org/react", "heroui / nextui"),
    ("@heroui/react", "heroui / nextui"),
    ("vuetify", "vuetify"),
    ("element-plus", "element-plus"),
    ("naive-ui", "naive-ui"),
    ("quasar", "quasar"),
    ("primereact", "prime"),
    ("primevue", "prime"),
    ("primeng", "prime"),
    ("@shoelace-style/shoelace", "shoelace"),
    ("@ionic/react", "ionic"),
    ("@ionic/vue", "ionic"),
    ("@ionic/angular", "ionic"),
    ("@ark-ui/react", "ark-ui / zag"),
    ("@ark-ui/vue", "ark-ui / zag"),
    ("bits-ui", "bits-ui"),
    ("react-aria-components", "react-aria"),
    ("@base-ui-components/react", "base-ui"),
    ("cmdk", "cmdk"),
)

EXTS = {
    # Web & JS/TS/JSX/MDX
    ".html", ".htm", ".jsx", ".tsx", ".js", ".ts", ".mjs", ".cjs", ".mts", ".cts", ".mdx",
    # Single-file & Web Components
    ".vue", ".svelte", ".astro", ".webc",
    # Stylesheets
    ".css", ".scss", ".sass", ".less", ".styl", ".pcss", ".postcss",
    # Server & CMS templates
    ".erb", ".php", ".twig", ".hbs", ".njk", ".liquid", ".ejs", ".pug", ".jade",
    ".haml", ".slim", ".cshtml", ".razor", ".jsp", ".ftl", ".jinja", ".jinja2",
    ".j2", ".djhtml", ".heex", ".leex", ".eex", ".templ",
}
MAX_FILE_BYTES = 600_000

A = r'["\']'  # attribute quote
# Matches class="...", className="...", :class="...", cn("..."), clsx("..."), styles.foo
CLS_WRAP = r'(?:class(?:Name)?\s*=\s*["\'`]|(?:cn|clsx|twMerge|classNames|cva)\s*\([^)\n]*["\'`]|ngClass|class:)'

# category: (label, showcase #, technique, morph idea, [regexes])
CATEGORIES = {
    "tabs": (
        "Tabs / tab bar", "#2 tabs", "edge pair",
        "indicator stretches like a worm between tabs",
        [
            rf'role={A}tab(list)?{A}',
            r'<(Tabs?(List|Trigger|Content)?|TabView|TabGroup|UTabs)\b',
            r'<(v-tabs?|el-tabs?|n-tabs?|q-tabs?|p-tabView|mat-tab-group|a-tabs?|b-tabs?|sl-tab-group|ion-tabs|x-tabs|u-tabs)\b',
            r'\b(TabList|TabPanel|TabsList|TabsTrigger)\b',
            rf'data-bs-toggle={A}(tab|pill){A}|data-tabs-(toggle|target)|uk-tab',
            rf'class(Name)?={A}[^"\']*\b(tabs?|nav-tabs|nav-pills|tab-bar|tab-active|tabs-boxed|tabs-lifted)\b',
            r'\bstyles\.(tabs?|tabBar|tabList)\b',
            r'\b(activeTab|selectedTab|currentTab|setActiveTab|setSelectedTab|setTab)\b',
        ],
    ),
    "segmented": (
        "Segmented control / button group", "#2 tabs (segmented)", "edge pair",
        "selected pill worms between options",
        [
            r'segmented',
            r'<(ToggleGroup|SegmentedControl|Segmented|ButtonGroup|IonSegment)\b',
            r'<(el-segmented|n-radio-group|q-btn-toggle|v-btn-toggle|ion-segment|p-selectButton|a-segmented)\b',
            r'\b(ToggleGroup|ButtonGroup|SegmentedControl)\b',
            rf'class(Name)?={A}[^"\']*\b(btn-group|segmented|join)\b',
        ],
    ),
    "switch": (
        "Toggle switch", "#7 toggles", "edge pair + thinning knob",
        "knob stretches into a capsule while it travels",
        [
            rf'role={A}switch{A}',
            r'<(Switch|ToggleSwitch|UToggle)\b',
            r'<(v-switch|el-switch|n-switch|q-toggle|p-inputSwitch|mat-slide-toggle|a-switch|sl-switch|ion-toggle|x-toggle)\b',
            rf'class(Name)?={A}[^"\']*\b(toggle|switch|form-switch|toggle-primary|toggle-accent)\b',
            r'\bstyles\.(toggle|switch)\b',
        ],
    ),
    "checkbox_radio": (
        "Checkboxes / radio groups", "#8 radio and checkbox", "edge pair (radio dot) + kick",
        "radio dot flows between options; checkbox squashes on tick",
        [
            rf'type={A}(checkbox|radio){A}',
            r'<(Checkbox|Radio|RadioGroup|CheckboxGroup)\b',
            r'<(v-checkbox|v-radio|el-checkbox|el-radio|n-checkbox|n-radio|q-checkbox|q-radio|mat-checkbox|mat-radio|sl-checkbox|sl-radio|ion-checkbox|ion-radio)\b',
            rf'role={A}(radiogroup|radio|checkbox){A}',
        ],
    ),
    "loading_button": (
        "Buttons with loading / submit states", "#6 send button", "split axes + volume + sequenced morph",
        "button squeezes into a spinner circle, then a check, then back",
        [
            r'\b(isLoading|isSubmitting|isPending|submitting|loading)\b\s*(\?|&&|\|\|)',
            r'<(Spinner|Loader|Loader2|CircularProgress|LoadingButton)\b',
            r'aria-busy',
            r'disabled=\{\s*(isLoading|loading|isSubmitting|pending|isPending)',
            r':loading=|\[loading\]=|wire:loading|hx-indicator',
            r'กำลังโหลด|กำลังส่ง|กำลังบันทึก',
        ],
    ),
    "modal": (
        "Modals / dialogs", "#17 modal", "container transform",
        "the trigger button grows into the dialog and shrinks back on close",
        [
            r'<dialog\b',
            rf'role={A}(alert)?dialog{A}',
            r'<(Modal|Dialog|AlertDialog|DialogContent|UModal)\b',
            r'<(v-dialog|el-dialog|n-modal|q-dialog|p-dialog|a-modal|b-modal|sl-dialog|ion-modal|x-modal|u-modal)\b',
            r'\.showModal\(',
            rf'data-bs-toggle={A}modal{A}|data-modal-(toggle|target)|uk-modal',
            rf'class(Name)?={A}[^"\']*\b(modal|modal-box|modal-dialog)\b',
            r'\bstyles\.(modal|dialog)\b',
            r'\b(isModalOpen|showModal|openModal|setModalOpen|isDialogOpen|setDialogOpen)\b',
        ],
    ),
    "dropdown": (
        "Dropdowns / selects / menus / popovers", "#11 dropdown", "split axes + vertical edge-pair highlight",
        "menu pours out of its button; highlight worms through options",
        [
            r'<select\b',
            r'<(Select|Menu|DropdownMenu|Dropdown|Listbox|Combobox|Popover|MenuItems|UDropdown|UPopover)\b',
            r'<(v-select|v-menu|el-select|el-dropdown|n-select|n-dropdown|q-select|q-menu|p-dropdown|mat-select|mat-menu|a-select|a-dropdown|sl-select|sl-dropdown|ion-select|x-dropdown)\b',
            rf'role={A}(listbox|menu|combobox){A}',
            r'\bpopovertarget\b|\bpopover(?:=|\s|>)',
            rf'data-(bs|dropdown)-toggle={A}(dropdown|popover){A}|data-dropdown-toggle|data-popover-target|aria-haspopup={A}(menu|listbox|true){A}',
            rf'class(Name)?={A}[^"\']*\b(dropdown|dropdown-content|popover)\b',
        ],
    ),
    "accordion": (
        "Accordions / collapsibles / details", "#22 accordion", "overshooting height + lagging content (makeAccordion for plain/CMS <details>)",
        "panel overshoots its height, content lags like it is shaken, opened card drifts apart",
        [
            r'<details\b',
            r'<(Accordion|AccordionItem|Collapsible|Disclosure|Collapse|ExpansionPanel|UAccordion)\b',
            r'<(v-expansion-panel|el-collapse|n-collapse|q-expansion-item|p-accordion|mat-expansion-panel|a-collapse|sl-details|ion-accordion|x-accordion)\b',
            rf'data-(bs-toggle={A}collapse{A}|accordion-target)|uk-accordion',
            rf'class(Name)?={A}[^"\']*\b(accordion|accordion-item|collapse-title|collapse-content)\b',
            r'\b(openAccordion|activeAccordion|expandedIndex|expandedId|setExpanded)\b',
            r'คำถามที่พบบ่อย',
        ],
    ),
    "carousel": (
        "Carousels / sliders of cards", "#5 carousel", "velocity skew + rubber band + worm dots",
        "cards lean with swipe speed, edges resist like rubber",
        [
            r'<(Swiper|SwiperSlide|Carousel|Splide|Slider|Slide|UCarousel)\b',
            r'<(v-carousel|el-carousel|n-carousel|q-carousel|p-carousel|a-carousel|sl-carousel|ion-slides)\b',
            r'scroll-snap-type|snap-x\b|snap-mandatory',
            r'\b(carousel|swiper|splide|glide)\b',
            r'embla|keen-slider|slick|flickity',
        ],
    ),
    "range_slider": (
        "Range inputs / sliders", "#12 slider", "velocity stretch + lagging bubble",
        "thumb stretches with drag speed, value bubble swings",
        [
            rf'type={A}range{A}',
            rf'role={A}slider{A}',
            r'<(RangeSlider|v-slider|el-slider|n-slider|q-slider|p-slider|mat-slider|a-slider|sl-range|ion-range)\b',
        ],
    ),
    "toast": (
        "Toasts / snackbars / alerts", "#18 toast", "split axes from a dot + stacked springs",
        "toast sprouts from a dot into a bar, old ones are pushed up",
        [
            r'\btoast\b',
            r'<(Toast|Toaster|Snackbar|Alert|UNotifications)\b',
            r'<(v-snackbar|el-notification|n-notification|p-toast|ion-toast)\b',
            r'notistack|sonner|react-hot-toast|react-toastify|vue-toastification|sweetalert2|toastify',
        ],
    ),
    "tooltip": (
        "Tooltips", "#19 tooltip", "travelling follower + velocity stretch",
        "one tooltip travels between controls and resizes to its label",
        [
            r'<(Tooltip|UTooltip|v-tooltip|el-tooltip|n-tooltip|q-tooltip|a-tooltip|sl-tooltip)\b',
            rf'role={A}tooltip{A}',
            r'data-tooltip|data-bs-toggle=["\']tooltip["\']|data-tip=|v-tooltip|matTooltip',
            r'\b(tippy|tooltip)\b',
        ],
    ),
    "sidebar": (
        "Sidebars / drawers / off-canvas", "#4 sidebar", "bulging SVG edge + vertical worm",
        "edge bulges with speed and wobbles flat; nav highlight worms",
        [
            r'<(Sidebar|Drawer|Sheet|SheetContent|Offcanvas|USlideover)\b',
            r'<(v-navigation-drawer|el-drawer|n-drawer|q-drawer|p-sidebar|mat-sidenav|a-drawer|sl-drawer|ion-menu)\b',
            r'<aside\b',
            rf'data-(bs-toggle={A}offcanvas{A}|drawer-target|drawer-show)|uk-offcanvas',
            r'\b(sidebar|drawer|offcanvas|side-nav|drawer-side|drawer-toggle)\b',
            r'\b(sidebarOpen|drawerOpen|isDrawerOpen|setDrawerOpen|setSidebarOpen)\b',
        ],
    ),
    "bottom_sheet": (
        "Bottom sheets", "#20 bottom sheet", "bulging top edge + drag with velocity",
        "draggable sheet whose top edge bends with speed",
        [
            r'bottom-?sheet',
            r'<(BottomSheet|v-bottom-sheet|ion-action-sheet)\b',
            rf'side={A}bottom{A}',
            r'\bvaul\b|\bbtm-nav\b',
        ],
    ),
    "stepper": (
        "Steppers / wizards / progress steps", "#3 stepper", "edge pair blob + overshooting fill",
        "current-step blob stretches to the next step, progress line overshoots",
        [
            r'<(Stepper|Steps|Step|Wizard|v-stepper|el-steps|n-steps|q-stepper|p-steps|mat-stepper|a-steps)\b',
            r'\b(stepper|steps-horizontal|steps-vertical)\b',
            r'\b(currentStep|activeStep|stepIndex)\b',
            r'\[\s*step\s*,\s*setStep\s*\]',
            r'\bset(Current|Active)?Step\b',
        ],
    ),
    "rating": (
        "Star ratings", "#14 rating", "edge-pair capsule + staggered kicks",
        "capsule behind the stars follows the pointer; stars pop in sequence",
        [
            r'<(Rating|v-rating|el-rate|n-rate|q-rating|p-rating|a-rate|sl-rating)\b',
            r'\b(rating|star-?rating)\b',
            r'ให้คะแนน',
        ],
    ),
    "chips": (
        "Chips / tags / filter pills", "#9 chips (multi) / #24 choice chips (single)", "springing icon slot + kick; 2-D edge-pair blob if single-select",
        "selected chip swells as its check pushes in; single-select: one capsule worms between chips, across rows",
        [
            r'<(Chip|Tag|FilterChip|v-chip|el-tag|n-tag|q-chip|p-chip|mat-chip|a-tag|sl-tag|ion-chip)\b',
            r'\b(chip|filter-chip|tag-pill)s?\b',
            r'\b(selectedCategory|activeCategory|selectedFilter|activeFilter|setSelectedCategory|setActiveFilter)\b',
            r'ตัวกรอง|หมวดหมู่',
        ],
    ),
    "search": (
        "Search fields", "#10 search", "split axes from icon + volume",
        "search icon bursts open into a field; suggestions bounce in",
        [
            rf'type={A}search{A}',
            rf'role={A}search{A}',
            rf'placeholder={A}[^"\']*(search|ค้นหา)',
            r'<(SearchBar|SearchInput|ion-searchbar)\b',
        ],
    ),
    "quantity": (
        "Quantity steppers / number inputs", "#13 quantity", "directional kick + digit roll",
        "pill stretches toward the side pressed, digits roll",
        [
            r'\b(quantity|qty)\b',
            rf'type={A}number{A}',
            r'<(NumberInput|el-input-number|n-input-number|a-input-number|p-inputNumber)\b',
        ],
    ),
    "add_to_cart": (
        "Add-to-cart / save / send-to actions", "#15 add to cart", "thrown clone + sequenced button morph",
        "the product picture flies into the cart, button morphs into a stepper",
        [
            r'add\s*to\s*cart|addToCart|add-to-cart|เพิ่มลงตะกร้า|ตะกร้าสินค้า',
            r'\bcart\b',
            r'wishlist|addToWishlist',
        ],
    ),
    "date_picker": (
        "Date pickers / calendars", "#23 date picker", "2-D edge-pair blob + per-row range capsules",
        "selection blob flows between days; range pours row by row",
        [
            rf'type={A}(date|datetime-local|month|week){A}',
            r'<(DatePicker|Calendar|DateRangePicker|DayPicker|v-date-picker|el-date-picker|n-date-picker|q-date|p-calendar|a-date-picker|ion-datetime)\b',
            r'datepicker|flatpickr|react-datepicker|react-day-picker|vuepic|pikaday|เลือกวันที่',
        ],
    ),
    "pagination": (
        "Pagination / page dots", "#5 carousel dots", "edge pair",
        "current-page marker worms between numbers or dots",
        [
            r'<(Pagination|UPagination|v-pagination|el-pagination|n-pagination|q-pagination|p-paginator|a-pagination)\b',
            r'\bpagination\b',
            rf'aria-current={A}page{A}',
        ],
    ),
    "badge": (
        "Badges / counters", "#15 cart badge", "kick on change",
        "count pops when it changes",
        [
            r'<(Badge|UBadge|v-badge|el-badge|n-badge|q-badge|a-badge|sl-badge|ion-badge)\b',
            r'\bbadge\b',
        ],
    ),
    "fab": (
        "Floating action buttons", "#21 FAB", "split axes (width leads, then height)",
        "round button spreads into a form or menu",
        [
            r'\bfab\b',
            r'floating-action',
            r'<(Fab|SpeedDial|ion-fab|q-fab|v-speed-dial)\b',
        ],
    ),
    "menu_toggle": (
        "Hamburger / nav toggles", "new-components: hamburger", "edge pair bars + container transform",
        "bars fold into an X and the button grows into the menu",
        [
            r'hamburger|menu-toggle|navbar-toggler|nav-toggle|w-nav-button',
            rf'aria-label={A}[^"\']*(open |toggle )?(menu|navigation|เมนู)[^"\']*{A}',
            r'\b(mobileMenuOpen|isMenuOpen|setMobileMenuOpen|toggleMenu)\b',
        ],
    ),
    "reorder": (
        "Drag-to-reorder lists", "new-components: drag to reorder", "pointer follower + tilt + FLIP",
        "picked item tilts with speed while others spring apart",
        [
            r'react-beautiful-dnd|@hello-pangea/dnd|@dnd-kit|sortablejs|vuedraggable|svelte-dnd|@formkit/drag-and-drop',
            r'\bdraggable\b',
        ],
    ),
    "like": (
        "Like / favourite buttons", "new-components: like button", "kick squash + ring pulse",
        "heart squashes on press and launches on release",
        [
            r'\b(isLiked|liked|toggleLike|likeCount|onLike|LikeButton|isFavou?rite|toggleFavou?rite)\b',
            r'HeartIcon|icon-heart|bi-heart|fa-heart',
        ],
    ),
    "nav_bar": (
        "Navigation bars with active link", "#2 tabs", "edge pair",
        "active pill or underline worms along nav links",
        [
            r'<(NavLink|Navbar|NavigationMenu|Menubar)\b',
            r'<router-link\b|<nuxt-link\b',
            rf'class(Name)?={A}[^"\']*\b(navbar-nav|nav-underline|w-nav-menu|top-nav|main-nav)\b',
        ],
    ),
    "theme_toggle": (
        "Dark / light theme toggle", "#28 theme toggle", "edge pair + kick",
        "sun/moon morphs and stretches across the switch track",
        [
            r'\b(toggleTheme|setTheme|themeToggle|darkMode|isDarkMode|colorMode|useTheme)\b',
            r'theme-toggle|theme-switch|data-theme=|swap-rotate',
        ],
    ),
    "command_palette": (
        "Command palette / quick search", "#10 search / #17 modal", "container transform + vertical edge-pair highlight",
        "trigger expands into command box; active row highlight worms",
        [
            r'<(CommandDialog|CommandPalette|CommandMenu|KBarPortal)\b',
            r'\b(cmdk|kbar|command-palette|CommandPalette)\b',
        ],
    ),
    "otp_input": (
        "OTP / PIN code input", "#25 otp input", "directional kick + active box follower",
        "focus frame worms to the next digit box; filled digit pops",
        [
            r'<(InputOTP|OTPInput|PinInput|v-otp-input|p-inputOtp)\b',
            rf'autocomplete={A}one-time-code{A}',
            r'\b(otp-input|pin-input|otpCode)\b',
        ],
    ),
    "file_upload": (
        "File uploads / dropzones", "#31 upload progress", "sequenced morph + volume",
        "dropzone compresses into a progress ring, then morphs into a check",
        [
            rf'type={A}file{A}',
            r'<(Dropzone|FileUpload|Upload|v-file-input|el-upload|n-upload|q-uploader|a-upload|p-fileUpload)\b',
            r'\b(useDropzone|dropzone|file-upload|uploadProgress)\b',
        ],
    ),
    "notification_bell": (
        "Notification bell & popover", "#26 notification bell", "kick swing + split-axes popover",
        "bell swings on new alert; notification list pours out from the bell",
        [
            r'<(NotificationBell|NotificationsPopover|BellIcon)\b',
            r'\b(notification-bell|notifications-popover|unreadCount)\b',
            r'fa-bell|bi-bell|แจ้งเตือน',
        ],
    ),
    "view_switcher": (
        "Grid / list view switcher", "#27 view switcher", "edge pair + FLIP with springs",
        "toggle pill worms while cards FLIP-spring between grid and list",
        [
            r'\b(viewMode|setViewMode|view-switcher|layoutMode|setLayoutMode)\b',
        ],
    ),
    "context_menu": (
        "Context menus", "#30 context menu", "split axes from cursor",
        "menu blooms out from the pointer position with overshooting height",
        [
            r'<(ContextMenu|ContextMenuContent|p-contextMenu)\b',
            r'\b(onContextMenu|@contextmenu|context-menu)\b',
        ],
    ),
    "floating_label": (
        "Floating-label text fields", "new-components: floating-label text field", "spring lift + kick",
        "label springs up out of the field and settles with slight overshoot",
        [
            r'form-floating|peer-placeholder-shown|floating-label|<(FloatingLabel|v-text-field|mat-form-field)\b',
        ],
    ),
    "swipe_actions": (
        "Pull-to-refresh / swipe-to-delete", "#29 swipe to delete", "rubber band + bulging edge",
        "overscroll resists like rubber and snaps back with a spring",
        [
            r'<(PullToRefresh|SwipeableList|ion-refresher|ion-item-sliding)\b',
            r'\b(pull-to-refresh|swipe-to-delete|useSwipeable|onSwipe)\b',
        ],
    ),
}

STACK_SIGNS = {
    "react": [r'from\s+["\']react["\']', r'\buseState\b', r'\.jsx\b'],
    "next.js": [r'from\s+["\']next/', r'__NEXT_DATA__'],
    "vue": [r'<template\b', r'from\s+["\']vue["\']', r'defineComponent', r'<script\s+setup'],
    "nuxt": [r'from\s+["\']#app["\']', r'<NuxtPage\b|<NuxtLink\b', r'__NUXT__'],
    "svelte": [r'<script[^>]*>\s*(export let|import|\$props)', r'\$:\s|\$state\('],
    "angular": [r'@Component\(', r'from\s+["\']@angular', r'\*ngIf|\*ngFor|@if\s*\('],
    "astro": [r'Astro\.props', r'from\s+["\']astro:'],
    "solidjs": [r'from\s+["\']solid-js["\']', r'\bcreateSignal\b'],
    "alpine.js": [r'\bx-data\s*=', r'\bx-show\s*=', r'alpinejs'],
    "htmx": [r'\bhx-(get|post|put|delete|swap|target)\s*=', r'htmx\.org'],
    "lit / web components": [r'from\s+["\']lit["\']', r'customElements\.define\('],
    "jquery": [r'jquery(?:\.min)?\.js', r'\$\(["\'][#.a-z]'],
    "laravel blade / livewire": [r'@(extends|section|foreach|endif)\b', r'\bwire:(click|model|loading)\b'],
    "wordpress": [r'/wp-content/|wp_enqueue_script|get_template_part'],
    "shopify liquid": [r'\{%\s*(section|schema|render)\b', r'Shopify\.'],
    "webflow": [r'data-wf-page|w-nav-menu|w-dropdown'],
    "tailwind": [
        r'(?:class(?:Name)?|cn|clsx)\s*[=(]\s*["\'`][^"\'`]*\b(px-\d|py-\d|bg-[a-z]+-\d{2,3}|text-[a-z]+-\d{2,3}|rounded-(md|lg|xl|2xl|full))\b',
        r'cdn\.tailwindcss\.com',
    ],
    "bootstrap": [r'data-bs-toggle=|bootstrap(?:\.bundle)?(?:\.min)?\.(js|css)', r'\b(navbar-toggler|form-switch|offcanvas-body)\b'],
    "daisyui": [r'\b(drawer-toggle|modal-box|tabs-boxed|tabs-lifted|swap-rotate|btm-nav)\b', r'daisyui'],
    "flowbite": [r'data-(modal|tabs|dropdown|drawer)-toggle=|data-accordion-target=|flowbite'],
    "uikit": [r'\buk-(tab|modal|accordion|offcanvas|switcher)\b', r'uikit(?:\.min)?\.(js|css)'],
    "bulma": [r'bulma(?:\.min)?\.css', r'\bis-tab\b.*\bis-active\b'],
    "framer-motion / motion": [r'framer-motion', r'from\s+["\']motion', r'<motion\.'],
    "react-spring": [r'@react-spring|react-spring'],
    "gsap": [r'\bgsap\b'],
    "anime.js / popmotion": [r'animejs|popmotion'],
    "view transitions api": [r'startViewTransition|@view-transition'],
    "radix / shadcn": [r'@radix-ui', r'components/ui/', r'data-state=["\'](open|closed|active)["\']'],
    "headless ui": [r'@headlessui'],
    "mui / chakra / antd": [r'@mui/|@chakra-ui|antd'],
    "mantine": [r'@mantine/'],
    "vuetify": [r'vuetify|<v-(tabs|dialog|switch|navigation-drawer|expansion-panel|snackbar)\b'],
    "element-plus": [r'element-plus|<el-(tabs|dialog|switch|drawer|collapse)\b'],
    "naive-ui": [r'naive-ui|<n-(tabs|modal|switch|drawer|collapse)\b'],
    "quasar": [r'quasar|<q-(tabs|dialog|toggle|drawer|expansion-item)\b'],
    "prime": [r'prime(react|vue|ng)|<p-(tabView|dialog|accordion|sidebar|dropdown)\b'],
    "shoelace": [r'@shoelace-style|<sl-(tab-group|dialog|switch|drawer|details|dropdown)\b'],
    "ionic": [r'@ionic/|<ion-(tabs|segment|toggle|modal|accordion|fab)\b'],
}

MOTION_SIGNS = {
    "css transitions": r'transition\s*:|transition-(all|colors|transform|opacity)\b',
    "css keyframes": r'@keyframes',
    "reduced-motion handling": r'prefers-reduced-motion|useReducedMotion|motion-reduce|motion-safe',
}

# One combined pattern per category: a whole-file search is a superset filter for the line tests.
COMPILED_CATS = {k: re.compile('|'.join('(?:%s)' % rx for rx in v[4]), re.I) for k, v in CATEGORIES.items()}
STACK_RX = {k: [re.compile(rx) for rx in v] for k, v in STACK_SIGNS.items()}
MOTION_RX = {k: re.compile(v, re.I) for k, v in MOTION_SIGNS.items()}


# Live DOM & Computed-Style inspector executed in headless Chromium (Playwright or Selenium).
# Traverses open Shadow DOMs and detects both semantic/library widgets and visual/structural
# patterns (even on Tailwind-only, CSS-in-JS, or obfuscated-class websites).
DOM_AUDIT_JS = r"""() => {
  const MAX_NODES = 4000;
  const allEls = [];
  const shadowHosts = new Set();

  function walk(root, shadowPrefix) {
    if (allEls.length >= MAX_NODES) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
    let node = walker.currentNode;
    while (node && allEls.length < MAX_NODES) {
      if (node.nodeType === 1) {
        allEls.push({ el: node, shadow: shadowPrefix });
        if (node.shadowRoot) {
          const hostName = node.tagName.toLowerCase() + (node.id ? '#' + node.id : '');
          shadowHosts.add(hostName);
          walk(node.shadowRoot, shadowPrefix ? shadowPrefix + ' >> ' + hostName : hostName);
        }
      }
      node = walker.nextNode();
    }
  }
  walk(document.body || document.documentElement, '');

  const isVisible = (el) => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.02) return false;
    const r = el.getBoundingClientRect();
    return r.width >= 4 && r.height >= 4;
  };

  const clsList = (el) => (typeof el.className === 'string' ? el.className.trim().split(/\s+/).filter(Boolean) : []);

  const cssSelector = (el, shadow) => {
    const tag = el.tagName.toLowerCase();
    let s = tag;
    if (el.id) {
      s += '#' + el.id;
    } else {
      const cls = clsList(el).filter(c => !/^(css|sc|_[a-z0-9]{5,}|tw-)/i.test(c)).slice(0, 2);
      if (cls.length) s += '.' + cls.join('.');
      else if (el.getAttribute('role')) s += '[role="' + el.getAttribute('role') + '"]';
      else if (el.getAttribute('aria-label')) s += '[aria-label="' + el.getAttribute('aria-label').slice(0, 24) + '"]';
    }
    return shadow ? 'shadow(' + shadow + ') ' + s : s;
  };

  const snippetOf = (el, note) => {
    const txt = (el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 65);
    return (note ? '[' + note + '] ' : '') + (txt || el.tagName.toLowerCase());
  };

  // --- 1. Live stack detection ---
  const stack = new Set();
  const html = document.documentElement.outerHTML.slice(0, 120000);
  if (window.__NEXT_DATA__ || document.getElementById('__next')) { stack.add('next.js'); stack.add('react'); }
  if (window.__NUXT__ || document.getElementById('__nuxt')) { stack.add('nuxt'); stack.add('vue'); }
  if (window.__REACT_DEVTOOLS_GLOBAL_HOOK__ || allEls.some(x => Object.keys(x.el).some(k => k.startsWith('__reactFiber') || k.startsWith('__reactProps')))) stack.add('react');
  if (window.__VUE__ || allEls.some(x => x.el.__vue_app__ || [...x.el.attributes].some(a => a.name.startsWith('data-v-')))) stack.add('vue');
  if (allEls.some(x => clsList(x.el).some(c => /^svelte-[a-z0-9]+$/.test(c)))) stack.add('svelte');
  if (document.querySelector('[ng-version]')) stack.add('angular');
  if (document.querySelector('astro-island')) stack.add('astro');
  if (window.Alpine || document.querySelector('[x-data]')) stack.add('alpine.js');
  if (window.htmx || document.querySelector('[hx-get],[hx-post],[hx-swap]')) stack.add('htmx');
  if (window.jQuery || window.$?.fn?.jquery) stack.add('jquery');
  if (window.gsap) stack.add('gsap');
  if (window.Shopify) stack.add('shopify liquid');
  if (document.documentElement.hasAttribute('data-wf-page') || document.querySelector('.w-nav')) stack.add('webflow');
  if (html.includes('/wp-content/')) stack.add('wordpress');
  if (document.querySelector('[data-bs-toggle]')) stack.add('bootstrap');
  if (document.querySelector('[data-radix-collection-item],[data-radix-popper-content-wrapper],[data-state]')) stack.add('radix / shadcn');
  if (document.querySelector('[class*="Mui"]')) stack.add('mui / chakra / antd');
  if (document.querySelector('[class*="ant-"]')) stack.add('mui / chakra / antd');
  if (document.querySelector('.v-application,[class*="v-tabs"]')) stack.add('vuetify');
  if (document.querySelector('[class*="el-tabs"],[class*="el-dialog"]')) stack.add('element-plus');
  if (document.querySelector('[data-framer-appear-id]')) stack.add('framer-motion / motion');
  if (shadowHosts.size > 0) stack.add('web components / shadow dom');
  if (typeof window.Spring === 'function' && typeof window.edgePair === 'function') stack.add('stretchy-core (already present)');

  // Tailwind heuristic: count elements with typical utility classes
  let twCount = 0;
  const twRx = /^(flex|grid|px-\d|py-\d|gap-\d|rounded-(md|lg|xl|2xl|full)|bg-[a-z]+-\d{2,3}|text-[a-z]+-\d{2,3})$/;
  for (const { el } of allEls) {
    if (clsList(el).some(c => twRx.test(c))) twCount++;
  }
  if (twCount >= 5) stack.add('tailwind');

  // --- 2. Motion & reduced-motion audit from live stylesheets ---
  const motion = { 'css transitions': 0, 'css keyframes': 0, 'reduced-motion handling': 0 };
  for (const sheet of document.styleSheets) {
    let rules;
    try { rules = sheet.cssRules; } catch (e) { continue; }
    if (!rules) continue;
    for (const r of rules) {
      if (r.type === CSSRule.KEYFRAMES_RULE) motion['css keyframes']++;
      else if (r.type === CSSRule.MEDIA_RULE && /prefers-reduced-motion/i.test(r.conditionText || '')) {
        motion['reduced-motion handling']++;
      } else if (r.style && r.style.transition && r.style.transition !== 'none') {
        motion['css transitions']++;
      }
    }
  }
  for (const { el } of allEls) {
    if (el.style && el.style.transition && el.style.transition !== 'none') motion['css transitions']++;
  }

  // --- 3. Semantic + Structural + Computed-style UI candidate detection ---
  const hits = {};
  const seen = new Set();
  const addHit = (cat, el, shadow, note) => {
    const sel = cssSelector(el, shadow);
    const key = cat + '::' + sel;
    if (seen.has(key)) return;
    seen.add(key);
    if (!hits[cat]) hits[cat] = [];
    hits[cat].push({ selector: sel, snippet: snippetOf(el, note), source: note || 'dom' });
  };

  const vw = window.innerWidth || 1280;
  const vh = window.innerHeight || 900;

  for (const { el, shadow } of allEls) {
    const tag = el.tagName.toLowerCase();
    const role = (el.getAttribute('role') || '').toLowerCase();
    const type = (el.getAttribute('type') || '').toLowerCase();
    const cls = clsList(el).join(' ').toLowerCase();
    const label = ((el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('placeholder') || '')).toLowerCase();
    const vis = isVisible(el);
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();

    // Semantic / ARIA / native elements
    if (role === 'tablist' || tag === 'sl-tab-group' || tag === 'ion-tabs' || el.hasAttribute('data-tabs-toggle')) addHit('tabs', el, shadow, 'aria/tag');
    if (role === 'switch' || tag === 'sl-switch' || tag === 'ion-toggle' || /\b(form-switch|toggle-switch)\b/.test(cls)) addHit('switch', el, shadow, 'aria/tag');
    if ((tag === 'input' && (type === 'checkbox' || type === 'radio')) || role === 'radiogroup') addHit('checkbox_radio', el, shadow, 'native/aria');
    if (tag === 'dialog' || role === 'dialog' || role === 'alertdialog' || tag === 'sl-dialog' || tag === 'ion-modal' || el.hasAttribute('data-modal-toggle')) addHit('modal', el, shadow, 'native/aria');
    if (tag === 'select' || role === 'listbox' || role === 'menu' || role === 'combobox' || el.hasAttribute('popover') || el.hasAttribute('popovertarget') || el.getAttribute('aria-haspopup') === 'menu' || el.getAttribute('aria-haspopup') === 'listbox') addHit('dropdown', el, shadow, 'native/aria');
    if (tag === 'details' || tag === 'sl-details' || tag === 'ion-accordion' || el.hasAttribute('data-accordion-target')) addHit('accordion', el, shadow, 'native/tag');
    if ((tag === 'input' && type === 'range') || role === 'slider' || tag === 'sl-range' || tag === 'ion-range') addHit('range_slider', el, shadow, 'native/aria');
    if (role === 'tooltip' || el.hasAttribute('data-tooltip') || el.hasAttribute('data-tip')) addHit('tooltip', el, shadow, 'aria/attr');
    if (role === 'alert' || role === 'status' || /\b(toast|snackbar)\b/.test(cls)) { if (/\b(toast|snackbar|notistack|sonner)\b/.test(cls) || cs.position === 'fixed') addHit('toast', el, shadow, 'aria/fixed'); }
    if ((tag === 'input' && type === 'search') || role === 'search' || /search|ค้นหา/.test(label)) addHit('search', el, shadow, 'native/aria');
    if (tag === 'input' && (type === 'date' || type === 'datetime-local' || type === 'month' || type === 'week')) addHit('date_picker', el, shadow, 'native');
    if (tag === 'input' && type === 'file') addHit('file_upload', el, shadow, 'native');
    if (tag === 'input' && type === 'number') addHit('quantity', el, shadow, 'native');
    if (el.getAttribute('autocomplete') === 'one-time-code') addHit('otp_input', el, shadow, 'native');
    if (el.getAttribute('aria-busy') === 'true') addHit('loading_button', el, shadow, 'aria');
    if (el.getAttribute('aria-current') === 'page' || /\bpagination\b/.test(cls)) addHit('pagination', el, shadow, 'aria/class');
    if (tag === 'aside' || tag === 'sl-drawer' || el.hasAttribute('data-drawer-target') || /\b(sidebar|drawer|offcanvas)\b/.test(cls)) addHit('sidebar', el, shadow, 'tag/class');
    if (/\b(bottom-?sheet|btm-nav)\b/.test(cls)) addHit('bottom_sheet', el, shadow, 'class');
    if (/\b(stepper|wizard)\b/.test(cls)) addHit('stepper', el, shadow, 'class');
    if (/\b(rating|star-?rating)\b/.test(cls) || tag === 'sl-rating') addHit('rating', el, shadow, 'class/tag');
    if (/\b(chip|filter-chip)\b/.test(cls) || tag === 'ion-chip') addHit('chips', el, shadow, 'class/tag');
    if (/\b(badge)\b/.test(cls) && r.width < 120 && r.height < 48) addHit('badge', el, shadow, 'class');
    if (/\b(hamburger|menu-toggle|navbar-toggler|nav-toggle|w-nav-button)\b/.test(cls) || /(open |toggle )?(menu|navigation|เมนู)/.test(label)) addHit('menu_toggle', el, shadow, 'aria/class');
    if (/add\s*to\s*cart|เพิ่มลงตะกร้า/.test((el.innerText || '').toLowerCase() + ' ' + label)) {
      if (tag === 'button' || tag === 'a' || role === 'button') addHit('add_to_cart', el, shadow, 'text');
    }
    if (el.hasAttribute('draggable') && el.getAttribute('draggable') === 'true') addHit('reorder', el, shadow, 'attr');

    // aria-expanded disclosure heuristic (accordion vs dropdown vs menu toggle)
    if (vis && el.hasAttribute('aria-expanded') && (tag === 'button' || role === 'button')) {
      if (el.closest('header, nav') && r.width < 64 && r.height < 64) {
        addHit('menu_toggle', el, shadow, 'structure:aria-expanded');
      } else if (el.getAttribute('aria-haspopup')) {
        addHit('dropdown', el, shadow, 'structure:aria-expanded');
      } else {
        addHit('accordion', el, shadow, 'structure:aria-expanded');
      }
    }

    if (!vis) continue;

    // --- Structural & Computed-Style Heuristics (works on Tailwind / obfuscated classes!) ---

    // A) Horizontal group of 2..10 buttons/links with an active visual/ARIA state -> tabs / segmented / nav_bar
    const kids = [...el.children].filter(c => {
      const ct = c.tagName.toLowerCase();
      return (ct === 'button' || ct === 'a' || c.getAttribute('role') === 'tab' || c.getAttribute('role') === 'button') && isVisible(c);
    });
    if (kids.length >= 2 && kids.length <= 10) {
      const tops = kids.map(k => k.getBoundingClientRect().top);
      const sameRow = (Math.max(...tops) - Math.min(...tops)) <= 14;
      if (sameRow) {
        const hasAriaActive = kids.some(k =>
          k.getAttribute('aria-selected') === 'true' ||
          k.getAttribute('aria-pressed') === 'true' ||
          k.getAttribute('aria-current') === 'page' ||
          k.getAttribute('data-state') === 'active' ||
          /\bactive\b/.test(clsList(k).join(' '))
        );
        const bgs = kids.map(k => getComputedStyle(k).backgroundColor);
        const bbs = kids.map(k => getComputedStyle(k).borderBottomColor + ':' + getComputedStyle(k).borderBottomWidth);
        const bgCounts = {};
        bgs.forEach(b => bgCounts[b] = (bgCounts[b] || 0) + 1);
        const bbCounts = {};
        bbs.forEach(b => bbCounts[b] = (bbCounts[b] || 0) + 1);
        const uniqueActiveBg = Object.values(bgCounts).includes(1) && Object.keys(bgCounts).length === 2;
        const uniqueActiveBb = Object.values(bbCounts).includes(1) && Object.keys(bbCounts).length === 2;

        if (hasAriaActive || uniqueActiveBg || uniqueActiveBb) {
          const allLinks = kids.every(k => k.tagName.toLowerCase() === 'a');
          if (allLinks && (tag === 'nav' || el.closest('nav, header'))) {
            addHit('nav_bar', el, shadow, 'structure:active-nav(' + kids.length + ')');
          } else if (kids.length <= 5 && uniqueActiveBg && parseFloat(cs.borderRadius) >= 6 && cs.backgroundColor !== 'rgba(0, 0, 0, 0)') {
            addHit('segmented', el, shadow, 'structure:pill-group(' + kids.length + ')');
          } else {
            addHit('tabs', el, shadow, 'structure:tab-row(' + kids.length + ')');
          }
        }
      }
    }

    // B) Horizontal scrollable card track -> carousel
    if ((cs.overflowX === 'auto' || cs.overflowX === 'scroll' || (cs.scrollSnapType && cs.scrollSnapType !== 'none')) &&
        el.scrollWidth > el.clientWidth + 24 && el.children.length >= 3) {
      const cardKids = [...el.children].filter(c => {
        const cr = c.getBoundingClientRect();
        return cr.width >= 100 && cr.height >= 80;
      });
      if (cardKids.length >= 3) {
        addHit('carousel', el, shadow, 'structure:scroll-track(' + cardKids.length + ')');
      }
    }

    // C) Fixed-position edge panels & FABs
    if (cs.position === 'fixed') {
      // Fixed FAB (bottom-right or bottom-left circular button)
      if ((tag === 'button' || tag === 'a' || role === 'button') &&
          r.width >= 38 && r.width <= 84 && r.height >= 38 && r.height <= 84 &&
          (vh - r.bottom) <= 72 && ((vw - r.right) <= 72 || r.left <= 72) &&
          parseFloat(cs.borderRadius) >= 16) {
        addHit('fab', el, shadow, 'structure:fixed-fab');
      }
      // Fixed full-height sidebar/drawer
      else if (r.height >= vh * 0.6 && r.width >= 160 && r.width <= 460 && (r.left <= 8 || (vw - r.right) <= 8)) {
        addHit('sidebar', el, shadow, 'structure:fixed-sidebar');
      }
      // Fixed bottom sheet
      else if (r.width >= vw * 0.5 && r.height >= 120 && r.height <= vh * 0.85 && (vh - r.bottom) <= 24) {
        addHit('bottom_sheet', el, shadow, 'structure:fixed-bottom-sheet');
      }
    }
  }

  return {
    title: document.title || '',
    url: location.href,
    elements_inspected: allEls.length,
    shadow_roots: shadowHosts.size,
    stack: [...stack],
    motion,
    hits,
  };
}"""


def is_url(s):
    return s.lower().startswith(("http://", "https://"))


def within(path, base):
    a = os.path.normcase(str(path))
    b = os.path.normcase(str(base))
    try:
        return os.path.commonpath([a, b]) == b
    except ValueError:
        return False


def is_candidate(fp):
    return fp.suffix.lower() in EXTS or fp.name == "package.json"


def is_skipped_file(fp, allow_skill):
    name = fp.name.lower()
    if name.endswith(".d.ts") or any(part in name for part in SKIP_NAME_PARTS):
        return True
    return not allow_skill and within(fp, SKILL_DIR)


def iter_files(paths):
    """Yield (file, skipped) for each candidate file under the resolved input paths."""
    for p in paths:
        # The skill folder is skipped unless the command line names a folder inside it.
        allow_skill = within(p, SKILL_DIR) and p != SKILL_DIR
        if p.is_file():
            if is_candidate(p):
                yield p, is_skipped_file(p, allow_skill)
        elif p.is_dir():
            for root, dirs, files in os.walk(p):
                for d in dirs:
                    if d in COUNTED_SKIP_DIRS:
                        for sub_root, _, sub_files in os.walk(Path(root) / d):
                            for f in sub_files:
                                fp = Path(sub_root) / f
                                if is_candidate(fp):
                                    yield fp, True
                dirs[:] = [
                    d for d in dirs
                    if d not in SKIP_DIRS and d not in COUNTED_SKIP_DIRS and not d.startswith(".")
                ]
                for f in files:
                    fp = Path(root) / f
                    if is_candidate(fp):
                        yield fp, is_skipped_file(fp, allow_skill)


def plural(n, word):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


def select_hits(cat_hits, max_hits):
    """Group hits by file/target (definition files first, then most hits), keep the first max_hits.
    Returns (files, chosen, shown): chosen is [(file, hits)], shown is the flat list."""
    by_file = {}
    for h in cat_hits:
        by_file.setdefault(h["file"], []).append(h)
    files = sorted(
        by_file,
        key=lambda f: (not any(h["kind"] == "def" for h in by_file[f]), -len(by_file[f]), f),
    )
    chosen, left = [], max_hits
    for f in files:
        if left <= 0:
            break
        take = by_file[f][:left]
        chosen.append((f, take))
        left -= len(take)
    shown = [h for _, take in chosen for h in take]
    return files, chosen, shown


COMMENT_RX = re.compile(r'\{/\*.*?\*/\}|/\*.*?\*/|<!--.*?-->|\{#.*?#\}', re.S)
LINE_COMMENT_RX = re.compile(r'(?m)^\s*//.*$')
CORE_BLOCK_RX = re.compile(r'(?ms)^/\* CORE START.*?^/\* CORE END \*/[^\r\n]*')
CUSTOM_TAG_RX = re.compile(r'<([a-z][a-z0-9]*(?:-[a-z0-9]+)+)\b')


def is_core_copy(fp, text):
    """A stretchy-core.js copy inside the project (not user code)."""
    return fp.suffix.lower() in (".js", ".mjs", ".ts") and "stretchy-core.js" in text[:600] and "class Spring" in text


def blank_core_block(text):
    """Blank the inline core of a page built from the starter. Newlines are kept, so line numbers stay right."""
    return CORE_BLOCK_RX.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def strip_comments(text):
    """Remove block, JSX, template and line comments before counting component tags."""
    return LINE_COMMENT_RX.sub('', COMMENT_RX.sub('', text))


def comment_closer(line):
    """The closer of a block comment that this line opens and does not close, else None."""
    closer = None
    for m in re.finditer(r'/\*|\*/|<!--|-->|\{#|#\}', line):
        tok = m.group(0)
        if closer is None:
            closer = {"/*": "*/", "<!--": "-->", "{#": "#}"}.get(tok)
        elif tok == closer:
            closer = None
    return closer


def scan_text_source(name_rel, suffix, text, hits, css_count, css_files, css_first, stack, motion, uses, use_files):
    """Run static scan on a single text source (file, stdin, or fetched HTML)."""
    names = set()
    if suffix in (".jsx", ".tsx"):
        names.add("react")
    if suffix == ".vue":
        names.add("vue")
    if suffix == ".svelte":
        names.add("svelte")
    if suffix == ".astro":
        names.add("astro")
    if suffix in (".razor", ".cshtml"):
        names.add("razor / blazor")
    if suffix in (".jinja", ".jinja2", ".j2", ".djhtml"):
        names.add("jinja2 / django")
    if suffix in (".heex", ".leex", ".eex"):
        names.add("phoenix liveview")
    if suffix == ".templ":
        names.add("go templ")
    names.update(n for n, rxs in STACK_RX.items() if any(rx.search(text) for rx in rxs))
    if "class Spring" in text and "edgePair" in text:
        names.add(CORE_SIGN)
    stack.update(names)

    scan_text = blank_core_block(text)
    for n, rx in MOTION_RX.items():
        motion[n] += len(rx.findall(scan_text))

    stripped = None
    if suffix in JSX_EXTS:
        stripped = strip_comments(scan_text)
        for n in re.findall(r'<([A-Z][A-Za-z0-9]*)', stripped):
            uses[n] += 1
            use_files[n].add(name_rel)
    if suffix in CUSTOM_TAG_EXTS:
        if stripped is None:
            stripped = strip_comments(scan_text)
        for n in CUSTOM_TAG_RX.findall(stripped):
            uses[n] += 1
            use_files[n].add(name_rel)

    active = [k for k, rx in COMPILED_CATS.items() if rx.search(scan_text)]
    if not active:
        return
    css_file = suffix in CSS_EXTS
    sfc_file = suffix in SFC_EXTS
    in_style = False
    block_end = None
    for i, raw in enumerate(scan_text.splitlines(), 1):
        if css_file:
            css = True
        else:
            css = in_style or "<style" in raw
            if "<style" in raw:
                in_style = True
            if "</style>" in raw:
                in_style = False
        if block_end is not None:
            if block_end in raw:
                block_end = None
            continue
        block_end = comment_closer(raw)
        if block_end is not None:
            continue
        line = raw[:600]
        if css:
            for k in active:
                if COMPILED_CATS[k].search(line):
                    css_count[k] += 1
                    css_files[k].add(name_rel)
                    css_first.setdefault(k, (name_rel, i))
            continue
        if line.lstrip().startswith(COMMENT_STARTS):
            continue
        kind = "def" if (DEF_RX.search(line) or (sfc_file and i <= 5)) else "use"
        for k in active:
            if COMPILED_CATS[k].search(line):
                hits[k].append({
                    "file": name_rel,
                    "line": i,
                    "kind": kind,
                    "snippet": line.strip()[:110],
                })


def _is_blocked_browser_page(body_text):
    low = (body_text or "").lower()
    return ("this page is blocked" in low and "organization" in low) or "err_blocked_by_administrator" in low


def inspect_dom_playwright(target_url, width, height, wait_ms, channel="", fallback_html=None):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        order = [channel] if channel else ["chromium", "msedge", "chrome"]
        browser = None
        last_err = None
        for ch in order:
            try:
                browser = p.chromium.launch() if ch == "chromium" else p.chromium.launch(channel=ch)
                break
            except Exception as e:
                last_err = e
        if browser is None:
            raise RuntimeError(f"Playwright browser launch failed: {last_err}")
        page = browser.new_page(viewport={"width": width, "height": height})
        try:
            page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
            if fallback_html is not None and _is_blocked_browser_page(page.evaluate("document.body ? document.body.innerText : ''")):
                page.set_content(fallback_html, wait_until="domcontentloaded")
            page.wait_for_timeout(wait_ms)
            data = page.evaluate(DOM_AUDIT_JS)
        finally:
            browser.close()
        data["engine"] = "playwright"
        return data


def inspect_dom_selenium(target_url, width, height, wait_ms, fallback_html=None):
    import time
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument(f"--window-size={width},{height}")
    driver = webdriver.Chrome(options=opts)
    try:
        driver.set_page_load_timeout(25)
        driver.get(target_url)
        body_txt = driver.execute_script("return document.body ? document.body.innerText : '';")
        if _is_blocked_browser_page(body_txt):
            if fallback_html is not None:
                driver.get("about:blank")
                driver.execute_script("document.open(); document.write(arguments[0]); document.close();", fallback_html)
            else:
                raise RuntimeError("Browser blocked target URL")
        time.sleep(max(0.1, wait_ms / 1000.0))
        data = driver.execute_script(f"return ({DOM_AUDIT_JS})();")
    finally:
        driver.quit()
    data["engine"] = "selenium"
    return data


def inspect_live_dom(target_url, width, height, wait_ms, channel="", fallback_html=None):
    """Inspect a live URL or file:// URI in headless Chromium (Playwright -> Selenium)."""
    errors = []
    try:
        return inspect_dom_playwright(target_url, width, height, wait_ms, channel, fallback_html=fallback_html)
    except Exception as e:
        errors.append(f"playwright: {e.__class__.__name__}")
    try:
        return inspect_dom_selenium(target_url, width, height, wait_ms, fallback_html=fallback_html)
    except Exception as e:
        errors.append(f"selenium: {e.__class__.__name__}")
    return {"error": "; ".join(errors)}


def fetch_url_html(url, timeout=15):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; stretchy-morph-ui-audit/1.0)",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(MAX_FILE_BYTES)
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def parse_viewport(vp_str):
    m = re.match(r'^(\d+)\s*[xX,]\s*(\d+)$', vp_str.strip())
    if not m:
        return 1280, 900
    return int(m.group(1)), int(m.group(2))


def main():
    # Windows consoles default to a legacy code page that garbles Thai snippets.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="local file(s), folder(s), or http(s):// URL(s)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-hits", type=int, default=6)
    ap.add_argument("--dom", action="store_true", help="also inspect local HTML file(s) in headless Chromium (rendered DOM + computed styles)")
    ap.add_argument("--stdin", action="store_true", help="scan code pasted via standard input")
    ap.add_argument("--ext", default=".html", help="file extension hint for --stdin (default: .html)")
    ap.add_argument("--wait-ms", type=int, default=1500, help="ms to wait for SPA hydration in live DOM mode")
    ap.add_argument("--viewport", default="1280x900", help="viewport WxH for live DOM inspection")
    ap.add_argument("--channel", default="", help="browser channel for Playwright: chromium, msedge, or chrome")
    args = ap.parse_args()

    if not args.paths and not args.stdin:
        ap.error("provide at least one PATH or URL, or pass --stdin")

    url_inputs = [p for p in args.paths if is_url(p)]
    path_raw = [p for p in args.paths if not is_url(p)]
    inputs = [Path(p).resolve() for p in path_raw]
    missing = [p for p, fp in zip(path_raw, inputs) if not fp.exists()]
    if missing:
        for p in missing:
            print(f"path not found: {p}")
        sys.exit(2)

    if inputs:
        bases = [p if p.is_dir() else p.parent for p in inputs]
        try:
            root = Path(os.path.commonpath([str(b) for b in bases]))
        except ValueError:
            root = bases[0]
        root_posix = root.as_posix()
    elif url_inputs:
        root = None
        root_posix = url_inputs[0]
    else:
        root = None
        root_posix = "<stdin>"

    def rel(fp):
        if root is None:
            return fp.name
        return os.path.relpath(str(fp), str(root)).replace(os.sep, "/")

    hits = {k: [] for k in CATEGORIES}
    css_count = collections.Counter()
    css_files = collections.defaultdict(set)
    css_first = {}
    stack = collections.Counter()
    motion = {k: 0 for k in MOTION_RX}
    uses = collections.Counter()
    use_files = collections.defaultdict(set)
    deps = {}
    nfiles = skipped = 0
    dom_targets = []
    notes = []

    # 1. Optional --stdin scan
    if args.stdin:
        ext = args.ext if args.ext.startswith(".") else "." + args.ext
        stdin_text = sys.stdin.read()
        if stdin_text.strip():
            nfiles += 1
            scan_text_source(f"<stdin>{ext}", ext.lower(), stdin_text,
                             hits, css_count, css_files, css_first, stack, motion, uses, use_files)

    # 2. Local filesystem static scan
    local_html_for_dom = []
    for fp, is_skip in iter_files(inputs):
        if is_skip:
            skipped += 1
            continue
        try:
            if fp.stat().st_size > MAX_FILE_BYTES:
                skipped += 1
                continue
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        nfiles += 1
        if fp.name == "package.json":
            try:
                pj = json.loads(text)
                for sec in ("dependencies", "devDependencies"):
                    deps.update(pj.get(sec, {}) or {})
            except (ValueError, AttributeError):
                pass
            continue
        if is_core_copy(fp, text):
            stack.add(CORE_SIGN) if hasattr(stack, "add") else stack.update([CORE_SIGN])
            continue
        if args.dom and fp.suffix.lower() in (".html", ".htm"):
            local_html_for_dom.append((rel(fp), fp.as_uri(), text))
        scan_text_source(rel(fp), fp.suffix.lower(), text,
                         hits, css_count, css_files, css_first, stack, motion, uses, use_files)

    # 3. Live DOM inspection for URLs (and local HTML files when --dom is set)
    vp_w, vp_h = parse_viewport(args.viewport)
    dom_queue = [(u, u, True, None) for u in url_inputs] + [(label, uri, False, html) for label, uri, html in local_html_for_dom]
    for label, target_uri, allow_http_fallback, fallback_html in dom_queue:
        dom_res = inspect_live_dom(target_uri, vp_w, vp_h, args.wait_ms, args.channel, fallback_html=fallback_html)
        if "error" in dom_res:
            if allow_http_fallback:
                try:
                    html = fetch_url_html(target_uri)
                    nfiles += 1
                    scan_text_source(label, ".html", html,
                                     hits, css_count, css_files, css_first, stack, motion, uses, use_files)
                    notes.append(
                        f"Live DOM browser unavailable ({dom_res['error']}); fetched static HTML for {label} "
                        "(client-rendered SPAs may need Playwright or Selenium)."
                    )
                except (urllib.error.URLError, OSError, ValueError) as e:
                    notes.append(f"Could not fetch {label}: {e}")
            else:
                notes.append(f"Live DOM skipped for {label} ({dom_res['error']}); static scan still ran.")
            continue

        nfiles += 1 if allow_http_fallback else 0
        dom_targets.append({
            "target": label,
            "engine": dom_res.get("engine", "browser"),
            "title": dom_res.get("title", ""),
            "elements_inspected": dom_res.get("elements_inspected", 0),
            "shadow_roots": dom_res.get("shadow_roots", 0),
        })
        stack.update(dom_res.get("stack", []))
        for mk, mv in (dom_res.get("motion") or {}).items():
            if mk in motion:
                motion[mk] += mv
        for cat, items in (dom_res.get("hits") or {}).items():
            if cat not in hits:
                continue
            for item in items:
                hits[cat].append({
                    "file": f"{label} [DOM]",
                    "line": 0,
                    "selector": item.get("selector", ""),
                    "kind": "dom",
                    "snippet": f"{item.get('selector', '')} -> {item.get('snippet', '')}"[:110],
                })

    stack.update({label for d in deps for key, label in DEP_LABELS if d == key})
    stack_names = sorted(stack, key=lambda k: -stack[k])
    shared = [
        {"name": n, "uses": c, "files": len(use_files[n])}
        for n, c in sorted(uses.items(), key=lambda kv: (-kv[1], kv[0]))
        if c >= 2
    ][:8]

    # Categories with non-CSS hits first (most hits first), CSS-only categories last.
    order = sorted((k for k in CATEGORIES if hits[k] or css_count[k]), key=lambda k: -len(hits[k]))
    candidates = []
    for k in order:
        label, showcase, technique, idea, _ = CATEGORIES[k]
        files, _, shown = select_hits(hits[k], args.max_hits)
        candidates.append({
            "category": k,
            "label": label,
            "showcase": showcase,
            "technique": technique,
            "idea": idea,
            "count": len(hits[k]),
            "css_count": css_count[k],
            "files": files,
            "hits": shown,
        })

    if args.json:
        result = {
            "root": root_posix,
            "files_scanned": nfiles,
            "files_skipped": skipped,
            "stack": stack_names,
            "motion": motion,
            "shared_components": shared,
            "candidates": candidates,
        }
        if dom_targets:
            result["dom_targets"] = dom_targets
        if notes:
            result["notes"] = notes
        print(json.dumps(result, ensure_ascii=False, separators=(',', ':')))
        return

    print(
        f"Scanned {plural(nfiles, 'source')} under {root_posix} "
        f"(skipped {skipped}: tests, stories, minified, generated or the skill itself)"
    )
    if dom_targets:
        for dt in dom_targets:
            sh = f", {dt['shadow_roots']} shadow root(s)" if dt["shadow_roots"] else ""
            print(f"Live DOM ({dt['engine']}): {dt['target']} — {dt['elements_inspected']} elements inspected{sh}")
    print("Stack: " + (", ".join(stack_names) or "plain HTML/CSS/JS (no framework detected)"))
    if CORE_SIGN in stack:
        print("Note: the stretchy core is already in this code: reuse it, do not add a second copy.")
    for note in notes:
        print("Note: " + note)
    motion_txt = ", ".join(f"{k} {v}" for k, v in motion.items())
    if motion["reduced-motion handling"] == 0:
        motion_txt += " (none: add it)"
    print("Motion today: " + motion_txt)
    if shared:
        print(
            "Shared components (uses/files): "
            + ", ".join(f"{s['name']} {s['uses']}/{s['files']}" for s in shared)
        )
    if not candidates:
        print("\nNo UI candidates found. If this is a compiled SPA or Tailwind-only site, try passing its live URL or --dom.")
        return
    print("\nCandidates (heuristic: inspect the code or DOM selector around each hit before proposing; d = definition line)\n")
    for c in candidates:
        k = c["category"]
        label, showcase, technique, idea, _ = CATEGORIES[k]
        if not hits[k]:
            first_file, first_line = css_first[k]
            print(
                f"{label}: CSS only, {plural(css_count[k], 'line')} in {plural(len(css_files[k]), 'file')} "
                f"({first_file}:{first_line}) -> showcase {showcase} | check the class is still used"
            )
            continue
        files, chosen, shown = select_hits(hits[k], args.max_hits)
        css_part = f" (+{css_count[k]} in CSS)" if css_count[k] else ""
        print(
            f"{label}: {plural(len(hits[k]), 'hit')}, {plural(len(files), 'source')}{css_part}"
            f" -> showcase {showcase} | {technique} | {idea}"
        )
        for f, take in chosen:
            if take[0].get("kind") == "dom":
                sels = ", ".join(h.get("selector", "") for h in take[:3])
                print(f"  {f}: {sels}  ({take[0]['snippet'][:75]})")
            else:
                nums = ",".join(f"{h['line']}{'d' if h['kind'] == 'def' else ''}" for h in take)
                print(f"  {f}:{nums}  {take[0]['snippet'][:80]}")
        left = len(hits[k]) - len(shown)
        if left:
            more_files = len(files) - len(chosen)
            tail = f" in {more_files} more {'source' if more_files == 1 else 'sources'}" if more_files else ""
            print(f"  … {left} more {'hit' if left == 1 else 'hits'}{tail}")


if __name__ == "__main__":
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # quiet when piped into head
    main()
