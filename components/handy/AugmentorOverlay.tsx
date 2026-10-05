// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Orb geometry follows augmentor_linux/voice_button.py; waveform stays in Handy.
import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

type Theme = { background: string; foreground: string; accent: string; border: string; opacity: number; animated: boolean; mode: "light" | "dark" };
export function useAugmentorTheme() {
  const [theme, setTheme] = useState<Theme | null>(null);
  useEffect(() => {
    let closed = false, received = false;
    let cleanup: (() => void) | undefined;
    // Subscribe before reading: a live edit cannot disappear in the read gap.
    void listen<Theme>("augmentor-theme", e => { if (!closed) { received = true; setTheme(e.payload); } }).then(async unlisten => {
      if (closed) { unlisten(); return; } cleanup = unlisten;
      const value = await invoke<Theme | null>("overlay_theme");
      if (!closed && !received && value) setTheme(value);
    }).catch(() => undefined);
    return () => { closed = true; cleanup?.(); };
  }, []);
  useEffect(() => {
    if (!theme) return;
    const el = document.documentElement;
    el.dataset.theme = theme.mode;
    el.dataset.augmentorAnimation = String(theme.animated);
    const vars: Record<string, string> = {
      "--color-text": theme.foreground, "--color-background": theme.background,
      "--color-logo-primary": theme.accent, "--color-background-ui": theme.accent,
      "--s-surface": `color-mix(in srgb, ${theme.background} ${theme.opacity * 100}%, transparent)`,
      "--s-accent": theme.accent, "--s-muted": theme.foreground,
      "--s-faint": theme.foreground, "--s-border": theme.border,
      "--s-hair": theme.border,
    };
    for (const [key, value] of Object.entries(vars)) el.style.setProperty(key, value);
  }, [theme]);
  return theme;
}

export function AugmentorOrb({ animated, colour }: { animated: boolean; colour: string }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const el = canvas.current, ctx = el?.getContext("2d");
    if (!el || !ctx) return;
    let frame = 0, start: number | null = null, repaint = false;
    // WebKitGTK 2.54 clears transparent frames outside the animated damage.
    // Invalidate the whole overlay with an imperceptible opacity change so the
    // static pill, border and close button stay present alongside live levels.
    const linux = navigator.userAgent.includes("Linux");
    const previousOpacity = document.body.style.opacity;
    const draw = (time: number) => {
      if (start === null) start = time;
      if (linux) {
        repaint = !repaint;
        document.body.style.opacity = repaint ? "0.99999" : "1";
      }
      const phase = animated ? (time - start) / 1000 * 2 : 0;
      const ratio = window.devicePixelRatio || 1;
      el.width = Math.round(28 * ratio); el.height = Math.round(28 * ratio);
      ctx.setTransform(ratio, 0, 0, ratio, 14 * ratio, 14 * ratio);
      ctx.clearRect(-14, -14, 28, 28);
      const glow = ctx.createRadialGradient(-2, -2, 0, -2, -2, 14);
      glow.addColorStop(0, colour + "64"); glow.addColorStop(1, colour + "00");
      ctx.fillStyle = glow; ctx.beginPath(); ctx.arc(0, 0, 14, 0, Math.PI * 2); ctx.fill();
      const radius = 8.8 + (phase ? .5 * Math.sin(phase * 2) : 0);
      ctx.beginPath();
      for (let i = 0; i <= 96; i++) {
        const a = i * Math.PI * 2 / 96;
        const r = radius * (1 + .065 * Math.sin(3 * a + phase * .85) + .035 * Math.cos(2 * a - phase));
        const x = Math.cos(a) * r, y = Math.sin(a) * r;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.closePath(); ctx.fillStyle = colour + "4b"; ctx.fill();
      ctx.strokeStyle = colour; ctx.lineWidth = 1.3; ctx.stroke();
      if (animated || linux) frame = requestAnimationFrame(draw);
    };
    draw(performance.now());
    return () => { cancelAnimationFrame(frame); if (linux) document.body.style.opacity = previousOpacity; };
  }, [animated, colour]);
  return <canvas ref={canvas} className="augmentor-orb" aria-hidden="true" style={{ width: 28, height: 28 }} />;
}
