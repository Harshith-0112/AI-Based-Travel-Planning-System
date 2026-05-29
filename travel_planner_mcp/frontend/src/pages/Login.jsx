import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Alert from "../components/Alert";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(form.email, form.password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center px-4 py-10">
      <section className="glass-card w-full max-w-md p-8">
        <p className="text-sm font-black uppercase tracking-[0.22em] text-teal-200">Welcome back</p>
        <h1 className="mt-3 text-4xl font-black text-white">Sign in to plan smarter trips.</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          Access saved itineraries, hotel choices, and AI-assisted planning from your workspace.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <Alert type="error">{error}</Alert>
          <input
            className="input-field"
            type="email"
            placeholder="Email"
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
            required
          />
          <input
            className="input-field"
            type="password"
            placeholder="Password"
            value={form.password}
            onChange={(event) => setForm({ ...form, password: event.target.value })}
            required
          />
          <button className="primary-button w-full" disabled={loading}>
            {loading ? "Signing in..." : "Login"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-400">
          New here?{" "}
          <Link to="/register" className="font-bold text-teal-200 hover:text-teal-100">
            Create an account
          </Link>
        </p>
      </section>
    </main>
  );
}
