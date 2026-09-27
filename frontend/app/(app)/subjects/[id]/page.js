import { redirect } from "next/navigation";

export default async function SubjectIndex({ params }) {
  const { id } = await params;
  redirect(`/subjects/${id}/materials`);
}
