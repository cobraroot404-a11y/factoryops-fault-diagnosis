import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { AuthProvider } from "../AuthContext";
import { LoginPage } from "./LoginPage";

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (String(url).includes("/auth/me")) {
        return new Response(JSON.stringify({ detail: "unauthenticated" }), { status: 401 });
      }
      throw new Error("unexpected fetch in test: " + url);
    }),
  );
});

function renderLogin() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  it("renders the sign-in form with accessible labels", async () => {
    renderLogin();
    expect(await screen.findByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("shows a validation error when submitted without a password", async () => {
    renderLogin();
    const email = await screen.findByLabelText(/email/i);
    fireEvent.change(email, { target: { value: "tech@example.com" } });
    const form = screen.getByRole("form", { name: /sign in/i });
    fireEvent.submit(form);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/required/i));
  });
});
