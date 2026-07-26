/** Shantranj icon set — one coherent, engraved 1.5px-stroke inline-SVG family.
 *  Replaces the Unicode glyph grab-bag. No CDN, CSP-safe. New file: additive,
 *  does not reshuffle the existing module graph. */

interface IconProps {
  size?: number;
  strokeWidth?: number;
  className?: string;
}

function make(d: string) {
  return function Icon({ size = 18, strokeWidth = 1.5, className }: IconProps) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        className={className}
        aria-hidden="true"
      >
        <path d={d} />
      </svg>
    );
  };
}

/* nav */
export const PathIcon = make(
  'M5 20c5.5 0 4-8 7-8s1.5-8 6.5-8 M17 4a1.6 1.6 0 1 0 3.2 0a1.6 1.6 0 1 0 -3.2 0',
);
export const PlayIcon = make(
  'M5 5l12 12 M19 5L7 17 M15 17l2.5 2.5 M9 17l-2.5 2.5 M17 14.5L19.5 17 M7 14.5L4.5 17',
);
export const DuelIcon = make('M13 3L6 13.5h5L9 21l9-10.5h-5L15 3z');
export const FriendsIcon = make(
  'M9 11a3 3 0 1 0 0-6a3 3 0 0 0 0 6 M3.5 20c0-3 2.3-5 5.5-5s5.5 2 5.5 5 M15.5 5.4a3 3 0 0 1 0 5.2 M17 15.3c2.1.7 3.5 2.3 3.5 4.7',
);
export const RanksIcon = make('M4 20h16 M6 20V11 M12 20V5 M18 20V8.5');
export const ProfileIcon = make(
  'M12 12a4 4 0 1 0 0-8a4 4 0 0 0 0 8 M5 20c0-3.5 3-5.5 7-5.5s7 2 7 5.5',
);
export const RosetteIcon = make(
  'M12 14a5 5 0 1 0 0-10a5 5 0 0 0 0 10 M9.6 13.4L7.5 21l4.5-2.4L16.5 21l-2.1-7.6',
);
export const ArchiveIcon = make('M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z M19 15H6 M8 3v12');
export const SettingsIcon = make(
  'M12 15a3 3 0 1 0 0-6a3 3 0 0 0 0 6 M12 2.8v2.7 M12 18.5v2.7 M2.8 12h2.7 M18.5 12h2.7 M5.5 5.5l1.9 1.9 M16.6 16.6l1.9 1.9 M18.5 5.5l-1.9 1.9 M7.4 16.6l-1.9 1.9',
);
export const QuillIcon = make(
  'M19 4c-6 0-11 4-13 11l-1 5 5-1c7-2 11-7 11-13z M5 19L15 9',
);

/* content & states */
export const LessonIcon = make(
  'M12 6c-1.8-1.4-4.6-1.4-6.5 0v12c1.9-1.4 4.7-1.4 6.5 0c1.8-1.4 4.6-1.4 6.5 0V6c-1.9-1.4-4.7-1.4-6.5 0 M12 6v12',
);
export const DrillIcon = make('M5 5l12 12 M19 5L7 17');
export const CrownIcon = make(
  'M4.5 17.5h15 M5.5 15L4.5 7.5 9.5 11 12 5.5 14.5 11 19.5 7.5 18.5 15z',
);
export const LockIcon = make('M7.5 11V8.5a4.5 4.5 0 0 1 9 0V11 M6 11h12v8.5H6z');
export const CheckIcon = make('M5 13l4 4L19 7');
export const FlameIcon = make(
  'M12 4c2 3-3.5 5-3.5 9a3.5 3.5 0 0 0 7 0c0-2-1.2-3.2-1.2-4.5 1.8 1 2.7 3 2.7 4.5',
);
export const BoltIcon = DuelIcon;
export const TakebackIcon = make('M8 5L3 10l5 5 M3 10h11a6 6 0 0 1 0 12h-4');
export const SearchIcon = make('M11 18a7 7 0 1 0 0-14a7 7 0 0 0 0 14 M16 16l5 5');
