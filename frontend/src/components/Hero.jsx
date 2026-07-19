import SideRays from './reactbits/SideRays'

function Hero({ onLearnMore }) {
  return (
    <div className="relative overflow-hidden border-b border-ink-700">
      {/* Cascading light effect, positioned top-right like the reference */}
      <div className="absolute inset-0 pointer-events-none">
        <SideRays
          speed={2.5}
          rayColor1="#c6a15b"
          rayColor2="#4fae8d"
          intensity={1.6}
          spread={2}
          origin="top-right"
          tilt={0}
          saturation={1.2}
          blend={0.6}
          falloff={1.6}
          opacity={0.9}
        />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto px-6 pt-28 pb-24 text-center">
        <div className="inline-flex items-center gap-2 bg-ink-900/80 border border-ink-700 rounded-full px-4 py-1.5 mb-8">
          <span className="bg-brass text-ink-950 text-xs font-semibold px-2 py-0.5 rounded-full">LIVE</span>
          <span className="text-sm text-paper-dim">Connected to your bank statements</span>
        </div>

        <h1 className="font-display font-semibold text-5xl md:text-6xl text-paper leading-tight mb-6">
          Your Spending,
          <br />
          Mapped and Understood
        </h1>

        <p className="text-paper-dim text-lg max-w-xl mx-auto mb-10">
          Upload a statement. See where it went, what repeats every month,
          and what to expect next -- automatically.
        </p>

        <div className="flex items-center justify-center">
          <button
            onClick={onLearnMore}
            className="bg-brass text-ink-950 font-medium px-8 py-3 rounded-full hover:bg-brass-bright transition-colors"
          >
            Upload a Statement
          </button>
        </div>
      </div>
    </div>
  )
}

export default Hero
