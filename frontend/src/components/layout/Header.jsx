import { ShieldCheck } from 'lucide-react';

const Header = () => {
  return (
    <header className="h-16 w-full glass-panel flex items-center px-6 relative z-20">
      <div className="flex items-center gap-3 z-10 w-full relative">
        <ShieldCheck className="text-neon-cyan glow-cyan rounded-full bg-quantum-void p-[2px]" size={28} />
        <h1 className="text-xl font-bold tracking-widest bg-transparent">
          <span className="text-white">QUANTUM</span><span className="text-neon-cyan">CIPHERSIM</span>
        </h1>
        <div className="ml-4 px-3 py-1 bg-quantum-surface border border-neon-cyan/50 text-neon-cyan text-xs font-mono rounded-sm uppercase tracking-wider animate-pulse glow-cyan">
          SOC SECURE
        </div>
      </div>
    </header>
  );
};

export default Header;
