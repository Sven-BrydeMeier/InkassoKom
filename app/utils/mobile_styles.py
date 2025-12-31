"""
Mobile-optimized styles for NotarFlow
Responsive CSS for phones and tablets
"""

MOBILE_CSS = """
<style>
    /* ============================================= */
    /* MOBILE-FIRST RESPONSIVE DESIGN               */
    /* ============================================= */

    /* Base Mobile Styles (< 768px) */
    @media (max-width: 768px) {
        /* Hide sidebar by default on mobile */
        section[data-testid="stSidebar"] {
            width: 100% !important;
            min-width: 100% !important;
        }

        section[data-testid="stSidebar"][aria-expanded="false"] {
            margin-left: -100% !important;
        }

        /* Full width main content */
        .main .block-container {
            padding: 1rem 0.5rem !important;
            max-width: 100% !important;
        }

        /* Larger touch targets */
        .stButton > button {
            min-height: 48px !important;
            font-size: 16px !important;
            padding: 12px 24px !important;
            width: 100% !important;
            margin-bottom: 8px !important;
        }

        /* Stack columns vertically */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
        }

        /* Form inputs */
        .stTextInput input,
        .stSelectbox select,
        .stNumberInput input,
        .stDateInput input,
        .stTextArea textarea {
            font-size: 16px !important; /* Prevents iOS zoom */
            min-height: 48px !important;
            padding: 12px !important;
        }

        /* Metrics */
        [data-testid="metric-container"] {
            padding: 8px !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
        }

        /* Tables */
        .stDataFrame {
            overflow-x: auto !important;
        }

        /* Cards */
        .case-card, .metric-card {
            padding: 12px !important;
            margin-bottom: 12px !important;
        }

        /* Headers */
        h1 {
            font-size: 1.5rem !important;
        }

        h2 {
            font-size: 1.25rem !important;
        }

        h3 {
            font-size: 1.1rem !important;
        }

        /* Tab buttons */
        .stTabs [data-baseweb="tab-list"] {
            flex-wrap: wrap !important;
            gap: 4px !important;
        }

        .stTabs [data-baseweb="tab"] {
            flex: 1 1 auto !important;
            min-width: 80px !important;
            padding: 8px 12px !important;
            font-size: 14px !important;
        }

        /* Expander */
        .streamlit-expanderHeader {
            font-size: 14px !important;
            padding: 12px !important;
        }

        /* Progress bar */
        .stProgress > div {
            height: 12px !important;
        }

        /* Hide less important elements on mobile */
        .hide-on-mobile {
            display: none !important;
        }
    }

    /* Tablet Styles (768px - 1024px) */
    @media (min-width: 768px) and (max-width: 1024px) {
        .main .block-container {
            padding: 1rem 1.5rem !important;
        }

        /* 2-column layout for tablets */
        [data-testid="column"]:nth-child(odd) {
            width: 48% !important;
        }

        [data-testid="column"]:nth-child(even) {
            width: 48% !important;
        }

        .stButton > button {
            min-height: 44px !important;
        }
    }

    /* ============================================= */
    /* TOUCH-FRIENDLY COMPONENTS                    */
    /* ============================================= */

    /* Swipe-friendly cards */
    .touch-card {
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        padding: 16px;
        margin-bottom: 12px;
        transition: transform 0.2s ease;
    }

    .touch-card:active {
        transform: scale(0.98);
    }

    /* Action buttons row */
    .action-buttons {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }

    .action-buttons button {
        flex: 1;
        min-width: 100px;
    }

    /* Status badges - touch friendly */
    .status-badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 500;
    }

    .status-success {
        background-color: #E8F5E9;
        color: #2E7D32;
    }

    .status-warning {
        background-color: #FFF3E0;
        color: #E65100;
    }

    .status-error {
        background-color: #FFEBEE;
        color: #C62828;
    }

    .status-info {
        background-color: #E3F2FD;
        color: #1565C0;
    }

    /* ============================================= */
    /* MOBILE NAVIGATION                            */
    /* ============================================= */

    .mobile-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        border-top: 1px solid #E0E0E0;
        padding: 8px 0;
        z-index: 999;
        display: none;
    }

    @media (max-width: 768px) {
        .mobile-nav {
            display: flex;
            justify-content: space-around;
        }

        /* Add padding at bottom for mobile nav */
        .main .block-container {
            padding-bottom: 80px !important;
        }
    }

    .mobile-nav-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 8px 16px;
        color: #666;
        text-decoration: none;
        font-size: 12px;
    }

    .mobile-nav-item.active {
        color: #1E88E5;
    }

    .mobile-nav-item span {
        margin-top: 4px;
    }

    /* ============================================= */
    /* PWA / FULLSCREEN SUPPORT                     */
    /* ============================================= */

    /* Safe area insets for notched devices */
    @supports (padding: env(safe-area-inset-bottom)) {
        .mobile-nav {
            padding-bottom: env(safe-area-inset-bottom);
        }

        .main .block-container {
            padding-left: env(safe-area-inset-left);
            padding-right: env(safe-area-inset-right);
        }
    }

    /* iOS standalone mode */
    @media (display-mode: standalone) {
        .stApp header {
            padding-top: env(safe-area-inset-top);
        }
    }

    /* ============================================= */
    /* TIMELINE MOBILE OPTIMIZATION                 */
    /* ============================================= */

    .timeline-item {
        padding: 12px;
        border-left: 3px solid #1E88E5;
        margin-left: 8px;
        margin-bottom: 16px;
    }

    .timeline-item-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        flex-wrap: wrap;
        gap: 8px;
    }

    .timeline-item-title {
        font-weight: 600;
        font-size: 15px;
    }

    .timeline-item-date {
        color: #666;
        font-size: 13px;
    }

    .timeline-item-body {
        margin-top: 8px;
        font-size: 14px;
        color: #444;
    }

    /* ============================================= */
    /* AMOUNT DISPLAY                               */
    /* ============================================= */

    .amount-large {
        font-size: 1.75rem;
        font-weight: 700;
        color: #1E88E5;
    }

    .amount-positive {
        color: #2E7D32;
    }

    .amount-negative {
        color: #C62828;
    }

    /* ============================================= */
    /* PULL-TO-REFRESH INDICATOR                    */
    /* ============================================= */

    .refresh-indicator {
        text-align: center;
        padding: 16px;
        color: #666;
        font-size: 14px;
    }

    /* ============================================= */
    /* LOADING STATES                               */
    /* ============================================= */

    .skeleton {
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: skeleton-loading 1.5s infinite;
        border-radius: 4px;
    }

    @keyframes skeleton-loading {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }

    /* ============================================= */
    /* ACCESSIBILITY                                */
    /* ============================================= */

    /* Focus indicators */
    button:focus,
    input:focus,
    select:focus,
    textarea:focus {
        outline: 2px solid #1E88E5 !important;
        outline-offset: 2px !important;
    }

    /* Reduce motion for users who prefer it */
    @media (prefers-reduced-motion: reduce) {
        * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }

    /* High contrast mode */
    @media (prefers-contrast: high) {
        .status-badge {
            border: 2px solid currentColor;
        }

        .touch-card {
            border: 1px solid #000;
        }
    }

    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .touch-card {
            background: #1E1E1E;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }

        .mobile-nav {
            background: #1E1E1E;
            border-top-color: #333;
        }
    }
</style>
"""

PWA_META_TAGS = """
<head>
    <!-- Mobile Meta Tags -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="NotarFlow">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#1E88E5">
    <meta name="format-detection" content="telephone=no">

    <!-- PWA Icons -->
    <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
    <link rel="manifest" href="/manifest.json">
</head>
"""

MOBILE_BOTTOM_NAV_LAWYER = """
<div class="mobile-nav">
    <a href="/" class="mobile-nav-item active">
        <span style="font-size: 20px;">📊</span>
        <span>Dashboard</span>
    </a>
    <a href="/Akten" class="mobile-nav-item">
        <span style="font-size: 20px;">📁</span>
        <span>Akten</span>
    </a>
    <a href="/Posteingang" class="mobile-nav-item">
        <span style="font-size: 20px;">📬</span>
        <span>Post</span>
    </a>
    <a href="/Profil" class="mobile-nav-item">
        <span style="font-size: 20px;">👤</span>
        <span>Profil</span>
    </a>
</div>
"""

MOBILE_BOTTOM_NAV_CREDITOR = """
<div class="mobile-nav">
    <a href="/" class="mobile-nav-item active">
        <span style="font-size: 20px;">📊</span>
        <span>Aktuelles</span>
    </a>
    <a href="/Forderungen" class="mobile-nav-item">
        <span style="font-size: 20px;">💰</span>
        <span>Forderungen</span>
    </a>
    <a href="/Zahlungen" class="mobile-nav-item">
        <span style="font-size: 20px;">💳</span>
        <span>Zahlungen</span>
    </a>
    <a href="/Profil" class="mobile-nav-item">
        <span style="font-size: 20px;">👤</span>
        <span>Profil</span>
    </a>
</div>
"""

MOBILE_BOTTOM_NAV_DEBTOR = """
<div class="mobile-nav">
    <a href="/" class="mobile-nav-item active">
        <span style="font-size: 20px;">📊</span>
        <span>Übersicht</span>
    </a>
    <a href="/Dokumente" class="mobile-nav-item">
        <span style="font-size: 20px;">📄</span>
        <span>Dokumente</span>
    </a>
    <a href="/Ratenzahlung" class="mobile-nav-item">
        <span style="font-size: 20px;">📅</span>
        <span>Raten</span>
    </a>
    <a href="/Profil" class="mobile-nav-item">
        <span style="font-size: 20px;">👤</span>
        <span>Profil</span>
    </a>
</div>
"""


def inject_mobile_styles():
    """Inject mobile-optimized CSS into Streamlit."""
    import streamlit as st
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)


def inject_pwa_meta():
    """Inject PWA meta tags."""
    import streamlit as st
    st.markdown(PWA_META_TAGS, unsafe_allow_html=True)


def inject_mobile_nav(role: str):
    """Inject mobile bottom navigation based on role."""
    import streamlit as st

    nav_map = {
        'rechtsanwalt': MOBILE_BOTTOM_NAV_LAWYER,
        'admin': MOBILE_BOTTOM_NAV_LAWYER,
        'glaeubigerin': MOBILE_BOTTOM_NAV_CREDITOR,
        'schuldner': MOBILE_BOTTOM_NAV_DEBTOR,
    }

    nav_html = nav_map.get(role, MOBILE_BOTTOM_NAV_LAWYER)
    st.markdown(nav_html, unsafe_allow_html=True)


def get_device_type():
    """
    Detect device type from user agent.
    Note: This is a best-effort detection and may not be 100% accurate.
    """
    import streamlit as st

    # Streamlit doesn't expose user-agent directly
    # This is a placeholder for potential future implementation
    return "desktop"


def is_mobile():
    """Check if current device is mobile."""
    return get_device_type() in ["mobile", "tablet"]
