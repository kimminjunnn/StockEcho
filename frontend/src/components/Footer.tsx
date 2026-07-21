import React from 'react';

export default function Footer() {
  return (
    <footer className="bg-surface-container border-t border-outline-variant mt-3xl">
      <div className="flex flex-col md:flex-row justify-between items-center py-xl px-gutter max-w-container-max mx-auto gap-lg">
        <div className="flex flex-col items-center md:items-start gap-xs">
          <span className="font-label-caps text-label-caps text-primary">STOCK ECHO FINANCIAL</span>
          <p className="font-body-sm text-on-surface-variant text-center md:text-left opacity-80">© 2024 Stock Echo Financial. All rights reserved.</p>
        </div>
        <div className="flex gap-lg">
          <a className="font-body-sm text-on-surface-variant hover:text-primary transition-colors" href="#">Privacy Policy</a>
          <a className="font-body-sm text-on-surface-variant hover:text-primary transition-colors" href="#">Terms of Service</a>
          <a className="font-body-sm text-on-surface-variant hover:text-primary transition-colors" href="#">Contact</a>
          <a className="font-body-sm text-on-surface-variant hover:text-primary transition-colors" href="#">Disclosure</a>
        </div>
      </div>
    </footer>
  );
}
