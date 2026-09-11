import { ShieldCheck, Sparkles, Search, ArrowRight, Building2 } from "lucide-react";
import CasivaLogo from "./CasivaLogo";

const HERO_IMAGE =
  "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=2400&q=80";

const GALLERY_IMAGES = [
  "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=900&q=80",
  "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=900&q=80",
  "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=900&q=80",
];

const VALUE_PROPS = [
  {
    icon: Search,
    title: "AI-Guided Search",
    text: "A conversational agent that understands budgets, BHK configurations, and neighborhoods the way you'd describe them.",
  },
  {
    icon: ShieldCheck,
    title: "Verified Listings",
    text: "Every property photo set can be independently verified against its declared configuration before you visit.",
  },
  {
    icon: Building2,
    title: "Trusted Brokers",
    text: "Direct lines to vetted brokers, with enquiries and contact exchange handled transparently on-platform.",
  },
];

export default function LandingPage({ onGetStarted }) {
  return (
    <div className="min-h-screen w-full bg-[#FAF8F4] text-[#2B2B2B] font-body">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap');
        .font-display { font-family: 'Fraunces', serif; font-optical-sizing: auto; }
        .font-body { font-family: 'Inter', sans-serif; }
      `}</style>

      {/* HEADER */}
      <header className="fixed top-0 inset-x-0 z-30 bg-[#FAF8F4]/85 backdrop-blur-md border-b border-[#E4DCC9]">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2.5">
            <CasivaLogo className="w-8 h-8" />
            <span className="font-display text-lg tracking-[0.2em] text-[#3A3A3A]">CASIVA</span>
          </div>
          <nav className="hidden md:flex items-center gap-8 text-sm text-[#5B5B5B]">
            <a href="#value" className="hover:text-[#8A6C34] transition">Why Casiva</a>
            <a href="#properties" className="hover:text-[#8A6C34] transition">Properties</a>
          </nav>
          <button
            onClick={onGetStarted}
            className="flex items-center gap-2 px-4 py-2 rounded-sm bg-[#3A3A3A] hover:bg-[#1E1E1E] text-[#F3EEE1] text-xs font-semibold uppercase tracking-wider transition"
          >
            Get Started <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      {/* HERO */}
      <section className="relative pt-32 pb-24 px-6 overflow-hidden">
        <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-12 items-center">
          <div className="space-y-6">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[#8A6C34]">
              Private Client Real Estate
            </p>
            <h1 className="font-display text-4xl md:text-5xl leading-[1.15] text-[#2B2B2B]">
              Find a home that matches how you actually live.
            </h1>
            <p className="text-base text-[#5B5B5B] leading-relaxed max-w-md">
              CASIVA pairs an AI advisor with verified listings and trusted brokers,
              so every property you see is worth the visit.
            </p>
            <div className="flex items-center gap-4 pt-2">
              <button
                onClick={onGetStarted}
                className="flex items-center gap-2 px-6 py-3 rounded-sm bg-[#C6A15B] hover:bg-[#B08D4C] text-[#1E1E1E] font-semibold text-sm transition shadow-lg shadow-[#C6A15B]/20"
              >
                Get Started <ArrowRight className="w-4 h-4" />
              </button>
              <a href="#value" className="text-sm text-[#5B5B5B] hover:text-[#8A6C34] transition underline underline-offset-4">
                Learn more
              </a>
            </div>
          </div>
          <div className="relative rounded-md overflow-hidden shadow-2xl">
            <img src={HERO_IMAGE} alt="Featured property" className="w-full h-80 md:h-[26rem] object-cover" />
            <div className="absolute inset-0 ring-1 ring-inset ring-black/10 rounded-md" />
          </div>
        </div>
      </section>

      {/* VALUE PROPOSITION */}
      <section id="value" className="px-6 py-20 bg-white border-y border-[#E4DCC9]">
        <div className="max-w-6xl mx-auto">
          <h2 className="font-display text-2xl md:text-3xl text-center text-[#2B2B2B] mb-14">
            Everything you need, nothing you don&apos;t
          </h2>
          <div className="grid md:grid-cols-3 gap-10">
            {VALUE_PROPS.map(({ icon: Icon, title, text }) => (
              <div key={title} className="space-y-3 text-center md:text-left">
                <div className="inline-flex p-3 rounded-full bg-[#F5EEDD] text-[#8A6C34]">
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="font-display text-lg text-[#2B2B2B]">{title}</h3>
                <p className="text-sm text-[#6B6B6B] leading-relaxed">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* GALLERY */}
      <section id="properties" className="px-6 py-20">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-end justify-between mb-10">
            <h2 className="font-display text-2xl md:text-3xl text-[#2B2B2B]">Featured spaces</h2>
            <button onClick={onGetStarted} className="text-sm text-[#8A6C34] hover:underline underline-offset-4 flex items-center gap-1">
              Browse listings <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {GALLERY_IMAGES.map((src, i) => (
              <div key={i} className="rounded-md overflow-hidden shadow-lg h-56">
                <img src={src} alt="" className="w-full h-full object-cover hover:scale-105 transition duration-500" />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA BANNER */}
      <section className="px-6 py-20 bg-[#1E1E1E] text-[#F3EEE1]">
        <div className="max-w-3xl mx-auto text-center space-y-6">
          <Sparkles className="w-6 h-6 text-[#C6A15B] mx-auto" />
          <h2 className="font-display text-2xl md:text-3xl">Ready to see what fits?</h2>
          <p className="text-sm text-[#B9B2A0] max-w-md mx-auto">
            Create an account as a buyer or a broker and start exploring in minutes.
          </p>
          <button
            onClick={onGetStarted}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-sm bg-[#C6A15B] hover:bg-[#D9B876] text-[#1E1E1E] font-semibold text-sm transition"
          >
            Get Started <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="px-6 py-10 border-t border-[#E4DCC9]">
        <div className="max-w-6xl mx-auto flex items-center justify-between text-xs text-[#8B8B8B]">
          <div className="flex items-center gap-2">
            <CasivaLogo className="w-5 h-5" />
            <span className="tracking-wide">CASIVA</span>
          </div>
          <span>© {new Date().getFullYear()} Casiva. All rights reserved.</span>
        </div>
      </footer>
    </div>
  );
}
