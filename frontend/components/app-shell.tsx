"use client";

import {
  Bot,
  Database,
  FlaskConical,
  MessageSquareText,
  Workflow,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import { api } from "@/lib/api";

const navigation = [
  { href: "/", label: "Ask", icon: MessageSquareText },
  { href: "/knowledge", label: "Knowledge", icon: Database },
  { href: "/workspace", label: "Workspace", icon: Workflow },
  { href: "/evaluations", label: "Evaluations", icon: FlaskConical },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const current =
    navigation.find((item) =>
      item.href === "/" ? pathname === "/" : pathname.startsWith(item.href),
    ) || navigation[0];

  useEffect(() => {
    api<{ status: string }>("/health")
      .then(() => setHealthy(true))
      .catch(() => setHealthy(false));
  }, [pathname]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">
            <Bot size={18} />
          </span>
          <span>
            <strong>Ask Runtime</strong>
            <small>Enterprise AI</small>
          </span>
        </div>
        <nav className="side-nav" aria-label="主导航">
          {navigation.map((item) => {
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                href={item.href}
                key={item.href}
                className={active ? "nav-link active" : "nav-link"}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <span className={`health-dot ${healthy ? "ok" : ""}`} />
          {healthy === null
            ? "正在连接后端"
            : healthy
              ? "服务运行正常"
              : "后端未连接"}
        </div>
      </aside>

      <div className="page-frame">
        <header className="topbar">
          <div>
            <h1>{current.label}</h1>
            <p>RAG + Agent 企业知识工作台</p>
          </div>
          <span className="environment-badge">LOCAL</span>
        </header>
        <main className="page-content">{children}</main>
      </div>

      <nav className="mobile-nav" aria-label="移动端导航">
        {navigation.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              href={item.href}
              key={item.href}
              className={active ? "active" : ""}
              aria-label={item.label}
            >
              <Icon size={20} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
