"""
Hansen AI — Landing Page (Ultimate Edition)
Cinematic 3D scrollytelling with glassmorphism, parallax, and professional design.
Drop-in replacement for landing_page.py
"""

LANDING_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hansen AI — Sovereign Market Intelligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#020617;--bg2:#0f172a;--bg3:#1e293b;
  --cyan:#06b6d4;--emerald:#10b981;--violet:#8b5cf6;--amber:#f59e0b;--rose:#f43f5e;--blue:#3b82f6;
  --text:#f1f5f9;--muted:#94a3b8;--dim:#475569;--border:rgba(148,163,184,.1);
  --glass:rgba(15,23,42,.6);--glass-border:rgba(148,163,184,.08);
}
html{scroll-behavior:smooth;overflow-x:hidden}
body{background:var(--bg);color:var(--text);font-family:'Sora',sans-serif;overflow-x:hidden;line-height:1.6}
::selection{background:var(--cyan);color:var(--bg)}
body::before{content:'';position:fixed;inset:0;z-index:9999;pointer-events:none;opacity:.03;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}

@keyframes fadeUp{from{opacity:0;transform:translateY(50px)}to{opacity:1;transform:translateY(0)}}
@keyframes float{0%,100%{transform:translateY(0) rotate(0deg)}25%{transform:translateY(-15px) rotate(1deg)}75%{transform:translateY(5px) rotate(-1deg)}}
@keyframes pulse-glow{0%,100%{box-shadow:0 0 30px rgba(6,182,212,.15)}50%{box-shadow:0 0 60px rgba(6,182,212,.3),0 0 120px rgba(6,182,212,.1)}}
@keyframes spin-slow{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
@keyframes spin-reverse{from{transform:rotate(360deg)}to{transform:rotate(0deg)}}
@keyframes ticker{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@keyframes morph{0%,100%{border-radius:60% 40% 30% 70%/60% 30% 70% 40%}50%{border-radius:30% 60% 70% 40%/50% 60% 30% 60%}}
@keyframes gradient-x{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}

.reveal{opacity:0;transform:translateY(50px);transition:all .9s cubic-bezier(.16,1,.3,1)}
.reveal.active{opacity:1;transform:translateY(0)}
.reveal-left{opacity:0;transform:translateX(-60px);transition:all .9s cubic-bezier(.16,1,.3,1)}
.reveal-left.active{opacity:1;transform:translateX(0)}
.reveal-right{opacity:0;transform:translateX(60px);transition:all .9s cubic-bezier(.16,1,.3,1)}
.reveal-right.active{opacity:1;transform:translateX(0)}
.stagger-1{transition-delay:.1s}.stagger-2{transition-delay:.2s}.stagger-3{transition-delay:.3s}
.stagger-4{transition-delay:.4s}.stagger-5{transition-delay:.5s}.stagger-6{transition-delay:.6s}

nav{position:fixed;top:0;left:0;right:0;z-index:100;padding:20px 48px;display:flex;align-items:center;justify-content:space-between;transition:all .4s cubic-bezier(.16,1,.3,1)}
nav.scrolled{padding:12px 48px;background:rgba(2,6,23,.85);backdrop-filter:blur(24px) saturate(1.4);border-bottom:1px solid var(--glass-border)}
.nav-logo{display:flex;align-items:center;gap:12px;text-decoration:none}
.logo-cube{width:40px;height:40px;perspective:200px}
.logo-cube-inner{width:100%;height:100%;position:relative;transform-style:preserve-3d;animation:spin-slow 20s linear infinite}
.logo-face{position:absolute;width:40px;height:40px;display:flex;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace;font-weight:800;font-size:18px;border:1.5px solid rgba(6,182,212,.4);border-radius:8px}
.logo-face-front{background:linear-gradient(135deg,rgba(6,182,212,.2),rgba(139,92,246,.2));color:var(--cyan);transform:translateZ(20px)}
.logo-face-back{background:linear-gradient(135deg,rgba(139,92,246,.2),rgba(6,182,212,.2));color:var(--violet);transform:rotateY(180deg) translateZ(20px)}
.logo-face-left{background:rgba(6,182,212,.1);color:var(--cyan);transform:rotateY(-90deg) translateZ(20px)}
.logo-face-right{background:rgba(139,92,246,.1);color:var(--violet);transform:rotateY(90deg) translateZ(20px)}
.logo-text{font-size:20px;font-weight:700;letter-spacing:-.5px}
.logo-text span{background:linear-gradient(135deg,var(--cyan),var(--violet));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.nav-links{display:flex;gap:36px;align-items:center}
.nav-links a{color:var(--dim);text-decoration:none;font-size:13px;font-weight:500;transition:all .3s;position:relative;letter-spacing:.5px}
.nav-links a::after{content:'';position:absolute;bottom:-4px;left:0;width:0;height:1.5px;background:var(--cyan);transition:width .3s}
.nav-links a:hover{color:var(--text)}.nav-links a:hover::after{width:100%}
.nav-cta{display:flex;gap:12px}
.btn-glass{padding:9px 22px;border:1px solid var(--glass-border);border-radius:10px;color:var(--text);background:var(--glass);backdrop-filter:blur(12px);font-size:13px;font-weight:600;cursor:pointer;transition:all .3s;text-decoration:none;font-family:'Sora',sans-serif}
.btn-glass:hover{border-color:rgba(6,182,212,.3);background:rgba(6,182,212,.08)}
.btn-glow{padding:9px 26px;border:none;border-radius:10px;background:linear-gradient(135deg,var(--cyan),var(--blue));color:#fff;font-size:13px;font-weight:700;cursor:pointer;transition:all .3s;text-decoration:none;font-family:'Sora',sans-serif;position:relative;overflow:hidden}
.btn-glow::before{content:'';position:absolute;inset:-2px;background:linear-gradient(135deg,var(--cyan),var(--violet),var(--cyan));border-radius:12px;z-index:-1;opacity:0;transition:opacity .3s;filter:blur(8px)}
.btn-glow:hover{transform:translateY(-2px)}.btn-glow:hover::before{opacity:.6}

.hero{min-height:100vh;display:flex;align-items:center;position:relative;overflow:hidden;padding:0 80px}
.hero-bg{position:absolute;inset:0;z-index:0}
.hero-mesh{position:absolute;inset:0;background:radial-gradient(ellipse at 20% 50%,rgba(6,182,212,.08) 0%,transparent 50%),radial-gradient(ellipse at 80% 20%,rgba(139,92,246,.06) 0%,transparent 50%),radial-gradient(ellipse at 50% 80%,rgba(16,185,129,.04) 0%,transparent 50%)}
.hero-grid-3d{position:absolute;bottom:0;left:0;right:0;height:60%;background:linear-gradient(transparent,rgba(6,182,212,.03)),repeating-linear-gradient(90deg,rgba(6,182,212,.04) 0px,rgba(6,182,212,.04) 1px,transparent 1px,transparent 80px),repeating-linear-gradient(0deg,rgba(6,182,212,.04) 0px,rgba(6,182,212,.04) 1px,transparent 1px,transparent 80px);transform:perspective(400px) rotateX(45deg);transform-origin:bottom center;opacity:.5}
.hero-blob{position:absolute;width:500px;height:500px;filter:blur(100px);animation:morph 15s ease infinite,float 8s ease infinite}
.hero-blob-1{top:5%;left:10%;background:rgba(6,182,212,.12)}
.hero-blob-2{bottom:10%;right:5%;background:rgba(139,92,246,.1);animation-delay:5s}
.hero-blob-3{top:40%;right:30%;background:rgba(16,185,129,.06);animation-delay:10s}
.hero-content{position:relative;z-index:2;max-width:640px;padding-top:120px}
.hero-chip{display:inline-flex;align-items:center;gap:10px;padding:8px 18px;border-radius:100px;border:1px solid rgba(6,182,212,.2);background:rgba(6,182,212,.05);backdrop-filter:blur(8px);font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--cyan);margin-bottom:32px;letter-spacing:1px}
.hero-chip .pulse{width:7px;height:7px;border-radius:50%;background:var(--emerald);box-shadow:0 0 12px var(--emerald);animation:pulse-glow 2s infinite}
.hero h1{font-size:clamp(42px,5.5vw,68px);font-weight:800;line-height:1.08;letter-spacing:-2.5px;margin-bottom:24px}
.hero h1 .gradient{background:linear-gradient(135deg,var(--cyan) 0%,var(--violet) 50%,var(--emerald) 100%);background-size:200% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:gradient-x 6s ease infinite}
.hero-desc{font-size:17px;color:var(--muted);max-width:500px;line-height:1.8;margin-bottom:40px}
.hero-actions{display:flex;gap:16px;align-items:center}
.hero-actions .btn-big{padding:14px 36px;font-size:15px;border-radius:12px}
.hero-metric{display:inline-flex;align-items:center;gap:6px;margin-left:16px;font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--dim)}
.hero-metric i{color:var(--emerald);font-size:10px}

.hero-3d{position:absolute;right:60px;top:50%;transform:translateY(-50%);z-index:1;width:480px;height:480px}
.hex-grid{position:absolute;inset:0;display:flex;align-items:center;justify-content:center}
.hex-ring{position:absolute;border-radius:50%;border:1px solid}
.hex-ring-1{width:380px;height:380px;border-color:rgba(6,182,212,.12);animation:spin-slow 30s linear infinite}
.hex-ring-2{width:280px;height:280px;border-color:rgba(139,92,246,.1);animation:spin-reverse 25s linear infinite}
.hex-ring-3{width:180px;height:180px;border-color:rgba(16,185,129,.12);animation:spin-slow 20s linear infinite}
.hex-center{width:100px;height:100px;background:linear-gradient(135deg,rgba(6,182,212,.15),rgba(139,92,246,.15));border:1.5px solid rgba(6,182,212,.25);border-radius:20px;display:flex;align-items:center;justify-content:center;animation:pulse-glow 4s ease infinite;backdrop-filter:blur(12px)}
.hex-center i{font-size:36px;background:linear-gradient(135deg,var(--cyan),var(--violet));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hex-dot{position:absolute;width:10px;height:10px;border-radius:50%;border:2px solid}
.hex-dot-1{top:50px;left:80px;border-color:var(--cyan);background:rgba(6,182,212,.3)}
.hex-dot-2{top:30%;right:40px;border-color:var(--violet);background:rgba(139,92,246,.3)}
.hex-dot-3{bottom:60px;left:120px;border-color:var(--emerald);background:rgba(16,185,129,.3)}
.hex-dot-4{bottom:30%;right:80px;border-color:var(--amber);background:rgba(245,158,11,.3)}
.hex-label{position:absolute;font-family:'JetBrains Mono',monospace;font-size:10px;padding:5px 12px;border-radius:6px;backdrop-filter:blur(8px);white-space:nowrap;letter-spacing:.5px}
.hl-1{top:30px;right:60px;color:var(--cyan);background:rgba(6,182,212,.08);border:1px solid rgba(6,182,212,.15)}
.hl-2{bottom:80px;right:40px;color:var(--violet);background:rgba(139,92,246,.08);border:1px solid rgba(139,92,246,.15)}
.hl-3{top:50%;left:10px;color:var(--emerald);background:rgba(16,185,129,.08);border:1px solid rgba(16,185,129,.15)}
.hl-4{bottom:40px;left:60px;color:var(--amber);background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.15)}

.ticker-wrap{overflow:hidden;border-top:1px solid var(--border);border-bottom:1px solid var(--border);padding:12px 0;background:rgba(15,23,42,.4)}
.ticker-track{display:flex;gap:48px;animation:ticker 40s linear infinite;width:max-content}
.ticker-item{display:flex;align-items:center;gap:8px;font-family:'JetBrains Mono',monospace;font-size:12px;white-space:nowrap}
.ticker-sym{color:var(--text);font-weight:600}.ticker-up{color:var(--emerald)}.ticker-down{color:var(--rose)}

.metrics-bar{padding:80px 80px 40px;display:grid;grid-template-columns:repeat(4,1fr);gap:20px}
.metric-card{background:var(--glass);backdrop-filter:blur(16px);border:1px solid var(--glass-border);border-radius:16px;padding:28px 24px;text-align:center;transition:all .4s cubic-bezier(.16,1,.3,1);position:relative;overflow:hidden}
.metric-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(6,182,212,.3),transparent);opacity:0;transition:opacity .3s}
.metric-card:hover{transform:translateY(-6px);border-color:rgba(6,182,212,.15)}.metric-card:hover::before{opacity:1}
.metric-num{font-size:38px;font-weight:800;font-family:'JetBrains Mono',monospace;background:linear-gradient(135deg,var(--cyan),var(--emerald));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.metric-label{font-size:12px;color:var(--dim);margin-top:6px;letter-spacing:1.5px;text-transform:uppercase}

.section{padding:100px 80px;position:relative}
.section-header{text-align:center;margin-bottom:64px}
.section-chip{display:inline-block;font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:3px;text-transform:uppercase;color:var(--cyan);padding:7px 18px;border:1px solid rgba(6,182,212,.15);border-radius:100px;margin-bottom:20px;background:rgba(6,182,212,.04)}
.section-title{font-size:clamp(30px,4vw,46px);font-weight:800;letter-spacing:-1.5px;margin-bottom:16px;line-height:1.15}
.section-title .gradient{background:linear-gradient(135deg,var(--cyan),var(--violet));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.section-sub{font-size:15px;color:var(--muted);max-width:520px;margin:0 auto;line-height:1.8}

.features-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.f-card{background:var(--glass);backdrop-filter:blur(12px);border:1px solid var(--glass-border);border-radius:16px;padding:28px;transition:all .4s cubic-bezier(.16,1,.3,1);position:relative;overflow:hidden;cursor:default}
.f-card::after{content:'';position:absolute;inset:0;background:linear-gradient(135deg,rgba(6,182,212,.03),transparent);opacity:0;transition:opacity .3s}
.f-card:hover{border-color:rgba(6,182,212,.2);transform:translateY(-6px)}.f-card:hover::after{opacity:1}
.f-icon{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:18px;margin-bottom:14px}
.fi-cyan{background:rgba(6,182,212,.1);color:var(--cyan)}.fi-violet{background:rgba(139,92,246,.1);color:var(--violet)}
.fi-emerald{background:rgba(16,185,129,.1);color:var(--emerald)}.fi-amber{background:rgba(245,158,11,.1);color:var(--amber)}
.fi-rose{background:rgba(244,63,94,.1);color:var(--rose)}.fi-blue{background:rgba(59,130,246,.1);color:var(--blue)}
.f-tag{display:inline-block;font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:1.5px;padding:3px 8px;border-radius:4px;margin-bottom:10px}
.tag-live{background:rgba(16,185,129,.1);color:var(--emerald)}.tag-ai{background:rgba(139,92,246,.1);color:var(--violet)}.tag-new{background:rgba(6,182,212,.1);color:var(--cyan)}
.f-card h3{font-size:15px;font-weight:700;margin-bottom:6px;letter-spacing:-.3px}
.f-card p{font-size:12.5px;color:var(--muted);line-height:1.65}

.brain-section{background:linear-gradient(180deg,var(--bg2),var(--bg));border-top:1px solid var(--border);border-bottom:1px solid var(--border)}
.brain-layout{display:grid;grid-template-columns:1fr 1fr;gap:80px;align-items:center}
.brain-visual{position:relative;height:440px;display:flex;align-items:center;justify-content:center}
.brain-sphere{width:180px;height:180px;border-radius:50%;background:radial-gradient(circle at 30% 30%,rgba(6,182,212,.25),rgba(139,92,246,.15),transparent);border:1.5px solid rgba(6,182,212,.2);display:flex;align-items:center;justify-content:center;animation:pulse-glow 4s ease infinite;position:relative;z-index:2;backdrop-filter:blur(20px)}
.brain-sphere i{font-size:42px;background:linear-gradient(135deg,var(--cyan),var(--violet));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.brain-orbit{position:absolute;border-radius:50%;border:1px dashed;top:50%;left:50%;transform:translate(-50%,-50%)}
.bo-1{width:280px;height:280px;border-color:rgba(6,182,212,.08);animation:spin-slow 40s linear infinite}
.bo-2{width:380px;height:380px;border-color:rgba(139,92,246,.06);animation:spin-reverse 50s linear infinite}
.brain-tag{position:absolute;font-family:'JetBrains Mono',monospace;font-size:10px;padding:6px 14px;border-radius:8px;backdrop-filter:blur(12px);border:1px solid;white-space:nowrap;font-weight:600;letter-spacing:.5px;animation:float 6s ease infinite}
.bt-1{top:10%;left:5%;color:var(--cyan);border-color:rgba(6,182,212,.2);background:rgba(6,182,212,.06);animation-delay:0s}
.bt-2{top:0%;right:15%;color:var(--emerald);border-color:rgba(16,185,129,.2);background:rgba(16,185,129,.06);animation-delay:1s}
.bt-3{bottom:20%;left:0%;color:var(--violet);border-color:rgba(139,92,246,.2);background:rgba(139,92,246,.06);animation-delay:2s}
.bt-4{bottom:5%;right:5%;color:var(--amber);border-color:rgba(245,158,11,.2);background:rgba(245,158,11,.06);animation-delay:3s}
.bt-5{top:45%;right:-5%;color:var(--rose);border-color:rgba(244,63,94,.2);background:rgba(244,63,94,.06);animation-delay:4s}
.bt-6{bottom:45%;left:-5%;color:var(--blue);border-color:rgba(59,130,246,.2);background:rgba(59,130,246,.06);animation-delay:5s}
.brain-info h2{font-size:34px;font-weight:800;letter-spacing:-1px;margin-bottom:14px;line-height:1.15}
.brain-info p{color:var(--muted);margin-bottom:28px;line-height:1.8;font-size:14px}
.brain-list{list-style:none;padding:0}
.brain-list li{display:flex;align-items:center;gap:14px;padding:9px 0;font-size:13px;color:var(--muted);border-bottom:1px solid var(--border)}
.brain-list li:last-child{border:none}
.brain-list li i{color:var(--cyan);width:16px;text-align:center;font-size:11px}

.how-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:20px}
.how-card{text-align:center;padding:32px 20px;background:var(--glass);border:1px solid var(--glass-border);border-radius:16px;backdrop-filter:blur(12px);transition:all .3s}
.how-card:hover{transform:translateY(-4px);border-color:rgba(6,182,212,.15)}
.how-num{font-family:'JetBrains Mono',monospace;font-size:40px;font-weight:800;background:linear-gradient(135deg,var(--cyan),transparent);-webkit-background-clip:text;-webkit-text-fill-color:transparent;opacity:.3;line-height:1}
.how-card h3{font-size:15px;font-weight:700;margin:14px 0 8px}
.how-card p{font-size:12px;color:var(--muted);line-height:1.65}

.pricing-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;max-width:1000px;margin:0 auto}
.p-card{background:var(--glass);backdrop-filter:blur(16px);border:1px solid var(--glass-border);border-radius:20px;padding:36px;transition:all .4s;position:relative;overflow:hidden}
.p-card.featured{border-color:rgba(6,182,212,.25);background:linear-gradient(180deg,rgba(6,182,212,.06),var(--glass))}
.p-card.featured::before{content:'RECOMMENDED';position:absolute;top:0;left:0;right:0;text-align:center;font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:3px;padding:6px;background:linear-gradient(135deg,var(--cyan),var(--blue));color:#fff;font-weight:700}
.p-card:hover{transform:translateY(-4px)}
.p-tier{font-size:12px;color:var(--dim);letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;margin-top:8px}
.p-amount{font-size:40px;font-weight:800;font-family:'JetBrains Mono',monospace;margin-bottom:4px}
.p-amount span{font-size:15px;color:var(--dim);font-weight:400}
.p-desc{font-size:12.5px;color:var(--muted);margin-bottom:24px;line-height:1.6}
.p-features{list-style:none;padding:0;margin-bottom:28px}
.p-features li{padding:7px 0;font-size:12.5px;color:var(--text);display:flex;align-items:center;gap:10px;border-bottom:1px solid rgba(148,163,184,.05)}
.p-features li i{font-size:11px;width:16px;text-align:center}
.p-features li i.fa-check{color:var(--emerald)}
.p-features li i.fa-xmark{color:var(--dim)}
.p-features li.locked{color:var(--dim)}
.p-btn{width:100%;padding:12px;border:1px solid var(--glass-border);border-radius:12px;background:var(--glass);backdrop-filter:blur(8px);color:var(--text);font-size:13px;font-weight:600;cursor:pointer;transition:all .3s;font-family:'Sora',sans-serif}
.p-btn:hover{border-color:rgba(6,182,212,.3);color:var(--cyan)}
.p-btn.primary{background:linear-gradient(135deg,var(--cyan),var(--blue));color:#fff;border:none}
.p-btn.primary:hover{transform:translateY(-2px);box-shadow:0 12px 40px rgba(6,182,212,.3)}

.trust{padding:64px 80px;display:flex;justify-content:center;gap:48px;flex-wrap:wrap;border-top:1px solid var(--border)}
.trust-item{display:flex;align-items:center;gap:10px;font-size:13px;color:var(--dim)}
.trust-item i{font-size:16px;color:var(--cyan)}

footer{padding:48px 80px;border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.footer-left{font-size:12px;color:var(--dim);display:flex;align-items:center;gap:8px}
.footer-left i{color:var(--cyan)}
.footer-links{display:flex;gap:28px}
.footer-links a{color:var(--dim);text-decoration:none;font-size:12px;transition:color .2s;letter-spacing:.5px}
.footer-links a:hover{color:var(--cyan)}

.modal-bg{position:fixed;inset:0;background:rgba(2,6,23,.85);backdrop-filter:blur(16px);z-index:200;display:none;align-items:center;justify-content:center}
.modal-bg.show{display:flex}
.modal{background:var(--bg2);border:1px solid var(--glass-border);border-radius:20px;padding:40px;max-width:440px;width:90%;position:relative;backdrop-filter:blur(20px)}
.modal h2{font-size:22px;font-weight:700;margin-bottom:8px}
.modal p{font-size:12.5px;color:var(--muted);margin-bottom:24px;line-height:1.6}
.modal-close{position:absolute;top:16px;right:16px;background:none;border:none;color:var(--dim);font-size:18px;cursor:pointer;transition:color .2s}
.modal-close:hover{color:var(--text)}
.modal label{display:block;font-size:11px;color:var(--dim);letter-spacing:1.5px;margin-bottom:6px;text-transform:uppercase}
.modal input,.modal select{width:100%;padding:11px 14px;background:var(--bg);border:1px solid var(--glass-border);border-radius:10px;color:var(--text);font-size:13px;margin-bottom:16px;font-family:'Sora',sans-serif;transition:border .2s}
.modal input:focus,.modal select:focus{outline:none;border-color:var(--cyan)}
.modal .btn-glow{width:100%;padding:13px;font-size:14px;border-radius:12px;text-align:center}

@media(max-width:900px){
  .hero{padding:120px 24px 60px;text-align:center}.hero-3d{display:none}
  .hero-desc{margin:0 auto 36px}.hero-actions{justify-content:center;flex-wrap:wrap}.hero-metric{display:none}
  .features-grid,.how-grid{grid-template-columns:1fr}.pricing-grid{grid-template-columns:1fr}
  .brain-layout{grid-template-columns:1fr}.brain-visual{display:none}
  .metrics-bar{grid-template-columns:repeat(2,1fr);padding:40px 24px}
  nav{padding:12px 20px}.nav-links{display:none}.section{padding:60px 24px}
  .trust{padding:40px 24px;gap:24px}footer{padding:32px 24px;flex-direction:column;gap:16px;text-align:center}
}
</style>
</head>
<body>
<nav id="nav">
  <a href="/" class="nav-logo">
    <div class="logo-cube"><div class="logo-cube-inner">
      <div class="logo-face logo-face-front">H</div>
      <div class="logo-face logo-face-back">AI</div>
      <div class="logo-face logo-face-left">H</div>
      <div class="logo-face logo-face-right">AI</div>
    </div></div>
    <div class="logo-text">Hansen<span>AI</span></div>
  </a>
  <div class="nav-links">
    <a href="#features">Features</a>
    <a href="#brain">AI Brain</a>
    <a href="#how">How It Works</a>
    <a href="#pricing">Pricing</a>
  </div>
  <div class="nav-cta">
    <a href="/login" class="btn-glass">Login</a>
    <a href="/register" class="btn-glow">Get Started</a>
  </div>
</nav>

<section class="hero">
  <div class="hero-bg"><div class="hero-mesh"></div><div class="hero-grid-3d"></div><div class="hero-blob hero-blob-1"></div><div class="hero-blob hero-blob-2"></div><div class="hero-blob hero-blob-3"></div></div>
  <div class="hero-content">
    <div class="hero-chip"><span class="pulse"></span> SOVEREIGN AI &middot; 100% LOCAL &middot; ZERO CLOUD</div>
    <h1 style="animation:fadeUp .8s ease .1s both">Your Private<br><span class="gradient">Market Intelligence</span><br>Engine</h1>
    <p class="hero-desc" style="animation:fadeUp .8s ease .3s both">Real-time crypto analytics powered by local AI. 16 sectors, 110+ coins, 8 intelligence modules &mdash; sovereign on your machine.</p>
    <div class="hero-actions" style="animation:fadeUp .8s ease .5s both">
      <a href="/register" class="btn-glow btn-big">Start Free Trial</a>
      <a href="#features" class="btn-glass btn-big">Explore <i class="fa-solid fa-arrow-down" style="margin-left:6px;font-size:12px"></i></a>
      <span class="hero-metric"><i class="fa-solid fa-circle"></i> 641+ symbols live</span>
    </div>
  </div>
  <div class="hero-3d">
    <div class="hex-grid"><div class="hex-ring hex-ring-1"></div><div class="hex-ring hex-ring-2"></div><div class="hex-ring hex-ring-3"></div><div class="hex-center"><i class="fa-solid fa-brain"></i></div></div>
    <div class="hex-dot hex-dot-1"></div><div class="hex-dot hex-dot-2"></div><div class="hex-dot hex-dot-3"></div><div class="hex-dot hex-dot-4"></div>
    <div class="hex-label hl-1"><i class="fa-solid fa-chart-line"></i> Sectors</div>
    <div class="hex-label hl-2"><i class="fa-solid fa-bell"></i> Alerts</div>
    <div class="hex-label hl-3"><i class="fa-solid fa-water"></i> Whale Intel</div>
    <div class="hex-label hl-4"><i class="fa-solid fa-fire"></i> Derivatives</div>
  </div>
</section>

<div class="ticker-wrap"><div class="ticker-track" id="ticker-track"></div></div>

<div class="metrics-bar">
  <div class="metric-card reveal stagger-1"><div class="metric-num">641+</div><div class="metric-label">Symbols Tracked</div></div>
  <div class="metric-card reveal stagger-2"><div class="metric-num">16</div><div class="metric-label">Sector Analysis</div></div>
  <div class="metric-card reveal stagger-3"><div class="metric-num">8</div><div class="metric-label">Intel Modules</div></div>
  <div class="metric-card reveal stagger-4"><div class="metric-num">100%</div><div class="metric-label">Sovereign Local</div></div>
</div>

<section class="section" id="features">
  <div class="section-header reveal"><div class="section-chip">Intelligence Suite</div><div class="section-title">Everything to <span class="gradient">Dominate</span> the Market</div><div class="section-sub">Nine specialized modules. Real-time data and AI analysis, all running locally.</div></div>
  <div class="features-grid">
    <div class="f-card reveal stagger-1"><div class="f-icon fi-cyan"><i class="fa-solid fa-chart-line"></i></div><span class="f-tag tag-live">LIVE</span><h3>Sector Performance</h3><p>110+ coins across 16 sectors. Multi-timeframe ranking, rotation detection, and strength scoring.</p></div>
    <div class="f-card reveal stagger-2"><div class="f-icon fi-violet"><i class="fa-solid fa-brain"></i></div><span class="f-tag tag-ai">AI-POWERED</span><h3>Market Sentiment</h3><p>Composite Fear &amp; Greed index from momentum, volatility, volume, and breadth. Narrative auto-detection.</p></div>
    <div class="f-card reveal stagger-3"><div class="f-icon fi-emerald"><i class="fa-solid fa-water"></i></div><span class="f-tag tag-new">NEW</span><h3>Whale Intelligence</h3><p>Whale activity detection, exchange flow analysis, stablecoin deployment. Know smart money moves.</p></div>
    <div class="f-card reveal stagger-4"><div class="f-icon fi-amber"><i class="fa-solid fa-bolt"></i></div><span class="f-tag tag-live">LIVE</span><h3>Smart Screener</h3><p>6 preset filters: Momentum Kings, Dip Buys, Volume Surge, Breakout Candidates, and more.</p></div>
    <div class="f-card reveal stagger-5"><div class="f-icon fi-rose"><i class="fa-solid fa-fire"></i></div><span class="f-tag tag-live">REAL-TIME</span><h3>Derivatives Intel</h3><p>Funding rates, open interest spikes, liquidation cascades. Full derivatives intelligence.</p></div>
    <div class="f-card reveal stagger-6"><div class="f-icon fi-blue"><i class="fa-solid fa-table-cells"></i></div><span class="f-tag tag-ai">AI-POWERED</span><h3>Correlation Matrix</h3><p>25-coin heatmap, beta vs BTC, strongest/weakest pairs. Multi-window analysis.</p></div>
    <div class="f-card reveal stagger-1"><div class="f-icon fi-cyan"><i class="fa-solid fa-bell"></i></div><span class="f-tag tag-live">REAL-TIME</span><h3>Alert Center</h3><p>Price pumps/dumps, funding spikes, liquidation surges, volume anomalies with severity tracking.</p></div>
    <div class="f-card reveal stagger-2"><div class="f-icon fi-emerald"><i class="fa-solid fa-map"></i></div><span class="f-tag tag-new">NEW</span><h3>Market Heatmap</h3><p>Visual sector heatmap with color-coded intensity. See the entire market at a glance.</p></div>
    <div class="f-card reveal stagger-3"><div class="f-icon fi-violet"><i class="fa-solid fa-file-lines"></i></div><span class="f-tag tag-ai">AI-POWERED</span><h3>AI Reports</h3><p>Daily, weekly, flash reports from your local LLM. Full analysis with actionable intelligence.</p></div>
  </div>
</section>

<section class="section brain-section" id="brain">
  <div class="brain-layout">
    <div class="brain-visual reveal-left">
      <div class="brain-orbit bo-1"></div><div class="brain-orbit bo-2"></div>
      <div class="brain-sphere"><i class="fa-solid fa-atom"></i></div>
      <div class="brain-tag bt-1"><i class="fa-solid fa-chart-pie"></i> Sectors</div>
      <div class="brain-tag bt-2"><i class="fa-solid fa-face-smile"></i> Sentiment</div>
      <div class="brain-tag bt-3"><i class="fa-solid fa-coins"></i> Derivatives</div>
      <div class="brain-tag bt-4"><i class="fa-solid fa-water"></i> Whale Intel</div>
      <div class="brain-tag bt-5"><i class="fa-solid fa-triangle-exclamation"></i> Alerts</div>
      <div class="brain-tag bt-6"><i class="fa-solid fa-link"></i> Correlation</div>
    </div>
    <div class="brain-info reveal-right">
      <div class="section-chip">Market Brain</div>
      <h2>8 Data Sources.<br>One <span class="gradient">Unified Intelligence.</span></h2>
      <p>The Market Brain aggregates all modules into a single reasoning context. Every snapshot richer, every report smarter.</p>
      <ul class="brain-list">
        <li><i class="fa-solid fa-arrow-right"></i> 16-sector performance, rotation &amp; ranking</li>
        <li><i class="fa-solid fa-arrow-right"></i> Fear &amp; Greed with 4-component scoring</li>
        <li><i class="fa-solid fa-arrow-right"></i> Whale activity &amp; exchange flow</li>
        <li><i class="fa-solid fa-arrow-right"></i> Derivatives: funding, OI, liquidation cascade</li>
        <li><i class="fa-solid fa-arrow-right"></i> 6 preset smart screening filters</li>
        <li><i class="fa-solid fa-arrow-right"></i> 25-coin correlation &amp; beta vs BTC</li>
        <li><i class="fa-solid fa-arrow-right"></i> Automatic narrative detection</li>
        <li><i class="fa-solid fa-arrow-right"></i> Local Llama 3.1 8B AI reports</li>
      </ul>
    </div>
  </div>
</section>

<section class="section" id="how">
  <div class="section-header reveal"><div class="section-chip">Getting Started</div><div class="section-title">Live in <span class="gradient">4 Steps</span></div></div>
  <div class="how-grid">
    <div class="how-card reveal stagger-1"><div class="how-num">01</div><h3>Choose Plan</h3><p>Free Viewer or full Analyst. No commitment.</p></div>
    <div class="how-card reveal stagger-2"><div class="how-num">02</div><h3>Pay Crypto</h3><p>BSC, ARB, ETH, SOL, BTC, Aptos. Instant.</p></div>
    <div class="how-card reveal stagger-3"><div class="how-num">03</div><h3>Access Dashboard</h3><p>Real-time intelligence. AI insights. Market brain.</p></div>
    <div class="how-card reveal stagger-4"><div class="how-num">04</div><h3>Trade Smarter</h3><p>Sectors, whales, sentiment, AI. All in one.</p></div>
  </div>
</section>

<section class="section" id="pricing">
  <div class="section-header reveal"><div class="section-chip">Pricing</div><div class="section-title">Simple, <span class="gradient">Transparent</span></div><div class="section-sub">Crypto payments only. No hidden fees.</div></div>
  <div class="pricing-grid">
    <div class="p-card reveal stagger-1"><div class="p-tier">Viewer</div><div class="p-amount">$0<span>/mo</span></div><div class="p-desc">Basic overview for observers.</div><ul class="p-features"><li><i class="fa-solid fa-check"></i> Market Regime &amp; Volatility</li><li><i class="fa-solid fa-check"></i> Top Gainers &amp; Losers</li><li><i class="fa-solid fa-check"></i> Live Price Ticker</li><li class="locked"><i class="fa-solid fa-xmark"></i> Sector Performance</li><li class="locked"><i class="fa-solid fa-xmark"></i> AI Reports</li><li class="locked"><i class="fa-solid fa-xmark"></i> Whale Intel</li></ul><button class="p-btn" onclick="location.href='/register'">Get Started</button></div>
    <div class="p-card featured reveal stagger-2"><div class="p-tier">Analyst</div><div class="p-amount">$5<span>/mo</span></div><div class="p-desc">Full suite for serious traders.</div><ul class="p-features"><li><i class="fa-solid fa-check"></i> Everything in Viewer</li><li><i class="fa-solid fa-check"></i> 16-Sector Performance</li><li><i class="fa-solid fa-check"></i> Correlation Matrix</li><li><i class="fa-solid fa-check"></i> Smart Screener</li><li><i class="fa-solid fa-check"></i> Whale &amp; Flow</li><li><i class="fa-solid fa-check"></i> AI Reports &amp; Brain</li><li><i class="fa-solid fa-check"></i> Alerts + Heatmap</li><li><i class="fa-solid fa-check"></i> Derivatives Intel</li></ul><button class="p-btn primary" onclick="openModal()">Subscribe Now</button></div>
    <div class="p-card reveal stagger-3"><div class="p-tier">Admin</div><div class="p-amount">Custom</div><div class="p-desc">Full system + management.</div><ul class="p-features"><li><i class="fa-solid fa-check"></i> Everything in Analyst</li><li><i class="fa-solid fa-check"></i> User Management</li><li><i class="fa-solid fa-check"></i> Payment Admin</li><li><i class="fa-solid fa-check"></i> Audit Log</li><li><i class="fa-solid fa-check"></i> System Config</li><li><i class="fa-solid fa-check"></i> API Access (soon)</li></ul><button class="p-btn" onclick="location.href='/login'">Contact</button></div>
  </div>
</section>

<div class="trust reveal"><div class="trust-item"><i class="fa-solid fa-lock"></i> 100% Local</div><div class="trust-item"><i class="fa-solid fa-server"></i> Zero Cloud</div><div class="trust-item"><i class="fa-brands fa-bitcoin"></i> Crypto Pay</div><div class="trust-item"><i class="fa-solid fa-microchip"></i> Local LLM</div><div class="trust-item"><i class="fa-solid fa-signal"></i> 641+ Symbols</div></div>

<footer><div class="footer-left"><i class="fa-solid fa-cube"></i> &copy; 2026 Hansen AI &mdash; Sovereign Market Intelligence</div><div class="footer-links"><a href="/login">Login</a><a href="/register">Register</a><a href="#pricing">Pricing</a><a href="#features">Features</a></div></footer>

<div class="modal-bg" id="modal-bg" onclick="if(event.target===this)closeModal()">
  <div class="modal">
    <button class="modal-close" onclick="closeModal()"><i class="fa-solid fa-xmark"></i></button>
    <h2>Subscribe to Analyst</h2>
    <p>Pay $5 USDT via any supported chain. Auto-activated after confirmation.</p>
    <label>Email</label><input type="email" id="sub-email" placeholder="you@example.com">
    <label>Payment Chain</label>
    <select id="sub-chain"><option value="USDT_BSC">USDT (BSC)</option><option value="USDT_ARB">USDT (Arbitrum)</option><option value="USDT_ETH">USDT (Ethereum)</option><option value="USDT_SOL">USDT (Solana)</option><option value="BTC">BTC</option><option value="APT">Aptos</option></select>
    <button class="btn-glow" onclick="submitSubscription()">Proceed to Payment</button>
  </div>
</div>

<script>
window.addEventListener('scroll',()=>{document.getElementById('nav').classList.toggle('scrolled',window.scrollY>50)});
const obs=new IntersectionObserver(e=>{e.forEach(el=>{if(el.isIntersecting){el.target.classList.add('active');obs.unobserve(el.target)}})},{threshold:.1,rootMargin:'0px 0px -60px 0px'});
document.querySelectorAll('.reveal,.reveal-left,.reveal-right').forEach(el=>obs.observe(el));
async function loadTicker(){try{const r=await fetch('/api/v1/sector-performance');const d=await r.json();if(d.status!=='ok')return;const ranking=d.data.ranking_24h||[];const t=document.getElementById('ticker-track');let h='';ranking.forEach(s=>{const c=s.avg_change>0?'ticker-up':'ticker-down';const sign=s.avg_change>0?'+':'';h+=`<div class="ticker-item"><span class="ticker-sym">${s.name}</span><span class="${c}">${sign}${s.avg_change.toFixed(2)}%</span></div>`});t.innerHTML=h+h}catch(e){}}loadTicker();
function openModal(){document.getElementById('modal-bg').classList.add('show')}
function closeModal(){document.getElementById('modal-bg').classList.remove('show')}
async function submitSubscription(){const email=document.getElementById('sub-email').value;const chain=document.getElementById('sub-chain').value;if(!email){alert('Please enter your email');return}try{const r=await fetch('/subscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,chain})});const d=await r.json();if(d.status==='ok'){alert('Payment registered! Check email for instructions.');closeModal()}else{alert(d.message||'Error')}}catch(e){alert('Connection error')}}

// 3D PARALLAX ON MOUSE
document.addEventListener('mousemove',e=>{const x=(e.clientX/window.innerWidth-.5)*20;const y=(e.clientY/window.innerHeight-.5)*20;const hero3d=document.querySelector('.hero-3d');if(hero3d)hero3d.style.transform=`translateY(-50%) translate(${x}px,${y}px)`;const brainVis=document.querySelector('.brain-visual');if(brainVis){const rect=brainVis.getBoundingClientRect();if(rect.top<window.innerHeight&&rect.bottom>0){brainVis.style.transform=`translate(${x*.5}px,${y*.5}px)`}}});
</script>
</body>
</html>"""
