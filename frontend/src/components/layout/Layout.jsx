import { Outlet } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';

const Layout = () => {
  return (
    <div className="flex h-screen w-screen bg-quantum-bg text-slate-100 font-sans overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 relative h-full">
        <Header />
        {/* Main Content Area */}
        <main className="flex-1 relative overflow-hidden p-6 z-10">
          {/* Outlet is where the nested routes render their content */}
          <Outlet />
        </main>
      </div>
      
      {/* Background ambient lighting */}
      <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-quantum-primary/5 rounded-full blur-[120px] pointer-events-none -z-10"></div>
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-quantum-neon/5 rounded-full blur-[100px] pointer-events-none -z-10"></div>
    </div>
  );
};

export default Layout;
