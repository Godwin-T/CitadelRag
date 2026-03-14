import { useState } from "react";
import { apiFetch } from "../lib/api";

export type AuthMode = "login" | "signup";

type Props = {
  mode: AuthMode;
  onAuthSuccess: () => void;
};

export default function AuthForm({ mode, onAuthSuccess }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const isSignup = mode === "signup";

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const payload = isSignup ? { email, password, name } : { email, password };
      const data = await apiFetch(isSignup ? "/auth/register" : "/auth/login", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      if (data?.access_token) {
        localStorage.setItem("access_token", data.access_token);
        onAuthSuccess();
      } else {
        setError("Authentication failed.");
      }
    } catch (err: any) {
      setError(err?.message || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {isSignup && (
        <input
          className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      )}
      <input
        className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
        placeholder={isSignup ? "Email" : "Email or username"}
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <input
        className="w-full p-3 rounded-xl border border-[color:var(--border)] bg-transparent"
        placeholder="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      {error && <div className="text-sm text-red-500">{error}</div>}
      <button
        type="submit"
        disabled={loading}
        className="w-full px-6 py-2 rounded-xl bg-[color:var(--accent-strong)] text-white"
      >
        {loading ? "Please wait..." : isSignup ? "Sign Up" : "Log In"}
      </button>
    </form>
  );
}
