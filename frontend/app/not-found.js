import Link from "next/link";
import { SearchX } from "lucide-react";
import { Button } from "@/components/ui/primitives";

export const metadata = { title: "Not found" };
export default function NotFound() {
  return (
    <main id="main" className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center px-4 text-center">
      <span className="grid h-12 w-12 place-items-center rounded-full bg-brand-soft text-brand-deep"><SearchX className="h-6 w-6" /></span>
      <h1 className="mt-4 font-display text-2xl font-semibold">Not found</h1>
      <p className="mt-1 text-sm text-muted">That page does not exist, or it belongs to someone else.</p>
      <Button asChild className="mt-5"><Link href="/dashboard">Go to the dashboard</Link></Button>
    </main>
  );
}
