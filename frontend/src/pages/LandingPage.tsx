import React from 'react';
import { Link } from 'react-router-dom';
import { Shield, ShieldAlert, FileText, Search, PhoneCall, TrendingUp, HelpCircle, Sparkles } from 'lucide-react';
import Layout from '../components/layout/Layout';

export const LandingPage: React.FC = () => {
  return (
    <Layout>
      {/* Hero Section */}
      <section className="hero-gradient text-white py-16 px-4 md:py-24 md:px-8 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#fff_1px,transparent_1px)] [background-size:16px_16px]"></div>
        <div className="max-w-5xl mx-auto text-center relative z-10 space-y-6">
          <span className="bg-orange-500/20 text-orange-400 border border-orange-500/30 px-3.5 py-1 rounded-full text-xs font-bold tracking-wider uppercase inline-block">
            National Cyber Security Portal
          </span>
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight font-sans">
            Cyber Crime Reporting <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-orange-600">
              Management System
            </span>
          </h1>
          <p className="text-slate-300 max-w-2xl mx-auto text-base md:text-lg font-light leading-relaxed">
            Report UPI fraud, credit/debit card scams, cyber harassment, hacking, identity theft, or women/children related offenses. Take action securely.
          </p>

          <div className="flex flex-col sm:flex-row justify-center gap-4 pt-4">
            <Link
              to="/file-complaint"
              className="bg-orange-600 hover:bg-orange-700 text-white font-bold px-8 py-3.5 rounded-lg shadow-lg hover:shadow-orange-600/10 transition-all text-sm flex items-center justify-center space-x-2"
            >
              <ShieldAlert className="h-5 w-5" />
              <span>Report Cyber Crime</span>
            </Link>
            <Link
              to="/file-complaint?ai=true"
              className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-8 py-3.5 rounded-lg shadow-lg hover:shadow-indigo-600/10 transition-all text-sm flex items-center justify-center space-x-2"
            >
              <Sparkles className="h-5 w-5" />
              <span>File Complaint with AI Officer</span>
            </Link>
            <Link
              to="/track"
              className="bg-slate-800 hover:bg-slate-700 text-white font-bold px-8 py-3.5 rounded-lg border border-slate-700 hover:border-slate-600 transition-all text-sm flex items-center justify-center space-x-2"
            >
              <FileText className="h-5 w-5" />
              <span>Track Complaint</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Emergency Helpline Banner */}
      <section className="bg-orange-600 text-white py-4 px-4 font-sans shadow-md">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center text-center md:text-left gap-3">
          <div className="flex items-center space-x-3">
            <PhoneCall className="h-7 w-7 animate-bounce flex-shrink-0" />
            <div>
              <p className="font-extrabold text-sm md:text-base">FINANCIAL FRAUD IMMEDIATE EMERGENCY HELPLINE</p>
              <p className="text-xs text-orange-100">Dial instantly to freeze fraudulent transfers from your bank account.</p>
            </div>
          </div>
          <a
            href="tel:1930"
            className="bg-slate-900 text-white hover:bg-black font-extrabold px-6 py-2.5 rounded-full text-base tracking-widest shadow-md transition-all flex-shrink-0"
          >
            CALL 1930
          </a>
        </div>
      </section>

      {/* Quick Action Category Cards */}
      <section className="py-16 px-4 max-w-7xl mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-12 space-y-2">
          <h2 className="text-2xl md:text-3xl font-extrabold text-gov-navy">Report Category Wise</h2>
          <p className="text-sm text-gov-slate">Choose a dedicated reporting flow. Offenses involving Women & Children support anonymous filings.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Card 1 */}
          <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm hover:shadow-md transition-all flex flex-col justify-between group">
            <div className="space-y-4">
              <div className="bg-orange-50 h-12 w-12 rounded-xl flex items-center justify-center text-orange-600 group-hover:scale-110 transition-transform">
                <TrendingUp className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-gov-navy">Financial Frauds</h3>
              <p className="text-xs text-gov-slate leading-relaxed">
                UPI fraud, online banking transfers, credit/debit card theft, fake stock trading channels, loan app extortion, and cryptocurrency theft.
              </p>
            </div>
            <Link
              to="/file-complaint?cat=FF"
              className="text-xs font-bold text-gov-indigo hover:text-orange-500 mt-6 inline-flex items-center space-x-1"
            >
              <span>File Transaction Fraud &rarr;</span>
            </Link>
          </div>

          {/* Card 2 */}
          <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm hover:shadow-md transition-all flex flex-col justify-between group">
            <div className="space-y-4">
              <div className="bg-indigo-50 h-12 w-12 rounded-xl flex items-center justify-center text-gov-indigo group-hover:scale-110 transition-transform">
                <Shield className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-gov-navy">Other Cyber Crimes</h3>
              <p className="text-xs text-gov-slate leading-relaxed">
                Hacking of email or social media accounts, impersonation, ransomware attacks, server defacement, malware compromises, and cyberbullying.
              </p>
            </div>
            <Link
              to="/file-complaint?cat=OC"
              className="text-xs font-bold text-gov-indigo hover:text-orange-500 mt-6 inline-flex items-center space-x-1"
            >
              <span>File General Cyber Crime &rarr;</span>
            </Link>
          </div>

          {/* Card 3 */}
          <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm hover:shadow-md transition-all flex flex-col justify-between group">
            <div className="space-y-4">
              <div className="bg-red-50 h-12 w-12 rounded-xl flex items-center justify-center text-red-600 group-hover:scale-110 transition-transform">
                <ShieldAlert className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-gov-navy">Women & Children Crime</h3>
              <p className="text-xs text-gov-slate leading-relaxed">
                Cyberstalking, blackmail, sextortion, child exploitation (CSAM), fake profile defamation, and obscene harassment.
              </p>
            </div>
            <Link
              to="/file-complaint?cat=WC"
              className="text-xs font-bold text-red-600 hover:text-red-700 mt-6 inline-flex items-center space-x-1"
            >
              <span>File Report (Anonymous option) &rarr;</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Suspect Search Section */}
      <section className="bg-slate-900 text-white py-16 px-4">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-6">
            <span className="bg-gov-indigo/80 border border-slate-700 px-3 py-1 rounded-full text-xs font-bold tracking-wider uppercase inline-block">
              Citizen Registry
            </span>
            <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight font-sans">
              Search the Suspect Repository
            </h2>
            <p className="text-slate-300 text-sm leading-relaxed">
              Verify unknown contacts before completing transactions. Our database aggregates citizen reports of suspicious mobile numbers, bank accounts, UPI IDs, social media handles, and website URLs.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 pt-2">
              <Link
                to="/suspect-search"
                className="bg-orange-600 hover:bg-orange-700 text-white font-bold px-6 py-3 rounded-lg text-sm transition-all flex items-center justify-center space-x-2"
              >
                <Search className="h-4 w-4" />
                <span>Search Repository</span>
              </Link>
            </div>
          </div>
          <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 md:p-8 space-y-4">
            <h3 className="font-bold text-lg border-b border-slate-700 pb-3 flex items-center text-orange-500">
              <ShieldAlert className="h-5 w-5 mr-2" />
              Suspect Registry Statistics
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-700/50">
                <p className="text-xs text-slate-400 font-medium uppercase">Active Suspect IDs</p>
                <p className="text-2xl font-black text-white mt-1">42,501</p>
              </div>
              <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-700/50">
                <p className="text-xs text-slate-400 font-medium uppercase">Reports Registered</p>
                <p className="text-2xl font-black text-white mt-1">118,240</p>
              </div>
              <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-700/50">
                <p className="text-xs text-slate-400 font-medium uppercase">UPI Fraud Links</p>
                <p className="text-2xl font-black text-white mt-1">12,940</p>
              </div>
              <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-700/50">
                <p className="text-xs text-slate-400 font-medium uppercase">Fraudulent Mobiles</p>
                <p className="text-2xl font-black text-white mt-1">20,410</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-16 px-4 max-w-7xl mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-16 space-y-2">
          <h2 className="text-2xl md:text-3xl font-extrabold text-gov-navy">Incident Filing Workflow</h2>
          <p className="text-sm text-gov-slate">Understand how complaints are processed by law enforcement.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 relative">
          <div className="space-y-4 text-center">
            <div className="bg-gov-indigo text-white h-12 w-12 rounded-full flex items-center justify-center font-black mx-auto text-lg">1</div>
            <h3 className="font-bold text-sm text-gov-navy">Citizen Files Incident</h3>
            <p className="text-xs text-gov-slate leading-relaxed">Submit details of the incident, suspect identifiers, and screenshots.</p>
          </div>
          <div className="space-y-4 text-center">
            <div className="bg-gov-indigo text-white h-12 w-12 rounded-full flex items-center justify-center font-black mx-auto text-lg">2</div>
            <h3 className="font-bold text-sm text-gov-navy">Acknowledgement Receipt</h3>
            <p className="text-xs text-gov-slate leading-relaxed">Portal generates a unique ACK number and downloadable PDF file.</p>
          </div>
          <div className="space-y-4 text-center">
            <div className="bg-gov-indigo text-white h-12 w-12 rounded-full flex items-center justify-center font-black mx-auto text-lg">3</div>
            <h3 className="font-bold text-sm text-gov-navy">Officer Assignment</h3>
            <p className="text-xs text-gov-slate leading-relaxed">Complaint is reviewed and assigned to an Investigation Officer.</p>
          </div>
          <div className="space-y-4 text-center">
            <div className="bg-gov-indigo text-white h-12 w-12 rounded-full flex items-center justify-center font-black mx-auto text-lg">4</div>
            <h3 className="font-bold text-sm text-gov-navy">Resolution / Action</h3>
            <p className="text-xs text-gov-slate leading-relaxed">Funds are frozen, sites are taken down, or legal FIR is filed.</p>
          </div>
        </div>
      </section>

      {/* Cyber Safety Tips */}
      <section className="py-16 bg-slate-100 border-t border-slate-200 px-4">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="space-y-3 bg-white p-6 rounded-2xl border border-slate-200/60 shadow-sm">
            <div className="text-orange-500 font-extrabold text-sm uppercase flex items-center">
              <ShieldAlert className="h-4 w-4 mr-2" />
              Safety Tip #1
            </div>
            <h4 className="font-bold text-sm text-gov-navy">Protect UPI Passcodes</h4>
            <p className="text-xs text-gov-slate leading-relaxed">
              No government agency, bank, or online merchant will ever ask you to enter your UPI PIN to receive money. PIN is only for sending money.
            </p>
          </div>
          <div className="space-y-3 bg-white p-6 rounded-2xl border border-slate-200/60 shadow-sm">
            <div className="text-orange-500 font-extrabold text-sm uppercase flex items-center">
              <ShieldAlert className="h-4 w-4 mr-2" />
              Safety Tip #2
            </div>
            <h4 className="font-bold text-sm text-gov-navy">Verify Website Domain URLs</h4>
            <p className="text-xs text-gov-slate leading-relaxed">
              Phishing portals replicate e-commerce or bank logins. Check the address bar for extra domains, e.g. "www.merchant.payments-portal.xyz" instead of the official site.
            </p>
          </div>
          <div className="space-y-3 bg-white p-6 rounded-2xl border border-slate-200/60 shadow-sm">
            <div className="text-orange-500 font-extrabold text-sm uppercase flex items-center">
              <ShieldAlert className="h-4 w-4 mr-2" />
              Safety Tip #3
            </div>
            <h4 className="font-bold text-sm text-gov-navy">Report Instantly</h4>
            <p className="text-xs text-gov-slate leading-relaxed">
              Report transaction scams within the first 2-24 hours ("Golden Hour") to drastically increase the probability of retrieving stolen bank funds.
            </p>
          </div>
        </div>
      </section>
    </Layout>
  );
};
export default LandingPage;
