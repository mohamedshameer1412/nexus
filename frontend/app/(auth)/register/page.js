import { AuthScreen } from "@/components/nexus/auth";

export const metadata = { title: "Create your account" };
export default function RegisterPage() {
  return <AuthScreen initial="register" />;
}
