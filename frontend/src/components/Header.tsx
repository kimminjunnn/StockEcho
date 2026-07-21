import React from 'react';

export default function Header() {
  return (
    <header className="bg-surface sticky top-0 z-50 border-b border-outline-variant">
      <div className="flex justify-between items-center px-gutter h-[80px] max-w-container-max mx-auto">
        <div className="flex items-center gap-xl">
          <div className="flex items-center gap-sm">
            <img alt="Stock Echo Logo" className="h-8 w-8 object-contain" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDcs8cBtRCO17vFBZot9ai7qM5v4r30IFAUx8H-ZqrjsW0KkSdiBcaR3dVplyb49q-3DspEgyVI0VxxZ9ukvqozWuxOt4jjJkb4iVhect8lILQU8xfV6nbr1epJ0E09teVwC-8eTAMk9-S5yIZbibbkvuh2Ge5ZcQg-RLRfjASVgWnVhV0krKLq8xO3rwQNv7dyHdZZhNPASn0nxAq9BhTgPm_RsnJK9AcW5nwfkxVXr02tviJ7UOKfJw" />
            <span className="font-display-lg text-[24px] font-black text-primary tracking-tight">Stock Echo</span>
          </div>
          <nav className="hidden md:flex items-center gap-lg">
            <a className="text-primary font-bold border-b-2 border-primary h-[80px] flex items-center px-xs transition-all" href="#">Portfolio</a>
            <a className="text-on-surface-variant hover:text-primary transition-colors h-[80px] flex items-center px-xs" href="#">Insights</a>
            <a className="text-on-surface-variant hover:text-primary transition-colors h-[80px] flex items-center px-xs" href="#">Market</a>
            <a className="text-on-surface-variant hover:text-primary transition-colors h-[80px] flex items-center px-xs" href="#">Settings</a>
          </nav>
        </div>
        <div className="flex items-center gap-md">
          <div className="hidden sm:flex flex-col items-end mr-md border-r border-outline-variant pr-md">
            <span className="font-label-caps text-[10px] text-outline">KOSPI INDEX</span>
            <span className="font-title-sm text-sm font-bold">2,650.21 <span className="text-error ml-xs font-normal">-0.45%</span></span>
          </div>
          <div className="flex items-center gap-sm">
            <span className="font-title-sm text-sm font-bold">강건호님</span>
            <div className="h-10 w-10 rounded-full bg-surface-container-highest overflow-hidden border border-outline-variant">
              <img className="h-full w-full object-cover" alt="Profile" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAWL9Tlw8Ft6xmYdXi49DDSdoW1WFEBHfcIR-eyhDPo4TrTVPkLfecZ5ENq93brGbbowzwOgrXLmTSULiR5pdUW5MMMlX1Qtbi_QFE3-KaUpRQo1k70AeVe3AChpsdJXHutz0qk2_vg4l30amTaqKIUo6hUjzJWWoeNZY4nxM4kjn8x5WqiAirlvUyKnQwVfZGYfDUTyJ_FzTK1T_LEvzT5bYolQeiCRzC0vOfWNshughGerafM84H_Kg" />
            </div>
          </div>
          <button className="material-symbols-outlined p-sm hover:bg-surface-container-low rounded-full transition-colors">notifications</button>
          <button className="material-symbols-outlined md:hidden p-sm hover:bg-surface-container-low rounded-full transition-colors">menu</button>
        </div>
      </div>
    </header>
  );
}
