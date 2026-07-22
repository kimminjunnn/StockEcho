"use client";

import React, { useEffect } from 'react';
import Link from 'next/link';

export default function OnboardingPage() {
  // Simple micro-interactions for buttons
  useEffect(() => {
    const buttons = document.querySelectorAll('button');
    const handleMouseDown = (e: Event) => {
      (e.currentTarget as HTMLElement).style.transform = 'scale(0.98)';
    };
    const handleMouseUp = (e: Event) => {
      (e.currentTarget as HTMLElement).style.transform = 'scale(1)';
    };
    const handleMouseLeave = (e: Event) => {
      (e.currentTarget as HTMLElement).style.transform = 'scale(1)';
    };

    buttons.forEach(button => {
      button.addEventListener('mousedown', handleMouseDown);
      button.addEventListener('mouseup', handleMouseUp);
      button.addEventListener('mouseleave', handleMouseLeave);
    });

    return () => {
      buttons.forEach(button => {
        button.removeEventListener('mousedown', handleMouseDown);
        button.removeEventListener('mouseup', handleMouseUp);
        button.removeEventListener('mouseleave', handleMouseLeave);
      });
    };
  }, []);

  return (
    <>
      <style dangerouslySetInnerHTML={{
        __html: `
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap');
        
        .onboarding-container {
            background-color: #f8f9ff;
            font-family: 'Manrope', sans-serif;
            color: #0b1c30;
            overflow-x: hidden;
            min-height: 100vh;
        }
        .onboarding-container .glass-card {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(229, 238, 255, 0.5);
        }
        .onboarding-container .text-gradient {
            background: linear-gradient(135deg, #004ac6 0%, #2563eb 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .onboarding-container .hero-mesh {
            position: absolute;
            top: -20%;
            right: -10%;
            width: 60%;
            height: 80%;
            background: radial-gradient(circle at 50% 50%, rgba(37, 99, 235, 0.08), transparent 70%);
            z-index: -1;
            filter: blur(60px);
        }
      `}} />

      <div className="onboarding-container bg-background w-full">
        {/* Main Content */}
        <main className="pt-24 pb-32">
          {/* Hero Section */}
          <section className="relative max-w-[1200px] mx-auto px-gutter mb-xl overflow-visible">
            <div className="hero-mesh"></div>
            <div className="max-w-[768px] mx-auto md:mx-0">
              <div className="inline-flex items-center gap-xs bg-secondary-container text-on-secondary-container px-md py-xs rounded-full mb-md">
                <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>auto_awesome</span>
                <span className="text-label-mono font-label-mono text-[12px] uppercase tracking-wider font-semibold" style={{ fontFamily: "'JetBrains Mono'" }}>AI-DRIVEN RISK ENGINE v2.4</span>
              </div>
              <h1 className="font-display-lg text-[40px] md:text-[56px] mb-md leading-tight" style={{ fontWeight: 700, letterSpacing: '-0.02em', wordBreak: 'keep-all' }}>
                공시·뉴스 기반 AI 포트폴리오 <br />
                <span className="text-gradient">위험 진단, Stock Echo</span>
              </h1>
              <p className="font-body-lg text-[16px] md:text-[18px] text-on-surface-variant mb-lg leading-relaxed max-w-[600px] break-keep">
                BERTopic과 RAG 기반 과거 유사 사건(Risk Replay) 분석으로 <br className="hidden md:block" />
                투자 위험을 객관적으로 관리하고 의사결정의 확신을 더하세요.
              </p>
              <div className="flex flex-col sm:flex-row gap-sm">
                <Link href="/" className="bg-primary text-on-primary px-lg py-md rounded-xl font-headline-sm shadow-xl shadow-primary/20 hover:shadow-2xl hover:shadow-primary/30 transition-all flex items-center justify-center gap-xs font-semibold">
                  서비스 시작하기
                  <span className="material-symbols-outlined">arrow_forward</span>
                </Link>
                <button className="bg-white border border-outline-variant text-on-surface px-lg py-md rounded-xl font-headline-sm hover:bg-surface-container-low transition-colors font-semibold">
                  데모 보기
                </button>
              </div>
            </div>
          </section>

          {/* Features Section (Bento Style) */}
          <section className="max-w-[1200px] mx-auto px-gutter mb-xl mt-32">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-md">
              {/* Card 1 */}
              <div className="glass-card p-lg rounded-xl flex flex-col hover:border-primary/30 transition-all duration-300 group">
                <div className="w-12 h-12 rounded-lg bg-primary/10 text-primary flex items-center justify-center mb-md group-hover:scale-110 transition-transform">
                  <span className="material-symbols-outlined text-[28px]" style={{ fontVariationSettings: "'FILL' 1" }}>history_toggle_off</span>
                </div>
                <h3 className="font-headline-md text-[24px] mb-sm font-semibold">Risk Replay</h3>
                <p className="font-body-md text-[14px] text-on-surface-variant leading-relaxed">
                  위험 사건 감지 및 과거 유사 사건(Top 5) 분석 — 1일·5일·20일 시장 대비 초과수익률 및 하락 비율 제시
                </p>
                <div className="mt-auto pt-lg">
                  <div className="h-1 w-12 bg-primary/20 group-hover:w-full transition-all duration-500"></div>
                </div>
              </div>

              {/* Card 2 */}
              <div className="glass-card p-lg rounded-xl flex flex-col hover:border-primary/30 transition-all duration-300 group">
                <div className="w-12 h-12 rounded-lg bg-surface-container-high text-primary flex items-center justify-center mb-md group-hover:scale-110 transition-transform">
                  <span className="material-symbols-outlined text-[28px]" style={{ fontVariationSettings: "'FILL' 1" }}>description</span>
                </div>
                <h3 className="font-headline-md text-[24px] mb-sm font-semibold">AI Briefing</h3>
                <p className="font-body-md text-[14px] text-on-surface-variant leading-relaxed">
                  할루시네이션 없는 팩트 중심 3줄 요약 및 100% 검증된 공시·뉴스 원문 링크 제공으로 투명성 확보
                </p>
                <div className="mt-auto pt-lg">
                  <div className="h-1 w-12 bg-primary/20 group-hover:w-full transition-all duration-500"></div>
                </div>
              </div>

              {/* Card 3 */}
              <div className="glass-card p-lg rounded-xl flex flex-col hover:border-primary/30 transition-all duration-300 group">
                <div className="w-12 h-12 rounded-lg bg-primary-container/10 text-primary flex items-center justify-center mb-md group-hover:scale-110 transition-transform">
                  <span className="material-symbols-outlined text-[28px]" style={{ fontVariationSettings: "'FILL' 1" }}>monitoring</span>
                </div>
                <h3 className="font-headline-md text-[24px] mb-sm font-semibold">Stress Test</h3>
                <p className="font-body-md text-[14px] text-on-surface-variant leading-relaxed">
                  과거 충격 반영 자산 변동액 시뮬레이션 및 개인별 투자 성향에 맞춘 최적화된 위험 관리 제안
                </p>
                <div className="mt-auto pt-lg">
                  <div className="h-1 w-12 bg-primary/20 group-hover:w-full transition-all duration-500"></div>
                </div>
              </div>
            </div>
          </section>

          {/* Preview Section */}
          <section className="max-w-[1200px] mx-auto px-gutter mb-xl mt-32">
            <div className="relative rounded-3xl overflow-hidden bg-on-background border border-outline/20 p-xs shadow-2xl">
              <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-on-background/40 backdrop-blur-md text-center px-sm">
                <span className="material-symbols-outlined text-white text-[48px] mb-md opacity-80">lock</span>
                <h2 className="font-headline-md text-[24px] font-semibold text-white mb-sm break-keep">
                  로그인 후 맞춤형 포트폴리오 분석 리포트를 확인하실 수 있습니다
                </h2>
                <p className="font-body-md text-[14px] text-white/70 max-w-[500px] mb-lg break-keep">
                  실시간 데이터 동기화를 통해 당신의 자산이 직면한 잠재적 위험 요소를 즉시 진단합니다.
                </p>
                <Link href="/" className="bg-white text-primary px-lg py-md rounded-xl font-headline-sm font-semibold hover:bg-surface-bright transition-colors shadow-lg">
                  로그인하여 분석 시작
                </Link>
              </div>

              {/* Example Dashboard Preview (Simulated with Gradient/Cards) */}
              <div className="bg-surface-bright p-lg rounded-2xl grid grid-cols-12 gap-sm opacity-40">
                <div className="col-span-12 md:col-span-8 bg-white h-96 rounded-xl border border-outline-variant p-md">
                  <div className="flex justify-between mb-lg">
                    <div className="h-8 w-48 bg-surface-container rounded"></div>
                    <div className="h-8 w-24 bg-primary/10 rounded"></div>
                  </div>
                  <div className="space-y-sm">
                    <div className="h-4 w-full bg-surface-container rounded"></div>
                    <div className="h-4 w-5/6 bg-surface-container rounded"></div>
                    <div className="h-4 w-4/6 bg-surface-container rounded"></div>
                  </div>
                  <div className="mt-lg flex gap-sm">
                    <div className="h-32 flex-1 bg-surface-container rounded-lg"></div>
                    <div className="h-32 flex-1 bg-surface-container rounded-lg"></div>
                  </div>
                </div>
                <div className="col-span-12 md:col-span-4 flex flex-col gap-sm">
                  <div className="bg-white h-44 rounded-xl border border-outline-variant p-md">
                    <div className="h-6 w-32 bg-surface-container rounded mb-md"></div>
                    <div className="h-16 w-full bg-error-container/20 rounded"></div>
                  </div>
                  <div className="bg-white h-48 rounded-xl border border-outline-variant p-md">
                    <div className="h-6 w-32 bg-surface-container rounded mb-md"></div>
                    <div className="space-y-xs">
                      <div className="h-3 w-full bg-surface-container rounded"></div>
                      <div className="h-3 w-full bg-surface-container rounded"></div>
                      <div className="h-3 w-full bg-surface-container rounded"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
