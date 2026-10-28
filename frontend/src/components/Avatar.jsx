import { initials } from "../utils/format";

const TONES = ["coral", "sage", "gold", "sky", "plum", "ink"];

function toneFor(name) {
  const total = (name || "")
    .split("")
    .reduce((sum, character) => sum + character.charCodeAt(0), 0);
  return TONES[total % TONES.length];
}

export default function Avatar({ name, size = "md", className = "" }) {
  return (
    <span
      className={`avatar avatar--${size} avatar--${toneFor(name)} ${className}`.trim()}
      aria-hidden="true"
      title={name}
    >
      {initials(name)}
    </span>
  );
}
