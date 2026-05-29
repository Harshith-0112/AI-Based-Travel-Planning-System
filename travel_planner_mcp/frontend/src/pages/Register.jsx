import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { registerUser } from "../api/authApi";
import Alert from "../components/Alert";

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    try {
      await registerUser(form);
      setMessage("Account created. Redirecting to login...");
      setTimeout(() => navigate("/login"), 700);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center px-4 py-10">
      <section className="glass-card w-full max-w-md p-8">
        <p className="text-sm font-black uppercase tracking-[0.22em] text-teal-200">Start planning</p>
        <h1 className="mt-3 text-4xl font-black text-white">Create your travel workspace.</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          Save AI-generated routes, hotels, budgets, and day-wise plans.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <Alert type="error">{error}</Alert>
          <Alert type="success">{message}</Alert>
          <input
            className="input-field"
            placeholder="Full name"
            value={form.full_name}
            onChange={(event) => setForm({ ...form, full_name: event.target.value })}
            required
          />
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
            {loading ? "Creating account..." : "Register"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-400">
          Already have an account?{" "}
          <Link to="/login" className="font-bold text-teal-200 hover:text-teal-100">
            Login
          </Link>
        </p>
      </section>
    </main>
  );
}
