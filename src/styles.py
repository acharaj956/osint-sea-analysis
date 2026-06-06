GLOBAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
    }

    .page-header {
        background: linear-gradient(135deg, #009edb 0%, #005a8c 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }

    .page-header h1 {
        margin: 0;
        font-size: 1.8rem;
        color: white;
    }

    .page-header p {
        margin: 0.3rem 0 0 0;
        opacity: 0.85;
        font-size: 0.95rem;
    }

    .metric-card {
        background: #1a1f2e;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        transition: border-color 0.2s;
    }

    .metric-card:hover {
        border-color: #009edb;
    }

    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #009edb;
        line-height: 1.2;
    }

    .metric-label {
        font-size: 0.8rem;
        color: #95a5a6;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.3rem;
    }

    .risk-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    .risk-high {
        background: rgba(231, 76, 60, 0.2);
        color: #e74c3c;
        border: 1px solid #e74c3c;
    }

    .risk-medium {
        background: rgba(243, 156, 18, 0.2);
        color: #f39c12;
        border: 1px solid #f39c12;
    }

    .risk-low {
        background: rgba(39, 174, 96, 0.2);
        color: #27ae60;
        border: 1px solid #27ae60;
    }

    .sanctioned-tag {
        background: rgba(231, 76, 60, 0.15);
        color: #e74c3c;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid rgba(231, 76, 60, 0.3);
    }

    .info-box {
        background: rgba(0, 158, 219, 0.08);
        border-left: 3px solid #009edb;
        padding: 1rem 1.2rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
        font-size: 0.9rem;
    }

    div[data-testid="stSidebar"] {
        background: #0a0e17;
        border-right: 1px solid #1a1f2e;
    }

    div[data-testid="stSidebar"] .stRadio > label {
        font-size: 0.85rem;
        color: #95a5a6;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }

    div[data-testid="stExpander"] {
        border: 1px solid #2d3748;
        border-radius: 8px;
    }

    footer {visibility: hidden;}
</style>
"""


def metric_card(value: str, label: str) -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """


def risk_badge(level: str) -> str:
    css_class = f"risk-{level.lower()}"
    return f'<span class="risk-badge {css_class}">{level.upper()} RISK</span>'


def sanctioned_tag() -> str:
    return '<span class="sanctioned-tag">OFAC SANCTIONED</span>'


def page_header(title: str, subtitle: str) -> str:
    return f"""
    <div class="page-header">
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    """
