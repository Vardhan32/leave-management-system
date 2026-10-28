import { CheckCircle2, Info, TriangleAlert } from "lucide-react";

const ICONS = {
  success: CheckCircle2,
  error: TriangleAlert,
  info: Info,
  warning: TriangleAlert,
};

export default function InlineAlert({ tone = "info", children }) {
  const Icon = ICONS[tone] || Info;
  return (
    <div className={`inline-alert inline-alert--${tone}`} role="status">
      <Icon size={17} />
      <div>{children}</div>
    </div>
  );
}
