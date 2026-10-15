import { Crown } from "lucide-react";

export default function TossLogo({ large = false }: { large?: boolean }) {
  return (
    <span
      className={`toss-logo ${large ? "toss-logo-large" : ""}`}
      aria-label="TOSS · Get caught in the flavour"
    >
      <Crown aria-hidden="true" className="toss-crown" strokeWidth={1.7} />
      <span className="toss-wordmark">
        TOSS<span className="toss-period">.</span>
      </span>
      <small>GET CAUGHT IN THE FLAVOUR</small>
    </span>
  );
}
