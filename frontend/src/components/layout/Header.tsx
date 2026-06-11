import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Shield, Menu, X, LogOut } from 'lucide-react';

export const Header: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/');
    setMobileMenuOpen(false);
  };

  return (
    <header className="bg-slate-900 text-white shadow-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo Brand */}
          <Link to="/" className="flex items-center space-x-3 hover:opacity-90">
            <Shield className="h-8 w-8 text-orange-500 animate-pulse" />
            <div>
              <span className="font-extrabold text-lg tracking-wider block font-sans">CyberSathi-AI</span>
              <span className="text-[10px] text-slate-300 block -mt-1 uppercase font-semibold">Cyber Security Portal</span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex space-x-6 items-center text-sm font-medium">
            <Link to="/" className="hover:text-orange-500 transition-colors">Home</Link>
            <Link to="/track" className="hover:text-orange-500 transition-colors">Track Complaint</Link>
            <Link to="/suspect-search" className="hover:text-orange-500 transition-colors">Suspect Search</Link>

            {user ? (
              <>
                <Link
                  to={user.role === 'citizen' ? '/dashboard' : '/admin'}
                  className="bg-gov-indigo/80 px-3 py-1.5 rounded hover:bg-gov-indigo transition-colors"
                >
                  Dashboard
                </Link>
                <div className="flex items-center space-x-3 pl-4 border-l border-slate-700">
                  <div className="text-right">
                    <p className="text-xs font-bold">{user.full_name}</p>
                    <span className="text-[9px] bg-orange-600 text-white px-1.5 py-0.5 rounded capitalize font-extrabold">
                      {user.role}
                    </span>
                  </div>
                  <button
                    onClick={handleLogout}
                    title="Sign Out"
                    className="p-1.5 hover:bg-slate-800 rounded text-slate-300 hover:text-white transition-colors"
                  >
                    <LogOut className="h-5 w-5" />
                  </button>
                </div>
              </>
            ) : (
              <div className="flex items-center space-x-4 pl-4 border-l border-slate-700">
                <Link to="/login" className="hover:text-orange-500 transition-colors">Sign In</Link>
                <Link
                  to="/register"
                  className="bg-orange-600 px-4 py-2 rounded font-bold hover:bg-orange-700 transition-colors"
                >
                  Register
                </Link>
              </div>
            )}
          </nav>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden items-center">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-slate-400 hover:text-white focus:outline-none"
            >
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-slate-900 border-t border-slate-800 px-2 pt-2 pb-4 space-y-1 sm:px-3 text-sm font-medium">
          <Link
            to="/"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded hover:bg-slate-800 text-white"
          >
            Home
          </Link>
          <Link
            to="/track"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded hover:bg-slate-800 text-white"
          >
            Track Complaint
          </Link>
          <Link
            to="/suspect-search"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded hover:bg-slate-800 text-white"
          >
            Suspect Search
          </Link>

          {user ? (
            <>
              <Link
                to={user.role === 'citizen' ? '/dashboard' : '/admin'}
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded bg-indigo-850 hover:bg-slate-800 text-white font-bold"
              >
                Dashboard
              </Link>
              <div className="pt-4 pb-2 border-t border-slate-850 pl-3">
                <p className="text-sm font-bold text-white">{user.full_name}</p>
                <p className="text-xs text-slate-400 capitalize">{user.role}</p>
              </div>
              <button
                onClick={handleLogout}
                className="w-full text-left flex items-center space-x-2 px-3 py-2 rounded text-red-400 hover:bg-slate-800"
              >
                <LogOut className="h-5 w-5" />
                <span>Logout</span>
              </button>
            </>
          ) : (
            <div className="pt-4 border-t border-slate-800 space-y-2 px-3">
              <Link
                to="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="block text-center py-2 rounded border border-slate-700 hover:bg-slate-800 text-white"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                onClick={() => setMobileMenuOpen(false)}
                className="block text-center py-2 rounded bg-orange-600 hover:bg-orange-700 text-white font-bold"
              >
                Register
              </Link>
            </div>
          )}
        </div>
      )}
    </header>
  );
};
export default Header;
