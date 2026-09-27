import { redirect } from "next/navigation";

// The root sends everyone to the dashboard; signed-out visitors are sent on to /login by the app shell.
export default function Home() {
  redirect("/dashboard");
}
