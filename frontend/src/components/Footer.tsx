import React from 'react';

export default function Footer() {
  return (
    <footer className="bg-[#EEF4FF] border-t border-blue-100/80 py-8 mt-auto">
      <div className="flex flex-col md:flex-row justify-between items-center max-w-[1240px] mx-auto px-6 gap-4 text-slate-600 text-xs">
        <div className="flex flex-col items-center md:items-start gap-1">
          <span className="font-extrabold tracking-wider text-[#2563EB]">STOCK ECHO FINANCIAL</span>
          <p className="opacity-80">© 2026 Stock Echo Financial. All rights reserved.</p>
        </div>
        <div className="flex gap-6 font-medium">
          <a className="hover:text-blue-600 transition-colors" href="#">Privacy Policy</a>
          <a className="hover:text-blue-600 transition-colors" href="#">Terms of Service</a>
          <a className="hover:text-blue-600 transition-colors" href="#">Contact</a>
          <a className="hover:text-blue-600 transition-colors" href="#">Disclosure</a>
        </div>
      </div>
    </footer>
  );
}

