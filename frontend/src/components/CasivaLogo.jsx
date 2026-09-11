import casivaLogoSrc from "../assets/casiva-logo.png";

// Shield "CS" monogram supplied by the brand — a raster asset with its
// background matted to transparent so it drops onto any surface cleanly.
export default function CasivaLogo({ className = "w-10 h-10", withWordmark = false }) {
  const mark = <img src={casivaLogoSrc} alt="CASIVA monogram" className={`${className} object-contain`} />;

  if (!withWordmark) return mark;

  return (
    <div className="flex items-center gap-3">
      {mark}
      <span className="font-display text-2xl tracking-[0.18em] text-[#3A3A3A]">CASIVA</span>
    </div>
  );
}
