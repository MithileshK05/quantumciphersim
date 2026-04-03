import { Activity, Beaker, BrainCircuit, Library } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const Sidebar = () => {
  const links = [
    { to: '/', name: 'Dashboard', icon: <Activity size={24} /> },
    { to: '/sim', name: 'Simulation', icon: <Beaker size={24} /> },
    { to: '/ml', name: 'ML Analysis', icon: <BrainCircuit size={24} /> },
    { to: '/concepts', name: 'Concepts', icon: <Library size={24} /> },
  ];

  return (
    <nav className="flex flex-col w-20 bg-quantum-surface border-r border-quantum-border h-full items-center py-8 gap-8 transition-colors">
      {links.map((link) => (
        <NavLink
          key={link.name}
          to={link.to}
          className={({ isActive }) =>
            `p-3 transition-all duration-300 relative group flex items-center justify-center w-full ${
              isActive
                ? 'text-neon-cyan before:absolute before:left-0 before:top-0 before:bottom-0 before:w-1 before:bg-neon-cyan before:shadow-[0_0_10px_#00F0FF]'
                : 'text-text-muted hover:text-text-main hover:bg-quantum-surface-hover'
            }`
          }
          title={link.name}
        >
          {link.icon}
        </NavLink>
      ))}
    </nav>
  );
};

export default Sidebar;
