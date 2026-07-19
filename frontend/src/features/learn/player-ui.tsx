/** Shared player chrome: the parchment note card and buttons. */

import type { ReactNode } from 'react';

export function NoteCard({
  label,
  body,
  takeaway,
  cue,
}: {
  label: string;
  body: string;
  takeaway?: string;
  cue?: string;
}) {
  return (
    <div className="relative rounded-xs bg-parchment px-5 py-4 text-parchment-ink shadow-xl">
      <div className="absolute left-5 right-5 top-0 h-[3px] rounded-b-xs bg-gold" />
      <div className="mb-2 font-mono text-[13px] font-semibold text-[#8c5f22]">{label}</div>
      <div className="text-[15px] leading-relaxed whitespace-pre-line">{body}</div>
      {cue && <p className="mt-2 text-[13px] italic text-parchment-muted">{cue}</p>}
      {takeaway && (
        <div className="mt-3 border-t border-dashed border-[#c9b78d] pt-3">
          <div className="font-display text-sm font-semibold italic text-[#8c5f22]">Takeaway</div>
          <p className="mt-1 text-[15px] leading-relaxed">{takeaway}</p>
        </div>
      )}
    </div>
  );
}

export function PlayerButton({
  children,
  onClick,
  disabled,
  primary,
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  primary?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`rounded-xs px-4 py-2 text-sm transition disabled:opacity-35 ${
        primary
          ? 'bg-gold font-bold text-walnut-950 hover:bg-[#e5b458]'
          : 'border border-walnut-line bg-walnut-800 text-cream hover:border-muted hover:bg-walnut-700'
      }`}
    >
      {children}
    </button>
  );
}
