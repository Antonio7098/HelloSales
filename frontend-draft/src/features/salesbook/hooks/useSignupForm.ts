import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useCurrentUser, type UserRole } from "@/shared/auth/useCurrentUser";
import { useAppData } from "@/shared/data/context";

export function useSignupForm() {
  const navigate = useNavigate();
  const provider = useAppData();
  const { signIn } = useCurrentUser();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [role, setRole] = useState<UserRole>("admin");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const user = await provider.signup({ name, email, companyName, role });
      signIn(user);
      navigate(user.role === "admin" ? "/onboarding" : "/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in.");
    } finally {
      setSubmitting(false);
    }
  }

  return {
    name, setName,
    email, setEmail,
    companyName, setCompanyName,
    role, setRole,
    submitting,
    error,
    handleSubmit,
  };
}
