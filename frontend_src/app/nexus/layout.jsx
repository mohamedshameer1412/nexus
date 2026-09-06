import NexusNav from "@/components/nexus/NexusNav";

export const metadata = {
  title: "NEXUS — Agentic Learner Intelligence OS",
  description: "Your personal AI learning intelligence system",
};

export default function NexusLayout({ children }) {
  return (
    <div className="nexus-layout">
      <NexusNav />
      <main className="nexus-main">{children}</main>
    </div>
  );
}
