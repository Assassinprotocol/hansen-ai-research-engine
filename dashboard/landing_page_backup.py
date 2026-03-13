LANDING_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hansen AI — Market Intelligence System</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow+Condensed:wght@400;600;700;800&family=Barlow:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:       #050810;
  --panel:    #090e18;
  --border:   #111e30;
  --cyan:     #00e5ff;
  --green:    #00ff88;
  --red:      #ff3d5a;
  --yellow:   #ffd600;
  --text:     #c9d1d9;
  --dim:      #4a6070;
  --glow:     0 0 24px #00e5ff33;
}
* { margin:0; padding:0; box-sizing:border-box; }
html { scroll-behavior:smooth; }
body {
  background:var(--bg);
  color:var(--text);
  font-family:'Barlow',sans-serif;
  font-size:16px;
  overflow-x:hidden;
}

/* ---- GRID BG ---- */
body::before {
  content:'';
  position:fixed; inset:0;
  background-image:
    linear-gradient(rgba(0,229,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,229,255,0.03) 1px, transparent 1px);
  background-size:40px 40px;
  pointer-events:none;
  z-index:0;
}

/* ---- NAV ---- */
nav {
  position:fixed; top:0; left:0; right:0; z-index:100;
  background:rgba(5,8,16,0.85);
  backdrop-filter:blur(12px);
  border-bottom:1px solid var(--border);
  padding:14px 48px;
  display:flex; align-items:center; justify-content:space-between;
}
.nav-logo {
  font-family:'Barlow Condensed',sans-serif;
  font-size:20px; font-weight:800;
  letter-spacing:4px; color:var(--cyan);
  text-transform:uppercase;
}
.nav-logo span { color:var(--text); }
.nav-links { display:flex; gap:32px; }
.nav-links a {
  font-size:12px; letter-spacing:2px; text-transform:uppercase;
  color:var(--dim); text-decoration:none; transition:color 0.2s;
}
.nav-links a:hover { color:var(--cyan); }
.nav-cta {
  display:flex; gap:10px;
}
.btn-outline {
  font-family:'Barlow Condensed',sans-serif;
  font-size:13px; font-weight:700; letter-spacing:2px;
  text-transform:uppercase; padding:8px 20px;
  border:1px solid var(--border); border-radius:2px;
  color:var(--dim); background:none; cursor:pointer;
  text-decoration:none; transition:all 0.2s;
}
.btn-outline:hover { border-color:var(--cyan); color:var(--cyan); }
.btn-primary {
  font-family:'Barlow Condensed',sans-serif;
  font-size:13px; font-weight:700; letter-spacing:2px;
  text-transform:uppercase; padding:8px 24px;
  border:1px solid var(--cyan); border-radius:2px;
  color:var(--bg); background:var(--cyan); cursor:pointer;
  text-decoration:none; transition:all 0.2s;
}
.btn-primary:hover { background:#00ccee; }

/* ---- HERO ---- */
.hero {
  min-height:100vh;
  display:flex; flex-direction:column;
  align-items:center; justify-content:center;
  text-align:center;
  padding:120px 48px 80px;
  position:relative; z-index:1;
}
.hero-badge {
  display:inline-flex; align-items:center; gap:8px;
  font-family:'Share Tech Mono',monospace;
  font-size:11px; letter-spacing:3px; text-transform:uppercase;
  color:var(--cyan); border:1px solid #00e5ff33;
  background:#00e5ff08; padding:6px 16px; border-radius:2px;
  margin-bottom:32px;
}
.live-dot {
  width:6px; height:6px; border-radius:50%;
  background:var(--green); animation:pulse 2s infinite;
}
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(0.8)} }

.hero h1 {
  font-family:'Barlow Condensed',sans-serif;
  font-size:clamp(52px,8vw,96px);
  font-weight:800; line-height:0.95;
  letter-spacing:-1px;
  color:#fff;
  margin-bottom:8px;
}
.hero h1 .accent { color:var(--cyan); }
.hero h1 .line2 { display:block; color:var(--text); font-weight:400; font-size:0.65em; letter-spacing:6px; text-transform:uppercase; margin-top:8px; }

.hero-sub {
  max-width:560px; margin:28px auto 48px;
  font-size:17px; line-height:1.7; color:#7a9ab8;
}
.hero-actions { display:flex; gap:14px; justify-content:center; flex-wrap:wrap; }
.btn-hero-primary {
  font-family:'Barlow Condensed',sans-serif;
  font-size:15px; font-weight:700; letter-spacing:3px;
  text-transform:uppercase; padding:14px 36px;
  background:var(--cyan); color:var(--bg);
  border:none; border-radius:2px; cursor:pointer;
  text-decoration:none; transition:all 0.2s;
  box-shadow:0 0 32px #00e5ff44;
}
.btn-hero-primary:hover { background:#00ccee; box-shadow:0 0 48px #00e5ff66; }
.btn-hero-outline {
  font-family:'Barlow Condensed',sans-serif;
  font-size:15px; font-weight:700; letter-spacing:3px;
  text-transform:uppercase; padding:14px 36px;
  background:none; color:var(--text);
  border:1px solid #2a3a4a; border-radius:2px; cursor:pointer;
  text-decoration:none; transition:all 0.2s;
}
.btn-hero-outline:hover { border-color:var(--cyan); color:var(--cyan); }

/* ---- LIVE TICKER ---- */
.live-bar {
  position:relative; z-index:1;
  background:#060a10;
  border-top:1px solid var(--border);
  border-bottom:1px solid var(--border);
  overflow:hidden; height:40px;
  display:flex; align-items:center;
}
.live-bar::before,.live-bar::after {
  content:''; position:absolute; top:0; bottom:0; width:80px; z-index:2; pointer-events:none;
}
.live-bar::before { left:0; background:linear-gradient(to right,#060a10,transparent); }
.live-bar::after  { right:0; background:linear-gradient(to left,#060a10,transparent); }
.live-track {
  display:flex; animation:scroll-left 40s linear infinite; white-space:nowrap;
}
@keyframes scroll-left { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
.live-item {
  display:inline-flex; align-items:center; gap:8px;
  padding:0 24px; font-family:'Share Tech Mono',monospace; font-size:12px;
  border-right:1px solid #111e30;
}
.live-sym { color:var(--dim); letter-spacing:1px; }
.live-val { color:var(--text); }
.live-up  { color:var(--green); font-size:10px; }
.live-dn  { color:var(--red);   font-size:10px; }

/* ---- STATS BAR ---- */
.stats-bar {
  position:relative; z-index:1;
  display:grid; grid-template-columns:repeat(4,1fr);
  border-bottom:1px solid var(--border);
}
.stat-cell {
  padding:32px 40px;
  border-right:1px solid var(--border);
  text-align:center;
  position:relative; overflow:hidden;
}
.stat-cell:last-child { border-right:none; }
.stat-cell::before {
  content:''; position:absolute; top:0; left:0; right:0; height:2px;
  background:linear-gradient(to right,transparent,var(--cyan),transparent);
  opacity:0;
  transition:opacity 0.3s;
}
.stat-cell:hover::before { opacity:1; }
.stat-num {
  font-family:'Barlow Condensed',sans-serif;
  font-size:40px; font-weight:800; color:#fff;
  line-height:1; margin-bottom:6px;
}
.stat-num span { color:var(--cyan); }
.stat-desc { font-size:11px; letter-spacing:2px; color:var(--dim); text-transform:uppercase; }

/* ---- SECTION BASE ---- */
section { position:relative; z-index:1; }
.section-inner { max-width:1200px; margin:0 auto; padding:100px 48px; }
.section-label {
  font-family:'Share Tech Mono',monospace;
  font-size:11px; letter-spacing:3px; color:var(--cyan);
  text-transform:uppercase; margin-bottom:16px;
  display:flex; align-items:center; gap:10px;
}
.section-label::before { content:''; display:block; width:32px; height:1px; background:var(--cyan); }
.section-title {
  font-family:'Barlow Condensed',sans-serif;
  font-size:clamp(36px,5vw,60px); font-weight:800;
  color:#fff; line-height:1; margin-bottom:20px;
}
.section-title .dim { color:var(--dim); font-weight:400; }
.section-sub { font-size:16px; color:#7a9ab8; line-height:1.7; max-width:540px; }

/* ---- FEATURES ---- */
.features-grid {
  display:grid; grid-template-columns:repeat(3,1fr); gap:1px;
  background:var(--border); margin-top:64px;
  border:1px solid var(--border);
}
.feature-card {
  background:var(--panel); padding:36px 32px;
  transition:background 0.2s; position:relative; overflow:hidden;
}
.feature-card:hover { background:#0d1520; }
.feature-card::after {
  content:''; position:absolute; bottom:0; left:0; right:0; height:1px;
  background:linear-gradient(to right,transparent,var(--cyan),transparent);
  opacity:0; transition:opacity 0.3s;
}
.feature-card:hover::after { opacity:1; }
.feature-icon {
  font-size:28px; margin-bottom:20px;
  display:block;
}
.feature-title {
  font-family:'Barlow Condensed',sans-serif;
  font-size:20px; font-weight:700; color:#fff;
  letter-spacing:1px; margin-bottom:12px;
  text-transform:uppercase;
}
.feature-desc { font-size:14px; color:#7a9ab8; line-height:1.7; }
.feature-tag {
  display:inline-block; margin-top:16px;
  font-family:'Share Tech Mono',monospace;
  font-size:10px; letter-spacing:2px;
  color:var(--cyan); border:1px solid #00e5ff33;
  padding:3px 10px; border-radius:2px;
}

/* ---- HOW IT WORKS ---- */
.how-grid {
  display:grid; grid-template-columns:repeat(4,1fr); gap:0;
  margin-top:64px; position:relative;
}
.how-grid::before {
  content:''; position:absolute;
  top:28px; left:calc(12.5% + 28px); right:calc(12.5% + 28px); height:1px;
  background:linear-gradient(to right,var(--cyan),transparent 30%,transparent 70%,var(--cyan));
  opacity:0.3;
}
.how-step { text-align:center; padding:0 24px; }
.how-num {
  width:56px; height:56px; border-radius:50%;
  border:1px solid var(--cyan);
  background:#00e5ff0a;
  display:flex; align-items:center; justify-content:center;
  margin:0 auto 20px;
  font-family:'Barlow Condensed',sans-serif;
  font-size:22px; font-weight:800; color:var(--cyan);
}
.how-title {
  font-family:'Barlow Condensed',sans-serif;
  font-size:18px; font-weight:700; color:#fff;
  text-transform:uppercase; letter-spacing:1px;
  margin-bottom:10px;
}
.how-desc { font-size:13px; color:#7a9ab8; line-height:1.6; }

/* ---- PRICING ---- */
.pricing-grid {
  display:grid; grid-template-columns:1fr 1fr; gap:24px;
  max-width:860px; margin:64px auto 0;
}
.price-card {
  background:var(--panel); border:1px solid var(--border);
  border-radius:4px; padding:40px 36px;
  position:relative; overflow:hidden;
  transition:transform 0.2s, box-shadow 0.2s;
}
.price-card:hover { transform:translateY(-4px); box-shadow:0 16px 48px #00000066; }
.price-card.featured {
  border-color:var(--cyan);
  box-shadow:0 0 48px #00e5ff11;
}
.price-card.featured::before {
  content:'MOST POPULAR';
  position:absolute; top:0; right:0;
  font-family:'Share Tech Mono',monospace;
  font-size:9px; letter-spacing:2px;
  background:var(--cyan); color:var(--bg);
  padding:4px 12px;
}
.price-plan {
  font-family:'Barlow Condensed',sans-serif;
  font-size:13px; font-weight:700; letter-spacing:3px;
  text-transform:uppercase; color:var(--dim); margin-bottom:16px;
}
.price-amount {
  font-family:'Barlow Condensed',sans-serif;
  font-size:60px; font-weight:800; color:#fff;
  line-height:1; margin-bottom:4px;
}
.price-amount sup { font-size:48px; color:#fff; vertical-align:top; margin-top:6px; display:inline-block; }
.price-amount .period { font-size:18px; color:var(--dim); font-weight:400; }
.price-desc { font-size:13px; color:var(--dim); margin-bottom:28px; }
.price-features { list-style:none; margin-bottom:32px; }
.price-features li {
  font-size:14px; color:#7a9ab8; padding:8px 0;
  border-bottom:1px solid var(--border);
  display:flex; align-items:center; gap:10px;
}
.price-features li:last-child { border-bottom:none; }
.price-features li::before { content:'✓'; color:var(--green); font-weight:700; flex-shrink:0; }
.price-features li.locked { color:var(--dim); }
.price-features li.locked::before { content:'✗'; color:var(--dim); }
.btn-plan {
  width:100%;
  font-family:'Barlow Condensed',sans-serif;
  font-size:14px; font-weight:700; letter-spacing:3px;
  text-transform:uppercase; padding:14px;
  border-radius:2px; cursor:pointer; transition:all 0.2s;
  text-decoration:none; display:block; text-align:center;
}
.btn-plan-free {
  background:none; border:1px solid var(--border); color:var(--dim);
}
.btn-plan-free:hover { border-color:var(--cyan); color:var(--cyan); }
.btn-plan-paid {
  background:var(--cyan); border:1px solid var(--cyan); color:var(--bg);
  box-shadow:0 0 24px #00e5ff33;
}
.btn-plan-paid:hover { background:#00ccee; }

/* ---- TRUST BAR ---- */
.trust-bar {
  border-top:1px solid var(--border);
  border-bottom:1px solid var(--border);
  background:#060a10;
}
.trust-inner {
  max-width:1200px; margin:0 auto;
  display:grid; grid-template-columns:repeat(4,1fr);
  divide:1px solid var(--border);
}
.trust-item {
  padding:28px 40px; text-align:center;
  border-right:1px solid var(--border);
}
.trust-item:last-child { border-right:none; }
.trust-icon { font-size:22px; margin-bottom:8px; }
.trust-title {
  font-family:'Barlow Condensed',sans-serif;
  font-size:14px; font-weight:700; color:#fff;
  letter-spacing:1px; text-transform:uppercase; margin-bottom:4px;
}
.trust-sub { font-size:12px; color:var(--dim); }

/* ---- SUBSCRIBE MODAL ---- */
.modal-bg {
  display:none; position:fixed; inset:0; z-index:200;
  background:rgba(5,8,16,0.92); backdrop-filter:blur(8px);
  align-items:center; justify-content:center;
}
.modal-bg.open { display:flex; }
.modal {
  background:var(--panel); border:1px solid var(--border);
  border-radius:4px; padding:48px 40px; width:500px;
  position:relative;
}
.modal-close {
  position:absolute; top:16px; right:16px;
  background:none; border:none; color:var(--dim);
  font-size:20px; cursor:pointer; transition:color 0.2s;
}
.modal-close:hover { color:#fff; }
.modal-title {
  font-family:'Barlow Condensed',sans-serif;
  font-size:26px; font-weight:800; color:#fff;
  letter-spacing:2px; text-transform:uppercase; margin-bottom:6px;
}
.modal-sub { font-size:13px; color:var(--dim); margin-bottom:28px; }
.form-label {
  display:block; font-size:11px; letter-spacing:2px;
  color:var(--dim); text-transform:uppercase; margin-bottom:6px;
}
.form-input {
  width:100%; background:#060a10; border:1px solid var(--border);
  border-radius:2px; padding:11px 14px; color:var(--text);
  font-family:'Share Tech Mono',monospace; font-size:13px;
  outline:none; margin-bottom:16px; transition:border-color 0.2s;
}
.form-input:focus { border-color:var(--cyan); }
.form-select {
  width:100%; background:#060a10; border:1px solid var(--border);
  border-radius:2px; padding:11px 14px; color:var(--text);
  font-family:'Share Tech Mono',monospace; font-size:13px;
  outline:none; margin-bottom:16px; cursor:pointer;
}
.form-select option { background:#0d1117; }
.wallet-display {
  background:#060a10; border:1px solid #00e5ff22;
  border-radius:2px; padding:14px; margin-bottom:20px;
  display:none;
}
.wallet-label { font-size:10px; letter-spacing:2px; color:var(--dim); margin-bottom:6px; text-transform:uppercase; }
.wallet-addr {
  font-family:'Share Tech Mono',monospace; font-size:12px;
  color:var(--cyan); word-break:break-all; cursor:pointer;
}
.wallet-copy { font-size:10px; color:var(--dim); margin-top:4px; }
.btn-submit {
  width:100%; background:var(--cyan); border:none; color:var(--bg);
  font-family:'Barlow Condensed',sans-serif; font-size:15px;
  font-weight:700; letter-spacing:3px; text-transform:uppercase;
  padding:14px; border-radius:2px; cursor:pointer; transition:all 0.2s;
}
.btn-submit:hover { background:#00ccee; }
.modal-msg { font-size:13px; margin-top:12px; text-align:center; }

/* ---- FOOTER ---- */
footer {
  position:relative; z-index:1;
  border-top:1px solid var(--border);
  padding:40px 48px;
  display:flex; align-items:center; justify-content:space-between;
}
.footer-logo {
  font-family:'Barlow Condensed',sans-serif;
  font-size:16px; font-weight:800; letter-spacing:4px;
  color:var(--cyan); text-transform:uppercase;
}
.footer-copy { font-size:12px; color:var(--dim); }
.footer-links { display:flex; gap:24px; }
.footer-links a {
  font-size:12px; color:var(--dim); text-decoration:none;
  letter-spacing:1px; transition:color 0.2s;
}
.footer-links a:hover { color:var(--cyan); }

/* ---- ANIMATIONS ---- */
.fade-up {
  opacity:0; transform:translateY(24px);
  transition:opacity 0.6s, transform 0.6s;
}
.fade-up.visible { opacity:1; transform:translateY(0); }
</style>
</head>
<body>

<!-- NAV -->
<nav>
  <div class="nav-logo">Hansen<span> AI</span></div>
  <div class="nav-links">
    <a href="#features">Features</a>
    <a href="#how">How It Works</a>
    <a href="#pricing">Pricing</a>
  </div>
  <div class="nav-cta">
    <a href="/login" class="btn-outline">Login</a>
    <a href="/register" class="btn-primary">Free Trial</a>
  </div>
</nav>

<!-- HERO -->
<section class="hero">
  <div class="hero-badge">
    <span class="live-dot"></span>
    Live Market Intelligence — 641 Symbols Tracked
  </div>
  <h1>
    MARKET<br>
    <span class="accent">INTELLIGENCE</span>
    <span class="line2">Powered by Hansen AI</span>
  </h1>
  <p class="hero-sub">
    Real-time crypto market analysis powered by AI. Regime detection, volatility indexing, momentum signals, and deep market insights — all in one sovereign local system.
  </p>
  <div class="hero-actions">
    <a href="/register" class="btn-hero-primary">Start Free Trial</a>
    <a href="#features" class="btn-hero-outline">Explore Features</a>
  </div>
</section>

<!-- LIVE TICKER -->
<div class="live-bar">
  <div class="live-track" id="live-track">
    <div class="live-item"><span class="live-sym">BTC</span><span class="live-val">$84,200</span><span class="live-up">▲ 0.8%</span></div>
    <div class="live-item"><span class="live-sym">ETH</span><span class="live-val">$2,830</span><span class="live-up">▲ 1.2%</span></div>
    <div class="live-item"><span class="live-sym">SOL</span><span class="live-val">$86.02</span><span class="live-up">▲ 2.1%</span></div>
    <div class="live-item"><span class="live-sym">BNB</span><span class="live-val">$645</span><span class="live-dn">▼ 0.3%</span></div>
    <div class="live-item"><span class="live-sym">ARB</span><span class="live-val">$0.18</span><span class="live-up">▲ 3.2%</span></div>
    <div class="live-item"><span class="live-sym">INJ</span><span class="live-val">$2.99</span><span class="live-up">▲ 1.8%</span></div>
    <div class="live-item"><span class="live-sym">APT</span><span class="live-val">$0.96</span><span class="live-dn">▼ 0.5%</span></div>
    <div class="live-item"><span class="live-sym">SUI</span><span class="live-val">$0.97</span><span class="live-up">▲ 0.9%</span></div>
    <div class="live-item"><span class="live-sym">TIA</span><span class="live-val">$0.33</span><span class="live-dn">▼ 1.1%</span></div>
    <div class="live-item"><span class="live-sym">WIF</span><span class="live-val">$0.17</span><span class="live-up">▲ 4.2%</span></div>
    <div class="live-item"><span class="live-sym">BTC</span><span class="live-val">$84,200</span><span class="live-up">▲ 0.8%</span></div>
    <div class="live-item"><span class="live-sym">ETH</span><span class="live-val">$2,830</span><span class="live-up">▲ 1.2%</span></div>
    <div class="live-item"><span class="live-sym">SOL</span><span class="live-val">$86.02</span><span class="live-up">▲ 2.1%</span></div>
    <div class="live-item"><span class="live-sym">BNB</span><span class="live-val">$645</span><span class="live-dn">▼ 0.3%</span></div>
    <div class="live-item"><span class="live-sym">ARB</span><span class="live-val">$0.18</span><span class="live-up">▲ 3.2%</span></div>
    <div class="live-item"><span class="live-sym">INJ</span><span class="live-val">$2.99</span><span class="live-up">▲ 1.8%</span></div>
    <div class="live-item"><span class="live-sym">APT</span><span class="live-val">$0.96</span><span class="live-dn">▼ 0.5%</span></div>
    <div class="live-item"><span class="live-sym">SUI</span><span class="live-val">$0.97</span><span class="live-up">▲ 0.9%</span></div>
    <div class="live-item"><span class="live-sym">TIA</span><span class="live-val">$0.33</span><span class="live-dn">▼ 1.1%</span></div>
    <div class="live-item"><span class="live-sym">WIF</span><span class="live-val">$0.17</span><span class="live-up">▲ 4.2%</span></div>
  </div>
</div>

<!-- STATS BAR -->
<div class="stats-bar fade-up">
  <div class="stat-cell">
    <div class="stat-num">641<span>+</span></div>
    <div class="stat-desc">Symbols Tracked</div>
  </div>
  <div class="stat-cell">
    <div class="stat-num">5<span>min</span></div>
    <div class="stat-desc">Data Sampling Rate</div>
  </div>
  <div class="stat-cell">
    <div class="stat-num">90<span>d</span></div>
    <div class="stat-desc">Historical Depth</div>
  </div>
  <div class="stat-cell">
    <div class="stat-num">24<span>/7</span></div>
    <div class="stat-desc">Live Monitoring</div>
  </div>
</div>

<!-- FEATURES -->
<section id="features">
  <div class="section-inner">
    <div class="section-label">Core Features</div>
    <h2 class="section-title fade-up">BUILT FOR <span class="dim">SERIOUS</span><br>TRADERS</h2>
    <p class="section-sub fade-up">Everything you need to understand market structure — not just price.</p>
    <div class="features-grid">
      <div class="feature-card fade-up">
        <span class="feature-icon">📡</span>
        <div class="feature-title">Market Regime Detection</div>
        <div class="feature-desc">AI-powered classification of market conditions — Bull, Bear, Sideways, or Ranging — updated in real-time across major assets.</div>
        <span class="feature-tag">LIVE</span>
      </div>
      <div class="feature-card fade-up">
        <span class="feature-icon">⚡</span>
        <div class="feature-title">Volatility Index</div>
        <div class="feature-desc">Proprietary volatility scoring across 641 symbols. Know when the market is calm or about to move before it happens.</div>
        <span class="feature-tag">REAL-TIME</span>
      </div>
      <div class="feature-card fade-up">
        <span class="feature-icon">🎯</span>
        <div class="feature-title">Momentum Engine</div>
        <div class="feature-desc">Multi-timeframe momentum analysis. Identify which assets have the strongest directional conviction right now.</div>
        <span class="feature-tag">AI-POWERED</span>
      </div>
      <div class="feature-card fade-up">
        <span class="feature-icon">🔥</span>
        <div class="feature-title">Top Movers & Gainers</div>
        <div class="feature-desc">Instant scan of top gainers, losers, and highest-momentum movers across the entire market universe.</div>
        <span class="feature-tag">AUTO-SCAN</span>
      </div>
      <div class="feature-card fade-up">
        <span class="feature-icon">🧠</span>
        <div class="feature-title">AI Market Insights</div>
        <div class="feature-desc">Natural language market analysis generated by local LLM. Understand the "why" behind market movements instantly.</div>
        <span class="feature-tag">ANALYST ONLY</span>
      </div>
      <div class="feature-card fade-up">
        <span class="feature-icon">🗄️</span>
        <div class="feature-title">90-Day Data History</div>
        <div class="feature-desc">Sovereign local data storage with 90-day rolling history. Your data stays on your machine — no cloud dependency.</div>
        <span class="feature-tag">LOCAL</span>
      </div>
    </div>
  </div>
</section>

<!-- TRUST BAR -->
<div class="trust-bar">
  <div class="trust-inner">
    <div class="trust-item fade-up">
      <div class="trust-icon">🔒</div>
      <div class="trust-title">100% Local</div>
      <div class="trust-sub">Your data never leaves your machine</div>
    </div>
    <div class="trust-item fade-up">
      <div class="trust-icon">⚙️</div>
      <div class="trust-title">No Cloud</div>
      <div class="trust-sub">Sovereign AI — zero external dependency</div>
    </div>
    <div class="trust-item fade-up">
      <div class="trust-icon">🌐</div>
      <div class="trust-title">641 Symbols</div>
      <div class="trust-sub">Full market coverage, not just top 10</div>
    </div>
    <div class="trust-item fade-up">
      <div class="trust-icon">💳</div>
      <div class="trust-title">Crypto Payment</div>
      <div class="trust-sub">USDT / BTC — auto provisioning</div>
    </div>
  </div>
</div>

<!-- HOW IT WORKS -->
<section id="how">
  <div class="section-inner">
    <div class="section-label">Process</div>
    <h2 class="section-title fade-up">HOW IT <span class="dim">WORKS</span></h2>
    <p class="section-sub fade-up">From signup to live market intelligence in under 5 minutes.</p>
    <div class="how-grid">
      <div class="how-step fade-up">
        <div class="how-num">01</div>
        <div class="how-title">Choose Plan</div>
        <div class="how-desc">Select Viewer (free) or Analyst ($5/mo). No credit card required for trial.</div>
      </div>
      <div class="how-step fade-up">
        <div class="how-num">02</div>
        <div class="how-title">Get Access</div>
        <div class="how-desc">Credentials delivered instantly to your email after signup or payment confirmation.</div>
      </div>
      <div class="how-step fade-up">
        <div class="how-num">03</div>
        <div class="how-title">Login</div>
        <div class="how-desc">Access your personalized market intelligence dashboard immediately.</div>
      </div>
      <div class="how-step fade-up">
        <div class="how-num">04</div>
        <div class="how-title">Trade Smarter</div>
        <div class="how-desc">Use AI-powered signals and insights to make better informed trading decisions.</div>
      </div>
    </div>
  </div>
</section>

<!-- PRICING -->
<section id="pricing" style="background:#060a10; border-top:1px solid var(--border); border-bottom:1px solid var(--border);">
  <div class="section-inner">
    <div class="section-label">Pricing</div>
    <h2 class="section-title fade-up" style="text-align:center">SIMPLE <span class="dim">PRICING</span></h2>
    <p class="section-sub fade-up" style="text-align:center;margin:0 auto">No hidden fees. No subscriptions traps. Cancel anytime.</p>
    <div class="pricing-grid">
      <div class="price-card fade-up">
        <div class="price-plan">Viewer</div>
        <div class="price-amount">$<span style="font-size:60px">0</span><span class="period">/mo</span></div>
        <div class="price-desc">Basic market dashboard access</div>
        <ul class="price-features">
          <li>Live price ticker</li>
          <li>Market regime indicator</li>
          <li>Volatility index</li>
          <li>Top gainers & losers</li>
          <li class="locked">AI market insights</li>
          <li class="locked">Momentum analysis</li>
          <li class="locked">Deep market intelligence</li>
        </ul>
        <a href="/register" class="btn-plan btn-plan-free">Get Started Free</a>
      </div>
      <div class="price-card featured fade-up">
        <div class="price-plan">Analyst</div>
        <div class="price-amount"><sup>$</sup>5<span class="period">/mo</span></div>
        <div class="price-desc">Full market intelligence suite</div>
        <ul class="price-features">
          <li>Everything in Viewer</li>
          <li>AI market insights (LLM)</li>
          <li>Momentum engine access</li>
          <li>Deep market intelligence</li>
          <li>90-day history analysis</li>
          <li>Priority data updates</li>
          <li>Full dashboard access</li>
        </ul>
        <a href="#" class="btn-plan btn-plan-paid" onclick="openModal(); return false;">Subscribe — $5 USDT</a>
      </div>
    </div>
    <p style="text-align:center;margin-top:24px;font-size:12px;color:var(--dim)">
      Payment accepted in USDT (BSC/ARB/ETH/SOL/Aptos) and BTC. Auto-provisioned within minutes.
    </p>
  </div>
</section>

<!-- FOOTER -->
<footer>
  <div class="footer-logo">Hansen AI</div>
  <div class="footer-copy">© 2026 Hansen AI Market Intelligence</div>
  <div class="footer-links">
    <a href="/login">Login</a>
    <a href="/register">Trial</a>
    <a href="#pricing">Pricing</a>
  </div>
</footer>

<!-- SUBSCRIBE MODAL -->
<div class="modal-bg" id="modal">
  <div class="modal">
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div class="modal-title">Subscribe</div>
    <div class="modal-sub">Analyst Plan — $5 USDT / month</div>
    <label class="form-label">Your Email</label>
    <input type="email" class="form-input" id="sub-email" placeholder="your@email.com">
    <label class="form-label">Payment Chain</label>
    <select class="form-select" id="sub-chain" onchange="updateWallet()">
      <option value="">Select chain...</option>
      <option value="USDT_BSC">USDT — BNB Chain (BSC)</option>
      <option value="USDT_ARB">USDT — Arbitrum</option>
      <option value="USDT_ETH">USDT — Ethereum</option>
      <option value="USDT_SOL">USDT — Solana</option>
      <option value="USDT_APT">USDT — Aptos</option>
      <option value="USDC_APT">USDC — Aptos</option>
      <option value="BTC">BTC — Bitcoin</option>
    </select>
    <div class="wallet-display" id="wallet-display">
      <div class="wallet-label">Send exactly <span id="wallet-amount"></span> to:</div>
      <div class="wallet-addr" id="wallet-addr" onclick="copyWallet()"></div>
      <div class="wallet-copy">Click to copy address</div>
    </div>
    <button class="btn-submit" onclick="submitSubscription()">Send Payment Instructions</button>
    <div class="modal-msg" id="modal-msg"></div>
  </div>
</div>

<script>
// ---- WALLETS ----
const WALLETS = {
  USDT_BSC:  { addr: "0xC0D018E7278De2611B67c7e59b9b45570dC59aEB", amount: "5.00 USDT" },
  USDT_ARB:  { addr: "0xC0D018E7278De2611B67c7e59b9b45570dC59aEB", amount: "5.00 USDT" },
  USDT_ETH:  { addr: "0xC0D018E7278De2611B67c7e59b9b45570dC59aEB", amount: "5.00 USDT" },
  USDT_SOL:  { addr: "DvbvPU25fftYV6LA21FxQ7B5y4bb6C6rQxMCLR5ariF", amount: "5.00 USDT" },
  USDT_APT:  { addr: "0x88001f20fc5d01220851e8cb9353e3cddc5fadc29c5cf41ec5d1caece0db6d73", amount: "5.00 USDT" },
  USDC_APT:  { addr: "0x88001f20fc5d01220851e8cb9353e3cddc5fadc29c5cf41ec5d1caece0db6d73", amount: "5.00 USDC" },
  BTC:       { addr: "bc1ptknrx96kuyudg5xnqc3wq6y4hdckqxay5cgq808um7e7gnygwc8swnv8xn", amount: "0.000050 BTC" },
};

function openModal()  { document.getElementById("modal").classList.add("open"); }
function closeModal() { document.getElementById("modal").classList.remove("open"); }

function updateWallet() {
  const chain = document.getElementById("sub-chain").value;
  const display = document.getElementById("wallet-display");
  if (!chain || !WALLETS[chain]) { display.style.display = "none"; return; }
  document.getElementById("wallet-addr").textContent   = WALLETS[chain].addr;
  document.getElementById("wallet-amount").textContent = WALLETS[chain].amount;
  display.style.display = "block";
}

function copyWallet() {
  const addr = document.getElementById("wallet-addr").textContent;
  navigator.clipboard.writeText(addr);
  document.querySelector(".wallet-copy").textContent = "✓ Copied!";
  setTimeout(() => document.querySelector(".wallet-copy").textContent = "Click to copy address", 2000);
}

async function submitSubscription() {
  const email = document.getElementById("sub-email").value.trim();
  const chain = document.getElementById("sub-chain").value;
  const msg   = document.getElementById("modal-msg");
  if (!email || !chain) { msg.style.color="#ff3d5a"; msg.textContent="Fill in email and chain."; return; }
  try {
    const res = await fetch("/subscribe", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({email, chain, currency: chain==="BTC"?"BTC":"USDT", plan:"analyst"})
    });
    const d = await res.json();
    if (d.success) {
      msg.style.color="#00ff88";
      msg.textContent = "Payment instructions sent to your email! Check inbox.";
    } else {
      msg.style.color="#ff3d5a";
      msg.textContent = d.error || "Failed. Try again.";
    }
  } catch(e) {
    msg.style.color="#ff3d5a"; msg.textContent="Connection error.";
  }
}

// ---- SCROLL ANIMATIONS ----
const observer = new IntersectionObserver((entries) => {
  entries.forEach((e, i) => {
    if (e.isIntersecting) {
      setTimeout(() => e.target.classList.add("visible"), i * 80);
    }
  });
}, { threshold: 0.1 });
document.querySelectorAll(".fade-up").forEach(el => observer.observe(el));

// ---- CLOSE MODAL ON BG CLICK ----
document.getElementById("modal").addEventListener("click", function(e) {
  if (e.target === this) closeModal();
});
</script>
</body>
</html>
"""