import React from 'react';
import Header from './Header';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="flex flex-col min-h-screen bg-slate-50">
      {/* Sticky Header */}
      <Header />

      {/* Main Content Area */}
      <main className="flex-grow">
        {children}
      </main>

      {/* Government-style professional footer */}
      <footer className="bg-slate-900 text-slate-400 border-t border-slate-800 text-xs py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <h3 className="text-white font-bold mb-3 text-sm">CCRMS Portal</h3>
              <p className="leading-relaxed">
                Cyber Crime Reporting Management System is an educational simulation portal inspired by India's National Cyber Crime Reporting Portal. Report cybercrimes securely and track their investigation.
              </p>
            </div>
            <div>
              <h3 className="text-white font-bold mb-3 text-sm">Emergency Resources</h3>
              <ul className="space-y-2">
                <li>
                  National Cyber Crime Helpline: <span className="text-orange-500 font-bold">1930</span> (24/7 Helpline)
                </li>
                <li>
                  Women Helpline Number: <span className="text-white">1091</span>
                </li>
                <li>
                  Child Helpline Number: <span className="text-white">1098</span>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="text-white font-bold mb-3 text-sm">Important Notice</h3>
              <p className="leading-relaxed">
                This website is a generic educational clone. Do not upload actual highly confidential or sensitive national security data. In case of actual cybercrime incidents, please report directly to the official government channel.
              </p>
            </div>
          </div>
          <div className="mt-8 pt-8 border-t border-slate-800 text-center flex flex-col sm:flex-row justify-between items-center text-[10px]">
            <p>&copy; {new Date().getFullYear()} CCRMS. Designed for Portfolio & educational review.</p>
            <p className="space-x-4 mt-2 sm:mt-0">
              <a href="#" className="hover:text-white transition-colors">Privacy Policy</a>
              <span>&bull;</span>
              <a href="#" className="hover:text-white transition-colors">Terms of Service</a>
              <span>&bull;</span>
              <a href="#" className="hover:text-white transition-colors">Hyperlinking Policy</a>
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};
export default Layout;
