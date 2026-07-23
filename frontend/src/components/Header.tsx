"use client";

import React from 'react';
import Link from 'next/link';
import { useSession, signIn, signOut } from "next-auth/react";

export default function Header() {
  const { data: session, status } = useSession();

  return (
    <header className="bg-surface sticky top-0 z-50 border-b border-outline-variant">
      <div className="flex justify-between items-center px-gutter h-[80px] max-w-container-max mx-auto">
        <div className="flex items-center gap-xl">
          <Link
            href="/"
            aria-label="Stock Echo 홈으로 이동"
            className="flex items-center gap-sm rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
          >
            <img alt="Stock Echo Logo" className="h-8 w-8 object-contain" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDcs8cBtRCO17vFBZot9ai7qM5v4r30IFAUx8H-ZqrjsW0KkSdiBcaR3dVplyb49q-3DspEgyVI0VxxZ9ukvqozWuxOt4jjJkb4iVhect8lILQU8xfV6nbr1epJ0E09teVwC-8eTAMk9-S5yIZbibbkvuh2Ge5ZcQg-RLRfjASVgWnVhV0krKLq8xO3rwQNv7dyHdZZhNPASn0nxAq9BhTgPm_RsnJK9AcW5nwfkxVXr02tviJ7UOKfJw" />
            <span className="font-display-lg text-[24px] font-black text-primary tracking-tight">Stock Echo</span>
          </Link>

        </div>

        <div className="flex items-center gap-md">
          <div className="hidden sm:flex flex-col items-end mr-md border-r border-outline-variant pr-md">
            <span className="font-label-caps text-[10px] text-outline">KOSPI INDEX</span>
            <span className="font-title-sm text-sm font-bold">2,650.21 <span className="text-error ml-xs font-normal">-0.45%</span></span>
          </div>

          {status === "loading" ? (
            <div className="flex items-center gap-sm">
              <div className="w-24 h-5 bg-gray-200 animate-pulse rounded"></div>
              <div className="h-10 w-10 rounded-full bg-gray-200 animate-pulse"></div>
            </div>
          ) : session?.user ? (
            <div className="flex items-center gap-sm group relative">
              <span className="font-title-sm text-sm font-bold">{session.user.name}님</span>
              <div className="h-10 w-10 rounded-full bg-surface-container-highest overflow-hidden border border-outline-variant cursor-pointer">
                <img className="h-full w-full object-cover" alt="Profile" src={session.user.image || "https://lh3.googleusercontent.com/aida-public/AB6AXuAWL9Tlw8Ft6xmYdXi49DDSdoW1WFEBHfcIR-eyhDPo4TrTVPkLfecZ5ENq93brGbbowzwOgrXLmTSULiR5pdUW5MMMlX1Qtbi_QFE3-KaUpRQo1k70AeVe3AChpsdJXHutz0qk2_vg4l30amTaqKIUo6hUjzJWWoeNZY4nxM4kjn8x5WqiAirlvUyKnQwVfZGYfDUTyJ_FzTK1T_LEvzT5bYolQeiCRzC0vOfWNshughGerafM84H_Kg"} />
              </div>

              {/* Hover Dropdown for Logout */}
              <div className="absolute right-0 top-12 mt-2 w-32 bg-white rounded-md shadow-lg py-1 border border-gray-100 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                <button 
                  onClick={() => signOut({ callbackUrl: '/onboarding' })}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-red-600 transition-colors"
                >
                  로그아웃
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => signIn('google')}
              className="bg-primary hover:bg-blue-600 text-white text-sm font-bold py-2 px-4 rounded-full transition-colors flex items-center gap-2 shadow-sm"
            >
              <svg className="w-4 h-4 bg-white rounded-full p-[2px]" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              구글로 로그인
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
