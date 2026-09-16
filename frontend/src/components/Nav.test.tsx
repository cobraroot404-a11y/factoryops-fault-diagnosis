import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../AuthContext";
import { Nav } from "./Nav";

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "unauthenticated" }), { status: 401 })));
});

describe("Nav", () => {
  it("renders nothing before the user is authenticated", () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Nav />
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.queryByText("FactoryOps")).not.toBeInTheDocument();
  });
});
