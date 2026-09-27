import { AuthScreen } from "@/components/nexus/auth";

export const metadata = { title: "Sign in" };
export default function LoginPage() {
  return <AuthScreen initial="login" />;
}
